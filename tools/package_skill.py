#!/usr/bin/env python3
"""
把技能源码目录打包成 .skill（标准 ZIP 格式）
==============================================
为什么需要这个脚本而不是直接 zip：
  * Windows 的 Git Bash 里经常没有 zip 命令；
  * Claude Skills 的 .skill 包要求 **SKILL.md 在压缩包根目录**，
    如果直接压目录，解压后会多一层文件夹，装不进去。

用法:
    python tools/package_skill.py skill-src/homework-solver \
        --out Songpengfei_C4C_homework-solver.skill
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
import zipfile
from pathlib import Path

# 不打包进 .skill 的东西
EXCLUDE_DIRS = {"__pycache__", ".git", ".venv", "venv", "_out", "output", ".pytest_cache"}
EXCLUDE_GLOBS = ["*.pyc", "*.pyo", "*.aux", "*.log", "*.synctex.gz", "config.local.yaml"]


def should_skip(path: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return True
    return any(fnmatch.fnmatch(path.name, g) for g in EXCLUDE_GLOBS)


def package(src: Path, out: Path) -> dict:
    src = Path(src).resolve()
    if not src.is_dir():
        raise NotADirectoryError(f"源码目录不存在: {src}")
    if not (src / "SKILL.md").exists():
        raise FileNotFoundError(
            f"{src} 里没有 SKILL.md —— Claude Skills 要求技能包根目录必须有 SKILL.md")

    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    n_files = 0
    total = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        # 先写 SKILL.md，保证它在包内的最前面（有些加载器按顺序读）
        z.write(src / "SKILL.md", "SKILL.md")
        n_files += 1
        total += (src / "SKILL.md").stat().st_size
        for p in sorted(src.rglob("*")):
            if p.is_dir() or should_skip(p):
                continue
            rel = p.relative_to(src)
            if str(rel).replace("\\", "/") == "SKILL.md":
                continue
            z.write(p, str(rel).replace("\\", "/"))
            n_files += 1
            total += p.stat().st_size

    return {"out": str(out), "files": n_files,
            "raw_bytes": total, "zip_bytes": out.stat().st_size}


def main(argv=None):
    ap = argparse.ArgumentParser(description="打包 .skill")
    ap.add_argument("src", help="技能源码目录（含 SKILL.md）")
    ap.add_argument("--out", required=True, help="输出的 .skill 路径")
    args = ap.parse_args(argv)

    try:
        r = package(Path(args.src), Path(args.out))
    except Exception as e:  # noqa: BLE001
        print(f"❌ 打包失败：{e}")
        return 1
    print(f"✅ 已打包 {r['out']}")
    print(f"   {r['files']} 个文件，压缩前 {r['raw_bytes']:,} B → 压缩后 {r['zip_bytes']:,} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
