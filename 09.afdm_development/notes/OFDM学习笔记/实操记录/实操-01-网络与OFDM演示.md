---
created: 2026-11-18
updated: 2026-11-18
type: operation-record
tags:
  - P047Pro
  - 实操记录
---

# 网络与 OFDM 演示操作记录

总记录：[[02-P047Pro已完成操作全记录]]。原理对应：[[OFDM-06-P047Pro实现与实验对应]]。

## 1. 板端终端可用，查看网络

用户提供的终端提示为 `xilinx@pynq:~$`，运行过 `ifconfig`。关键输出为：

```text
eth0:1: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>
inet 192.168.2.99  netmask 255.255.255.0  broadcast 192.168.2.255
```

普通 `eth0` 段没有显示 IPv4，IPv4 出现在别名 `eth0:1`。当时已具备该地址，不应因为第一段只有 IPv6 就判断整个有线接口没有 IPv4。

没有保存具体网络修改命令，也没有记录本次终端究竟通过串口还是 SSH 进入。因此只确认“板端终端和该 IPv4 地址可用”，不补写其他配置为已完成。

## 2. 浏览器进入 JupyterLab

历史入口：

```text
http://192.168.2.99:9090/lab
```

用户随后确认已进入 JupyterLab，截图进一步显示浏览器地址：

```text
192.168.2.99:9090/lab/tree/rfsoc_ofdm/02_rfsoc_ofdm_demonstrator.ipynb
```

这是浏览器访问地址；`/root/jupyter_notebooks/...` 或 `/home/xilinx/jupyter_notebooks/...` 则是板端文件系统路径，二者含义不同。

![[P047Pro-01-Jupyter文件列表.png]]

截图中 `01_ofdm_software_loopback.ipynb` 只是被选中，不能据此将该软件回环 Notebook 的所有实验记作已完成。

## 3. TX4→RX2 接好 OFDM 回环

用户明确反馈已经将 TX 与 RX 回环；本项目指导并沿用的 OFDM 通道为 **TX4→RX2**。

```text
发送硬件 → TX4 → 射频线缆 → RX2 → 接收硬件
```

完整射频频点、衰减器配置和实际接头照片尚未归档。笔记没有补造这些参数。

## 4. 打开厂家 02 演示并初始化

运行文件为：

```text
rfsoc_ofdm/02_rfsoc_ofdm_demonstrator.ipynb
```

从电脑归档的执行 Notebook 中读取到的初始化代码是：

```python
from rfsoc_ofdm.overlay import Overlay
import ipywidgets as ipw

ofdm_hw = Overlay()
```

后续截图显示接收星座控件单元格已经执行，图上有四个点簇。结合用户反馈，可以记录厂家演示已运行到接收观察阶段。

这属于现成 OFDM Overlay 的使用记录。镜像烧录、启动拨码、安装包命令、源码重建等步骤未取得逐项历史证据。

## 5. 显示接收星座，选择调制并刷新

截图中的控件显示代码是：

```python
ipw.VBox([
    ofdm_hw.inspectors['constellation'].constellation_plot(),
    ofdm_hw.inspectors['constellation'].plot_control()
])
```

已确认完成的操作顺序：

1. 显示调制选择与接收星座控件。
2. 选择 QPSK，启动图形刷新，观察四个点簇。
3. 切换 16-QAM，观察十六个点簇。
4. 后续分别做保存、重载与重绘，见 [[实操-02-星座采集保存与重绘]]。

![[P047Pro-02-OFDM实时QPSK星座.png]]

图中的播放/停止按钮控制图形采集刷新。保存数据前应先停止自动刷新并等当前采集结束，避免与手动取帧争用 DMA；这属于原操作指导，后续复现仍应遵循。

## 6. 进入 OFDM 03 综合界面

打开文件：

```text
03_voila_rfsoc_ofdm_demonstrator.ipynb
```

截图中代码执行编号为 `[3]`，调用为：

```python
ofdm_hw.ofdm_loopback_application()
```

当时显示：

- 左侧 Transmit Spectrum 页、Interpolated 观察点。
- 以零频附近为中心的发射频谱。
- 右侧调制为 16-QAM，接收星座有十六个点簇。

![[P047Pro-06-OFDM综合界面.png]]

当时提供的切换建议是停止 02 的刷新、保存并关闭其内核，再在 03 初始化。截图只确认 03 运行结果，不把未记录的关闭内核动作另行计为已验收项目。

接收频谱、收发时域页、持续刷新和三轮独立初始化并未逐项确认完成。频谱纵轴为相对归一化 dB，而不是经过标定的绝对射频功率。

## 容易混淆的两个 03

- `03_voila_rfsoc_ofdm_demonstrator.ipynb`：厂家 **OFDM 硬件演示综合界面**。
- `03_afdm_cpp_multipath.ipynb`：后续 **AFDM Python 软件自检**。

两者不是同一个实验。AFDM 阶段见 [[实操-03-AFDM软件02至04]]。
