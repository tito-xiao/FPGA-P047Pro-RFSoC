"""PYNQ DMA adapter, explicitly gated on a verified user-supplied profile.

No factory bitstream is assumed to provide an MM2S channel. No bitstream is
downloaded here. Caller must load/clock the approved overlay and confirm the
actual RFDC packing, rate conversion, gain, routing, and loopback first.
"""
import time
import numpy as np


def validate_profile(profile):
    required=['bitstream_sha256','stream_rate_hz','tx_dma','rx_dma','tx_dma_max_bytes',
              'rx_dma_max_bytes','capture_samples','replay_samples','format','verified_by','verified_at']
    if profile.get('board_verified') is not True or any(profile.get(k) in [None,''] for k in required):
        raise ValueError('No verified board profile: do not run RF transfer with the factory OFDM overlay')
    if profile['format']!='int16_le_interleaved_iq' or profile['stream_rate_hz']<=0:
        raise ValueError('Unsupported stream format or rate')
    if profile.get('capture_generates_tlast') is not True:
        raise ValueError('Capture TLAST must be implemented and verified before S2MM transfer')
    if profile.get('replay_mode') != 'load_then_start':
        raise ValueError('This adapter requires a load-then-start replay memory')
    if not profile.get('arm_capture_writes') or not profile.get('start_replay_writes'):
        raise ValueError('Verified capture and replay register sequences are required')
    if len(profile['bitstream_sha256']) != 64:
        raise ValueError('Expected a SHA-256 bitstream identity')


def inspect_overlay(overlay):
    report=[]
    for name,info in overlay.ip_dict.items():
        if 'axi_dma' in info.get('type',''):
            params=info.get('parameters',{})
            report.append(dict(name=name,mm2s=params.get('c_include_mm2s',params.get('C_INCLUDE_MM2S')),
                               s2mm=params.get('c_include_s2mm',params.get('C_INCLUDE_S2MM'))))
    return report


def _resolve(overlay,name):
    target=overlay
    for component in name.split('/'):
        target=getattr(target,component)
    return target


def _writes(overlay,items):
    for item in items:
        _resolve(overlay,item['ip']).write(int(item['offset']),int(item['value']))


def dma_capture(overlay,tx_words,profile,waveform_rate_hz,loaded_bitstream_sha256,timeout=10):
    validate_profile(profile)
    if profile['bitstream_sha256']!=loaded_bitstream_sha256:
        raise ValueError('Loaded bitstream identity is not the verified profile bitstream')
    if not np.isclose(profile['stream_rate_hz'],waveform_rate_hz,rtol=1e-9,atol=0):
        raise ValueError('I/Q sample rate and verified hardware stream rate differ')
    tx_words=np.asarray(tx_words)
    if tx_words.dtype.kind!='i' or tx_words.dtype.itemsize!=2 or tx_words.ndim!=2 or tx_words.shape[1]!=2:
        raise ValueError('tx_words must be int16 [samples, I/Q]')
    count=int(profile['capture_samples'])
    if timeout <= 0 or count<=0 or len(tx_words)!=profile['replay_samples'] or tx_words.nbytes>profile['tx_dma_max_bytes'] or count*4>profile['rx_dma_max_bytes']:
        raise ValueError('DMA length exceeds verified profile limits')
    tx_dma,rx_dma=_resolve(overlay,profile['tx_dma']),_resolve(overlay,profile['rx_dma'])
    if not hasattr(tx_dma,'sendchannel') or not hasattr(rx_dma,'recvchannel'):
        raise ValueError('Required MM2S/S2MM channel is missing')
    from pynq import allocate
    tx=rx=None
    completed=False
    try:
        tx=allocate(shape=tx_words.shape,dtype=np.int16)
        rx=allocate(shape=(count,2),dtype=np.int16)
        tx[:]=tx_words
        # Receiver must be ready before enabling the waveform source.
        rx_dma.recvchannel.transfer(rx)
        tx_dma.sendchannel.transfer(tx)
        deadline=time.monotonic()+timeout
        def poll(channel, dma, status_offset):
            while True:
                if dma.read(status_offset)&0x770:
                    raise RuntimeError('DMA error status; transfer aborted')
                if channel.idle:
                    return
                if time.monotonic()>deadline:
                    raise TimeoutError('DMA timeout: check trigger, TLAST, rate and stream mapping')
                time.sleep(0.001)
        # Loading BRAM must finish BEFORE the replay start pulse. A start pulse
        # during LOAD is intentionally ignored by axis_iq_replay.
        poll(tx_dma.sendchannel,tx_dma,0x04)
        tx_dma.sendchannel.wait()
        _writes(overlay,profile.get('arm_capture_writes',[]))
        _writes(overlay,profile.get('start_replay_writes',[]))
        poll(rx_dma.recvchannel,rx_dma,0x34)
        # wait() synchronizes CPU caches and completes PYNQ transfer bookkeeping.
        rx_dma.recvchannel.wait()
        completed=True
        return np.array(rx,copy=True)
    finally:
        try:
            _writes(overlay,profile.get('stop_writes',[]))
        finally:
            try:
                if not completed:
                    try:
                        tx_dma.sendchannel.stop()
                    finally:
                        rx_dma.recvchannel.stop()
            finally:
                try:
                    if tx is not None: tx.freebuffer()
                finally:
                    if rx is not None: rx.freebuffer()

