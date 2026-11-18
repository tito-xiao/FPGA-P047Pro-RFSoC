"""Read-only local source audit. Writes facts/hashes, never vendor source copies."""
import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('vendor_root',type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();base=a.vendor_root.resolve()
    # Paths are to the supplied P047Pro distribution, not a generic board.
    hwh=base/'08.ofdm_afdm/setup/rfsoc_ofdm_p047pro/boards/rfsoc47dr/rfsoc_ofdm/bitstream/rfsoc_ofdm.hwh'
    if not hwh.is_file():
        hits=list((base/'08.ofdm_afdm').rglob('rfsoc_ofdm.hwh'))
        hits=[x for x in hits if 'rfsoc47dr' in x.parts]
        if len(hits)!=1:raise FileNotFoundError('Locate a unique adapted rfsoc47dr HWH first')
        hwh=hits[0]
    root=ET.parse(hwh).getroot();dmas=[]
    for module in root.iter('MODULE'):
        if 'axi_dma' not in module.attrib.get('MODTYPE',''):continue
        params={x.attrib['NAME']:x.attrib.get('VALUE') for x in module.iter('PARAMETER')}
        dmas.append(dict(name=module.attrib.get('INSTANCE'),mm2s=params.get('C_INCLUDE_MM2S'),
            s2mm=params.get('C_INCLUDE_S2MM')))
    xpr=base/'05.教程和源码/4_RF/4_RF/2_PZ_RF47DR/PZ_RF47DR.xpr'
    top=xpr.parent/'PZ_RF47DR.srcs/sources_1/new/rfsoc_top.v'
    bd=xpr.parent/'PZ_RF47DR.srcs/sources_1/bd/system/system.bd'
    files=[hwh]+[x for x in [xpr,top,bd] if x.is_file()]
    result=dict(scope='Read-only source inventory; project not rebuilt, no board accessed',
        files=[dict(path=str(f.relative_to(base)),bytes=f.stat().st_size,sha256=digest(f)) for f in files],
        factory_dmas=dmas,arbitrary_iq_tx_available=any(x['mm2s']=='1' for x in dmas),
        bare_rf_project_present=xpr.is_file(),bare_rf_top_present=top.is_file(),bare_rf_bd_present=bd.is_file())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
