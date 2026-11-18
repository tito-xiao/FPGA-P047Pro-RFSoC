"""Generate clean, small stage notebooks. Run from any working directory."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def markdown(text):return dict(cell_type='markdown',metadata={},source=text.splitlines(True))
def code(text):return dict(cell_type='code',metadata={},execution_count=None,outputs=[],source=text.splitlines(True))

BOOTSTRAP='''from pathlib import Path
import sys, json
from datetime import datetime
from uuid import uuid4
for candidate in [Path.cwd(), Path.cwd().parent]:
    if (candidate / "afdm_lab").is_dir():
        ROOT = candidate.resolve()
        sys.path.insert(0, str(ROOT))
        break
else:
    raise RuntimeError("请先将整个 afdm_workbench.zip 解压；Notebook 不能脱离 afdm_lab 单独上传")
from afdm_lab.core import Config
from afdm_lab import workflows as work
cfg = Config()  # 默认 1 MHz 仅用于软件；不是自动测得的 RFDC 速率
out = ROOT / "afdm_runs" / (datetime.now().strftime("%Y%m%d_%H%M%S") + "_STAGE_" + uuid4().hex[:6])
print("结果目录：", out)
'''

STAGES=[
('05_afdm_channel_estimation.ipynb','05：训练导频与信道估计','channel_estimation',
 '静态、整数和非栅格分数多普勒各测试无噪声/25 dB。接收端只读取已知训练字段，估计时延、多普勒和增益；真实信道仅用于评估 NMSE。',
 '检查 `checks_passed == checks_total == 6`、`passed == True`。该实现每个整数时延最多一条路径，不是论文中的嵌入式单导频方案。'),
('06_afdm_framing_sync_crc.ipynb','06：成帧、同步、频偏与 CRC','framed_link',
 '使用重复前导、独立训练、QPSK 数据和 CRC32，在未知整数采样位置及公共频率旋转下恢复中文消息。无需沿用 05 的变量或结果。',
 '检查六组消息、序号和 CRC 均通过。当前没有采样时钟漂移、分数采样定时或 FEC；频率估计包含主径多普勒，不能独立解释为本振频偏。'),
('07_afdm_iq_waveform_export.ipynb','07：任意 I/Q 波形文件','waveform_export',
 '生成三个已知消息帧、int16 小端 I/Q 文件及元数据。此步骤仅生成文件，不会发送到 DAC。',
 '输出 tx.iq16、tx.iq16.json、receiver_config.json、payload_reference.json。默认软件采样率为 1 MHz；接入 RFDC 前必须确认实际速率与打包格式。'),
('08_afdm_offline_capture_receiver.ipynb','08：采集文件与离线接收','replay_file_loopback',
 '默认先完成量化文件→模拟信道→采集文件→同步解调的完整闭环。结果明确标为 SIMULATED。拿到真实 ADC 文件后，在后面的可选单元格指定文件。',
 '默认应恢复三个 CRC 正确帧、PER=0。软件文件闭环通过不能证明射频通过。'),
('09_afdm_fixedpoint_rtl_vectors.ipynb','09：定点模型与 RTL 测试向量','fixedpoint',
 '生成 Q2.14 数据、Q1.15 系数和逐拍预期值。矩阵包含单位化缩放。RTL 是串行矩阵变换参考核，需在电脑的 Vivado 仿真器运行。',
 '先检查定点 bit_errors=0。再将该结果目录拷回电脑，运行 hardware/run_xsim.ps1 -WorkDirectory <该目录>。没有执行 XSim 时不能把 RTL 状态改成 PASS。'),
('10_afdm_software_stability.ipynb','10：多帧软件稳定性统计','stability',
 '默认 24 个随机帧，改变未知起点、公共频率旋转、分数多普勒和路径相位。每帧固定增益，28 dB；统计接收成功帧 BER 和总体 PER。',
 '默认期望 frames_delivered=24、PER=0、已接收帧 BER=0。这是有限种子的软件回归；连续板上运行、重启复现和丢样计数需要另做实测。')]


def main():
    for name,title,function,intro,criterion in STAGES:
        stage=name[:2]
        cells=[markdown('# '+title+'\n\n'+intro+'\n\n依赖：Python 3.8+、NumPy；完整解压本工具包后使用。'),
            code(BOOTSTRAP.replace('STAGE',stage)),
            code('result = work.%s(out, cfg)\nprint(json.dumps(result, ensure_ascii=False, indent=2))\nassert result["passed"], "检查失败：请保留 summary.json 和完整输出"\n'%function),
            markdown('**判断依据**\n\n'+criterion+'\n\n结果保存在上面打印的目录与 `summary.json`。再次运行会建立新目录，不覆盖原结果。')]
        if stage=='08':
            cells.extend([markdown('**可选：真实采集文件的离线接收**\n\n先按 docs/afdm-workbench.md 准备原始 I/Q 和相邻 JSON。不要使用 OFDM 的均衡后星座数据替代 ADC 采样。以下单元格默认跳过。'),code('''REAL_CAPTURE = None  # 例如 Path("/home/xilinx/jupyter_notebooks/captures/rf_rx.iq16")
if REAL_CAPTURE is not None:
    actual_out = out.with_name(out.name + "_actual")
    actual = work.decode_file(REAL_CAPTURE, actual_out)
    print(json.dumps(actual, ensure_ascii=False, indent=2))
else:
    print("真实射频接收：未执行")
''')])
        notebook=dict(cells=cells,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3'),
            language_info=dict(name='python',version='3.8')),nbformat=4,nbformat_minor=4)
        (ROOT/'notebooks'/name).write_text(json.dumps(notebook,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    rf_cells=[markdown('''# 08b：已验证 Overlay 的板端回放与采集

此文件是接口入口，不包含可直接烧写的 P047Pro 固件。厂家 OFDM 的 DMA 只有 S2MM，不能用来发送任意 I/Q。
必须先完成 hardware/README.md 所述板级集成、时钟和采样映射验证，并在另一单元格得到已初始化的 `overlay`。
本 Notebook 默认不运行硬件，Python 不会远程连接板卡。
'''),code(BOOTSTRAP.replace('STAGE','08b')),code('''RUN_RF = False
PROFILE_PATH = ROOT / "configs" / "p047pro_unverified.json"
TX_FILE = None  # 07 生成的 tx.iq16 的完整路径
if RUN_RF:
    from afdm_lab.rf import capture_loaded_overlay
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    # overlay 必须已经由用户按自己的板级工程配置完成。
    # 此函数不加载 bitstream、不设置 LMK/RFDC，也不改变通道接线。
    if TX_FILE is None:
        raise ValueError("先指定 07 的波形文件")
    rx_file = capture_loaded_overlay(overlay, TX_FILE, profile, out)
    print("实际采集文件：", rx_file)
    decoded = work.decode_file(rx_file, out.with_name(out.name + "_decode"))
    print(json.dumps(decoded, ensure_ascii=False, indent=2))
else:
    print("射频操作未执行：默认配置未验证，先完成板级回放/采集工程")
''')]
    (ROOT/'notebooks/08b_pynq_replay_capture.ipynb').write_text(json.dumps(dict(cells=rf_cells,
        metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3')),
        nbformat=4,nbformat_minor=4),ensure_ascii=False,indent=1)+'\n',encoding='utf-8')


if __name__=='__main__':main()
