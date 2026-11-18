"""Reproducible stages. All automatic captures here are explicitly simulated."""
import json
import time
from pathlib import Path
import numpy as np
from .core import (Config, qpsk, decisions, idaft, daft, add_cpp, physical_channel,
                   effective_matrix, detect, nmse, paths_json)
from .estimation import estimate_paths
from .link import build_frame, training, decode_capture, report_frame, capacity
from .simulation import capture
from .iqio import write_iq, read_iq
from .fixedpoint import export_vectors, quantize, dequantize, apply_matrix, matrix_coefficients

SCENARIOS = {
    'static': [(0,0.,.85+0j),(2,0.,.4+.15j),(5,0.,.14-.15j)],
    'integer': [(0,0.,.85+0j),(2,1.,.4+.15j),(5,-2.,.14-.15j)],
    'fractional_offgrid': [(0,.27,.85+0j),(2,1.43,.4+.15j),(5,-1.68,.14-.15j)]}


def save_json(path, value):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)


def fresh(directory):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    return directory


def _summary(directory, result):
    save_json(directory/'summary.json',result)
    return result


def channel_estimation(directory, cfg=None):
    """Truth is used by the evaluator only; not passed to the estimator."""
    cfg=cfg or Config();directory=fresh(directory)
    rng=np.random.default_rng(cfg.seed+5)
    pilot=training(cfg)
    bits=rng.integers(0,2,(cfg.data_blocks,cfg.n,2),dtype=np.uint8)
    payload=add_cpp(idaft(qpsk(bits),cfg.c1,cfg.c2),cfg).reshape(-1)
    wave=np.concatenate([pilot,payload])
    rows=[]
    for name,paths in SCENARIOS.items():
        for snr in [None,25.]:
            y=physical_channel(wave,paths,cfg.n)
            variance=0. if snr is None else float(np.mean(np.abs(wave)**2)*10**(-snr/10))
            y+=np.sqrt(variance/2)*(rng.standard_normal(y.size)+1j*rng.standard_normal(y.size))
            estimate=estimate_paths(pilot,y[:pilot.size],cfg)
            got=[];oracle=[];matrix_errors=[]
            for block in range(cfg.data_blocks):
                start=pilot.size+block*cfg.block_length+cfg.prefix
                symbol=daft(y[start:start+cfg.n],cfg.c1,cfg.c2)
                H=effective_matrix(cfg,estimate['paths'],start)
                truth=effective_matrix(cfg,paths,start)
                matrix_errors.append(nmse(H,truth))
                got.append(decisions(detect(symbol,H,max(estimate['residual_power'],1e-12))))
                oracle.append(decisions(detect(symbol,truth,variance)))
            errors=int(np.count_nonzero(np.stack(got)!=bits))
            reference_errors=int(np.count_nonzero(np.stack(oracle)!=bits))
            error=float(np.mean(matrix_errors))
            passed=errors==0 and error<(1e-10 if snr is None else .02)
            rows.append(dict(scenario=name,snr_db=snr,bit_errors=errors,bits=int(bits.size),
                oracle_bit_errors=reference_errors,channel_nmse=error,
                estimated_paths=paths_json(estimate['paths']),pass_check=passed))
    np.save(directory/'known_training.npy',pilot)
    return _summary(directory,dict(stage='05 channel estimation',scope='SOFTWARE ONLY',
        config=cfg.to_dict(),method='Separate training; unique integer delays; sparse search + continuous Doppler LS',
        checks_passed=sum(r['pass_check'] for r in rows),checks_total=len(rows),
        passed=all(r['pass_check'] for r in rows),cases=rows))


def framed_link(directory,cfg=None):
    cfg=cfg or Config();directory=fresh(directory)
    rows=[]
    for index,(name,paths) in enumerate(SCENARIOS.items()):
        for snr in [None,25.]:
            message=('P047Pro AFDM 消息校验 / '+name).encode('utf-8')
            wave,bits=build_frame(message,100+index,cfg)
            y,truth=capture(wave,cfg,paths,snr,offset=47+index*19,cfo_bins=.17-index*.11,seed=cfg.seed+index)
            result=decode_capture(y,cfg)
            frames=result['frames']
            ok=len(frames)==1 and frames[0]['payload']==message and frames[0]['sequence']==100+index
            errors=int(np.count_nonzero(frames[0]['bits']!=bits)) if ok else None
            rows.append(dict(scenario=name,snr_db=snr,passed=ok and errors==0,
                bit_errors=errors,bits=int(bits.size),crc_accepted=len(frames),truth=truth,
                received=[report_frame(f) for f in frames],rejected=result['rejected']))
    return _summary(directory,dict(stage='06 framing / acquisition / CRC',scope='SOFTWARE ONLY',
        config=cfg.to_dict(),payload_capacity_bytes=capacity(cfg),
        checks_passed=sum(r['passed'] for r in rows),checks_total=len(rows),
        passed=all(r['passed'] for r in rows),cases=rows))


def waveform_export(directory,cfg=None,frames=3):
    cfg=cfg or Config();directory=fresh(directory)
    parts=[];reference=[]
    for sequence in range(frames):
        message=('P047Pro AFDM replay frame %d / 数据校验'%sequence).encode('utf-8')
        wave,_=build_frame(message,sequence,cfg)
        parts.extend([wave,np.zeros(cfg.n)])
        reference.append(dict(sequence=sequence,payload_hex=message.hex()))
    signal=np.concatenate(parts)
    metadata=write_iq(directory/'tx.iq16',signal,cfg,extra=dict(
        note='Generated on CPU; not sent to DAC',frames=frames))
    save_json(directory/'payload_reference.json',reference)
    save_json(directory/'receiver_config.json',cfg.to_dict())
    return _summary(directory,dict(stage='07 arbitrary I/Q export',scope='FILE ONLY; NO RF',
        passed=True,samples=len(signal),frames=frames,sample_rate_hz=cfg.sample_rate_hz,
        metadata=metadata,note='Rate is a protocol setting; actual RFDC stream rate is not known.'))


def decode_file(path,directory,config=None,reference=None):
    """Use metadata/protocol settings, never transmitter bits, for decoding."""
    directory=fresh(directory)
    raw,meta=read_iq(path,config)
    cfg=config or Config(**meta['config'])
    decoded=decode_capture(raw,cfg)
    frames=decoded['frames']
    report=dict(stage='08 capture import / offline receiver',capture_kind=meta.get('kind','unknown'),
        source=str(Path(path).resolve()),samples=len(raw),
        received=[report_frame(f) for f in frames],rejected=decoded['rejected'],
        crc_accepted=len(frames),config=cfg.to_dict(),reference_checked=False)
    if reference is not None:
        report['reference_checked']=True
        expected={(int(r['sequence']),r['payload_hex']) for r in reference}
        got=[(f['sequence'],f['payload'].hex()) for f in frames]
        # Count each expected sequence once; duplicates are reported separately.
        valid=set(got)&expected
        unexpected=[dict(sequence=s,payload_hex=p) for s,p in got if (s,p) not in expected]
        report.update(expected_frames=len(expected),matched_frames=len(valid),
            packet_error_rate=1-len(valid)/max(len(expected),1),
            duplicate_frames=len(got)-len(set(got)),unexpected_frames=unexpected,
            passed=valid==expected and not unexpected and len(got)==len(expected))
    # A CRC accepted frame alone does not establish an expected-packet PER.
    save_json(directory/'decoded_payloads.json',[
        dict(sequence=f['sequence'],payload_hex=f['payload'].hex()) for f in frames])
    return _summary(directory,report)


def replay_file_loopback(directory,cfg=None):
    cfg=cfg or Config();directory=fresh(directory)
    waveform_export(directory/'tx',cfg)
    tx,_=read_iq(directory/'tx/tx.iq16',cfg)
    # This file is explicitly tagged simulated_capture, even on the board CPU.
    rx,truth=capture(tx,cfg,SCENARIOS['fractional_offgrid'],25.,offset=91,cfo_bins=.13,seed=cfg.seed)
    write_iq(directory/'simulated_rx.iq16',rx,cfg,kind='simulated_capture',extra=truth)
    reference=json.loads((directory/'tx/payload_reference.json').read_text(encoding='utf-8'))
    report=decode_file(directory/'simulated_rx.iq16',directory/'offline_decode',cfg,reference)
    return _summary(directory,dict(stage='08 file roundtrip',scope='SIMULATED, NOT RF',
        passed=report['passed'],frames=report['crc_accepted'],packet_error_rate=report['packet_error_rate'],
        rf_status='NOT_RUN: verified replay/capture overlay and measured rate/mapping required'))


def fixedpoint(directory,cfg=None):
    cfg=cfg or Config();directory=fresh(directory)
    result=export_vectors(directory,cfg)
    # Quantization accuracy and sign decisions are evaluated independently of RTL.
    rng=np.random.default_rng(cfg.seed+9)
    bits=rng.integers(0,2,(32,cfg.n,2))
    original=qpsk(bits)*.2
    words,input_clipped=quantize(original)
    tx,tx_clipped=apply_matrix(words,matrix_coefficients(cfg,True))
    rx,rx_clipped=apply_matrix(tx,matrix_coefficients(cfg,False))
    errors=int(np.count_nonzero(decisions(dequantize(rx))!=bits))
    result.update(stage='09 fixed-point / RTL vectors',scope='PYTHON FIXED POINT; RTL RUN SEPARATELY',
        config=cfg.to_dict(),bit_errors=errors,bits=int(bits.size),
        input_clipped=input_clipped,stress_tx_clipped=tx_clipped,stress_rx_clipped=rx_clipped,
        passed=errors==0 and input_clipped==tx_clipped==rx_clipped==0,
        rtl_status='NOT_RUN by Python; execute hardware/run_xsim.ps1',
        synthesis_status='NOT_RUN by Python; requires licensed Vivado target device',
        timing_closed=False,board_programmed=False)
    return _summary(directory,result)


def stability(directory,cfg=None,frames=24):
    if frames<1: raise ValueError('frames must be positive')
    cfg=cfg or Config();directory=fresh(directory)
    rng=np.random.default_rng(cfg.seed+10)
    rows=[];start=time.monotonic()
    for i in range(frames):
        # Disjoint integer delays, fixed gains per frame, off-grid Dopplers.
        nus=rng.uniform(-1.5,1.5,3)
        gains=[.85*np.exp(1j*rng.uniform(-.5,.5)),(.30+.1j)*np.exp(1j*rng.uniform(-1,1)),(.12-.1j)*np.exp(1j*rng.uniform(-1,1))]
        paths=list(zip([0,2,5],nus,gains))
        message=('AFDM stability %04d / 随机种子%d'%(i,cfg.seed)).encode('utf-8')
        wave,bits=build_frame(message,i,cfg)
        y,truth=capture(wave,cfg,paths,28.,offset=int(rng.integers(25,160)),
            cfo_bins=float(rng.uniform(-.3,.3)),seed=cfg.seed+i+100)
        decoded=decode_capture(y,cfg)
        accepted=[f for f in decoded['frames'] if f['sequence']==i and f['payload']==message]
        good=len(accepted)==1 and len(decoded['frames'])==1
        errors=int(np.count_nonzero(accepted[0]['bits']!=bits)) if good else None
        rows.append(dict(sequence=i,crc_and_payload_ok=good,bit_errors=errors,
            bits=int(bits.size),truth=truth))
    delivered=sum(r['crc_and_payload_ok'] for r in rows)
    delivered_bits=sum(r['bits'] for r in rows if r['crc_and_payload_ok'])
    bit_errors=sum(r['bit_errors'] for r in rows if r['bit_errors'] is not None)
    return _summary(directory,dict(stage='10 seeded software stability',scope='SOFTWARE ONLY; NOT hardware uptime',
        config=cfg.to_dict(),frames_sent=frames,frames_delivered=delivered,
        packet_error_rate=(frames-delivered)/frames,bit_errors_on_delivered_frames=bit_errors,
        delivered_bits=delivered_bits,ber_on_delivered_frames=bit_errors/max(delivered_bits,1),
        elapsed_seconds=time.monotonic()-start,passed=delivered==frames and bit_errors==0,cases=rows))


def suite(directory,cfg=None,frames=24):
    cfg=cfg or Config();directory=fresh(directory)
    stages={}
    functions=[('05_estimation',channel_estimation),('06_frames',framed_link),
        ('07_waveform',waveform_export),('08_offline',replay_file_loopback),('09_fixedpoint',fixedpoint)]
    for name,function in functions:
        print('Running '+name,flush=True)
        stages[name]=function(directory/name,cfg)
    print('Running 10_stability',flush=True)
    stages['10_stability']=stability(directory/'10_stability',cfg,frames)
    return _summary(directory,dict(scope='SOFTWARE / FILE / FIXED-POINT ONLY',
        software_passed=all(r['passed'] for r in stages.values()),
        rf_measured=False,fpga_realtime_validated=False,stages=stages,
        remaining=['Verified MM2S replay / S2MM capture overlay and RFDC clock/packing/rate integration',
          'Licensed xczu47dr synthesis, implementation, constraints, timing and bitstream build',
          'TX4 to RX2 actual I/Q capture, CRC/PER/BER and repeated initialization',
          'High-throughput FFT-based AFDM, PL synchronization/channel estimation/detection, hardware stability']))
