"""Explicit little-endian interleaved int16 I,Q files; no implicit resampling."""
import hashlib
import json
from pathlib import Path
import numpy as np
from .core import Config


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):
            h.update(part)
    return h.hexdigest()


def write_iq(path, samples, cfg, kind='generated_waveform', peak_fraction=0.75, extra=None):
    path=Path(path)
    metadata=path.with_suffix(path.suffix+'.json')
    if metadata.exists():
        raise FileExistsError('Metadata already exists: '+str(metadata))
    samples=np.asarray(samples,dtype=np.complex128)
    if samples.ndim!=1 or not samples.size or not np.all(np.isfinite(samples)) or not 0<peak_fraction<1:
        raise ValueError('Finite nonempty 1-D I/Q and 0<peak_fraction<1 required')
    peak=max(float(np.max(np.abs(samples.real))),float(np.max(np.abs(samples.imag))),1e-15)
    scale=32767*peak_fraction/peak
    raw=np.column_stack([samples.real,samples.imag])*scale
    words=np.rint(raw).astype('<i2')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:
        f.write(words.tobytes())
    meta=dict(format='int16_le_interleaved_iq',samples=int(samples.size),
        counts_per_unit=scale,sample_rate_hz=cfg.sample_rate_hz,kind=kind,
        config=cfg.to_dict(),sha256=sha256(path),clipped_components=0)
    if extra:meta['acquisition']=extra
    with metadata.open('x',encoding='utf-8') as f:json.dump(meta,f,indent=2)
    return meta


def read_iq(path, cfg=None):
    path=Path(path)
    meta=json.loads(path.with_suffix(path.suffix+'.json').read_text(encoding='utf-8'))
    if meta['format']!='int16_le_interleaved_iq' or sha256(path)!=meta['sha256']:
        raise ValueError('I/Q format or file checksum does not match metadata')
    raw=np.fromfile(path,dtype='<i2')
    if raw.size!=2*meta['samples'] or not np.isfinite(meta['counts_per_unit']) or meta['counts_per_unit']<=0:
        raise ValueError('I/Q sample count or scaling is invalid')
    expected_cfg=cfg or Config(**meta['config'])
    if not np.isclose(meta['sample_rate_hz'],expected_cfg.sample_rate_hz,rtol=1e-9,atol=0):
        raise ValueError('Capture rate differs from receiver rate; resample explicitly before decoding')
    iq=(raw[::2].astype(float)+1j*raw[1::2].astype(float))/meta['counts_per_unit']
    return iq,meta

