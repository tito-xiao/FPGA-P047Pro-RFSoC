# AFDM 后续阶段软件与功能 RTL 检查

## 目标与环境

日期 2026-11-17，分支 `dev/xiao`，任务改动未提交。按用户“一次实现、分文件执行”的要求，将 04 后的软件阶段做成可独立执行文件，补充定点与功能 RTL，并明确实际板级工作边界。

电脑 Windows、NumPy 2.3.5；Python 精确版本与源码摘要见[机器可读结果](20261117-afdm-workbench-results.json)。Vivado/XSim 2023.1，目标器件 `xczu47dr-ffve1156-2-i`。未连接或操作板卡，没有下载固件；16 GB 厂家工程只读核对，未重复复制。本次不使用实际 RF 增益、频点或线缆作为软件参数。

软件参数 N=64、CPP=16、QPSK、c1=5/128、c2=√2/4096；独立训练 4 块、数据 8 块。默认 1 MHz 是生成文件的协议速率，并非实际 RFDC 已确认速率。模型时延 0/2/5，静态、整数和非栅格分数多普勒三场景；每个整数时延最多一个多普勒分量。

## 执行与结果

1. `python -m afdm_lab.cli suite --output artifacts/software_run_20261117_final --frames 24`：六个软件阶段连跑通过。信道估计和消息链路各 6/6；三帧量化文件模拟闭环 CRC 全通过、PER=0；定点 4096 比特 0 错；24/24 软件帧成功、PER=0、已接收 24576 比特 0 错。软件结果不用于证明射频通过。
2. `python -m unittest discover -s tests -v`：最终 21/21 通过。覆盖独立矩阵公式、一般 CPP/连续相位、非栅格训练估计与外推、未知起点/CFO、连续帧、中文与 CRC 翻转、噪声空采集、I/Q 摘要/速率、定点饱和、未验证配置拒绝、模拟 DMA 装载先于触发、超时/分配失败清理和外部文件注册。DMA 测试全部为 mock，不接触设备。
3. `scripts/check_notebooks.py`：05、06、07、08、08b、09、10 共 7 文件的代码单元格在独立命名空间运行通过；08b 保持 `RUN_RF=False`，没有导入 PYNQ。分发 Notebook 保持空输出。
4. `hardware/run_xsim.ps1`：真实 XSim 编译、展开和功能仿真通过，在约 171575 ns 完成。N64/L16、3 块定点 TX→CP→去 CP→RX、全幅旋转、回放/采集、TLAST、随机 valid/ready 与输出停顿稳定均对照通过。日志 `artifacts/rtl_sim/simulation.log`。
5. `hardware/synthesize.tcl`：实际尝试 OOC 综合，因 `[Common 17-348]`、`[Common 17-345]` 缺少 Synthesis/xczu47dr 许可失败。没有资源报告通过、实现、时序闭合或 bitstream。日志 `artifacts/rtl_sim/synthesis_console.txt`、`synthesis.log`。这与已通过的功能仿真分别记录。
6. `scripts/audit_vendor.py`：HWH 解析出三个 DMA 均 `MM2S=0/S2MM=1`；裸 RF XPR、BD 与顶层均存在。只读文件清单及 SHA-256 位于 `artifacts/vendor_audit_20261117.json`。本次未打开或重建该 XPR。

同一默认软件向量分别在完整 CLI 连跑、Notebook 独立执行和单元检查中得到上述结果；这不是板上三次初始化。机器可读结果中保留原软件运行、RTL 日志、失败综合日志和核心源码的 SHA-256。

## 源码与分发

- `afdm_lab/`：NumPy 模型、训练估计、帧协议、接收、I/Q、定点与受配置约束的 PYNQ 适配。
- `notebooks/05*`～`10*` 及 `08b*`：独立执行入口，不依赖 02～04 的内核变量。
- `hardware/rtl/`、`hardware/tb/`：本项目功能模块与仿真；串行矩阵变换不承诺 RFDC 线速。
- `artifacts/afdm_workbench.zip`：仅打包本项目代码、配置和说明；含逐文件 SHA-256 清单，打包后检查 ZIP CRC 与清单。ZIP 与本机生成数据不进入 Git。

## 结论与下一步

本次实现了后续软件收发链路和可执行定点/RTL 参考，并非所有最终硬件步骤已经完成。接收端从已知训练估计信道，接收流程不读取信道真值；独立训练有额外开销，不能标作论文嵌入式单导频结果。当前测试也不能证明弱首径/强晚径捕获、同延迟多多普勒、分数采样定时、采样时钟漂移或普遍性能优势。

用户下一步只需上传 ZIP、解压并从 05 运行，见[分步说明](../afdm-workbench.md)。板级下一步是接入任意 I/Q 回放/采集及 RFDC 时钟、格式、速率、触发与 CDC，配置有效目标器件工具许可并通过综合/实现，再手动进行 TX4→RX2 实采和离线解调。全实时 PL 同步、信道估计/检测和持续运行验收仍待开发与实测。

本次未改动板卡固件或接线，无法报告板卡结束时的实时状态。
