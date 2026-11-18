"""Mock protocol tests only: no PYNQ or board is contacted."""
import sys
import types
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
from afdm_lab.board import validate_profile, dma_capture
from afdm_lab.core import Config
from afdm_lab.rf import capture_loaded_overlay, register_external_capture
from afdm_lab.iqio import read_iq


def profile():
    return dict(board_verified=True,bitstream_sha256='a'*64,stream_rate_hz=1e6,
        tx_dma='tx',rx_dma='rx',tx_dma_max_bytes=4096,rx_dma_max_bytes=4096,
        capture_samples=64,replay_samples=64,replay_mode='load_then_start',
        capture_generates_tlast=True,format='int16_le_interleaved_iq',verified_by='TEST MOCK',
        verified_at='TEST ONLY',arm_capture_writes=[dict(ip='control',offset=0,value=1)],
        start_replay_writes=[dict(ip='control',offset=0,value=2)],stop_writes=[dict(ip='control',offset=0,value=0)])


class MockBuffer(np.ndarray):
    def __new__(cls,shape,dtype,events):
        x=np.zeros(shape,dtype=dtype).view(cls);x.events=events;return x
    def freebuffer(self):self.events.append('free')


def mock_overlay(events,rx_idle=True,control_error=False):
    class Channel:
        def __init__(self,name):self.name=name;self.idle=(name=='tx' or rx_idle)
        def transfer(self,buffer):events.append(self.name+'_transfer')
        def wait(self):events.append(self.name+'_wait')
        def stop(self):events.append(self.name+'_stop')
    class Control:
        def write(self,offset,value):
            events.append('write_%d'%value)
            if control_error and value==0:raise RuntimeError('mock stop failure')
    return types.SimpleNamespace(tx=types.SimpleNamespace(sendchannel=Channel('tx'),read=lambda x:0),
        rx=types.SimpleNamespace(recvchannel=Channel('rx'),read=lambda x:0),control=Control())


class BoardContractTests(unittest.TestCase):
    def test_unverified_profile_rejected_before_pynq_import(self):
        with self.assertRaisesRegex(ValueError,'verified'):
            dma_capture(None,np.zeros((64,2),dtype=np.int16),{},1e6,'a'*64)
        with self.assertRaisesRegex(ValueError,'verified'):
            capture_loaded_overlay(None,None,{},'unused')

    def test_rate_hash_and_length_checks(self):
        p=profile();x=np.zeros((64,2),dtype=np.int16)
        for rate,identity,words in [(2e6,'a'*64,x),(1e6,'b'*64,x),(1e6,'a'*64,x[:-1])]:
            with self.assertRaises(ValueError):dma_capture(None,words,p,rate,identity)

    def test_load_completes_before_arm_and_start(self):
        events=[];overlay=mock_overlay(events)
        pynq=types.SimpleNamespace(allocate=lambda shape,dtype:MockBuffer(shape,dtype,events))
        with patch.dict(sys.modules,{'pynq':pynq}):
            result=dma_capture(overlay,np.zeros((64,2),dtype=np.int16),profile(),1e6,'a'*64)
        self.assertEqual(result.shape,(64,2))
        self.assertEqual(events[:6],['rx_transfer','tx_transfer','tx_wait','write_1','write_2','rx_wait'])
        self.assertEqual(events[-2:],['free','free'])

    def test_timeout_stops_channels_and_releases_buffers(self):
        events=[];overlay=mock_overlay(events,rx_idle=False)
        pynq=types.SimpleNamespace(allocate=lambda shape,dtype:MockBuffer(shape,dtype,events))
        with patch.dict(sys.modules,{'pynq':pynq}):
            with self.assertRaises(TimeoutError):
                dma_capture(overlay,np.zeros((64,2),dtype=np.int16),profile(),1e6,'a'*64,timeout=.002)
        self.assertEqual(events[-4:],['tx_stop','rx_stop','free','free'])

    def test_register_cleanup_failure_still_releases_buffers(self):
        events=[];overlay=mock_overlay(events,rx_idle=False,control_error=True)
        pynq=types.SimpleNamespace(allocate=lambda shape,dtype:MockBuffer(shape,dtype,events))
        with patch.dict(sys.modules,{'pynq':pynq}):
            with self.assertRaisesRegex(RuntimeError,'mock stop'):
                dma_capture(overlay,np.zeros((64,2),dtype=np.int16),profile(),1e6,'a'*64,timeout=.002)
        self.assertEqual(events[-4:],['tx_stop','rx_stop','free','free'])

    def test_second_allocation_failure_frees_first_buffer(self):
        events=[];overlay=mock_overlay(events)
        calls=[0]
        def allocate(shape,dtype):
            calls[0]+=1
            if calls[0]==2:raise MemoryError('mock allocation failure')
            return MockBuffer(shape,dtype,events)
        with patch.dict(sys.modules,{'pynq':types.SimpleNamespace(allocate=allocate)}):
            with self.assertRaises(MemoryError):
                dma_capture(overlay,np.zeros((64,2),dtype=np.int16),profile(),1e6,'a'*64)
        self.assertEqual(events.count('free'),1)

    def test_external_capture_metadata_does_not_modify_raw_samples(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'sample.iq16'
            raw=np.array([[100,-200],[32767,-32768]],dtype='<i2').tobytes()
            path.write_bytes(raw)
            register_external_capture(path,Config(),16384,{'source':'synthetic TEST file, not RF'})
            self.assertEqual(path.read_bytes(),raw)
            got,meta=read_iq(path,Config())
            np.testing.assert_allclose(got,np.array([100-200j,32767-32768j])/16384)
            self.assertEqual(meta['kind'],'external_capture_user_provenance')


if __name__=='__main__':unittest.main()
