"""Separate known training field: delay/Doppler dictionary + gain LS.

This is NOT the paper's embedded single-pilot estimator. It trades training
overhead for an independently testable receiver. No true path values or true
effective channel are accepted by the estimator API. This version assumes at
most one Doppler component per integer delay; co-delayed paths need a later
model-selection extension.
"""
import numpy as np


def training_dictionary(tx, cfg, time_start=0):
    tx = np.asarray(tx, dtype=np.complex128)
    t = np.arange(cfg.max_delay, tx.size)
    if t.size < 4*cfg.max_paths:
        raise ValueError('Training observation is too short')
    grid = np.arange(-cfg.nu_bound, cfg.nu_bound+cfg.nu_step/2, cfg.nu_step)
    params = [(d, float(v)) for d in range(cfg.max_delay+1) for v in grid]
    atoms = np.column_stack([tx[t-d]*np.exp(-2j*np.pi*v*(t+time_start)/cfg.n) for d, v in params])
    return t, params, atoms


def estimate_paths(tx_training, rx_training, cfg, time_start=0, refine_cycles=12):
    tx, rx = np.asarray(tx_training), np.asarray(rx_training)
    if tx.ndim != 1 or tx.shape != rx.shape or not np.all(np.isfinite(rx)):
        raise ValueError('Known training and received training must be equal finite 1-D arrays')
    t, grid_params, D = training_dictionary(tx, cfg, time_start)
    y = rx[t]
    norm = np.linalg.norm(D, axis=0)
    valid = norm > 1e-12
    unit = D / np.maximum(norm, 1e-30)
    residual = y.copy()
    support = []
    selected = []
    for _ in range(cfg.max_paths):
        score = np.abs(unit.conj().T @ residual)
        score[~valid] = -1
        for j in support:
            score[j] = -1
        # An off-grid strong path must not consume multiple support slots as
        # adjacent Doppler atoms at the same delay (derivative cancellation).
        used_delays = {int(p[0]) for p in selected}
        for k,(delay,_) in enumerate(grid_params):
            if delay in used_delays:
                score[k] = -1
        j = int(np.argmax(score))
        support.append(j)
        selected.append(list(grid_params[j]))
        coef = np.linalg.lstsq(D[:, support], y, rcond=None)[0]
        residual = y-D[:, support] @ coef
        if np.linalg.norm(residual) <= 1e-11*max(np.linalg.norm(y), 1):
            break

    def solve(params):
        B = np.column_stack([tx[t-int(d)]*np.exp(-2j*np.pi*v*(t+time_start)/cfg.n) for d, v in params])
        gains = np.linalg.lstsq(B, y, rcond=None)[0]
        error = y-B @ gains
        return float(np.vdot(error, error).real), gains, B

    # Continuous variable-projection refinement: off-grid fractions are not
    # rounded to the dictionary. Refit all complex gains at every evaluation.
    for _ in range(refine_cycles):
        before = solve(selected)[0]
        for i in range(len(selected)):
            center = selected[i][1]
            lo = max(-cfg.nu_bound, center-2*cfg.nu_step)
            hi = min(cfg.nu_bound, center+2*cfg.nu_step)
            ratio = (np.sqrt(5)-1)/2
            def score(v):
                trial = [p.copy() for p in selected]
                trial[i][1] = v
                return solve(trial)[0]
            a, b = hi-ratio*(hi-lo), lo+ratio*(hi-lo)
            fa, fb = score(a), score(b)
            for _ in range(38):
                if fa < fb:
                    hi, b, fb = b, a, fa
                    a = hi-ratio*(hi-lo); fa = score(a)
                else:
                    lo, a, fa = a, b, fb
                    b = lo+ratio*(hi-lo); fb = score(b)
            candidate = (lo+hi)/2
            if score(candidate) < score(center):
                selected[i][1] = candidate
        after = solve(selected)[0]
        if after < 1e-23*max(float(np.vdot(y, y).real), 1) or abs(before-after) < 1e-14*max(before, 1e-15):
            break
    error, gains, B = solve(selected)
    paths = [(int(d), float(v), complex(g)) for (d, v), g in zip(selected, gains)]
    fitted_variance = error/max(y.size-len(paths)*3, 1)
    return dict(paths=paths, residual_power=float(fitted_variance), relative_residual=error/max(float(np.vdot(y, y).real), 1e-30),
                observations=int(y.size), training_samples=int(tx.size), search_prior=dict(max_delay=cfg.max_delay,
                max_paths=cfg.max_paths, nu_bound=cfg.nu_bound, coarse_step=cfg.nu_step))

