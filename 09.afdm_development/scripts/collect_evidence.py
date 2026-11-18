"""Collect this local run's compact results; never upgrades hardware status."""
import hashlib
import json
import platform
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    run=ROOT/'artifacts/software_run_20261117_final'
    result=json.loads((run/'summary.json').read_text(encoding='utf-8'))
    stages=result['stages']
    sim=ROOT/'artifacts/rtl_sim/simulation.log'
    synth=ROOT/'artifacts/rtl_sim/synthesis_console.txt'
    sim_pass=any('RTL PASS:' in line for line in sim.read_text(errors='replace').splitlines())
    # Native output redirected by Windows PowerShell can be UTF-16.
    data=synth.read_bytes()
    synthesis=data.decode('utf-16' if data[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8',errors='replace')
    license_failure='17-345' in synthesis and 'license' in synthesis
    evidence=dict(date='2026-11-17',branch='dev/xiao',working_tree='uncommitted task changes',
        environment=dict(python=platform.python_version(),numpy=np.__version__,os=platform.system(),vivado='2023.1'),
        scope='Computer software + XSim only; no board connection/programming',
        software_passed=result['software_passed'],
        channel_estimation=dict(passed=stages['05_estimation']['checks_passed'],total=6,
            cases=[{k:r[k] for k in ['scenario','snr_db','bit_errors','bits','channel_nmse']} for r in stages['05_estimation']['cases']]),
        message_frames=dict(passed=stages['06_frames']['checks_passed'],total=6),
        file_loopback=dict(frames=stages['08_offline']['frames'],packet_error_rate=stages['08_offline']['packet_error_rate'],kind='SIMULATED'),
        fixedpoint={k:stages['09_fixedpoint'][k] for k in ['bits','bit_errors','max_roundtrip_error','stress_tx_clipped','stress_rx_clipped']},
        stability={k:stages['10_stability'][k] for k in ['frames_sent','frames_delivered','packet_error_rate','delivered_bits','bit_errors_on_delivered_frames']},
        rtl=dict(xsim_pass=sim_pass,simulation_log_sha256=digest(sim),
            tested='N64/L16/3 blocks; signed rotator, TX/CP/strip/RX, replay/capture, random AXI backpressure'),
        synthesis=dict(status='BLOCKED_LICENSE' if license_failure else 'INSPECT_LOG',
            target='xczu47dr-ffve1156-2-i',log_sha256=digest(synth),placed_routed=False,timing_closed=False),
        actual_rf_tested=False,full_fpga_realtime_tested=False,
        source_sha256={f.relative_to(ROOT).as_posix():digest(f) for folder in ['afdm_lab','hardware/rtl','hardware/tb']
            for f in sorted((ROOT/folder).glob('*')) if f.suffix in ['.py','.sv']})
    output=ROOT/'docs/experiments/20261117-afdm-workbench-results.json'
    output.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:evidence[k] for k in ['software_passed','rtl','synthesis']},indent=2))


if __name__=='__main__':main()
