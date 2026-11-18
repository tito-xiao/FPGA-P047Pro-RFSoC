"""Execute new stage notebooks as independent Python sessions, no Jupyter deps.

08b remains RUN_RF=False. This script never imports PYNQ or accesses a board.
"""
import contextlib
import io
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT/'notebooks')
    names=sorted(p for p in Path.cwd().glob('*.ipynb') if p.name[:2] in ['05','06','07','08','09','10'])
    for path in names:
        nb=json.loads(path.read_text(encoding='utf-8'))
        context={'__name__':'__main__'}
        with contextlib.redirect_stdout(io.StringIO()):
            for index,cell in enumerate(nb['cells']):
                if cell['cell_type']=='code':
                    if cell.get('outputs') or cell.get('execution_count') is not None:
                        raise ValueError('Distribution notebook must have empty outputs: '+path.name)
                    exec(compile(''.join(cell['source']),str(path)+':cell'+str(index),'exec'),context)
        print(path.name+': PASS (independent namespace; hardware disabled)')


if __name__=='__main__':main()
