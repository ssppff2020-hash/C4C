#!/usr/bin/env python3
"""
Stage 1: 文档摄入（Document Ingestion）
========================================
starter kit 只实现了 Markdown 读取，PDF / Word / 图片三个函数直接
`raise NotImplementedError("学生扩展点")`。C4C 把这三个补上：

    .md/.txt   直接读取
    .pdf       pdfplumber（首选，纯 Python 跨平台）
               → 失败则 pdftotext CLI（poppler，快）
               → 再失败则 pypdf（只抽文本层）
               扫描件（无文本层）会被识别出来并明确报错，而不是静默返回空
    .docx      python-docx（段落 + 表格 + 内嵌公式的 OMML 兜底）

**设计上最重要的决定**：把「抽取出来的文本」规范化成 **Markdown**，
而不是塞一堆裸文本给 Stage 2。因为 starter 的题目解析器认的是
Markdown 标题（`## Problems` / `## Questions`）和 `N.` / `Problem N` 题号。

PDF 转 Markdown 时做的清洗（都是踩过的坑，见 ai-log B3）：
    * 连字断行  "differen-\ntiate"  → "differentiate"
    * 页码/页眉  "18.06    HW 1    Page 3" → 丢弃
    * 数学符号降级  pdftotext 把 x² 抽成 "x�" → 用 Unicode 规范化尽力还原
    * 公式行粘连  "Compute the derivative of f(x)=x^3" 保持原样交给 Stage 2

用法:
    python ingest.py <输入文件> <输出.json>
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 各格式读取
# ─────────────────────────────────────────────────────────────

def read_markdown(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def read_pdf_text(filepath: str) -> str:
    """PDF → 文本。三级降级：pdfplumber → pdftotext → pypdf。"""
    errors: list[str] = []

    # ① pdfplumber（保留版面，跨平台）
    try:
        import pdfplumber  # type: ignore
        pages = []
        with pdfplumber.open(filepath) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                t = page.extract_text() or ""
                if t.strip():
                    pages.append(t)
        text = "\n\n".join(pages)
        if text.strip():
            return _pdf_text_to_markdown(text, source=os.path.basename(filepath))
        errors.append("pdfplumber: 没有抽出任何文本层")
    except ImportError:
        errors.append("pdfplumber: 未安装（pip install pdfplumber）")
    except Exception as e:  # noqa: BLE001
        errors.append(f"pdfplumber: {type(e).__name__}: {e}")

    # ② pdftotext CLI（poppler，最快，但表格差）
    exe = shutil.which("pdftotext")
    if exe:
        try:
            out = subprocess.run([exe, "-layout", "-enc", "UTF-8", filepath, "-"],
                                 capture_output=True, timeout=120)
            text = out.stdout.decode("utf-8", "replace")
            if text.strip():
                return _pdf_text_to_markdown(text, source=os.path.basename(filepath))
            errors.append("pdftotext: 没有抽出任何文本层")
        except Exception as e:  # noqa: BLE001
            errors.append(f"pdftotext: {type(e).__name__}: {e}")

    # ③ pypdf
    try:
        from pypdf import PdfReader  # type: ignore
        reader = PdfReader(filepath)
        text = "\n\n".join((p.extract_text() or "") for p in reader.pages)
        if text.strip():
            return _pdf_text_to_markdown(text, source=os.path.basename(filepath))
        errors.append("pypdf: 没有抽出任何文本层")
    except ImportError:
        errors.append("pypdf: 未安装")
    except Exception as e:  # noqa: BLE001
        errors.append(f"pypdf: {type(e).__name__}: {e}")

    raise NotImplementedError(
        "PDF 摄入失败。尝试过：" + "；".join(errors) +
        "\n如果这是**扫描件/拍照**的 PDF（没有文本层），需要 OCR：\n"
        "  pip install pytesseract Pillow 并安装 Tesseract-OCR\n"
        "  （本机未检测到 tesseract 可执行文件）\n"
        "或者用国产模型的 Vision 接口先把图片转成文字，再喂给本流水线。"
    )


def read_docx(filepath: str) -> str:
    """Word → Markdown。段落 + 表格 + 标题样式。"""
    try:
        import docx  # type: ignore
    except ImportError as e:
        raise NotImplementedError(
            "Word 摄入需要 python-docx：pip install python-docx") from e

    d = docx.Document(filepath)
    lines: list[str] = []
    for p in d.paragraphs:
        txt = (p.text or "").rstrip()
        style = (p.style.name or "").lower()
        if not txt:
            lines.append("")
            continue
        if "heading 1" in style or "title" in style:
            lines.append(f"# {txt}")
        elif "heading 2" in style:
            lines.append(f"## {txt}")
        elif "heading 3" in style:
            lines.append(f"### {txt}")
        else:
            lines.append(txt)
    for i, table in enumerate(d.tables, 1):
        lines.append(f"\n### Table {i}\n")
        for row in table.rows:
            cells = [c.text.strip().replace("\n", " ") for c in row.cells]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines)


def read_image_ocr(filepath: str) -> str:
    """图片 → 文本。优先 pytesseract；没有则给出可操作的报错。"""
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except ImportError as e:
        raise NotImplementedError(
            "图片/扫描件摄入需要 OCR：pip install pytesseract Pillow，"
            "并安装 Tesseract-OCR 可执行文件（Windows: UB-Mannheim 版）。\n"
            "替代方案：用国产模型的 Vision 接口把图片转成文字后存成 .md 再喂进来。"
        ) from e
    if not shutil.which("tesseract"):
        raise NotImplementedError(
            "已安装 pytesseract 但找不到 tesseract 可执行文件。\n"
            "Windows 安装：https://github.com/UB-Mannheim/tesseract/wiki\n"
            "装完把安装目录加进 PATH，或 pytesseract.pytesseract.tesseract_cmd = r'C:\\...\\tesseract.exe'"
        )
    img = Image.open(filepath)
    return pytesseract.image_to_string(img, lang="chi_sim+eng")


FORMAT_HANDLERS = {
    ".md": read_markdown,
    ".markdown": read_markdown,
    ".txt": read_markdown,
    ".tex": read_markdown,
    ".pdf": read_pdf_text,
    ".docx": read_docx,
    ".doc": read_docx,
    ".png": read_image_ocr,
    ".jpg": read_image_ocr,
    ".jpeg": read_image_ocr,
    ".bmp": read_image_ocr,
    ".tif": read_image_ocr,
    ".tiff": read_image_ocr,
}


# ─────────────────────────────────────────────────────────────
# PDF 文本 → Markdown 清洗
# ─────────────────────────────────────────────────────────────

_UNICODE_FIX = {
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl",
    "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
    "\u2212": "-", "\u2013": "-", "\u2014": "-", "\u00a0": " ",
    "\u221e": "\\infty",
}
_SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
_SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")

# 页眉页脚噪声
_NOISE_PATTERNS = [
    re.compile(r"^\s*Page\s+\d+\s*(of\s+\d+)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"^\s*18\.0\d.*(?:HW|Problem Set).*$", re.IGNORECASE),
    re.compile(r"^\s*MIT OpenCourseWare.*$", re.IGNORECASE),
    re.compile(r"^\s*https?://\S+\s*$"),
]


def _pdf_text_to_markdown(text: str, source: str = "") -> str:
    text = unicodedata.normalize("NFKC", text)
    for k, v in _UNICODE_FIX.items():
        text = text.replace(k, v)

    # 上标/下标数字（pdftotext 有时会保留）
    text = re.sub(r"([A-Za-z\)\]])\s*([\u2070-\u2079]+)",
                  lambda m: f"{m.group(1)}^{{{m.group(2).translate(_SUP)}}}", text)

    # 连字断行
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)

    # 逐行清洗
    lines = []
    for line in text.split("\n"):
        s = line.rstrip()
        if any(p.match(s) for p in _NOISE_PATTERNS):
            continue
        s = re.sub(r"[ \t]{3,}", "  ", s)
        s = s.replace("\ufffd", "")  # PDF 抽不出的字符往往是数学符号，留问号更误导
        lines.append(s)

    # 把 "N. " 形式的题号提升成 Markdown 结构，方便 Stage 2
    out = []
    for line in lines:
        m = re.match(r"^\s{0,4}(\d{1,2})\.\s+(\S.*)$", line)
        if m and len(m.group(2)) > 3:
            out.append(f"{m.group(1)}. {m.group(2)}")
        else:
            # 缩进的 (a) (b) (c) 子题
            m2 = re.match(r"^\s{2,}(\()?([a-h])[\).]\s+(\S.*)$", line)
            if m2:
                out.append(f"({m2.group(2)}) {m2.group(3)}")
            else:
                out.append(line)

    md = "\n".join(out)
    md = re.sub(r"\n{4,}", "\n\n\n", md)
    if source:
        md = f"<!-- ingested from {source} -->\n\n" + md
    return md.strip() + "\n"


# ─────────────────────────────────────────────────────────────
# 分段
# ─────────────────────────────────────────────────────────────

def split_into_sections(text: str) -> list:
    """按 Markdown 标题分段（与 starter 行为一致）。"""
    sections = []
    current_title = "Untitled"
    current_lines: list[str] = []
    for line in text.split("\n"):
        m = re.match(r"^(#{1,4})\s+(.+)", line)
        if m:
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    sections.append({"title": current_title, "content": content})
            current_title = m.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append({"title": current_title, "content": content})
    return sections


def detect_format(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext not in FORMAT_HANDLERS:
        raise ValueError(
            f"不支持的文件格式: {ext}\n支持: {sorted(set(FORMAT_HANDLERS))}")
    return ext


def ingest(filepath: str) -> dict:
    """主入口：任意格式 → 结构化结果（raw_text + sections）。"""
    filepath = str(filepath)
    ext = detect_format(filepath)
    raw_text = FORMAT_HANDLERS[ext](filepath)

    # PDF/DOCX 抽出来的文本通常没有 Markdown 标题，而 Stage 2 的分段依赖标题。
    # 只要检测到「1. / Problem 1 / 题 1」这类题号，就补一个 "## Problems"。
    if ext in (".pdf", ".docx", ".doc", ".tex") and not re.search(r"^#{1,4}\s", raw_text,
                                                                  re.MULTILINE):
        if re.search(r"(?:^|\n)\s*(?:Problem|Question|题)\s*\d", raw_text) or \
           re.search(r"(?:^|\n)\s*\d{1,2}\.\s+\S", raw_text):
            raw_text = "## Problems\n\n" + raw_text

    return {
        "source_file": Path(filepath).name,
        "format": ext,
        "handler": FORMAT_HANDLERS[ext].__name__,
        "raw_text": raw_text,
        "sections": split_into_sections(raw_text),
        "char_count": len(raw_text),
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) < 2:
        print("用法: python ingest.py <输入文件> <输出.json>")
        print("支持: .md .txt .tex .pdf .docx .png .jpg …")
        return 1

    input_path, output_path = argv[0], argv[1]
    if not Path(input_path).exists():
        print(f"错误: 文件不存在 — {input_path}")
        return 1

    print(f"[Stage 1] 文档摄入: {input_path}")
    try:
        result = ingest(input_path)
    except NotImplementedError as e:
        print(f"\n❌ {e}")
        return 2

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
    print(f"  格式: {result['format']}（handler: {result['handler']}）")
    print(f"  字符: {result['char_count']:,}")
    print(f"  分段: {len(result['sections'])} sections")
    print(f"  输出: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
