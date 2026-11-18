"""python -m afdm_lab.cli --help (NumPy + Python standard library only)."""
import argparse
import json
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from .core import Config
from . import workflows as w


def main(argv=None):
    p=argparse.ArgumentParser(description='P047Pro AFDM software workbench; no automatic RF transfer')
    p.add_argument('stage',choices=['suite','estimation','frames','waveform','offline','fixedpoint','stability','decode'])
    p.add_argument('--output',type=Path,help='NEW output directory (existing directories are never overwritten)')
    p.add_argument('--config',type=Path,help='Receiver Config JSON; default software rate is 1 MHz')
    p.add_argument('--frames',type=int,default=24,help='Software stability frame count')
    p.add_argument('--input',type=Path,help='Capture .iq16 with adjacent .iq16.json (decode only)')
    p.add_argument('--reference',type=Path,help='Optional payload_reference.json, used for scoring only')
    a=p.parse_args(argv)
    cfg=Config(**json.loads(a.config.read_text(encoding='utf-8'))) if a.config else Config()
    output=a.output or Path('afdm_runs')/(datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+a.stage+'_'+uuid4().hex[:6])
    if a.stage=='decode':
        if a.input is None:p.error('decode requires --input')
        reference=json.loads(a.reference.read_text(encoding='utf-8')) if a.reference else None
        report=w.decode_file(a.input,output,cfg if a.config else None,reference)
    elif a.stage in ['suite','stability']:
        report=getattr(w,a.stage)(output,cfg,a.frames)
    else:
        function=dict(estimation=w.channel_estimation,frames=w.framed_link,waveform=w.waveform_export,
            offline=w.replay_file_loopback,fixedpoint=w.fixedpoint)[a.stage]
        report=function(output,cfg)
    print('Result: '+str(output.resolve()))
    if 'software_passed' in report:print('Software checks passed: '+str(report['software_passed']))
    elif 'passed' in report:print('Stage checks passed: '+str(report['passed']))
    else:print('CRC accepted: '+str(report['crc_accepted'])+'; expected-packet scoring not supplied')
    print('Actual RF and full FPGA real-time acceptance require separate measurements.')
    return 0 if report.get('software_passed',report.get('passed',True)) else 1


if __name__=='__main__':
    raise SystemExit(main())
