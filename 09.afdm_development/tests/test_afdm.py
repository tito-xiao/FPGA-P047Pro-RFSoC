import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
import numpy as np
from afdm_lab.core import (Config, qpsk, decisions, idaft, daft, daft_matrix,
    add_cpp, physical_channel, time_matrix, effective_matrix, detect, nmse)
from afdm_lab.estimation import estimate_paths
from afdm_lab.link import (build_frame, training, decode_capture, pack_payload,
    unpack_payload, capacity, frame_length)
from afdm_lab.simulation import capture
from afdm_lab.iqio import write_iq, read_iq
from afdm_lab.fixedpoint import quantize, dequantize, apply_matrix, matrix_coefficients, rotate
from afdm_lab.workflows import SCENARIOS


class TransformTests(unittest.TestCase):
    def setUp(self):
        self.cfg=Config();self.rng=np.random.default_rng(47)

    def test_transform_against_independent_matrix_and_energy(self):
        x=self.rng.normal(size=64)+1j*self.rng.normal(size=64)
        A=daft_matrix(self.cfg)
        s=idaft(x,self.cfg.c1,self.cfg.c2)
        np.testing.assert_allclose(s,A.conj().T@x,atol=2e-13)
        np.testing.assert_allclose(daft(s,self.cfg.c1,self.cfg.c2),x,atol=2e-14)
        self.assertAlmostEqual(float(np.vdot(s,s).real),float(np.vdot(x,x).real),places=11)

    def test_general_cpp_continuous_blocks_fractional_channel(self):
        cfg=replace(self.cfg,c1=.03317)
        blocks=self.rng.normal(size=(3,cfg.n))+1j*self.rng.normal(size=(3,cfg.n))
        stream=add_cpp(blocks,cfg).reshape(-1)
        paths=SCENARIOS['fractional_offgrid']
        y=physical_channel(stream,paths,cfg.n,time_origin=129)
        for i in range(3):
            t=i*cfg.block_length+cfg.prefix
            np.testing.assert_allclose(y[t:t+cfg.n],time_matrix(cfg,paths,t+129)@blocks[i],atol=2e-13)

    def test_noiseless_known_channel_recovery(self):
        b=self.rng.integers(0,2,(64,2))
        H=effective_matrix(self.cfg,SCENARIOS['fractional_offgrid'],329)
        recovered=detect(H@qpsk(b),H)
        np.testing.assert_array_equal(decisions(recovered),b)


class ChannelEstimatorTests(unittest.TestCase):
    def test_offgrid_uses_only_training_and_extrapolates(self):
        cfg=Config();pilot=training(cfg)
        paths=SCENARIOS['fractional_offgrid']
        received=physical_channel(pilot,paths,cfg.n)[:len(pilot)]
        est=estimate_paths(pilot,received,cfg)
        for t in [400,1000]:
            error=nmse(effective_matrix(cfg,est['paths'],t),effective_matrix(cfg,paths,t))
            self.assertLess(error,1e-12)
        self.assertEqual(sorted(p[0] for p in est['paths']),[0,2,5])

    def test_input_length_and_model_prior(self):
        cfg=Config()
        with self.assertRaises(ValueError):estimate_paths(np.ones(5),np.ones(6),cfg)
        with self.assertRaises(ValueError):Config(max_paths=10)
        with self.assertRaises(ValueError):Config(sample_rate_hz=float('nan'))
        with self.assertRaises(ValueError):Config(n=18,data_blocks=1)


class ReceiverTests(unittest.TestCase):
    def test_unknown_start_cfo_multipath_and_unicode_crc(self):
        cfg=Config();message='你好，P047Pro AFDM！'.encode('utf-8')
        wave,bits=build_frame(message,91,cfg)
        received,_=capture(wave,cfg,SCENARIOS['fractional_offgrid'],25,offset=123,cfo_bins=-.19,seed=18)
        result=decode_capture(received,cfg)
        self.assertEqual(len(result['frames']),1)
        f=result['frames'][0]
        self.assertEqual((f['offset'],f['sequence'],f['payload']),(123,91,message))
        np.testing.assert_array_equal(f['bits'],bits)

    def test_consecutive_frames_not_given_expected_bits(self):
        cfg=Config();pieces=[]
        for seq in range(3):pieces.extend([build_frame('message %d'%seq,seq,cfg)[0],np.zeros(64)])
        received,_=capture(np.concatenate(pieces),cfg,SCENARIOS['integer'],28,offset=37,cfo_bins=.23,seed=99)
        result=decode_capture(received,cfg)
        self.assertEqual([f['sequence'] for f in result['frames']],[0,1,2])
        self.assertEqual([f['payload'] for f in result['frames']],[b'message 0',b'message 1',b'message 2'])

    def test_crc_detects_payload_corruption(self):
        cfg=Config();bits=pack_payload(b'known message',1,cfg).copy()
        # Flip a bit after the 11-byte header, before the CRC.
        bits.reshape(-1)[11*8+3]^=1
        with self.assertRaisesRegex(ValueError,'CRC'):unpack_payload(bits,cfg)

    def test_payload_boundaries(self):
        cfg=Config();payload=b'a'*capacity(cfg)
        self.assertEqual(unpack_payload(pack_payload(payload,0,cfg),cfg)[1],payload)
        with self.assertRaises(ValueError):pack_payload(payload+b'a',0,cfg)
        with self.assertRaises(ValueError):pack_payload(b'a',2**32,cfg)

    def test_noise_only_yields_no_accepted_frames(self):
        cfg=Config();rng=np.random.default_rng(101)
        samples=rng.normal(size=4000)+1j*rng.normal(size=4000)
        self.assertEqual(decode_capture(samples,cfg)['frames'],[])

    def test_short_and_nonfinite_captures_rejected(self):
        cfg=Config()
        for samples in [np.zeros(100),np.full(frame_length(cfg),np.nan)]:
            with self.assertRaises(ValueError):decode_capture(samples,cfg)


class FileAndFixedPointTests(unittest.TestCase):
    def test_iq_roundtrip_rate_hash_and_no_overwrite(self):
        cfg=Config();wave,_=build_frame('I/Q',0,cfg)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'tx.iq16';meta=write_iq(path,wave,cfg)
            restored,_=read_iq(path,cfg)
            self.assertLess(float(np.max(np.abs(restored-wave))),1/meta['counts_per_unit'])
            with self.assertRaises(FileExistsError):write_iq(path,wave,cfg)
            with self.assertRaises(ValueError):read_iq(path,replace(cfg,sample_rate_hz=2e6))
            metadata=path.with_suffix('.iq16.json')
            mismatch=dict(meta,sample_rate_hz=2e6)
            metadata.write_text(json.dumps(mismatch),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'rate'):read_iq(path)
            metadata.write_text(json.dumps(meta),encoding='utf-8')
            data=bytearray(path.read_bytes());data[0]^=1;path.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'checksum'):read_iq(path,cfg)

    def test_fixedpoint_noiseless_bits(self):
        cfg=Config();rng=np.random.default_rng(20)
        bits=rng.integers(0,2,(8,64,2));words,_=quantize(qpsk(bits)*.2)
        tx,clip1=apply_matrix(words,matrix_coefficients(cfg,True))
        rx,clip2=apply_matrix(tx,matrix_coefficients(cfg,False))
        self.assertEqual(clip1+clip2,0)
        np.testing.assert_array_equal(decisions(dequantize(rx)),bits)

    def test_signed_saturation_and_floor(self):
        words=np.array([[32767,32767],[-32768,-32768],[1,0]])
        coeff=np.array([[23170,23170],[23170,23170],[-1,0]])
        got=rotate(words,coeff)
        np.testing.assert_array_equal(got,np.array([[0,32767],[0,-32768],[-1,0]]))
        quant,clips=quantize(np.array([3+3j,-3-3j]))
        self.assertEqual(clips,4)
        np.testing.assert_array_equal(quant,[[32767,32767],[-32768,-32768]])


if __name__=='__main__':unittest.main()
