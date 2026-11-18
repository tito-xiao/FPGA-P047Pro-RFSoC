"""Framed AFDM receiver using only received samples and protocol constants.

Known separate training (not embedded pilot) estimates unknown channel paths.
Acquisition supports integer sample timing and a dominant-path coarse frequency
rotation. A common oscillator CFO cannot be separated from a common path
Doppler without an external reference; the residual paths absorb that ambiguity.
Fractional sample timing, clock drift, FEC and time-varying path gains are outside
this initial receiver's verified operating envelope.
"""
import struct
import zlib
import numpy as np
from .core import Config, qpsk, decisions, idaft, daft, add_cpp, effective_matrix, detect, paths_json
from .estimation import estimate_paths

HEADER = struct.Struct('>4sBIH')
MAGIC = b'AFD1'
VERSION = 1


def capacity(cfg):
    return cfg.data_blocks*cfg.n*2//8-HEADER.size-4


def pack_payload(payload, sequence, cfg):
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
    payload = bytes(payload)
    if len(payload) > capacity(cfg) or not 0 <= sequence <= 0xffffffff:
        raise ValueError('Payload or sequence exceeds frame capacity')
    body = HEADER.pack(MAGIC, VERSION, sequence, len(payload))+payload
    packet = body+struct.pack('>I', zlib.crc32(body)&0xffffffff)
    count = cfg.data_blocks*cfg.n*2//8
    rng = np.random.default_rng(cfg.seed+sequence)
    packet += rng.integers(0,256,count-len(packet),dtype=np.uint8).tobytes()
    return np.unpackbits(np.frombuffer(packet,dtype=np.uint8)).reshape(cfg.data_blocks,cfg.n,2)


def unpack_payload(bits, cfg):
    raw = np.packbits(np.asarray(bits,dtype=np.uint8).reshape(-1)).tobytes()
    if len(raw) < HEADER.size+4:
        raise ValueError('Short packet')
    magic,version,sequence,length = HEADER.unpack(raw[:HEADER.size])
    if magic != MAGIC or version != VERSION or length > capacity(cfg):
        raise ValueError('Header validation failed')
    end = HEADER.size+length
    expected = struct.unpack('>I',raw[end:end+4])[0]
    if expected != zlib.crc32(raw[:end])&0xffffffff:
        raise ValueError('CRC32 failed')
    return sequence,raw[HEADER.size:end]


def preamble(cfg):
    rng = np.random.default_rng(cfg.seed)
    a = qpsk(rng.integers(0,2,(cfg.n,2)))
    delimiter = qpsk(rng.integers(0,2,(cfg.n,2)))
    return np.concatenate([a,a,delimiter])


def training(cfg):
    rng = np.random.default_rng(cfg.seed+1)
    x = qpsk(rng.integers(0,2,(cfg.training_blocks,cfg.n,2)))
    return add_cpp(idaft(x,cfg.c1,cfg.c2),cfg).reshape(-1)


def frame_length(cfg):
    return 3*cfg.n+(cfg.training_blocks+cfg.data_blocks)*cfg.block_length+cfg.prefix


def build_frame(payload, sequence=0, cfg=None):
    cfg = cfg or Config()
    bits = pack_payload(payload,sequence,cfg)
    data = add_cpp(idaft(qpsk(bits),cfg.c1,cfg.c2),cfg).reshape(-1)
    wave = np.concatenate([preamble(cfg),training(cfg),data,np.zeros(cfg.prefix)])
    assert wave.size == frame_length(cfg)
    return wave,bits


def sync_candidates(samples, cfg, threshold=0.35, max_candidates=64):
    x = np.asarray(samples,dtype=np.complex128)
    ref = preamble(cfg)
    if x.ndim != 1 or x.size < frame_length(cfg) or not np.all(np.isfinite(x)):
        raise ValueError('Capture is short, nonfinite, or not one-dimensional')
    power = np.concatenate([[0.],np.cumsum(np.abs(x)**2)])
    windows = power[ref.size:]-power[:-ref.size]
    denominator = np.maximum(np.vdot(ref,ref).real*windows,1e-20)
    scores = np.zeros(windows.size)
    freqs = np.zeros(windows.size)
    grid = np.arange(-cfg.nu_bound,cfg.nu_bound+0.125,0.25)
    for freq in grid:
        template = ref*np.exp(2j*np.pi*freq*np.arange(ref.size)/cfg.n)
        score = np.abs(np.correlate(x,template,mode='valid'))**2/denominator
        better = score > scores
        freqs[better] = freq
        scores[better] = score[better]
    order = np.argsort(scores)[::-1]
    selected=[]
    for index in order:
        if scores[index] < threshold or len(selected)>=max_candidates:
            break
        index=int(index)
        if index+frame_length(cfg)>x.size:
            continue
        if any(abs(index-p['offset']) < ref.size for p in selected):
            continue
        selected.append(dict(offset=index,score=float(scores[index]),frequency_bins=float(freqs[index])))
    return sorted(selected,key=lambda p:p['offset'])


def decode_frame(samples, candidate, cfg):
    start = candidate['offset']
    frame = np.asarray(samples[start:start+frame_length(cfg)],dtype=np.complex128)
    if len(frame) != frame_length(cfg):
        raise ValueError('Incomplete frame')
    t = np.arange(frame.size)
    coarse = candidate['frequency_bins']
    first = frame*np.exp(-2j*np.pi*coarse*t/cfg.n)
    # Drop the delay transient before correlating the repeated preamble halves.
    a = first[cfg.max_delay:cfg.n]
    b = first[cfg.n+cfg.max_delay:2*cfg.n]
    fine = float(np.angle(np.vdot(a,b))/(2*np.pi))
    frequency = coarse+fine
    corrected = frame*np.exp(-2j*np.pi*frequency*t/cfg.n)
    pilot_start = 3*cfg.n
    known = training(cfg)
    estimate = estimate_paths(known,corrected[pilot_start:pilot_start+known.size],cfg,time_start=pilot_start)
    paths = estimate['paths']
    data_start = pilot_start+known.size
    blocks=[]
    estimates=[]
    variance=max(estimate['residual_power'],1e-12)
    for i in range(cfg.data_blocks):
        useful_start=data_start+i*cfg.block_length+cfg.prefix
        wave=corrected[useful_start:useful_start+cfg.n]
        H=effective_matrix(cfg,paths,time_start=useful_start)
        symbols=detect(daft(wave,cfg.c1,cfg.c2),H,variance)
        estimates.append(symbols)
        blocks.append(decisions(symbols))
    bits=np.stack(blocks)
    sequence,payload=unpack_payload(bits,cfg)
    return dict(sequence=sequence,payload=payload,bits=bits,symbols=np.stack(estimates),
                offset=start,sync_score=candidate['score'],coarse_frequency_bins=frequency,
                paths=paths_json(paths),training_relative_residual=estimate['relative_residual'],
                noise_variance_estimate=variance,crc_ok=True)


def decode_capture(samples, cfg=None):
    cfg=cfg or Config()
    frames=[]
    rejected=[]
    for candidate in sync_candidates(samples,cfg):
        try:
            frames.append(decode_frame(samples,candidate,cfg))
        except (ValueError,np.linalg.LinAlgError) as error:
            rejected.append(dict(offset=candidate['offset'],reason=str(error)))
    return dict(frames=frames,rejected=rejected,candidate_count=len(frames)+len(rejected))


def report_frame(frame):
    return {k:(v.decode('utf-8',errors='replace') if k=='payload' else v)
            for k,v in frame.items() if k not in ['bits','symbols']}

