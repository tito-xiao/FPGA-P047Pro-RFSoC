# P047Pro 已完成操作的回顾整理

整理日期：2026-11-18；分支 dev/xiao，未提交。依据既有聊天、截图、实验记录及本机现存归档，新增 notes/OFDM学习笔记/02-P047Pro已完成操作全记录.md 与四篇实操子笔记，串起网络/Jupyter、TX4→RX2、OFDM 02 星座、采样保存重绘、OFDM 03 综合界面、AFDM 软件 02～04。

已复制 6 张用户聊天截图与 2 张归档星座图到笔记附件，原字节 SHA-256 对照一致；不修改截图、原始采样或厂家工程。图片和采样索引保存在 notes/OFDM学习笔记/附件/实操记录/P047Pro-证据索引.json。

本次在原主目录 ofdm_baseline_b62ed1eb 中只读加载两份 iq.npy，均为 1024 个 complex128 样本、所有元素有限；meta 调制分别为 QPSK、16-QAM，samples=1024、tx_gain=1.0，采集点 receiver constellation。由此补充确认电脑归档已经存在；本次没有连接板卡、重新采集、测量 BER 或完成新的软件/硬件收发阶段。

QPSK iq.npy SHA-256：95f30961adc1e1538c502bb3d83fcdd3f5e7f19d8077962fca48ae722b38f249。
16-QAM iq.npy SHA-256：495c0de06b65389a2d739d7e4699c306cdf1f9ad91835f14a65cc37b5ca09edc。

用户 AFDM 02 的依据为结果导出反馈；03 为软件自检完成与结果目录反馈；04 明确为 PASS 8/8、无噪声六组各 0/32768。用户原始 JSON 未取回核对。05～10 及 XSim 为电脑端准备，未改记为用户板端完成。

原有笔记保留，并接入导航；检查内部链接、标题锚点、图片摘要、代码块语法和打包 CRC/逐文件清单。未运行笔记中的硬件控制/采集代码，未检查 Obsidian UI 渲染。完整笔记包为 artifacts/notes/p047pro_operations_obsidian_notes.zip。
