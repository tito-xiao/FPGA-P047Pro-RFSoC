"""Bit-exact reference for the functional block DFT and streaming rotator RTL.

16-bit data has 14 fractional bits; coefficients have 15 fractional bits.
Products are accumulated without intermediate saturation, shifted toward
negative infinity, then saturated to int16. This is NOT an AMD FFT IP model.
"""
from pathlib import Path
import numpy as np
from .core import daft_matrix

DATA_FRAC=14
COEFF_FRAC=15


def quantize(x, frac=DATA_FRAC):
    x=np.asarray(x)
    values=np.stack([x.real,x.imag],axis=-1)*2**frac
    rounded=np.rint(values)
    clipped=int(np.count_nonzero((rounded>32767)|(rounded< -32768)))
    return np.clip(rounded,-32768,32767).astype(np.int64),clipped


def dequantize(words, frac=DATA_FRAC):
    return (words[...,0]+1j*words[...,1])/2**frac


def matrix_coefficients(cfg, inverse=False):
    A=daft_matrix(cfg)
    return quantize(A.conj().T if inverse else A,COEFF_FRAC)[0]


def apply_matrix(words, coefficients):
    words=np.asarray(words,dtype=np.int64)
    a,b=words[...,0],words[...,1]
    c,d=coefficients[...,0],coefficients[...,1]
    real=a @ c.T-b @ d.T
    imag=a @ d.T+b @ c.T
    scaled=np.stack([real,imag],axis=-1)//2**COEFF_FRAC
    clipped=int(np.count_nonzero((scaled>32767)|(scaled< -32768)))
    return np.clip(scaled,-32768,32767).astype(np.int64),clipped


def rotate(words, coefficients):
    w,c=np.asarray(words,dtype=np.int64),np.asarray(coefficients,dtype=np.int64)
    real=w[...,0]*c[...,0]-w[...,1]*c[...,1]
    imag=w[...,0]*c[...,1]+w[...,1]*c[...,0]
    shifted=np.stack([real,imag],axis=-1)//2**COEFF_FRAC
    return np.clip(shifted,-32768,32767).astype(np.int64)


def write_mem(path, words):
    words=np.asarray(words).reshape(-1,2)
    with Path(path).open('w',encoding='ascii') as f:
        for i,q in words:
            f.write('%08x\n' % (((int(q)&0xffff)<<16)|(int(i)&0xffff)))


def export_vectors(directory,cfg,seed=47,frames=3):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(seed)
    # Full-range rotator vectors exercise signed multiplication and saturation.
    rot_input=rng.integers(-32768,32768,size=(frames,cfg.n,2),dtype=np.int64)
    theta=2*np.pi*cfg.c2*np.arange(cfg.n)**2
    rot_coeff,_=quantize(np.exp(1j*theta),COEFF_FRAC)
    rot_expected=rotate(rot_input,rot_coeff)
    # Scale transform inputs to leave headroom; separately exercise saturation.
    symbols=(rng.choice([-1.,1.],(frames,cfg.n))+1j*rng.choice([-1.,1.],(frames,cfg.n)))/np.sqrt(2)*0.2
    tx_in,_=quantize(symbols)
    tx_coeff=matrix_coefficients(cfg,True)
    tx_expected,tx_clipped=apply_matrix(tx_in,tx_coeff)
    rx_coeff=matrix_coefficients(cfg,False)
    rx_expected,rx_clipped=apply_matrix(tx_expected,rx_coeff)
    for name,value in [('rot_input',rot_input),('rot_coeff',rot_coeff),('rot_expected',rot_expected),
                       ('tx_input',tx_in),('tx_coeff',tx_coeff),('tx_expected',tx_expected),
                       ('rx_coeff',rx_coeff),('rx_expected',rx_expected)]:
        write_mem(directory/(name+'.mem'),value)
    return dict(frames=frames,n=cfg.n,tx_saturation=tx_clipped,rx_saturation=rx_clipped,
                max_roundtrip_error=float(np.max(np.abs(dequantize(rx_expected)-symbols))))

