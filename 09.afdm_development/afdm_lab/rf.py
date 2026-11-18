"""Optional board entry point. Never called by the automatic software suite."""
from pathlib import Path
import numpy as np
from .board import validate_profile, dma_capture
from .core import Config
from .iqio import read_iq, sha256
from .workflows import fresh, save_json


def capture_loaded_overlay(overlay,tx_path,profile,directory,timeout=10):
    """Caller first initializes the approved overlay, clocks and RFDC routing.

    This function cannot create the missing MM2S/RFDC integration. Its profile
    must describe a genuinely measured interface, not the factory OFDM overlay.
    """
    validate_profile(profile)  # before any buffer allocation or device access
    scale=profile.get('rx_counts_per_unit')
    if not isinstance(scale,(int,float)) or not np.isfinite(scale) or scale<=0:
        raise ValueError('Verified ADC counts_per_unit is required')
    bitfile=Path(overlay.bitfile_name)
    identity=sha256(bitfile)
    if identity!=profile['bitstream_sha256']:
        raise ValueError('Overlay bitfile differs from the verified profile')
    if not overlay.is_loaded():
        raise ValueError('Overlay is not currently loaded')
    _,meta=read_iq(tx_path)
    cfg=Config(**meta['config'])
    raw=np.fromfile(tx_path,dtype='<i2').reshape(-1,2)
    length=int(profile['replay_samples'])
    if len(raw)>length:
        raise ValueError('Waveform exceeds replay memory; increase RTL WORDS and rebuild')
    tx=np.zeros((length,2),dtype=np.int16)
    tx[:len(raw)]=raw
    directory=fresh(directory)
    # On timeout no result is labelled a successful RF acquisition.
    rx=dma_capture(overlay,tx,profile,cfg.sample_rate_hz,identity,timeout)
    path=directory/'rf_rx.iq16'
    with path.open('xb') as f:f.write(rx.astype('<i2').tobytes())
    metadata=dict(format='int16_le_interleaved_iq',samples=len(rx),counts_per_unit=float(scale),
        sample_rate_hz=profile['stream_rate_hz'],kind='rf_capture',config=cfg.to_dict(),
        sha256=sha256(path),acquisition=dict(bitstream_sha256=identity,profile=profile,
            tx_sha256=meta['sha256'],tx_samples_before_padding=len(raw),replay_samples=length,
            amplitude_rail_components=int(np.count_nonzero((rx==32767)|(rx==-32768)))))
    save_json(path.with_suffix('.iq16.json'),metadata)
    save_json(directory/'profile_used.json',profile)
    return path


def register_external_capture(path,cfg,counts_per_unit,acquisition):
    """Attach metadata to an existing HEADERLESS little-endian I,Q capture.

    No resampling, repacking or alteration of source bytes is performed.
    Source provenance and RFDC rate/packing must have been established by user.
    """
    path=Path(path)
    if path.stat().st_size==0 or path.stat().st_size%4:
        raise ValueError('Expected nonempty complete int16 I,Q pairs without a file header')
    if not np.isfinite(counts_per_unit) or counts_per_unit<=0:
        raise ValueError('A positive finite ADC scale is required')
    if not acquisition:
        raise ValueError('Describe the capture source, actual rate and sample packing')
    meta=dict(format='int16_le_interleaved_iq',samples=path.stat().st_size//4,
        counts_per_unit=float(counts_per_unit),sample_rate_hz=cfg.sample_rate_hz,
        kind='external_capture_user_provenance',config=cfg.to_dict(),sha256=sha256(path),
        acquisition=acquisition)
    save_json(path.with_suffix(path.suffix+'.json'),meta)
    return meta
