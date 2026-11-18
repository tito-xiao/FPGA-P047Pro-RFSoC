# 发布清单与原文件校验

盘点 77,401 个非缓存原文件，复制 120 个文件，生成 110 个文件说明。

每条清单包含原相对路径、原始字节数、处理原因和可用的 SHA-256，以及已发布副本/说明的路径和摘要。未上传的小型外部文件只记录名称和大小，source_sha256 为 null；大文件、文本占位和实际复制文件均计算摘要。源文件摘要和发布文件摘要可能因 Markdown 链接重定向而不同；占位说明的摘要不等于原文件摘要。

- [files-0001.json](files-0001.json)
- [files-0002.json](files-0002.json)
- [files-0003.json](files-0003.json)
- [files-0004.json](files-0004.json)
- [files-0005.json](files-0005.json)
- [files-0006.json](files-0006.json)
- [files-0007.json](files-0007.json)
- [files-0008.json](files-0008.json)
- [files-0009.json](files-0009.json)
- [files-0010.json](files-0010.json)
- [files-0011.json](files-0011.json)
- [files-0012.json](files-0012.json)
- [files-0013.json](files-0013.json)
- [files-0014.json](files-0014.json)
- [files-0015.json](files-0015.json)
- [files-0016.json](files-0016.json)
- [files-0017.json](files-0017.json)
- [files-0018.json](files-0018.json)
- [files-0019.json](files-0019.json)
- [files-0020.json](files-0020.json)
- [files-0021.json](files-0021.json)
- [files-0022.json](files-0022.json)
- [files-0023.json](files-0023.json)
- [files-0024.json](files-0024.json)
- [files-0025.json](files-0025.json)

[统计](summary.json) · [附件链接改写](link-rewrites.json) · [未上传的缓存目录](cache-directories.json)

被整体排除的缓存没有逐文件哈希；私有备份、会话迁移包和凭据不记录内部文件名或摘要。文件名称和校验值不包含原文件内容，也不能恢复缺失的文件。

[发布副本检查结果](validation.json)
