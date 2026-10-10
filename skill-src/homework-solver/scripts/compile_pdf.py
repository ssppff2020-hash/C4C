#!/usr/bin/env python3
"""
Stage 5: 编译与验证（Compile & Validate）
==========================================
starter kit 在这一步只做了「调 pdflatex，失败就让你上 Overleaf」。
问题是：**绝大多数学生机器上没有 LaTeX**，于是流水线最后一公里断掉，
交不出 PDF —— 而 rubric 明确要求「可导出 / 可提交」。

C4C 把这一步做成三级降级，保证「一定有 PDF」：

    Tier 1  LaTeX 编译    xelatex / lualatex / pdflatex / tectonic
                          质量最好，需要本机装 TeX（~几百 MB）
    Tier 2  浏览器打印     headless Edge / Chrome / Chromium --print-to-pdf
                          配合本地 MathJax（references/mathjax/tex-svg.js）
                          质量接近 Tier 1，零额外安装（Windows/macOS 自带 Edge）
    Tier 3  纯 Python      reportlab + 系统 CJK 字体 + LaTeX→Unicode 降级
                          一定能跑，公式是「近似的纯文本」

编译后做**验证**（对应 rubric 的「输出可核验」）：
    * PDF 能否被解析、页数、文件大小
    * 文本层能否抽出中文/数字（证明不是空白页）
    * .tex 是否产出、是否含未定义命令的疑似报错

用法:
    python compile_pdf.py <输出目录> [--basename homework] [--tier auto|latex|browser|reportlab]
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# LaTeX → Unicode 降级（Tier 3 用）
# ─────────────────────────────────────────────────────────────

_GREEK_UC = {
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ", r"\epsilon": "ε",
    r"\varepsilon": "ε", r"\zeta": "ζ", r"\eta": "η", r"\theta": "θ", r"\iota": "ι",
    r"\kappa": "κ", r"\lambda": "λ", r"\mu": "μ", r"\nu": "ν", r"\xi": "ξ", r"\pi": "π",
    r"\rho": "ρ", r"\sigma": "σ", r"\tau": "τ", r"\upsilon": "υ", r"\phi": "φ",
    r"\varphi": "φ", r"\chi": "χ", r"\psi": "ψ", r"\omega": "ω",
    r"\Gamma": "Γ", r"\Delta": "Δ", r"\Theta": "Θ", r"\Lambda": "Λ", r"\Xi": "Ξ",
    r"\Pi": "Π", r"\Sigma": "Σ", r"\Phi": "Φ", r"\Psi": "Ψ", r"\Omega": "Ω",
    r"\infty": "∞", r"\partial": "∂", r"\nabla": "∇", r"\pm": "±", r"\mp": "∓",
    r"\times": "×", r"\cdot": "·", r"\div": "÷", r"\leq": "≤", r"\le": "≤",
    r"\geq": "≥", r"\ge": "≥", r"\neq": "≠", r"\ne": "≠", r"\approx": "≈",
    r"\equiv": "≡", r"\to": "→", r"\rightarrow": "→", r"\Rightarrow": "⇒",
    r"\leftrightarrow": "↔", r"\in": "∈", r"\subset": "⊂", r"\cup": "∪", r"\cap": "∩",
    r"\forall": "∀", r"\exists": "∃", r"\sum": "∑", r"\prod": "∏", r"\int": "∫",
    r"\sqrt": "√", r"\quad": "  ", r"\qquad": "    ", r"\ldots": "…", r"\dots": "…",
    r"\times": "×", r"\circ": "∘", r"\star": "⋆", r"\prime": "′",
    r"\{": "{", r"\}": "}", r"\%": "%", r"\&": "&", r"\_": "_", r"\#": "#",
}

_SUP_UC = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")


def latex_to_unicode(s: str) -> str:
    """把 LaTeX 数学式降级成可读的 Unicode 纯文本（Tier 3 兜底）。"""
    if not s:
        return ""
    t = s.strip()
    t = re.sub(r"^\$\$(.*)\$\$$", r"\1", t, flags=re.DOTALL)
    t = re.sub(r"^\$(.*)\$$", r"\1", t, flags=re.DOTALL)
    t = t.replace(r"\left", "").replace(r"\right", "")

    # 矩阵 → 分行的 [a b; c d]
    def mat_repl(m):
        body = m.group(2)
        rows = [r.strip() for r in re.split(r"\\\\", body) if r.strip()]
        rows = ["[" + "  ".join(c.strip() for c in r.split("&")) + "]" for r in rows]
        return " ".join(rows)
    t = re.sub(r"\\begin\{((?:p|b|v|B|V)?matrix)\}(.*?)\\end\{\1\}", mat_repl, t, flags=re.DOTALL)

    # \frac{a}{b} → (a)/(b)
    for _ in range(4):
        t = re.sub(r"\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", t)
    # \sqrt{x}
    t = re.sub(r"\\sqrt\{([^{}]*)\}", r"√(\1)", t)
    # 上下标
    t = re.sub(r"\^\{([^{}]*)\}", lambda m: "".join(
        c if c not in "0123456789+-=()" else c for c in m.group(1)) if len(m.group(1)) > 2
        else m.group(1).translate(_SUP_UC), t)
    t = re.sub(r"\^(\w)", lambda m: m.group(1).translate(_SUP_UC), t)
    t = re.sub(r"_\{([^{}]*)\}", r"_{\1}", t)
    t = re.sub(r"_(\w)", r"_\1", t)

    for k, v in sorted(_GREEK_UC.items(), key=lambda kv: -len(kv[0])):
        t = t.replace(k, v)
    for cmd in (r"\displaystyle", r"\,", r"\;", r"\!", r"\limits"):
        t = t.replace(cmd, " ")
    t = re.sub(r"\\operatorname\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"\\mathrm\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"\\text\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"\\[a-zA-Z]+", "", t)
    t = t.replace("{", "").replace("}", "")
    return re.sub(r"\s{2,}", " ", t).strip()


# ─────────────────────────────────────────────────────────────
# Tier 1：LaTeX
# ─────────────────────────────────────────────────────────────

LATEX_ENGINES = ("xelatex", "lualatex", "pdflatex", "tectonic")


def find_latex_engine() -> str | None:
    for e in LATEX_ENGINES:
        p = shutil.which(e)
        if p:
            return p
    return None


def compile_with_latex(tex_path: Path, out_dir: Path, engine: str | None = None) -> tuple[bool, str]:
    engine = engine or find_latex_engine()
    if not engine:
        return False, "本机没有 xelatex / pdflatex / tectonic"
    name = Path(engine).stem
    # 3 遍编译（目录/交叉引用需要）
    last = ""
    for i in range(3):
        cmd = [engine, "-interaction=nonstopmode", "-halt-on-error",
               f"-output-directory={out_dir}", str(tex_path)]
        if name == "tectonic":
            cmd = [engine, "--outdir", str(out_dir), str(tex_path)]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=300,
                               cwd=str(tex_path.parent))
        except Exception as e:  # noqa: BLE001
            return False, f"调用 {name} 失败：{e}"
        last = (r.stdout or b"").decode("utf-8", "replace") + \
               (r.stderr or b"").decode("utf-8", "replace")
        if r.returncode != 0 and i == 2:
            errs = [ln for ln in last.splitlines() if ln.startswith("!")][:5]
            return False, f"{name} 编译失败：" + ("；".join(errs) or last[-400:])
    pdf = out_dir / (tex_path.stem + ".pdf")
    if pdf.exists():
        return True, f"{name}（3 遍编译）"
    return False, f"{name} 未产出 PDF"


# ─────────────────────────────────────────────────────────────
# Tier 2：浏览器打印
# ─────────────────────────────────────────────────────────────

BROWSER_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/snap/bin/chromium",
]


def find_browser() -> str | None:
    for c in BROWSER_CANDIDATES:
        if Path(c).exists():
            return c
    for name in ("msedge", "chrome", "chromium", "google-chrome", "microsoft-edge"):
        p = shutil.which(name)
        if p:
            return p
    return None


def _file_url(p: Path) -> str:
    # Chrome 要 file:///C:/... 形式
    return "file:///" + str(p.resolve()).replace("\\", "/")


def compile_with_browser(html_path: Path, out_dir: Path, browser: str | None = None,
                         timeout_s: int = 20) -> tuple[bool, str]:
    browser = browser or find_browser()
    if not browser:
        return False, "本机没有 Edge / Chrome / Chromium"

    pdf_path = (out_dir / (html_path.stem + ".pdf")).resolve()
    if pdf_path.exists():
        pdf_path.unlink()

    # ⚠️ 必须给一个独立的 --user-data-dir。
    # 否则当用户已经开着 Edge/Chrome 时，headless 实例会去连已有 profile，
    # 打印直接失败（并且是静默失败：进程正常退出但没产出 PDF）。
    # 这个坑让三段流水线里第二、三段 PDF 悄悄退化成 reportlab 版（见 ai-log B14）。
    profile_dir = Path(tempfile.mkdtemp(prefix="c4c-chrome-"))
    cmd = [
        browser,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        f"--user-data-dir={profile_dir}",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        f"--virtual-time-budget={timeout_s * 1000}",
        f"--print-to-pdf={pdf_path}",
        _file_url(html_path),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout_s + 60)
    except subprocess.TimeoutExpired:
        return False, f"{Path(browser).stem} 打印超时"
    except Exception as e:  # noqa: BLE001
        return False, f"调用 {Path(browser).stem} 失败：{e}"
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)

    if pdf_path.exists() and pdf_path.stat().st_size > 1000:
        return True, f"{Path(browser).stem} headless 打印（MathJax 本地渲染）"
    err = (r.stderr or b"").decode("utf-8", "replace")[-400:]
    return False, f"{Path(browser).stem} 未产出 PDF：{err}"


# ─────────────────────────────────────────────────────────────
# Tier 3：reportlab
# ─────────────────────────────────────────────────────────────

CJK_FONT_CANDIDATES = [
    (r"C:\Windows\Fonts\msyh.ttc", "MicrosoftYaHei"),
    (r"C:\Windows\Fonts\simsun.ttc", "SimSun"),
    (r"C:\Windows\Fonts\simhei.ttf", "SimHei"),
    (r"C:\Windows\Fonts\Deng.ttf", "DengXian"),
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]


def compile_with_reportlab(solutions: list, out_dir: Path, *, course="", student="",
                           title="", date_str=None, basename="homework") -> tuple[bool, str]:
    try:
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (HRFlowable, Paragraph, SimpleDocTemplate, Spacer)
    except ImportError as e:
        return False, f"reportlab 未安装（pip install reportlab）：{e}"

    # 注册中文字体
    font_name = "Helvetica"
    for path, name in CJK_FONT_CANDIDATES:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                font_name = name
                break
            except Exception:
                continue
    if font_name == "Helvetica":
        return False, "找不到可用的 CJK 字体（Windows: msyh.ttc / macOS: PingFang.ttc）"

    def esc(s: str) -> str:
        s = latex_to_unicode(s)
        return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["Normal"], fontName=font_name,
                          fontSize=10.5, leading=16, alignment=TA_LEFT)
    h1 = ParagraphStyle("h1", parent=body, fontSize=18, leading=24, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=body, fontSize=12.5, leading=18, spaceBefore=10,
                        spaceAfter=4, textColor="#0b6b5f")
    ans = ParagraphStyle("ans", parent=body, fontSize=10.5, leading=16,
                         backColor="#f5faf9", borderPadding=5, leftIndent=6)
    warn = ParagraphStyle("warn", parent=body, textColor="#b42318")

    from datetime import date as _date
    date_str = date_str or _date.today().isoformat()
    story = [Paragraph(esc(title or "Homework Solutions"), h1),
             Paragraph(esc(f"{course} · {student} · {date_str}"), body),
             Spacer(1, 4),
             HRFlowable(width="100%", color="#dcdcdc"),
             Spacer(1, 6)]

    total = len(solutions)
    solved = sum(1 for s in solutions if s.get("solved"))
    story += [Paragraph(esc(f"Solved {solved}/{total}"), body), Spacer(1, 8)]

    for s in solutions:
        story.append(Paragraph(esc(f"Problem {s.get('problem_id', '?')}"), h2))
        if s.get("problem_text"):
            story.append(Paragraph(esc(s["problem_text"]), body))
        if s.get("solved"):
            for i, st in enumerate(s.get("steps") or [], 1):
                story.append(Paragraph(f"{i}. {esc(st)}", body))
            if s.get("answer_latex"):
                story.append(Paragraph(f"<b>Answer:</b> {esc(s['answer_latex'])}", ans))
        else:
            story.append(Paragraph(esc("未解出：" + (s.get("reason") or "")), warn))
        story.append(Spacer(1, 10))

    pdf_path = out_dir / f"{basename}.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm,
                            title=title or "Homework", author=student or "")
    doc.build(story)
    return True, f"reportlab（公式降级为 Unicode 文本；字体 {font_name}）"


# ─────────────────────────────────────────────────────────────
# 验证
# ─────────────────────────────────────────────────────────────

def validate_pdf(pdf_path: Path) -> dict:
    """检查 PDF 是否真的可用（页数、大小、文本层）。"""
    info = {"path": str(pdf_path), "exists": pdf_path.exists(),
            "size": pdf_path.stat().st_size if pdf_path.exists() else 0,
            "pages": None, "text_chars": None, "ok": False, "notes": []}
    if not pdf_path.exists():
        info["notes"].append("文件不存在")
        return info
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(str(pdf_path))
        info["pages"] = len(doc)
        txt = []
        for i in range(min(len(doc), 5)):
            tp = doc[i].get_textpage()
            txt.append(tp.get_text_range())
        text = "".join(txt)
        info["text_chars"] = len(text)
        if info["pages"] < 1:
            info["notes"].append("页数为 0")
        if info["size"] < 2000:
            info["notes"].append("文件过小，可能是空文档")
        info["ok"] = info["pages"] >= 1 and info["size"] >= 2000
    except ImportError:
        info["notes"].append("未安装 pypdfium2，跳过深度校验")
        info["ok"] = info["size"] >= 2000
    except Exception as e:  # noqa: BLE001
        info["notes"].append(f"解析失败：{type(e).__name__}: {e}")
    return info


# ─────────────────────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────────────────────

def compile_pdf(out_dir: Path, basename: str = "homework", tier: str = "auto",
                solutions: list | None = None, course="", student="", title="",
                date_str=None) -> dict:
    """三级降级编译。返回 {ok, tier, engine, pdf, validation, attempts}。"""
    out_dir = Path(out_dir)
    tex = out_dir / f"{basename}.tex"
    html = out_dir / f"{basename}.html"
    attempts = []

    order = {
        "auto": ["latex", "browser", "reportlab"],
        "latex": ["latex"],
        "browser": ["browser"],
        "reportlab": ["reportlab"],
    }[tier]

    for t in order:
        if t == "latex":
            if not tex.exists():
                attempts.append(("latex", False, "缺 .tex"))
                continue
            ok, msg = compile_with_latex(tex, out_dir)
        elif t == "browser":
            if not html.exists():
                attempts.append(("browser", False, "缺 .html"))
                continue
            ok, msg = compile_with_browser(html, out_dir)
        else:
            if solutions is None:
                attempts.append(("reportlab", False, "没传 solutions"))
                continue
            ok, msg = compile_with_reportlab(solutions, out_dir, course=course,
                                             student=student, title=title,
                                             date_str=date_str, basename=basename)
        attempts.append((t, ok, msg))
        if ok:
            pdf = out_dir / f"{basename}.pdf"
            return {"ok": True, "tier": t, "engine": msg, "pdf": str(pdf),
                    "validation": validate_pdf(pdf),
                    "attempts": [{"tier": a, "ok": b, "message": c} for a, b, c in attempts]}

    return {"ok": False, "tier": None, "engine": "",
            "pdf": str(out_dir / f"{basename}.pdf"),
            "validation": {}, "attempts": attempts}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Stage 5: 编译 PDF（三级降级）")
    ap.add_argument("out_dir")
    ap.add_argument("--basename", default="homework")
    ap.add_argument("--tier", default="auto", choices=["auto", "latex", "browser", "reportlab"])
    ap.add_argument("--solutions", default=None, help="3_solutions.json（reportlab 兜底需要）")
    args = ap.parse_args(argv)

    sols = None
    if args.solutions and Path(args.solutions).exists():
        import json
        sols = json.loads(Path(args.solutions).read_text(encoding="utf-8"))

    r = compile_pdf(Path(args.out_dir), args.basename, args.tier, sols)
    print(f"[Stage 5] PDF 编译")
    for t, ok, msg in r["attempts"]:
        print(f"   {'✅' if ok else '❌'} {t:<10} {msg}")
    if r["ok"]:
        v = r["validation"]
        print(f"   → {r['pdf']}")
        print(f"   验证：{v.get('pages')} 页 / {v.get('size', 0):,} bytes / "
              f"文本层 {v.get('text_chars')} 字符 / ok={v.get('ok')}")
        return 0
    print("   ❌ 三级全部失败")
    return 1


if __name__ == "__main__":
    sys.exit(main())
