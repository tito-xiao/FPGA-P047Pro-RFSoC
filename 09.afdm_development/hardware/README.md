# AFDM 功能 RTL 与板级接口边界

本目录是自编 RTL 的功能参考和回放/采集组件，不含 P047Pro 可烧写整机工程。未修改厂家工程、下载 bitstream 或运行板卡。当前 `xczu47dr` 综合受本机 Vivado 许可缺失阻挡；实际报告为未综合成功、未布局布线、未验证时序。

## 已实现模块

| 源文件 | 接口/功能 | 条件 |
|---|---|---|
| `axis_complex_rotator.sv` | 32 位复数 AXI 流、逐点 chirp ROM、饱和 | 系数 Q1.15，数据 Q2.14，低 16 位 I、高 16 位 Q |
| `axis_afdm_transform.sv` | 完整单位化 DAFT/IDAFT 系数 ROM、串行复 MAC | 默认 N=64，系数含 1/√N；48 位累加，右移 15、向负无穷取整后饱和 |
| `axis_block_prefix.sv` | 缓冲 N 点、输出 L 点 CP 和原块 | 是 CP；仅在所选 AFDM 参数使 CPP=CP 时适用 |
| `axis_prefix_strip.sv` | 去掉同步块的前 L 点 | 输入必须已完成帧同步；不搜索边界 |
| `afdm_tx_block.sv` | IDAFT→前缀 | 不生成包头、训练或前导 |
| `afdm_rx_block.sv` | 去前缀→DAFT | 检测、信道估计、同步和 CRC 仍在 CPU |
| `axis_iq_replay.sv` | MM2S 装载固定 WORDS、开始/重复/边界停止 | 必须等 `loaded=1` 再发 start；重装载需复位 |
| `axis_capture_window.sv` | arm 后有限窗口抓取、缓存后 S2MM 输出 TLAST | 同时钟；输入永远 ready，窗外样本主动忽略，忙时 arm 有计数 |

默认 N=64、c1=5/128：`2*N*c1=5` 且 N 为偶数，软件 CPP 的相位因子为 1，可以用 CP。一般 c1 需要增加实际 CPP 相位旋转，不能直接使用当前 CP 模块。

RTL 每个复数采样 32 位，I/Q 都是有符号 int16。它不等于厂家裸机 RFDC 的“多流、每拍四个实采样”接口，也不等于尚未核对的 PYNQ RFDC 内部数据率。接入前需要实际打包、时钟与速率转换。

## 吞吐与缓冲

变换核每块至少 N² 个 MAC 时钟，另有输入装载、输出握手开销。它用于逐比特对照，不能按模块存在就认定满足 RFDC 连续采样率。最终需要 FFT/chirp 的高吞吐结构或经过预算的多核设计，并重新验证定点缩放和接口。

回放/采集模块默认 WORDS=64 便于测试。真实三帧波形默认 3696 点，必须在板级实例中增大参数，发送端按配置长度补零，接收窗还需要覆盖起点、路径延迟和末帧。`dma_capture` 接口检查长度、MM2S/S2MM、TLAST 配置与超时。

采集窗不要求 RF-ADC 停流：仅记录 arm 后的 WORDS 个有效采样，其余丢弃是设计的窗口行为。当前不支持边采边发给 DDR；忙时重触发计数，跨时钟、双缓冲和持续采集未实现。触发须由板级逻辑同步发给回放与采集，考虑射频通路时延；Python 两次写寄存器不能保证采样级对齐。

## 运行位精确仿真

电脑已安装 Vivado 2023.1。先在仓库根目录生成向量，再运行：

```powershell
python -m afdm_lab.cli fixedpoint --output artifacts/rtl_sim_new
./hardware/run_xsim.ps1 -VivadoBin 'D:/XIAO/Software/Xilinx/Vivado/2023.1/bin' -WorkDirectory 'C:/Users/Administrator/Desktop/FPGA-P047Pro-RFSoC/09.afdm_development/artifacts/rtl_sim_new'
```

测试平台固定 N=64、L=16、3 块，使用生成的 `.mem`。若修改 N/L、系数格式或帧数，需同时更新 testbench 和参考模型，不能拿不匹配向量宣称通过。

`tb_all.sv` 测试全幅 rotator、TX→CP→去 CP→RX、回放→采集、随机 valid/ready、停顿时数据/TLAST 稳定、逐拍预期值、TLAST 位置和忙时重复 arm。此次 XSim 实际输出：

```text
RTL PASS: bit-exact TX/RX, rotator saturation vectors, prefix, replay/capture, TLAST and randomized backpressure
```

这是 RTL 功能仿真，不代表器件时序或板上射频通过。尚未穷举复位中断、错误 TLAST 的所有恢复路径或多时钟域。

## 目标器件独立综合

需有覆盖 `xczu47dr-ffve1156-2-i` 的有效 Vivado 许可。工作目录必须包含刚生成的系数 ROM：

```powershell
Set-Location 'C:/Users/Administrator/Desktop/FPGA-P047Pro-RFSoC/09.afdm_development/artifacts/rtl_sim_new'
& 'D:/XIAO/Software/Xilinx/Vivado/2023.1/bin/vivado.bat' -mode batch -source 'C:/Users/Administrator/Desktop/FPGA-P047Pro-RFSoC/09.afdm_development/hardware/synthesize.tcl'
```

`synthesize.tcl` 仅尝试模块 OOC 综合，输出资源、综合时序与 DCP；不创建板级 RFDC/PS 工程，不执行实现或下载。本机本次实际停止于：

```text
[Common 17-348] Failed to get the license for feature 'Synthesis' and/or device 'xczu47dr'
[Common 17-345] A valid license was not found
```

约束中的 10 ns 只是 OOC 目标时钟，并非测得的板卡时钟，也不证明实现达标。

## 板级接入

现有厂家 PYNQ OFDM 三个 DMA 全为 S2MM，完整 RF 裸机参考 XPR 则存在于厂家工程。应在任务工程中检查其 IP/约束/时钟、RFDC 多流顺序和 Linux/PYNQ 集成方式，接入新增回放与采集组件，而不是覆盖原 OFDM 基线。

必须完成 MM2S/S2MM、DDR AXI 地址与缓存、AXI-Lite/控制寄存器、同步触发、CDC、RFDC 格式/速率适配、LMK 配置、复位及状态计数，再做布局布线和板上验证。本目录尚无该板级整合结果。08b Notebook 和 `afdm_lab/board.py` 只是已验证硬件的控制接口，默认拒绝不完整配置。
