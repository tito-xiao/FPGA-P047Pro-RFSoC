import numpy as np
from .core import physical_channel

DEFAULT_PATHS=[(0,0.,0.85+0j),(2,1.,0.35+0.12j),(5,-1.7,0.12-0.1j)]


def capture(wave,cfg,paths=None,snr_db=None,offset=47,cfo_bins=0.17,seed=1):
    paths=DEFAULT_PATHS if paths is None else paths
    padded=np.concatenate([np.zeros(offset),wave,np.zeros(cfg.prefix+cfg.n)])
    y=physical_channel(padded,paths,cfg.n)
    y*=np.exp(2j*np.pi*cfo_bins*np.arange(y.size)/cfg.n)
    variance=0. if snr_db is None else float(np.mean(np.abs(wave)**2)*10**(-snr_db/10))
    if variance:
        rng=np.random.default_rng(seed)
        y+=np.sqrt(variance/2)*(rng.standard_normal(y.size)+1j*rng.standard_normal(y.size))
    return y,dict(scope='SIMULATED capture, not RF',offset=offset,cfo_bins=cfo_bins,
                  noise_variance=variance,snr_db=snr_db,seed=seed)
