---
created: 2026-11-18
updated: 2026-11-18
type: experiment
tags:
  - 通信基础
  - OFDM
aliases:
  - OFDM最小软件实验
---

# FFT 与 IFFT 软件实验

主笔记：[[01-OFDM入门与实现过程]]；前置：[[OFDM-01-比特、IQ与调制]]、[[OFDM-02-子载波与正交性]]。

## 频域 X 和时域 x

大写 $X[k]$ 表示子载波 k 上的复数值，小写 $x[n]$ 表示时刻 n 的复数采样。

采用单位化变换时，发送端：

$$
x[n]=\frac{1}{\sqrt N}\sum_{k=0}^{N-1}X[k]e^{j2\pi kn/N}
$$

接收端：

$$
X[k]=\frac{1}{\sqrt N}\sum_{n=0}^{N-1}x[n]e^{-j2\pi kn/N}
$$

IFFT 的结果包含所有子载波的叠加。它把“每路子载波的符号”换成“依次发送的时间采样”；两种表示中的一个数组元素含义不同。

NumPy 的 `norm="ortho"` 让正反变换都包含 $1/\sqrt N$。默认 FFT 缩放方式不同，也可以配对使用，但不能把不同缩放约定混在一起。

## 复制运行这个理想实验

依赖 Python 和 NumPy。以下代码可在普通 Python Notebook 执行，不需要 PYNQ，不加载 FPGA。它使用 64 点 IFFT、48 个数据子载波、4 个已知导频和 16 点 CP；参数仅用于教学。

```python
import numpy as np

rng = np.random.default_rng(47047)
N, L = 64, 16

# 使用 FFT 数组索引；后半部分对应负频率。
occupied = np.r_[np.arange(1, 27), np.arange(38, 64)]
pilot_idx = np.array([7, 21, 43, 57])
data_idx = np.setdiff1d(occupied, pilot_idx)

# 每个数据子载波有两个 QPSK 比特。
bits = rng.integers(0, 2, size=(data_idx.size, 2))
b = bits.astype(float)
symbols = ((1 - 2*b[:, 0]) + 1j*(1 - 2*b[:, 1])) / np.sqrt(2)

# 组装频域符号，空位置保持为零。
X = np.zeros(N, dtype=complex)
X[data_idx] = symbols
X[pilot_idx] = 1.0

x = np.fft.ifft(X, norm="ortho")
tx = np.r_[x[-L:], x]

# 理想通道：不添加噪声、多径或频偏。
rx = tx.copy()
y = rx[L:L+N]
Y = np.fft.fft(y, norm="ortho")
z = Y[data_idx]

received_bits = np.column_stack((z.real < 0, z.imag < 0)).astype(int)
errors = np.count_nonzero(received_bits != bits)

print("数据子载波：", data_idx.size)
print("导频子载波：", pilot_idx.size)
print("有效采样/含CP采样：", x.size, tx.size)
print("比特错误：", errors, "/", bits.size)
print("频域恢复一致：", np.allclose(X, Y))
```

应得到：48 个数据子载波、4 个导频、64/80 个采样、0/96 个比特错误、`True`。浮点误差可能存在，所以频域数值比较用 `allclose`。

这里导频已经放入，但理想信道为 1，不需要实际估计。加入未知信道后，要实现 [[OFDM-05-同步、导频与均衡|估计和均衡]]。

## 这个实验验证了什么

它验证了子载波分配、QPSK 映射、IFFT/FFT 配对、CP 插入/去除和理想比特恢复。同步位置与通道都是已知条件，尚未验证真实收发机。

后续可一次只改变一个条件：先加噪声，再加静态多径，然后加入未知起点和频偏。静态多径条件先看 [[OFDM-04-循环前缀CP与多径]]。

官方说明见 [[OFDM-07-参考资料与阅读顺序#OFDM 调制接口参考]]。返回 [[00-OFDM学习导航]]。
