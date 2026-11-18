# OFDM 空口、B210 接收与基线的执行顺序

准备日期：2026-11-18。用户已确认：接收电脑 Windows，SSMA/SMA 转接线已有，天线频段暂未知。本文件是后续计划和操作入口，没有执行新的板卡、B210 或空口实验。先完成步骤 1～4，再根据天线与读回参数确定步骤 5～7。

## 1. 保留 P047Pro 原有回环，读回参数

先保持已经跑通的 TX4→RX2 同轴回环。在原 OFDM 02/03 Notebook、原有内核中添加一个代码单元。不要为了这一步新建第二个控制 Overlay 的内核。

```python
print('modulation:', ofdm_hw.ofdm_transmitter.modulation)
print('digital_tx_gain:', ofdm_hw.ofdm_transmitter.gain)
print('tx_enable:', ofdm_hw.ofdm_transmitter.transmit_enable)
print('DAC_MixerSettings:', ofdm_hw.dac_block.MixerSettings)
print('ADC_MixerSettings:', ofdm_hw.adc_block.MixerSettings)
print('DAC_NyquistZone:', ofdm_hw.dac_block.NyquistZone)
print('ADC_NyquistZone:', ofdm_hw.adc_block.NyquistZone)
```

把完整输出保存。上述仅查询现有对象，不调用 get_frame、不下载 bitstream、不修改频点或增益。若 ofdm_hw 不存在，先按原演示初始化流程在该内核加载现有 OFDM。

本地厂商 overlay.py 默认 DAC 混频频率为 +600 MHz、ADC 为 -600 MHz，NyquistZone=1。它们是代码默认值，不是本次读回值。RFDC 的采样率、PL 速率转换和观察点采样率需要分别确认，不能用默认 20 MHz 绘图标签代替实际空口带宽。

天线频段未知时，先完成接收机检查；不要直接照抄 2.4 GHz 或把默认 600 MHz 当成已匹配天线的空口配置。

## 2. Windows 识别 B210

本轮只需要 B210 通过 USB 3.0 接 Windows。P047Pro 保持原有回环。本轮不要求把 P047Pro TX4 连接到 B210。

先在 PowerShell 输入：

```powershell
Get-Command uhd_find_devices,uhd_usrp_probe,rx_samples_to_file -ErrorAction SilentlyContinue
```

找不到命令，可能是未安装或 PATH 未配置。使用实验室已有、与该 B210 匹配的 UHD 环境，或按 [Ettus Windows 安装说明](https://files.ettus.com/manual/page_install_binary.html) 安装官方 Windows UHD 二进制、依赖和 USB 驱动，再重新打开 PowerShell。本轮使用 UHD 自带的 C++ 工具，不依赖 Python UHD 包。

安装目录不是固定保证；常见为 C:\Program Files\UHD。可在实际安装目录中查找：

```powershell
Get-ChildItem -LiteralPath 'C:\Program Files\UHD' -Recurse -Filter 'rx_samples_to_file.exe'
```

找到后可用 `& '完整exe路径'` 调用。随后执行：

```powershell
uhd_find_devices --args 'type=b200'
uhd_usrp_probe --args 'type=b200'
rx_samples_to_file --help
```

B210 属于 UHD 的 b200 系列驱动。若接有多个设备，后续 args 应加入检测出的 serial，避免选错。识别成功应能看到 B210 产品信息、序列号和 RX 通道。保留输出；失败时先处理识别、驱动或 images 错误，不进入采集。

## 3. 仅做短时接收与文件通路测试

这是接收机保存能力测试，不是完整 OFDM 空口解调。600 MHz 是 B210 的接收调谐测试频点；即便没有接收到 OFDM，记录噪声也能检查 USB 和文件通路。P047Pro 不需要新增空口发射。

在 Windows PowerShell 进入当前项目，并新建目录：

```powershell
Set-Location 'C:\Users\Administrator\Desktop\FPGA-P047Pro-RFSoC\09.afdm_development'
$taskCaptureDir = Join-Path 'captures' ('b210_smoke_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $taskCaptureDir
$taskIqFile = Join-Path $taskCaptureDir 'rx_smoke.fc32'
$taskLogFile = Join-Path $taskCaptureDir 'uhd_capture.log'
```

先确认安装版本的 `--help` 支持下面选项，再执行：

```powershell
rx_samples_to_file --args 'type=b200' --channels '0' --ant 'RX2' --freq 600e6 --rate 10e6 --bw 8e6 --gain 0 --nsamps 1000000 --type float --file $taskIqFile --stats 2>&1 | Tee-Object -FilePath $taskLogFile
```

这是单通道 RX，初始 RX gain=0 dB，请使用 probe 中对应通道的 RX2 口。`--type float` 输出无文件头的复数 float32，即每个复数采样 8 字节；预期 1,000,000 点、8,000,000 字节。以控制台 Actual RX Rate 为准，保存频率/增益/带宽的实际读回信息和完整日志。

请求的 10 MS/s、8 MHz 滤波带宽只用于初次接收保存测试。它们没有确认能覆盖厂家 OFDM 的完整频谱，不据此评价 OFDM 解调、通信或感知性能。

如果日志出现 overflow、timeout、丢包/序号错误，或者没有收满采样，当前记录不能用于相干感知或连续帧统计。单纯文件长度正确也不能证明无采样间断。

## 4. 在 Windows 检查保存文件

使用电脑的 Python/Miniconda 环境，不是在板端 Jupyter 读取 Windows 文件。若 UHD 的 Actual RX Rate 确为 10.000000 MS/s：

```powershell
python scripts/check_b210_iq.py $taskIqFile --rate-hz 10000000 --expected-samples 1000000
```

如果实际采样率不同，把 rate-hz 改成实际值。可选添加 `--plot` 输出 PNG，需要该电脑 Python 已有 matplotlib。

通过文件检查时会看到 `samples=1000000`、`bytes=8000000`、`file_checks_passed=true`。工具输出相对频谱 CSV 和 JSON，报告明确保留 `ofdm_decoded=false`、`ber_measured=false`、`sensing_measured=false`。它不使用 UHD、不连接硬件、不修改原始 I/Q。幅度接近满量程只作诊断，不能替代 ADC 饱和和流连续性的实测判断。

本轮先反馈：步骤 1 的板端读回、uhd_find_devices/uhd_usrp_probe、Actual RX Rate、接收样本数和错误日志。得到这些输出后才确定正式空口采样参数。

## 5. 天线频段确认后再接入 P047Pro 空口

正式链路：P047Pro TX4 → 发射天线 → 空口 → 接收天线 → B210 通道 0 RX2 → USB 3.0 → Windows。

先从天线标签、型号或实验室资料确认频段；再确认两端接头型号、公母和实际 RF 通路。600 MHz 与实验室天线若不兼容，需要先核对 RFDC 混频、NyquistZone 和板上通路，不只改一个显示频率。

需在改接线前停止图表自动采集与发射，并按板卡说明完成接线/上电。B210 有线验证另需计算输入功率和衰减；[官方手册](https://files.ettus.com/manual/page_usrp_b200.html)规定 RF 输入不超过 -15 dBm，回环至少 30 dB 衰减，并仍需满足实际输入上限，不能把 P047Pro 发射口直接连入 B210。

厂商 Overlay 初始化最后会调用接收星座 get_frame。如果只保留 P047Pro 发射而 RX2 没有可解调信号，原初始化/界面可能等待。此时需要经过板端验证的“发射专用初始化”：发射先关闭、不等待同板星座，再以确认的参数启动。不要在等待 get_frame 时反复开启新内核抢占硬件；这个模式尚未在本轮实现或验证。

正式采集要：确认频点与实际采样率、模拟滤波带宽足以覆盖完整 OFDM 占用带宽；固定 RX 增益；在相同接收设置下保存发射关闭、打开、再关闭三组记录，验证目标频谱随发射控制变化。先比较相对频谱和接收质量，不把当前未标定值写成 dBm。

## 6. 通信基线如何取得

必须先从厂家模型/源码或对照数据确认 FFT 长度、CP、有效子载波、导频/前导、帧结构、调制映射、实际基带速率和发送数据源。当前 AFDM 接收器的自定义帧不能直接用来解调厂家 OFDM 波形。

| 顺序 | 要做的事情 | 留存结果 |
|---|---|---|
| A | 保存 B210 原始 I/Q 与实际配置 | 波形、日志、配置和丢样状态 |
| B | 按厂家帧结构实现离线 OFDM 同步与解调 | 帧起点、频偏、FFT 后符号与残差 |
| C | 获取已知/可重建的发送比特并对齐 | 发送参考、接收比特、匹配帧号 |
| D | 按定义统计 EVM、BER、PER 和有效吞吐 | 样本/比特/帧总数、漏帧与误差 |
| E | 固定场景独立重复，再逐项改变距离或增益 | 每组配置、原始数据与统计表 |

只有频谱说明接收到了能量，完整通信指标还需要接收处理与参考数据。没有帧号、发送总数和校验的厂家演示，不能直接报告 PER=0 或有效消息吞吐。

## 7. 感知基线如何取得

先与导师明确目标：测距、测速或两者；然后明确单站回波、双基地回波、还是单程通信链路。P047Pro 发射、B210 接收的分置几何，不应直接把单程或双基地时延套入单站 c*tau/2 距离公式。

需要已知发送符号/波形、时间频率同步、固定相干处理时长及通道延迟标定。可进一步评估 B210 双接收通道中“直达参考 + 目标回波”的方案；共同采样率、LO、通道相位/延迟和数据吞吐仍要验证。独立 P047Pro/B210 时钟不能直接视为具有绝对传播时间基准。

先做固定位置目标与空场对照，再做受控移动目标；保存参考信号、接收 I/Q、几何和距离/速度真值。输出检测图与误差，再谈分辨率和多次重复统计。当前均衡后星座数据不是完整的感知观测。

简单单站模型的距离分辨率约 c/(2B)，例如有效带宽 20 MHz 时约 7.5 m；这说明实验设计要匹配带宽，不意味着所有估计精度都固定等于这个分辨率，也不能照搬为双基地几何的距离定义。

通信与感知各取得基线后，再固定带宽、功率、开销和场景比较 AFDM。参考：[OFDM 通信感知处理示例](https://www.mathworks.com/help/phased/ug/joint-radar-communication-using-pmcw-and-ofdm-waveforms.html)，网页参数不等于本项目参数。

## 官方来源

- [Windows UHD 安装](https://files.ettus.com/manual/page_install_binary.html)
- [B210 配置、连接与输入限制](https://files.ettus.com/manual/page_usrp_b200.html)
- [rx_samples_to_file 官方源码与参数](https://github.com/EttusResearch/uhd/blob/master/host/examples/rx_samples_to_file.cpp)

每次实际板上实验按 docs/experiment-template.md 记录；本文所有硬件步骤当前均未执行，不计作验收通过。
