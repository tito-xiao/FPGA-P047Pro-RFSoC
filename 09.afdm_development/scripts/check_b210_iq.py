"""Inspect rx_samples_to_file --type float output; no UHD or hardware access.

File checks never establish OFDM decoding, BER or continuous RF acquisition.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def inspect(path, sample_rate_hz, expected_samples=None):
    path=Path(path)
    if not np.isfinite(sample_rate_hz) or sample_rate_hz<=0:
        raise ValueError('Use the positive ACTUAL RX sample rate from the UHD log')
    size=path.stat().st_size
    if size==0 or size%8:
        raise ValueError('Expected a nonempty fc32 file: 8 bytes per complex sample')
    x=np.memmap(path,mode='r',dtype='<c8')
    count=int(x.size)
    if expected_samples is not None and count!=expected_samples:
        raise ValueError('Sample count differs from request: %d != %d'%(count,expected_samples))
    if not np.all(np.isfinite(x)):
        raise ValueError('Nonfinite I/Q samples')
    peak=float(max(np.max(np.abs(x.real)),np.max(np.abs(x.imag))))
    rms=float(np.sqrt(np.mean(np.abs(x.astype(np.complex128))**2)))
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return dict(scope='OFFLINE FILE CHECK ONLY',format='little_endian_complex64',samples=count,
        bytes=size,actual_sample_rate_hz=float(sample_rate_hz),duration_seconds=count/sample_rate_hz,
        component_peak_full_scale_units=peak,rms_full_scale_units=rms,
        components_near_rail=int(np.count_nonzero(np.abs(x.real)>=.999)+np.count_nonzero(np.abs(x.imag)>=.999)),
        sha256=h.hexdigest(),file_checks_passed=True,
        stream_continuity='NOT_VERIFIED: retain UHD log; reject timeout/overflow/sequence errors',
        ofdm_decoded=False,ber_measured=False,sensing_measured=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path)
    p.add_argument('--rate-hz',type=float,required=True,help='ACTUAL RX rate shown by UHD')
    p.add_argument('--expected-samples',type=int,default=1000000)
    p.add_argument('--output',type=Path,help='NEW report directory, existing directories are refused')
    p.add_argument('--plot',action='store_true',help='Optional relative spectrum PNG, requires matplotlib')
    a=p.parse_args()
    report=inspect(a.input,a.rate_hz,a.expected_samples)
    out=a.output or a.input.with_name(a.input.name+'_check')
    out.mkdir(parents=True,exist_ok=False)
    x=np.memmap(a.input,mode='r',dtype='<c8')
    n=min(4096,len(x))
    window=np.hanning(n)
    blocks=min(len(x)//n,32)
    spectrum=np.zeros(n)
    for i in range(blocks):
        spectrum+=np.abs(np.fft.fft(np.asarray(x[i*n:(i+1)*n])*window))**2
    spectrum=np.fft.fftshift(spectrum/blocks)
    relative_db=10*np.log10(np.maximum(spectrum,1e-30)/max(float(np.max(spectrum)),1e-30))
    freq=np.fft.fftshift(np.fft.fftfreq(n,1/a.rate_hz))
    np.savetxt(out/'relative_spectrum.csv',np.column_stack([freq,relative_db]),delimiter=',',
        header='offset_hz,relative_power_db',comments='')
    if a.plot:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(8,4))
        ax.plot(freq/1e6,relative_db)
        ax.set(xlabel='Offset from RX center (MHz)',ylabel='Relative power (dB)',
               title='B210 capture spectrum - not calibrated RF power')
        ax.grid(True);fig.tight_layout();fig.savefig(out/'relative_spectrum.png',dpi=150);plt.close(fig)
    (out/'file_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    print('Report directory: '+str(out.resolve()))


if __name__=='__main__':main()
