# P047Pro OFDM 与 AFDM 开发

当前活动开发目录：`C:\Users\Administrator\Desktop\FPGA-P047Pro-RFSoC\09.afdm_development`。主项目入口见[上级目录说明](../README_项目入口.md)。

本项目围绕 P047Pro 板卡，先复现 OFDM 收发与射频回环，再建立可校验、可重建的实现，逐步开展 AFDM 波形研究。已有 OFDM 星座观察与保存重绘的用户证据，AFDM 软件链路、定点参考和功能 RTL 仿真已完成本机检查；实际 AFDM 射频与完整 FPGA 实时收发尚未验证。

## 从这里开始

1. 阅读 [学习开发路线](P047Pro_OFDM到AFDM学习开发路线.md)，了解阶段目标。
2. 阅读 [当前进度](docs/progress.md)，确认已经完成的准备和待验证事项。
3. 按 [复现指南](docs/reproduce.md) 准备环境和记录实验。
4. 开发前阅读 [协作指南](docs/collaboration.md)，在个人分支工作。

## 阶段目标

| 阶段 | 目标 | 当前状态 |
|---|---|---|
| A | 厂家 PYNQ 环境与 OFDM 有线回环 | QPSK/16-QAM 保存与重绘已有截图证据，待重复验证与完整参数归档 |
| B | 已知数据、帧对齐和 BER/CRC/PER 校验 | AFDM 软件消息链路已实现；OFDM 硬件已知数据验证待做 |
| C | 从源码重建并修改 FPGA OFDM | 裸 RF XPR/BD/顶层已定位；适配重建待做，目标器件综合许可缺失 |
| D | AFDM 软件基准与射频原型 | 估计、同步、CRC、I/Q 文件接收与软件回归通过；真实 RF 待做 |
| E | FPGA 实时 AFDM 收发 | 定点与功能模块 RTL 仿真通过；板级集成、时序、实时收发待做 |

阶段 C 的工程获取可与 A/B 并行。上表只记录本仓库已有证据支持的状态；算法、通信和感知性能均需独立验证。

## 仓库组织

```text
README.md                         项目入口
AGENTS.md                         AI 协作约定
P047Pro_OFDM到AFDM学习开发路线.md   总体路线
docs/progress.md                  进度与下一步
docs/reproduce.md                 环境和复现步骤
docs/collaboration.md             Git 与双人协作
docs/experiment-template.md       单次实验记录模板
docs/experiments/                 实际实验记录
.github/                         PR 和任务模板
```

`notebooks/` 包含 02～10 分阶段入口；`afdm_lab/` 为软件包，`hardware/` 为功能 RTL，`scripts/` 提供生成、核对与打包工具，`configs/` 保留默认未验证板级配置。

## 通信基础学习笔记

学习理论可查阅《通信原理知识手册》，从信息量、波形和噪声读到调制、检测、编码与容量，末章汇总常用公式的适用条件。[阅读 PDF](notes/通信原理知识手册.pdf) · [查看 Markdown](notes/通信原理知识手册.md)

从零开始可读[通信原理速查与实验笔记](notes/通信原理速查与实验笔记.md)，按问题查公式、运行三个 NumPy 小实验，或从星座、频谱和误码现象定位故障。

[OFDM 学习导航](notes/OFDM学习笔记/00-OFDM学习导航.md)包含入门主笔记、七篇原理专题和[已完成操作全记录](notes/OFDM学习笔记/02-P047Pro已完成操作全记录.md)，可将该文件夹作为 Obsidian 知识库打开。

## 当前软件入口

**已完成 04 的用户从这里继续：**[05～10 分阶段操作说明](docs/afdm-workbench.md)。支持逐个 Notebook 运行，也支持在完整工具包根目录执行 `python3 -m afdm_lab.cli suite` 一次完成全部软件阶段。08b 的硬件入口默认关闭；当前 OFDM 的 DMA 全为 S2MM，无法直接发送任意 I/Q。

[AFDM 软件基准 Notebook](notebooks/02_afdm_software_baseline.ipynb) 仅依赖 NumPy，包含变换自恢复、矩阵公式对照、能量守恒、OFDM 退化、无噪声比特收发和 AWGN BER 统计。电脑端已执行全部代码单元格；不加载 FPGA，也未做 AFDM 射频验证。使用步骤见[复现指南](docs/reproduce.md#运行-afdm-软件基准)。

[CPP 与静态多径 Notebook](notebooks/03_afdm_cpp_multipath.ipynb) 为独立文件，增加一般 CPP、连续块边界、线性卷积与有效信道矩阵对照，以及真实信道已知时的 ZF/LMMSE 检测。电脑端八项自检通过；尚未实现信道估计或射频收发。

[整数/分数多普勒 Notebook](notebooks/04_afdm_doppler_known_channel.ipynb) 增加逐路径时变相位、连续块相位、解析稀疏结构检查及完整已知信道 ZF/LMMSE 对照。电脑端八项自检通过；三个场景、两种波形的无噪声恢复均为 0/32768 错误，不用于宣称普遍性能优势。

## 分支与协作者

- `main`：经过对应检查的共同基线。当前基线仅包含文档和协作配置，不代表硬件已验证。
- `dev/xiao`：xiao 的日常开发分支。
- 同事账号暂未提供；收到账号后添加协作者，由同事建立自己的分支。

## 外部资料与实验数据

原学习路线中的 `05.教程和源码/...` 等链接指向本地厂家资料，这些文件未随仓库发布，因此在线链接暂不可用。按复现指南在本地准备资料，并记录版本、来源和校验值。源码是否允许公开需逐项确认。

大体积镜像、原始采样、生成的 bitstream、工具缓存及凭据由 `.gitignore` 排除。Git 记录可重建源码、配置、文档和经检查可公开的实验结论；二进制产物另存并在实验记录中注明获取位置和 SHA-256。
