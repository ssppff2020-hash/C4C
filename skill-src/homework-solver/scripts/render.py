#!/usr/bin/env python3
"""
Stage 4: 排版渲染（LaTeX / Markdown / HTML 三路输出）
======================================================
starter kit 的 render_latex.py 只出 .tex，而且只认「题目 + 解答」两段。
C4C 的渲染层做了三件事：

1. **三路输出**：同一份 solutions.json →
       homework.tex    （给有 LaTeX 环境的人；专业排版）
       homework.html   （给没装 LaTeX 的人；浏览器直接看，也是 PDF 的中间产物）
       homework.md     （给想快速扫一眼 / 复制到 Notion 的人）
2. **多出一层「求解元信息」**：每题标注用了哪个求解器（SymPy / 国产模型）、
   置信度、验证方式。这是 C4C 对「可核验」要求的正面回应——
   交上去的作业里能看出每道题的答案是怎么来的。
3. **中文支持**：tex 用 ctex/ctexart（xelatex），html 用系统 CJK 字体，
   都不需要额外配置。

用法:
    python render.py <3_solutions.json> <输出目录> --course "..." --student "..."
"""

from __future__ import annotations

import argparse
import html as _html
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


# ─────────────────────────────────────────────────────────────
# 通用：把解答结构铺平成「题目块」
# ─────────────────────────────────────────────────────────────

def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[一-鿿]", text or ""))


_MATH_DELIM = re.compile(r"\$[^$]+\$")


def ensure_math(text: str) -> str:
    """把答案的裸 LaTeX 裹上 $...$，否则渲染层会把它当纯文本（踩过的坑见 ai-log B7）。

    已经带 $...$ 的原样返回；含中文叙述的答案会按「中文/公式」切开分别处理。
    """
    if not text:
        return ""
    s = str(text).strip()
    if not s:
        return ""
    if _MATH_DELIM.search(s):
        return s  # 已经有公式定界符

    # 纯中文答案（如 "正定"、"不存在（A 奇异）"）不加数学定界符
    if _has_cjk(s) and not re.search(r"[\\^_{}]", s):
        return s

    # `\text{...}` 包着中文的情况：整体当数学式即可，MathJax 能处理 \text
    return f"${s}$"


def _flat_problem_block(sol: dict) -> dict:
    """把一条解答转成渲染层要的中间结构。"""
    return {
        "id": sol.get("problem_id", "?"),
        "text": sol.get("problem_text", ""),
        "solved": bool(sol.get("solved")),
        "steps": sol.get("steps") or [],
        "answer": ensure_math(sol.get("answer_latex") or ""),
        "reason": sol.get("reason") or "",
        "solver": sol.get("solver") or "",
        "subject": sol.get("subject") or "",
        "confidence": sol.get("confidence"),
        "verification": sol.get("verification") or {},
        "subs": [{
            "id": s.get("problem_id", "?"),
            "text": s.get("problem_text", ""),
            "solved": bool(s.get("solved")),
            "steps": s.get("steps") or [],
            "answer": ensure_math(s.get("answer_latex") or ""),
            "reason": s.get("reason") or "",
        } for s in (sol.get("sub_solutions") or [])],
        "partial": sol.get("partial", False),
    }


# ─────────────────────────────────────────────────────────────
# ① LaTeX
# ─────────────────────────────────────────────────────────────

def _tex_escape(text: str) -> str:
    """转义非数学部分（保留 $...$ 与 $$...$$）。"""
    parts = re.split(r"(\$\$.*?\$\$|\$.*?\$)", text or "", flags=re.DOTALL)
    out = []
    for part in parts:
        if part.startswith("$"):
            out.append(part)
        else:
            s = part
            for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                         ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}")):
                s = s.replace(a, b)
            s = s.replace("~", r"\textasciitilde{}").replace("^", r"\textasciicircum{}")
            out.append(s)
    return "".join(out)


# 这些命令 starter 的模板里没有，加进 preamble 免得编译报错
_EXTRA_PREAMBLE = r"""
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{enumitem}
\usepackage{xcolor}
\definecolor{solvercolor}{RGB}{90,90,90}
\definecolor{unsolvedcolor}{RGB}{180,0,0}
\newenvironment{answerbox}{\begin{quote}\bfseries\color{teal}}{\end{quote}}
\newcommand{\solvertag}[1]{{\footnotesize\color{solvercolor}\textsf{[#1]}}}
"""


def render_tex(solutions: list, course="", student="", title="", date_str=None,
               chinese=None) -> str:
    if date_str is None:
        date_str = date.today().isoformat()
    blocks = [_flat_problem_block(s) for s in solutions]

    if chinese is None:
        chinese = any(_has_cjk(b["text"] + "".join(b["steps"])) for b in blocks) \
            or _has_cjk(course + student + title)

    if chinese:
        doc = (r"\documentclass[11pt,a4paper]{ctexart}" + "\n"
               r"\usepackage[margin=2.2cm]{geometry}" + "\n")
    else:
        doc = (r"\documentclass[11pt,a4paper]{article}" + "\n"
               r"\usepackage[margin=2.2cm]{geometry}" + "\n"
               r"\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}" + "\n")

    doc += (r"\usepackage{amsmath,amssymb}" "\n"
            r"\usepackage{fancyhdr}\usepackage{enumitem}\usepackage{xcolor}" "\n"
            r"\usepackage{hyperref}" "\n"
            r"\pagestyle{fancy}\fancyhf{}" "\n"
            rf"\rhead{{{_tex_escape(course or '')}}}" "\n"
            rf"\lhead{{{_tex_escape(student or '')}}}" "\n"
            r"\rfoot{Page \thepage}" "\n"
            r"\newcommand{\solvertag}[1]{{\footnotesize\color{gray}\textsf{[#1]}}}" "\n"
            "\n")

    doc += (r"\title{" + _tex_escape(title or "Homework") + "}\n"
            r"\author{" + _tex_escape(student or "") + "}\n"
            r"\date{" + _tex_escape(date_str) + "}\n"
            r"\begin{document}" "\n" r"\maketitle" "\n\n")

    total = len(blocks)
    solved = sum(1 for b in blocks if b["solved"])
    doc += (rf"\noindent\textbf{{Solved: {solved}/{total}"
            rf" ({100*solved/max(total,1):.1f}\%)}}\quad"
            r"\textit{Auto-generated by C4C homework-solver.}" "\n\n")

    for b in blocks:
        doc += rf"\section*{{Problem {_tex_escape(str(b['id']))}}}" + "\n"
        if b["text"]:
            doc += _tex_escape(b["text"]) + "\n\n"
        if b["solved"]:
            doc += r"\paragraph{Solution.}" + " "
            if b["solver"]:
                doc += r"\solvertag{" + _tex_escape(str(b["solver"])) + "} "
            doc += "\n\n"
            if b["steps"]:
                doc += r"\begin{enumerate}[leftmargin=*]" "\n"
                for st in b["steps"]:
                    doc += r"  \item " + _tex_escape(st) + "\n"
                doc += r"\end{enumerate}" "\n\n"
            if b["subs"]:
                for s in b["subs"]:
                    doc += rf"\paragraph{{({_tex_escape(str(s['id']))})}} "
                    if s["solved"]:
                        doc += _tex_escape(s["answer"]) + "\n\n"
                    else:
                        doc += (r"{\color{red}\textit{unsolved: "
                                + _tex_escape(s["reason"]) + r"}}" + "\n\n")
            if b["answer"]:
                doc += r"\noindent\textbf{Answer:}\quad " + _tex_escape(b["answer"]) + "\n\n"
        else:
            doc += (r"{\color{red}\textit{Not solved.} "
                    + _tex_escape(b["reason"]) + "}" + "\n\n")
        doc += r"\medskip" "\n\n"

    doc += r"\end{document}" "\n"
    return doc


# ─────────────────────────────────────────────────────────────
# ② Markdown
# ─────────────────────────────────────────────────────────────

def render_markdown(solutions: list, course="", student="", title="", date_str=None) -> str:
    if date_str is None:
        date_str = date.today().isoformat()
    blocks = [_flat_problem_block(s) for s in solutions]
    total = len(blocks)
    solved = sum(1 for b in blocks if b["solved"])
    lines = [
        f"# {title or 'Homework Solutions'}",
        "",
        f"- **Course**: {course}",
        f"- **Student**: {student}",
        f"- **Date**: {date_str}",
        f"- **Solved**: {solved}/{total} ({100*solved/max(total,1):.1f}%)",
        "",
        "---",
        "",
    ]
    for b in blocks:
        lines.append(f"## Problem {b['id']}")
        lines.append("")
        if b["text"]:
            lines += [b["text"].strip(), ""]
        if b["solved"]:
            tag = f" `[{b['solver']}]`" if b["solver"] else ""
            lines.append(f"**Solution**{tag}")
            lines.append("")
            for i, st in enumerate(b["steps"], 1):
                lines.append(f"{i}. {st}")
            if b["steps"]:
                lines.append("")
            for s in b["subs"]:
                if s["solved"]:
                    lines.append(f"- **({s['id']})** {s['answer']}")
                else:
                    lines.append(f"- **({s['id']})** _未解：{s['reason']}_")
            if b["subs"]:
                lines.append("")
            lines.append(f"**Answer**: {b['answer']}")
            lines.append("")
        else:
            lines.append(f"> ⚠️ **未解出**：{b['reason']}")
            lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# ③ HTML（也是 PDF 的中间产物）
# ─────────────────────────────────────────────────────────────

_HTML_CSS = """
:root { --ink:#1a1a1a; --muted:#6b6b6b; --rule:#dcdcdc; --accent:#0b6b5f;
        --warn:#b42318; --bg:#ffffff; }
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei","Noto Sans CJK SC","PingFang SC","Segoe UI",sans-serif;
       color: var(--ink); background: var(--bg); line-height: 1.72;
       margin: 0 auto; max-width: 860px; padding: 34px 40px 60px; font-size: 15px; }
h1 { font-size: 1.7em; margin: 0 0 .2em; letter-spacing: .01em; }
h2 { font-size: 1.16em; margin: 1.9em 0 .5em; padding-bottom: .28em;
     border-bottom: 1px solid var(--rule); }
.meta { color: var(--muted); font-size: .9em; margin-bottom: 1.6em; }
.meta b { color: var(--ink); }
.problem { margin-bottom: 1.6em; page-break-inside: avoid; }
.prompt { margin: .2em 0 .8em; }
ol.steps { margin: .35em 0 .7em; padding-left: 1.5em; }
ol.steps li { margin: .28em 0; }
.answer { border-left: 3px solid var(--accent); background: #f5faf9;
          padding: .55em .9em; margin: .7em 0; border-radius: 3px; }
.answer .lbl { font-weight: 700; color: var(--accent); margin-right: .5em; }
.tag { font-size: .74em; color: var(--muted); border: 1px solid var(--rule);
       border-radius: 3px; padding: .05em .42em; margin-left: .5em; vertical-align: middle;
       font-family: ui-monospace, Consolas, monospace; }
.unsolved { color: var(--warn); background: #fdf3f2; border-left: 3px solid var(--warn);
            padding: .55em .9em; border-radius: 3px; }
.sub { margin: .45em 0 .45em 1.1em; }
.sub .lab { font-weight: 600; margin-right: .4em; }
.conf { color: var(--muted); font-size: .82em; }
hr { border: none; border-top: 1px solid var(--rule); margin: 2em 0; }
@page { margin: 16mm 14mm; }
"""


def _html_escape_outside_math(text: str) -> str:
    """HTML 转义，但保留 $...$ / $$...$$ 里的 LaTeX 原样给 MathJax。"""
    parts = re.split(r"(\$\$.*?\$\$|\$.*?\$)", text or "", flags=re.DOTALL)
    out = []
    for part in parts:
        if part.startswith("$"):
            out.append(part)
        else:
            out.append(_html.escape(part).replace("\n", "<br>"))
    return "".join(out)


def render_html(solutions: list, course="", student="", title="", date_str=None,
                mathjax_path: str = "references/mathjax/tex-svg.js",
                embed_mathjax: bool = False) -> str:
    if date_str is None:
        date_str = date.today().isoformat()
    blocks = [_flat_problem_block(s) for s in solutions]
    total = len(blocks)
    solved = sum(1 for b in blocks if b["solved"])

    if embed_mathjax:
        mj_file = Path(mathjax_path)
        if mj_file.exists():
            script = f"<script>{mj_file.read_text(encoding='utf-8')}</script>"
        else:
            script = '<script src="%s"></script>' % mathjax_path
    else:
        script = '<script src="%s"></script>' % mathjax_path

    parts = [
        "<!DOCTYPE html>",
        '<html lang="zh"><head><meta charset="utf-8">',
        f"<title>{_html.escape(title or 'Homework')}</title>",
        "<script>window.MathJax={tex:{inlineMath:[['$','$']],displayMath:[['$$','$$']],"
        "tags:'none'},svg:{fontCache:'local'},options:{enableMenu:false}};</script>",
        script,
        f"<style>{_HTML_CSS}</style>",
        "</head><body>",
        f"<h1>{_html.escape(title or 'Homework Solutions')}</h1>",
        '<div class="meta">'
        f"<b>Course</b> {_html.escape(course or '—')} &nbsp;·&nbsp; "
        f"<b>Student</b> {_html.escape(student or '—')} &nbsp;·&nbsp; "
        f"<b>Date</b> {_html.escape(date_str)} &nbsp;·&nbsp; "
        f"<b>Solved</b> {solved}/{total} ({100*solved/max(total,1):.1f}%)"
        "</div>",
        "<hr>",
    ]

    for b in blocks:
        parts.append('<div class="problem">')
        parts.append(f"<h2>Problem {_html.escape(str(b['id']))}</h2>")
        if b["text"]:
            parts.append(f'<div class="prompt">{_html_escape_outside_math(b["text"])}</div>')
        if b["solved"]:
            if b["steps"]:
                parts.append('<ol class="steps">')
                for st in b["steps"]:
                    parts.append(f"<li>{_html_escape_outside_math(st)}</li>")
                parts.append("</ol>")
            for s in b["subs"]:
                if s["solved"]:
                    parts.append(
                        f'<div class="sub"><span class="lab">({_html.escape(str(s["id"]))})</span>'
                        f'{_html_escape_outside_math(s["answer"])}</div>')
                else:
                    parts.append(
                        f'<div class="sub unsolved"><span class="lab">({_html.escape(str(s["id"]))})</span>'
                        f'未解：{_html.escape(s["reason"])}</div>')
            parts.append('<div class="answer"><span class="lbl">Answer</span>'
                         + _html_escape_outside_math(b["answer"]) + "</div>")
            foot = []
            if b["solver"]:
                foot.append(f'<span class="tag">{_html.escape(str(b["solver"]))}</span>')
            if b["confidence"] is not None and b["solver"].startswith("llm"):
                foot.append(f'<span class="conf">置信度 {b["confidence"]:.2f}</span>')
            if b["subject"]:
                foot.append(f'<span class="conf">{_html.escape(str(b["subject"]))}</span>')
            if foot:
                parts.append("<div>" + " ".join(foot) + "</div>")
        else:
            parts.append(f'<div class="unsolved">⚠️ <b>未解出</b>：{_html.escape(b["reason"])}</div>')
        parts.append("</div>")

    parts.append("</body></html>")
    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def render_all(solutions: list, out_dir: Path, *, course="", student="", title="",
               date_str=None, basename="homework", mathjax_path=None,
               embed_mathjax=False) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    produced = {}

    tex = render_tex(solutions, course, student, title, date_str)
    (out_dir / f"{basename}.tex").write_text(tex, encoding="utf-8")
    produced["tex"] = str(out_dir / f"{basename}.tex")

    md = render_markdown(solutions, course, student, title, date_str)
    (out_dir / f"{basename}.md").write_text(md, encoding="utf-8")
    produced["md"] = str(out_dir / f"{basename}.md")

    if mathjax_path is None:
        mathjax_path = str(Path(__file__).resolve().parent.parent / "references/mathjax/tex-svg.js")
    html = render_html(solutions, course, student, title, date_str,
                       mathjax_path=mathjax_path, embed_mathjax=embed_mathjax)
    (out_dir / f"{basename}.html").write_text(html, encoding="utf-8")
    produced["html"] = str(out_dir / f"{basename}.html")

    return produced


def main(argv=None):
    ap = argparse.ArgumentParser(description="Stage 4: 排版渲染")
    ap.add_argument("input", help="3_solutions.json")
    ap.add_argument("out_dir", help="输出目录")
    ap.add_argument("--course", default="Mathematics")
    ap.add_argument("--student", default="Student")
    ap.add_argument("--title", default="Homework Solutions")
    ap.add_argument("--date", default=None)
    ap.add_argument("--basename", default="homework")
    ap.add_argument("--embed-mathjax", action="store_true",
                    help="把 MathJax 内联进 HTML（单文件，便于分发）")
    args = ap.parse_args(argv)

    solutions = json.loads(Path(args.input).read_text(encoding="utf-8"))
    produced = render_all(solutions, Path(args.out_dir), course=args.course,
                          student=args.student, title=args.title, date_str=args.date,
                          basename=args.basename, embed_mathjax=args.embed_mathjax)
    print(f"[Stage 4] 排版完成：")
    for k, v in produced.items():
        print(f"   {k:5} → {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
