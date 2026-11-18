---
created: 2026-11-18
updated: 2026-11-18
type: reference
tags:
  - 通信基础
  - OFDM
aliases:
  - OFDM详细参考链接
---

# OFDM 参考资料与阅读顺序

主笔记：[[01-OFDM入门与实现过程]]。先读主笔记和专题，再把下面链接作为补充。这里的说明是阅读目标，公式推导与示例另见对应专题。

## OFDM 整体原理

[Introduction to OFDM — MathWorks](https://www.mathworks.com/help/comm/gs/introduction-to-ofdm.html)

配合 [[OFDM-02-子载波与正交性]] 阅读。重点看多个低速子载波怎样叠加、频谱重叠与正交性，以及子载波间隔和有效时间的关系。先理解图，再看推导。

读后尝试解释：一个 OFDM 符号为什么能同时承载多个 QPSK 符号？

## OFDM 调制接口参考

[comm.OFDMModulator — MathWorks](https://www.mathworks.com/help/comm/ref/comm.ofdmmodulator-system-object.html)

配合 [[OFDM-03-FFT与IFFT软件实验]] 阅读。关注 FFT 长度、数据与导频位置、空子载波、CP 长度分别控制什么。MATLAB 接口仅作原理参考，本组 Python 练习不依赖 MATLAB。

## 循环前缀与均衡参考

[Equalization, Convolution, and Cyclic Prefix Addition — MathWorks](https://www.mathworks.com/help/comm/gs/equalization-convolution-and-cyclic-prefix-addition.html)

配合 [[OFDM-04-循环前缀CP与多径]] 阅读。先看 CP 如何从末尾复制到前面，再对照线性卷积、循环卷积及频域补偿的关系。具体成立条件以本笔记和模型假设为准。

## 完整收发机参考

[OFDM Transmitter and Receiver — MathWorks](https://www.mathworks.com/help/comm/ug/ofdm-transmitter-and-receiver.html)

配合 [[OFDM-05-同步、导频与均衡]] 阅读。关注发送、信道、同步、接收和结果统计的组织方式，理解实际链路为什么比一对 FFT/IFFT 多出许多处理。

网页例子的带宽、频率、FFT/CP 等参数属于该例，不是本项目已确认的板卡参数。

## 项目内参考资料

主项目根目录：

```text
C:\Users\Administrator\Desktop\FPGA-P047Pro-RFSoC
```

建议按下面顺序找资料，配合 [[OFDM-06-P047Pro实现与实验对应]]：

| 根目录下的位置 | 建议用途 |
|---|---|
| `README_项目入口.md` | 找到活动开发目录与现有资料 |
| `09.afdm_development\P047Pro_OFDM到AFDM学习开发路线.md` | 查总体路线与厂家资料索引 |
| `09.afdm_development\docs\experiments\20261117-ofdm-capture.md` | 核对已经完成的 OFDM 观察与保存证据 |
| `09.afdm_development\docs\progress.md` | 区分软件、仿真和板上状态 |
| `08.ofdm_afdm\setup\rfsoc_ofdm_p047pro\rfsoc_ofdm` | 对照 Python 驱动和原演示 Notebook |
| `05.教程和源码\5_PYNQ` | 寻找厂家 PYNQ 指南及原始分发材料 |

本地厂家资料保留原位置，便携包只包含这组自编学习笔记。

## Obsidian 使用参考

[Manage vaults — Obsidian 官方帮助](https://obsidian.md/help/manage-vaults)

用 **Open folder as vault** 打开这组笔记所在的文件夹，或把整个笔记文件夹复制进已有知识库。

[Internal links — Obsidian 官方帮助](https://obsidian.md/help/links)

本组用 `[[笔记名]]` 和带显示名称的双向链接组织内容。点击主笔记里的链接可进入专题；反向链接面板可查看哪些笔记引用了当前内容。

返回 [[00-OFDM学习导航]]。
