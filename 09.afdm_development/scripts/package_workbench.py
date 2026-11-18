"""Package own code/docs only; no tool caches, vendor source or raw user data."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    files=[]
    for folder,patterns in [('afdm_lab',['*.py']),('configs',['*.json']),('notebooks',['*.ipynb']),
        ('hardware',['*.sv','*.ps1','*.tcl','*.md']),('tests',['*.py']),('scripts',['*.py'])]:
        for pattern in patterns:files.extend((ROOT/folder).rglob(pattern))
    files.extend([ROOT/'requirements.txt',ROOT/'docs/afdm-workbench.md',
        ROOT/'docs/experiments/20261117-afdm-workbench.md',
        ROOT/'docs/experiments/20261117-afdm-workbench-results.json'])
    files=sorted(set(files),key=lambda x:x.as_posix())
    manifest={f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    output=ROOT/'artifacts/afdm_workbench.zip';output.parent.mkdir(exist_ok=True)
    # Build artifact is intentionally replaceable; sources/data are not changed.
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for f in files:z.write(f,'afdm_workbench/'+f.relative_to(ROOT).as_posix())
        z.writestr('afdm_workbench/MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None:raise RuntimeError('Package CRC verification failed')
        for rel,expected in manifest.items():
            if hashlib.sha256(z.read('afdm_workbench/'+rel)).hexdigest()!=expected:
                raise RuntimeError('Manifest verification failed: '+rel)
    checksum=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(checksum+'  '+output.name+'\n',encoding='ascii')
    print(json.dumps(dict(path=str(output),files=len(files),bytes=output.stat().st_size,
        sha256=checksum),indent=2))


if __name__=='__main__':main()
