"""Export a public, size-limited snapshot while preserving original files."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
from urllib.parse import unquote, urlsplit, quote

LIMIT = 10 * 1024 * 1024
PRIVATE_TOP = {"Codex_迁移前备份_20261117", "RFSOC_Codex聊天迁移包_20261117", "tmp"}
VENDOR_TOP = {"01.芯片手册", "02.软件和驱动", "03.开机测试", "04.硬件相关", "05.教程和源码", "06.附件"}
CACHE_NAMES = {".git", "__pycache__", ".ipynb_checkpoints", ".Xil", ".cache",
               ".metadata", ".pytest_cache", ".venv", "venv", "node_modules",
               "Debug", "Release", "xsim.dir", ".idea", ".vscode", ".obsidian"}
CACHE_SUFFIXES = (".runs", ".sim", ".gen", ".cache", ".ip_user_files")
SOURCE_EXT = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
              ".py", ".ipynb", ".ps1", ".sh", ".bat", ".v", ".sv", ".vh", ".svh",
              ".vhd", ".vhdl", ".xdc", ".tcl", ".xpr", ".bd", ".xci", ".hwh",
              ".c", ".cpp", ".cc", ".h", ".hpp", ".m", ".mem", ".coe", ".hex",
              ".csv", ".tsv", ".html", ".css", ".js", ".xml"}
BINARY_EXT = {".png", ".jpg", ".jpeg", ".svg", ".pdf", ".npy", ".npz"}
SOURCE_NAMES = {".gitignore", ".gitattributes", ".gitkeep", "LICENSE", "Makefile"}
SECRET_NAMES = {".git-credentials", ".npmrc", ".pypirc", "id_rsa", "id_ed25519"}
SECRET_EXT = {".key", ".pem", ".pfx", ".p12", ".lic", ".sqlite", ".sqlite3", ".db"}
GENERATED_EXT = {".bit", ".bin", ".elf", ".o", ".obj", ".dcp", ".wdb", ".jou",
                 ".log", ".pb", ".pdom", ".exe", ".dll", ".msi", ".run",
                 ".iso", ".img", ".rar", ".zip", ".7z", ".gz", ".xz", ".bz2",
                 ".tar", ".hdf", ".xsa"}
SECRETS = [re.compile(p) for p in [
    r"github_pat_[A-Za-z0-9_]{30,}", r"gh[pousr]_[A-Za-z0-9]{30,}",
    r"(?:sk-proj-|sk-)[A-Za-z0-9_-]{32,}",
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", r"AKIA[0-9A-Z]{16}"]]
MD_LINK = re.compile(r"(?P<before>!?\[[^\]\n]*\]\()(?P<dest><[^>\n]+>|[^\s)\n]+)(?P<after>[^)\n]*\))")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build(root, output):
    root, output = root.resolve(), output.resolve()
    if os.name == 'nt':
        prefix = chr(92) * 2 + '?' + chr(92)
        root = Path(str(root) if str(root).startswith(prefix) else prefix + str(root))
        output = Path(str(output) if str(output).startswith(prefix) else prefix + str(output))
    if not output.is_relative_to(root / "09.afdm_development" / "artifacts"):
        raise ValueError("Output must be inside active repository artifacts.")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Choose an empty output directory; existing files are never removed.")
    output.mkdir(parents=True, exist_ok=True)
    records, by_path, copied, placeholders, private_items, cache_dirs = [], {}, [], {}, [], []
    manifests = output / "PUBLICATION_MANIFEST"

    def record_file(source, reason):
        relative = source.relative_to(root).as_posix()
        before = source.stat()
        if before.st_size > LIMIT:
            print(json.dumps({"hashing_large_file": relative, "bytes": before.st_size}, ensure_ascii=False), flush=True)
        hash_needed = (reason == 'copied' or before.st_size > LIMIT or source.suffix.lower() in {'.pdf', '.rar', '.zip', '.7z', '.gz', '.iso', '.img', '.run', '.exe', '.bit', '.hwh'})
        sha = digest(source) if hash_needed else None
        after = source.stat() if hash_needed else before
        if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
            raise RuntimeError("Source changed while reading: " + relative)
        rec = {"source_path": relative, "source_bytes": before.st_size, "source_sha256": sha,
               "disposition": reason, "published_path": None}
        records.append(rec)
        by_path[relative] = rec
        return rec

    def placeholder(relative):
        if relative in placeholders:
            return placeholders[relative]
        rec = by_path.get(relative)
        if rec is None:
            return ""
        if rec["source_sha256"] is None:
            rec["source_sha256"] = digest(root / relative)
        dest = relative + ".placeholder.md"
        if (root / dest).exists():
            raise RuntimeError("Placeholder would shadow source: " + dest)
        put(output / dest,
            "# 本地文件说明\n\n"
            f"- 原相对路径：{relative}\n"
            f"- 原文件大小：{rec['source_bytes']:,} 字节（{rec['source_bytes'] / 1024 / 1024:.2f} MiB）\n"
            f"- SHA-256：{rec['source_sha256']}\n"
            f"- 未上传原因：{rec['disposition']}\n\n"
            "这是文本说明，不是原文件，也不是 Git LFS 指针。原文件保留在本地主项目相同相对位置。"
            "厂家文件请通过厂家或官方渠道取得；构建产物按对应工程重新生成；校验 SHA-256 后再恢复到原位置。"
            "本次未验证所有厂家链接或下载可用性。\n")
        placeholders[relative] = dest
        rec["published_path"] = dest
        return dest

    for current, dirs, files in os.walk(root, followlinks=False):
        here = Path(current)
        kept = []
        for name in sorted(dirs):
            p = here / name
            rel = p.relative_to(root)
            if p.resolve() == output or p.name.startswith("github-publication"):
                continue
            if len(rel.parts) == 1 and name in PRIVATE_TOP:
                put(output / rel / "README_未上传.md",
                    "# 私人资料保留在本地\n\n本目录含私人备份、会话迁移或临时资料。"
                    "公开仓库仅保留目录说明，不上传原文件、内部文件名或内容。\n")
                private_items.append(rel.as_posix())
                continue
            if p.is_symlink() or name in CACHE_NAMES or name.endswith(CACHE_SUFFIXES):
                if name == ".git":
                    continue
                if not p.is_symlink():
                    put(output / rel / "README_未上传.md",
                        "# 构建缓存或本机配置\n\n原目录保留在本地。此处只保留说明，"
                        "缓存、仿真波形、编辑器状态和工具元数据不随源码发布。需要时由对应工具重新生成。\n")
                cache_dirs.append(rel.as_posix())
                continue
            kept.append(name)
        dirs[:] = kept
        for name in sorted(files):
            source = here / name
            relative = source.relative_to(root).as_posix()
            parts = source.relative_to(root).parts
            ext = source.suffix.lower()
            if source.is_symlink():
                continue
            if name in SECRET_NAMES or (name.startswith(".env") and name != ".env.example") or ext in SECRET_EXT:
                private_items.append(parts[0] + "/[private-file]")
                continue
            size = source.stat().st_size
            if size > LIMIT:
                reason = "单文件超过本次 10 MiB 上限"
            elif parts[0] in VENDOR_TOP or (parts[0] == "08.ofdm_afdm" and "setup" in parts):
                reason = "厂家或第三方配套资料，未确认再分发许可；以文本清单代替"
            elif parts[0] == "07.test" and "Vitis" in parts and (any(p in {"libsrc", "include", "hw", "export", "_ide", "zynqmp_fsbl", "zynqmp_fsbl_bsp", "zynqmp_pmufw", "zynqmp_pmufw_bsp"} for p in parts) or any(p.startswith("standalone_") for p in parts)):
                reason = "Vitis 自动生成平台、BSP 或第三方运行库；保留文本清单和校验值"
            elif ext in GENERATED_EXT or ("artifacts" in parts or "afdm_runs" in parts):
                reason = "安装包、归档包或本地生成结果；保留文本清单和校验值"
            elif "/ip/" in relative and ext not in {".xci", ".tcl", ".xdc"}:
                reason = "工具生成或第三方 IP 文件；保留文本清单和校验值"
            elif ext not in SOURCE_EXT | BINARY_EXT and name not in SOURCE_NAMES:
                reason = "未纳入公开源码白名单的文件；保留文本清单和校验值"
            else:
                reason = "copied"
            rec = record_file(source, reason)
            if reason == "copied":
                dest = output / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, dest)
                if digest(dest) != rec["source_sha256"]:
                    raise RuntimeError("Copy verification failed: " + relative)
                if ext in SOURCE_EXT or name in SOURCE_NAMES:
                    try:
                        normalized = dest.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
                        put(dest, normalized)
                    except UnicodeError:
                        pass
                rec["published_path"] = relative
                copied.append(relative)
            elif size > LIMIT or ext in {".pdf", ".rar", ".zip", ".7z", ".gz", ".iso", ".img", ".run", ".exe", ".bit", ".hwh"}:
                placeholder(relative)

    groups = {}
    for rec in records:
        parts = rec["source_path"].split("/")
        if parts[0] in VENDOR_TOP or parts[0] == "08.ofdm_afdm":
            group = "/".join(parts[:2]) if parts[0] == "05.教程和源码" else parts[0]
            groups.setdefault(group, []).append(rec)
    for group, entries in groups.items():
        table = "\n".join(f"| {r['source_path'].split('/')[-1]} | {r['source_bytes'] / 1024 / 1024:.2f} |"
                          for r in sorted(entries, key=lambda r: r["source_bytes"], reverse=True)[:12])
        back = posixpath.relpath("PUBLICATION_MANIFEST/README.md", group)
        put(output / group / "README_资料清单.md",
            f"# {group} 本地资料\n\n本次盘点 {len(entries)} 个非缓存文件，"
            f"合计 {sum(r['source_bytes'] for r in entries) / 1024 / 1024:.2f} MiB。\n\n"
            "未确认再分发许可的厂家原文件以清单代替，大文件另有同路径 .placeholder.md 说明。"
            "原始目录与文件仍保留在本机，不是从本机删除。\n\n"
            f"[完整文件清单与 SHA-256]({back})\n\n"
            "| 较大文件 | MiB |\n|---|---:|\n" + table + "\n")

    rewritten, unresolved = [], []
    for relative in list(copied):
        if Path(relative).suffix.lower() != ".md":
            continue
        dest = output / relative
        original = dest.read_text(encoding="utf-8-sig")
        def replace_link(match):
            address = match.group("dest").strip("<>")
            uri = urlsplit(address)
            if uri.scheme or address.startswith(("#", "/", "\\")):
                return match.group(0)
            target = posixpath.normpath(posixpath.join(posixpath.dirname(relative), unquote(uri.path)))
            if target.startswith("../") or (output / target).exists():
                return match.group(0)
            mapped = placeholder(target)
            if not mapped:
                unresolved.append({"file": relative, "target": target})
                return match.group(0)
            replacement = quote(posixpath.relpath(mapped, posixpath.dirname(relative) or "."), safe="/._-")
            rewritten.append({"file": relative, "old_target": target, "new_target": mapped})
            return match.group("before") + replacement + match.group("after")
        amended = MD_LINK.sub(replace_link, original)
        if amended != original:
            put(dest, amended)

    nav = []
    for name in sorted(p.name for p in root.iterdir() if p.is_dir()):
        rel = name + ("/README.md" if name == "09.afdm_development" else "")
        nav.append(f"- [{name}]({quote(rel, safe='/._-')})")
    put(output / "README.md",
        "# FPGA P047Pro RFSoC 项目总览\n\n"
        "这是本地主项目目录的公开归档，按原有层级发布。"
        "开发入口为 [09.afdm_development](09.afdm_development/README.md)，"
        "包含 AFDM 软件、Notebook、功能 RTL、测试和学习笔记。"
        "原开发仓库为 https://github.com/tito-xiao/P047Pro ，其远程和本地 Git 历史保持原样。\n\n"
        "## 目录\n\n" + "\n".join(nav) + "\n\n"
        "## 文件发布规则\n\n"
        "- 单文件上限为 10 MiB；超过上限的原文件只发布同路径 .placeholder.md 文本说明。\n"
        "- 厂家 01～06 及 08/setup 中未确认再分发许可的资料只发布目录、大小和 SHA-256 清单。\n"
        "- 安装包、镜像、归档包和构建产物也以文本说明或清单代替；原文件未移动、覆盖或删除。\n"
        "- 私人聊天迁移包、迁移前备份、凭据、数据库、Git 内部数据与缓存不上传。\n"
        "- 本仓库是文件快照，不包含嵌套 .git，也不是完整二进制备份；克隆后需按说明补齐外部资料。\n"
        "- 原 Markdown 的本地附件链接在副本中尽可能改指向对应说明文件，原文与原始文件不被修改。\n\n"
        "[文件清单与校验说明](PUBLICATION_MANIFEST/README.md) · "
        "[本地项目入口](README_项目入口.md) · "
        "[开发进度](09.afdm_development/docs/progress.md)\n\n"
        "## 验证边界\n\n"
        "当前软件、RTL 仿真与硬件状态以开发进度和实验记录为准。"
        "本次操作只进行发布副本生成、完整性和公开内容检查，不代表新增板上或射频验证。"
        "原有第三方资料不因列入清单而被重新授权。\n")
    put(output / ".gitignore",
        "# Filtered publication snapshot: do not add private originals.\n"
        ".git/\n.env\n.env.*\n*.pem\n*.key\n*.pfx\n*.p12\n__pycache__/\n.ipynb_checkpoints/\n")
    put(output / ".gitattributes",
        "* text=auto\n*.md text eol=lf\n*.json text eol=lf\n*.tsv text eol=lf\n"
        "*.py text eol=lf\n*.ipynb text eol=lf\n*.pdf binary\n*.png binary\n*.jpg binary\n")

    for rec in records:
        pub = rec["published_path"]
        if pub:
            rec["published_bytes"] = (output / pub).stat().st_size
            rec["published_sha256"] = digest(output / pub)
    manifests.mkdir(parents=True, exist_ok=True)
    chunk, chunk_bytes, manifest_paths = [], 0, []
    for rec in records:
        length = len(json.dumps(rec, ensure_ascii=False).encode("utf-8"))
        if chunk and chunk_bytes + length > 1024 * 1024:
            filename = f"files-{len(manifest_paths)+1:04d}.json"
            put(manifests / filename, json.dumps(chunk, ensure_ascii=False, indent=2) + "\n")
            manifest_paths.append(filename)
            chunk, chunk_bytes = [], 0
        chunk.append(rec)
        chunk_bytes += length
    if chunk:
        filename = f"files-{len(manifest_paths)+1:04d}.json"
        put(manifests / filename, json.dumps(chunk, ensure_ascii=False, indent=2) + "\n")
        manifest_paths.append(filename)
    summary = {
        "date": "2026-11-18", "repository": "tito-xiao/FPGA-P047Pro-RFSoC",
        "max_file_bytes": LIMIT, "inventoried_source_files": len(records),
        "inventoried_source_bytes": sum(r["source_bytes"] for r in records),
        "copied_files": len(copied), "placeholder_files": len(placeholders),
        "large_original_files": sum(r["source_bytes"] > LIMIT for r in records),
        "excluded_cache_directories": len(cache_dirs), "private_directory_names": sorted(PRIVATE_TOP),
        "private_file_count": sum("[private-file]" in p for p in private_items),
        "redirected_markdown_links": len(rewritten), "preexisting_unresolved_links": unresolved}
    put(manifests / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    put(manifests / "link-rewrites.json", json.dumps(rewritten, ensure_ascii=False, indent=2) + "\n")
    put(manifests / "cache-directories.json", json.dumps(cache_dirs, ensure_ascii=False, indent=2) + "\n")
    put(manifests / "README.md",
        "# 发布清单与原文件校验\n\n"
        f"盘点 {len(records):,} 个非缓存原文件，复制 {len(copied):,} 个文件，"
        f"生成 {len(placeholders):,} 个文件说明。\n\n"
        "每条清单包含原相对路径、原始字节数、处理原因和可用的 SHA-256，以及已发布副本/说明的路径和摘要。未上传的小型外部文件只记录名称和大小，source_sha256 为 null；大文件、文本占位和实际复制文件均计算摘要。"
        "源文件摘要和发布文件摘要可能因 Markdown 链接重定向而不同；占位说明的摘要不等于原文件摘要。\n\n"
        + "\n".join(f"- [{name}]({name})" for name in manifest_paths)
        + "\n\n[统计](summary.json) · [附件链接改写](link-rewrites.json) · "
        "[未上传的缓存目录](cache-directories.json)\n\n"
        "被整体排除的缓存没有逐文件哈希；私有备份、会话迁移包和凭据不记录内部文件名或摘要。"
        "文件名称和校验值不包含原文件内容，也不能恢复缺失的文件。\n")

    secret_hits, published_files = [], []
    for p in output.rglob("*"):
        if not p.is_file():
            continue
        relative = p.relative_to(output).as_posix()
        if p.stat().st_size > LIMIT:
            raise RuntimeError("Publication exceeds size cap: " + relative)
        if ".git" in p.relative_to(output).parts:
            raise RuntimeError("Nested Git metadata found.")
        if p.suffix.lower() in SOURCE_EXT or p.name in SOURCE_NAMES:
            try:
                text = p.read_text(encoding="utf-8-sig")
            except UnicodeError:
                text = ""
            if any(pattern.search(text) for pattern in SECRETS):
                secret_hits.append(relative)
        if p.suffix.lower() == ".ipynb":
            notebook = json.loads(p.read_text(encoding="utf-8-sig"))
            for cell in notebook.get("cells", []):
                if cell.get("cell_type") == "code":
                    code = "".join(cell.get("source", []))
                    if not any(line.lstrip().startswith(("%", "!")) for line in code.splitlines()):
                        compile(code, relative, "exec")
        published_files.append({"path": relative, "bytes": p.stat().st_size, "sha256": digest(p)})
    if secret_hits:
        raise RuntimeError("Potential credentials detected; inspect these paths: " + ", ".join(secret_hits))
    report = dict(summary, published_file_count=len(published_files),
                  published_bytes=sum(r["bytes"] for r in published_files),
                  max_published_file_bytes=max((r["bytes"] for r in published_files), default=0),
                  credential_scan="passed", notebook_json_and_syntax="passed", files=published_files)
    put(output.parent / (output.name + "-verification.json"), json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "files"}, ensure_ascii=False), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="An empty directory under active repository artifacts.")
    args = parser.parse_args()
    build(args.root, args.output)


if __name__ == "__main__":
    main()

