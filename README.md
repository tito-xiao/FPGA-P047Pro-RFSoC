# FPGA P047Pro RFSoC 项目总览

这是本地主项目目录的公开归档，按原有层级发布。开发入口为 [09.afdm_development](09.afdm_development/README.md)，包含 AFDM 软件、Notebook、功能 RTL、测试和学习笔记。原开发仓库为 https://github.com/tito-xiao/P047Pro ，其远程和本地 Git 历史保持原样。

## 目录

- [01.芯片手册](01.%E8%8A%AF%E7%89%87%E6%89%8B%E5%86%8C)
- [02.软件和驱动](02.%E8%BD%AF%E4%BB%B6%E5%92%8C%E9%A9%B1%E5%8A%A8)
- [03.开机测试](03.%E5%BC%80%E6%9C%BA%E6%B5%8B%E8%AF%95)
- [04.硬件相关](04.%E7%A1%AC%E4%BB%B6%E7%9B%B8%E5%85%B3)
- [05.教程和源码](05.%E6%95%99%E7%A8%8B%E5%92%8C%E6%BA%90%E7%A0%81)
- [06.附件](06.%E9%99%84%E4%BB%B6)
- [07.test](07.test)
- [08.ofdm_afdm](08.ofdm_afdm)
- [09.afdm_development](09.afdm_development/README.md)
- [Codex_迁移前备份_20261117](Codex_%E8%BF%81%E7%A7%BB%E5%89%8D%E5%A4%87%E4%BB%BD_20261117)
- [RFSOC_Codex聊天迁移包_20261117](RFSOC_Codex%E8%81%8A%E5%A4%A9%E8%BF%81%E7%A7%BB%E5%8C%85_20261117)
- [ofdm_baseline_b62ed1eb](ofdm_baseline_b62ed1eb)
- [tmp](tmp)

## 文件发布规则

- 单文件上限为 10 MiB；超过上限的原文件只发布同路径 .placeholder.md 文本说明。
- 厂家 01～06 及 08/setup 中未确认再分发许可的资料只发布目录、大小和 SHA-256 清单。
- 安装包、镜像、归档包和构建产物也以文本说明或清单代替；原文件未移动、覆盖或删除。
- 私人聊天迁移包、迁移前备份、凭据、数据库、Git 内部数据与缓存不上传。
- 本仓库是文件快照，不包含嵌套 .git，也不是完整二进制备份；克隆后需按说明补齐外部资料。
- 原 Markdown 的本地附件链接在副本中尽可能改指向对应说明文件，原文与原始文件不被修改。

[文件清单与校验说明](PUBLICATION_MANIFEST/README.md) · [本地项目入口](README_项目入口.md) · [开发进度](09.afdm_development/docs/progress.md)

## 验证边界

当前软件、RTL 仿真与硬件状态以开发进度和实验记录为准。本次操作只进行发布副本生成、完整性和公开内容检查，不代表新增板上或射频验证。原有第三方资料不因列入清单而被重新授权。
