# P047Pro 项目入口

本文件夹是 Codex 项目的主要源文件夹。原有厂家资料保持原名称和位置。

| 目录 | 用途 |
|---|---|
| `01.芯片手册`～`06.附件` | 厂家资料、驱动、硬件与教程 |
| `07.test` | 既有测试文件 |
| `08.ofdm_afdm` | 既有厂家适配包与 Notebook |
| **`09.afdm_development`** | **当前活动开发 Git 仓库，后续开发在此进行** |
| `ofdm_baseline_b62ed1eb` | 已有 OFDM 数据归档 |
| `Codex_迁移前备份_20261117`、`RFSOC_Codex聊天迁移包_20261117` | 既有聊天迁移资料，保留原样 |

开发入口：[README](09.afdm_development/README.md) · [当前进度](09.afdm_development/docs/progress.md) · [上传执行说明](09.afdm_development/docs/afdm-workbench.md)

上传到板卡的文件：[afdm_workbench.zip](09.afdm_development/artifacts/afdm_workbench.zip.placeholder.md)

开发目录内：`afdm_lab` 为算法包，`notebooks` 为分阶段入口，`hardware` 为功能 RTL，`configs` 为配置，`tests` 为检查，`scripts` 为工具，`docs` 为记录，`artifacts` 为结果和交付物。

原 `D:\XIAO\P047Pro` 保留为迁移前备份，勿在两处同时开发。该目录当前被程序占用，尚未重命名或替换成联接。软件迁移不代表新的板卡或射频测试通过。
