# AFDM 分阶段工具包：从 04 继续

你已完成 04 的已知信道自检。现在从 05 开始，不必重做 02～04。05～10 可以分别执行，也可以用一条命令运行全部软件阶段。08b 是实际硬件接口入口，现有厂家 OFDM 固件不能直接运行它。

本次新增：未知信道估计、成帧/同步/CRC、I/Q 文件生成和离线接收、定点模型、功能 RTL 和软件多帧回归。尚未完成：任意 I/Q 板级 Overlay、真实 AFDM 射频验证、全实时 FPGA 收发与验收。本机目标器件综合还遇到 Vivado 许可缺失。

## 上传到 Jupyter

1. 将电脑 `C:\Users\Administrator\Desktop\FPGA-P047Pro-RFSoC\09.afdm_development\artifacts\afdm_workbench.zip` 上传到板端 Jupyter 的 `rfsoc_ofdm` 目录。ZIP 只含本项目代码和文档，不包含 16 GB 厂家工程。
2. 在 Jupyter 的 Terminal 中进入上传目录，运行：

   ```bash
   python3 -m zipfile -e afdm_workbench.zip .
   ```

   解压得到独立的 `afdm_workbench/` 目录。若已有同名目录，先把本次 ZIP 解压到新的父目录，保留旧结果。
3. 进入 `afdm_workbench/notebooks/`，打开 05，选择 **Run → Run All Cells**。看到 `passed: true` 后继续 06、07、08、09、10。每个文件有独立变量和新结果目录，无需继承前一个内核。
4. 05～10 的默认步骤只用 CPU/NumPy，不下载 bitstream。08b 默认 `RUN_RF=False`。已有 TX4→RX2 接线可保留，软件步骤不依赖它。

也可以在 Terminal 一次执行所有软件阶段：

```bash
cd afdm_workbench
python3 -m afdm_lab.cli suite
```

终端会打印结果绝对路径。现有目录不覆盖；重新执行会建立新目录。仅需 Python 3.8+ 和 NumPy，先用板上现有 NumPy；不要为了运行本包替换 PYNQ 环境。

## 分文件顺序与判断依据

| 文件 | 做什么 | 默认应看到什么 |
|---|---|---|
| `05_afdm_channel_estimation.ipynb` | 从独立训练字段估计未知时延、多普勒、复增益 | 6/6，通过；无噪声与 25 dB 三种场景均 0 比特错 |
| `06_afdm_framing_sync_crc.ipynb` | 重复前导捕获、整数采样定时、公共频率旋转校正、消息/序号/CRC | 6/6，通过；中文消息与序号一致 |
| `07_afdm_iq_waveform_export.ipynb` | 生成三帧已知消息的任意 I/Q | `tx.iq16` 及相邻 JSON、配置和已知消息参考 |
| `08_afdm_offline_capture_receiver.ipynb` | 文件量化、模拟采集、导入与离线同步解调 | 3 帧、CRC 正确、PER=0；标签明确为模拟 |
| `08b_pynq_replay_capture.ipynb` | 已验证硬件的回放/抓取入口 | 默认显示“射频操作未执行”；目前不能用原 OFDM 固件启用 |
| `09_afdm_fixedpoint_rtl_vectors.ipynb` | Q2.14/Q1.15 位精确参考、ROM 与预期值 | 定点 4096 比特中 0 错；输出 `.mem`；RTL 另行仿真 |
| `10_afdm_software_stability.ipynb` | 24 个随机帧、不同起点/相位/频率/分数多普勒 | 24/24、PER=0、已接收 24576 比特中 0 错 |

输出目录位于 `afdm_workbench/afdm_runs/`，均有 `summary.json`。保存这些目录后再反馈结果；界面出现的历史日期可能仍来自板卡时钟。

终端分步入口如下，`--output` 必须是一个尚不存在的新目录：

```bash
python3 -m afdm_lab.cli estimation
python3 -m afdm_lab.cli frames
python3 -m afdm_lab.cli waveform
python3 -m afdm_lab.cli offline
python3 -m afdm_lab.cli fixedpoint
python3 -m afdm_lab.cli stability --frames 24
python3 -m unittest discover -s tests -v
```

## 协议和估计器范围

默认 N=64、CPP=16、QPSK、c1=5/128、c2=√2/4096。前导为两个重复的 64 点段和一个 64 点分隔段；之后是 4 个训练块、8 个数据块和 16 个尾部零。单帧 1168 个复数采样，数据载荷最多 113 字节，包头包含版本、序号、长度和 CRC32。中文按 UTF-8 字节计数。

本包使用**独立已知训练字段**，通过稀疏时延/多普勒字典搜索、连续分数多普勒细化和复增益最小二乘拟合信道。接收器不接收真实路径、发送比特或真实信道矩阵；真值仅在软件评估器计算 NMSE/BER 时使用。该方案有额外训练开销，不能称为论文的嵌入式单导频算法。[AFDM 原论文](https://arxiv.org/html/2204.12798v2)

当前搜索先验为时延 0～8、最多 3 径、归一化多普勒 ±3，每个整数时延最多一条路径；测试主径时延为 0 且强于其他路径。模型中每径使用 `exp(-j 2πνt/N)`，相位随连续采样时间推进。相同整数时延上的多个多普勒分量、弱首径/强晚到径捕获、分数采样时延、采样时钟漂移、帧内增益变化及 FEC 尚未验证。

同步估计的公共频率包含主径多普勒；没有外部参考时，不能把它解释为独立、本振物理 CFO 的估计。软件 SNR 为发射波形平均功率与每复采样噪声方差之比，不是 Eb/N0，不用于推断实际射频增益或宣称 AFDM 优于 OFDM。

## 真正进入射频前需要的工程

只读检查厂家 `rfsoc47dr/rfsoc_ofdm.hwh`：三个 DMA 均 `MM2S=0, S2MM=1`。`Transmitter` 是发射观察点的采集 DMA，不能因为名称里含发射就用于任意波形播放。

本机也存在裸机 `PZ_RF47DR.xpr`、`rfsoc_top.v` 和 `system.bd`，可作为板级时钟/RFDC/约束的移植参考；它们并非已经重建验证的 PYNQ 回放 Overlay。本包没有复制或修改厂家工程。只读清单工具为：

```powershell
python scripts/audit_vendor.py 'C:/Users/Administrator/Desktop/FPGA-P047Pro-RFSoC' --output artifacts/vendor-audit-new.json
```

板级工作顺序：

1. 在任务工程中接入 MM2S→回放缓存→DAC，ADC→有限采集窗→S2MM；复用已核对的板级引脚、LMK/RFDC 初始化。
2. 将本包 32 位单复采样接口适配到 RFDC 多采样/多流接口，实现实际需要的插值/抽取、跨时钟域和复位。不能把 1 MHz 软件波形直接当成 RFDC 固有速率；修改配置数值不会自动完成重采样。
3. 实现寄存器、同步触发、状态与计数；验证发射装载完成后才开始回放、接收 TLAST、捕获样本数、通路延迟和幅度。不要依赖两次 Python MMIO 写操作精确同时触发 ADC/DAC。
4. 通过目标器件综合、实现和时序检查，保存 bit/hwh SHA-256。当前电脑 Vivado 2023.1 的 `xczu47dr` 综合因缺少 Synthesis/器件许可失败，尚未生成本包板级 bitstream。
5. 实际确认 TX4→RX2 的信号路径、数据率、I/Q 顺序与缩放后，在新的配置中填写 `configs/p047pro_unverified.json` 的字段和测量依据。改成 `true` 本身不完成硬件验证。
6. 用户手动初始化已验证 Overlay、时钟与 RFDC，再运行 08b。默认配置会在分配 PYNQ 缓冲前停止，避免把软件演示误当实际采集。

硬件模块、位宽与仿真方法见 [hardware/README.md](../hardware/README.md)。S2MM 完成依赖正确 TLAST；DMA 长度受 IP 的配置限制。[PYNQ DMA 文档](https://pynq.readthedocs.io/en/latest/pynq_libraries/dma.html)

## 导入真正的 I/Q

新通路输出无文件头、小端 int16 `[I0,Q0,I1,Q1,...]`，每个复数 4 字节，且接收数据率已与发射协议一致时，可以注册已有文件：

```python
from pathlib import Path
from afdm_lab.core import Config
from afdm_lab.rf import register_external_capture

# 使用已实测的协议采样率和 ADC 缩放，不直接照抄下面的变量值。
cfg = Config(sample_rate_hz=MEASURED_PROTOCOL_RATE_HZ)
register_external_capture(
    Path("/完整路径/rf_rx.iq16"), cfg, counts_per_unit=MEASURED_ADC_SCALE,
    acquisition={"source": "实际采集通路", "bitstream_sha256": VERIFIED_HASH,
                 "rate_and_packing_evidence": "填写实测记录路径"})
```

然后执行：

```bash
python3 -m afdm_lab.cli decode --input /完整路径/rf_rx.iq16 --reference /07结果目录/payload_reference.json
```

每个 `.iq16` 文件旁必须有同名 `.iq16.json`，包含采样数、采样率、缩放、Config 和 SHA-256。导入会核对字节数、摘要和速率，不自动重采样。不提供已知消息参考时，只报告 CRC 接收帧，不能据此给出总体 PER。OFDM 的 1024 点均衡后星座不是这里需要的原始 AFDM ADC 采集。

## 后续验收

实际 RF 路线先做单径/短消息，再多帧与幅度、频偏、采集窗扫描；逐次保存原始 I/Q、配置、CRC、已知载荷比对与漏帧统计。至少补齐三轮独立初始化。发射 payload、bit/hwh、采样率和线缆路径必须一同归档。

PL 路线先将串行参考核对照通过，再换为满足实际吞吐的 FFT/chirp 结构；核对缩放、输出顺序和 CPP。接着迁移同步、信道估计/检测和帧统计，检查 CDC、时序、丢样/溢出/欠载和持续运行。当前 RTL 是功能模块，不是完整全实时 AFDM 收发机。
