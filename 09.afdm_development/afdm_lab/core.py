"""Unitary AFDM conventions and independently indexed physical channels.

nu is in subcarrier spacings; each path uses exp(-j*2*pi*nu*t/N).
This module has no PYNQ, filesystem or hardware side effects.
"""
from dataclasses import dataclass, asdict
from numbers import Integral
import numpy as np


@dataclass(frozen=True)
class Config:
    n: int = 64
    prefix: int = 16
    c1: float = 5 / 128
    c2: float = float(np.sqrt(2) / 4096)
    sample_rate_hz: float = 1e6  # software waveform rate; NOT a detected RFDC rate
    training_blocks: int = 4
    data_blocks: int = 8
    max_delay: int = 8
    max_paths: int = 3
    nu_bound: float = 3.0
    nu_step: float = 0.1
    seed: int = 47047

    def __post_init__(self):
        integers=[self.n,self.prefix,self.training_blocks,self.data_blocks,self.max_delay,self.max_paths,self.seed]
        if any(not isinstance(v,Integral) for v in integers) or self.seed<0:
            raise ValueError('Lengths, path count and seed must be nonnegative integers')
        if not np.all(np.isfinite([self.c1,self.c2,self.sample_rate_hz,self.nu_bound,self.nu_step])):
            raise ValueError('Chirp, rate and search parameters must be finite')
        if self.n < 16 or self.n % 2 or not 0 <= self.max_delay <= self.prefix <= self.n:
            raise ValueError('Require even N>=16 and 0<=max_delay<=prefix<=N')
        if self.training_blocks < 2 or self.data_blocks < 1 or self.max_paths < 1:
            raise ValueError('Training>=2, data_blocks>=1, max_paths>=1 required')
        if self.max_paths > self.max_delay+1:
            raise ValueError('This estimator supports at most one path per integer delay')
        if self.n*self.data_blocks % 4 or self.n*self.data_blocks//4 < 15:
            raise ValueError('QPSK frame must contain whole bytes and fit the header plus CRC')
        if self.nu_bound <= 0 or not 0 < self.nu_step <= self.nu_bound or self.sample_rate_hz <= 0:
            raise ValueError('Invalid search bounds or sample rate')

    @property
    def block_length(self):
        return self.n + self.prefix

    def to_dict(self):
        return asdict(self)


def idaft(x, c1, c2):
    x = np.asarray(x, dtype=np.complex128)
    n = np.arange(x.shape[-1])
    return np.exp(2j*np.pi*c1*n*n)*np.fft.ifft(x*np.exp(2j*np.pi*c2*n*n), axis=-1, norm='ortho')


def daft(x, c1, c2):
    x = np.asarray(x, dtype=np.complex128)
    n = np.arange(x.shape[-1])
    return np.exp(-2j*np.pi*c2*n*n)*np.fft.fft(x*np.exp(-2j*np.pi*c1*n*n), axis=-1, norm='ortho')


def daft_matrix(cfg):
    m, n = np.arange(cfg.n)[:, None], np.arange(cfg.n)[None, :]
    return np.exp(-2j*np.pi*(cfg.c2*m*m + m*n/cfg.n + cfg.c1*n*n))/np.sqrt(cfg.n)


def qpsk(bits):
    b = np.asarray(bits)
    if b.shape[-1] != 2 or not np.all((b == 0) | (b == 1)):
        raise ValueError('QPSK needs pairs of binary bits')
    return ((1-2*b[..., 0].astype(float))+1j*(1-2*b[..., 1].astype(float)))/np.sqrt(2)


def decisions(x):
    return np.stack([x.real < 0, x.imag < 0], axis=-1).astype(np.uint8)


def add_cpp(wave, cfg):
    wave = np.asarray(wave)
    if wave.shape[-1] != cfg.n:
        raise ValueError('Waveform block length differs from N')
    if cfg.prefix == 0:
        return wave.copy()
    t = np.arange(-cfg.prefix, 0)
    prefix = wave[..., -cfg.prefix:]*np.exp(-2j*np.pi*cfg.c1*(cfg.n**2+2*cfg.n*t))
    return np.concatenate([prefix, wave], axis=-1)


def time_matrix(cfg, paths, time_start=0):
    H = np.zeros((cfg.n, cfg.n), dtype=np.complex128)
    n = np.arange(cfg.n)
    for delay, nu, gain in paths:
        if int(delay) != delay or not 0 <= delay <= cfg.prefix:
            raise ValueError('Channel delay must fit CPP')
        delay = int(delay)
        k = n-delay
        phase = np.exp(-2j*np.pi*nu*(n+time_start)/cfg.n)
        mask = k < 0
        phase[mask] *= np.exp(-2j*np.pi*cfg.c1*(cfg.n**2+2*cfg.n*k[mask]))
        H[n, k % cfg.n] += gain*phase
    return H


def effective_matrix(cfg, paths, time_start=0):
    A = daft_matrix(cfg)
    return A @ time_matrix(cfg, paths, time_start) @ A.conj().T


def physical_channel(signal, paths, n=64, time_origin=0):
    """Explicit delayed linear samples with path phase at OUTPUT time."""
    x = np.asarray(signal, dtype=np.complex128)
    if x.ndim != 1 or not len(paths):
        raise ValueError('Need a 1-D waveform and nonempty paths')
    if any(int(d) != d or d < 0 for d, _, _ in paths):
        raise ValueError('Delays must be nonnegative integers')
    out = np.zeros(x.size+max(int(p[0]) for p in paths), dtype=np.complex128)
    for delay, nu, gain in paths:
        delay = int(delay)
        t = np.arange(x.size)+delay+time_origin
        out[delay:delay+x.size] += gain*x*np.exp(-2j*np.pi*nu*t/n)
    return out


def detect(y, H, noise_variance=0):
    if noise_variance < 0:
        raise ValueError('Noise variance must be nonnegative')
    if noise_variance == 0:
        return np.linalg.solve(H, y)
    return np.linalg.solve(H.conj().T @ H+noise_variance*np.eye(H.shape[1]), H.conj().T @ y)


def paths_json(paths):
    return [dict(delay=int(d), nu=float(nu), gain_real=float(h.real), gain_imag=float(h.imag)) for d, nu, h in paths]


def nmse(estimate, reference):
    denominator = np.linalg.norm(reference)**2
    return float(np.linalg.norm(estimate-reference)**2/max(denominator, 1e-30))

