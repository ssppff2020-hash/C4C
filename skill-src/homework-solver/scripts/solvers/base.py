#!/usr/bin/env python3
"""
solvers/base.py —— 所有学科求解器共享的地基
============================================
三件事：

1. **LaTeX → SymPy 的表达式解析**（`parse_tex` / `parse_tex_matrix`）
   starter kit 里有一个只管 \frac 的 `safe_parse`；这里把它扩展成
   能处理 \sqrt \cdot \times \pi \sin \lim \int \begin{pmatrix} 等
   作业里真正会出现的东西。零依赖（不用 antlr4），因为学生的机器上
   通常装不上 sympy 的 LaTeX 解析器。

2. **统一的解答数据结构**（`sol` / `unsolved` / `sub_sol`）
   字段与 starter kit 的 3_solutions.json 完全兼容（render 阶段直接复用），
   另外附加了 solver / confidence / verification 三个字段。

3. **符号与变量工具**（`symbols_for` / `find_var` / `auto_symbols`）
   从题干文本里猜出自变量和参数，避免每道题都手写符号表。
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

import sympy
from sympy import (
    Abs, Matrix, Rational, Symbol, acos, asin, atan, cos, cosh, exp, factorial,
    log, pi, sin, sinh, sqrt, symbols, tan, tanh, E, I, oo, sympify,
)

# ─────────────────────────────────────────────────────────────
# 1. LaTeX → 文本表达式
# ─────────────────────────────────────────────────────────────

_GREEK = {
    r"\alpha": "alpha", r"\beta": "beta", r"\gamma": "gamma", r"\delta": "delta",
    r"\epsilon": "epsilon", r"\varepsilon": "epsilon", r"\theta": "theta",
    r"\lambda": "lambda", r"\mu": "mu", r"\rho": "rho", r"\sigma": "sigma",
    r"\tau": "tau", r"\phi": "phi", r"\varphi": "phi", r"\omega": "omega",
    r"\Omega": "Omega", r"\Delta": "Delta", r"\Sigma": "Sigma", r"\Theta": "Theta",
    r"\Phi": "Phi", r"\Lambda": "Lambda", r"\pi": "pi",
}

# 顺序重要：先长后短
_TEXT_SUBS: list[tuple[str, str]] = [
    (r"\cdot", "*"), (r"\times", "*"), (r"\div", "/"),
    (r"\pm", "+"), (r"\mp", "-"),
    (r"\infty", "oo"), (r"\infinity", "oo"),
    (r"\leq", "<="), (r"\le", "<="), (r"\geq", ">="), (r"\ge", ">="),
    (r"\neq", "!="), (r"\ne", "!="), (r"\approx", "="), (r"\equiv", "="),
    (r"\to", "->"), (r"\rightarrow", "->"), (r"\Rightarrow", "=>"),
    (r"\%", "/100"),
]

# LaTeX 函数命令 → SymPy 函数名。
# 必须在「丢弃未知 \\命令」之前替换，否则 \sin(x) 会被清成 (x)。
_FUNCTIONS: list[tuple[str, str]] = [
    (r"\arcsin", "asin"), (r"\arccos", "acos"), (r"\arctan", "atan"),
    (r"\sinh", "sinh"), (r"\cosh", "cosh"), (r"\tanh", "tanh"),
    (r"\coth", "coth"), (r"\sech", "sech"), (r"\csch", "csch"),
    (r"\cot", "cot"), (r"\sec", "sec"), (r"\csc", "csc"),
    (r"\sin", "sin"), (r"\cos", "cos"), (r"\tan", "tan"),
    (r"\ln", "log"), (r"\log", "log"), (r"\lg", "log"), (r"\exp", "exp"),
    (r"\max", "Max"), (r"\min", "Min"), (r"\det", "det"), (r"\tr", "trace"),
]

# sympify 时被当作「函数名」的标识符（后面紧跟 ( 时按调用处理，不做隐式乘法）
_FUNC_NAMES = {
    "sin", "cos", "tan", "cot", "sec", "csc", "asin", "acos", "atan",
    "sinh", "cosh", "tanh", "coth", "sech", "csch", "log", "exp", "sqrt",
    "Abs", "Max", "Min", "factorial", "sign", "floor", "ceiling",
}


def strip_math_delims(s: str) -> str:
    """去掉 $...$、$$...$$、\\[ \\] 、\\( \\) 等数学定界符。"""
    s = s.strip()
    s = re.sub(r"^\$\$(.*)\$\$$", r"\1", s, flags=re.DOTALL)
    s = re.sub(r"^\$(.*)\$$", r"\1", s, flags=re.DOTALL)
    s = re.sub(r"^\\\[(.*)\\\]$", r"\1", s, flags=re.DOTALL)
    s = re.sub(r"^\\\((.*)\\\)$", r"\1", s, flags=re.DOTALL)
    return s.strip()


def _strip_outer_braces(s: str) -> str:
    s = s.strip()
    while s.startswith("{") and s.endswith("}") and _braces_balanced(s[1:-1]):
        s = s[1:-1].strip()
    return s


def _braces_balanced(s: str) -> bool:
    depth = 0
    for ch in s:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _find_group(s: str, start: int) -> tuple[str, int]:
    """从 s[start] 位置读一个 LaTeX 参数（{...} 块或单个 token）。

    返回 (内容, 结束位置)。
    """
    if start >= len(s):
        return "", start
    if s[start] == "{":
        depth = 0
        for i in range(start, len(s)):
            if s[i] == "{":
                depth += 1
            elif s[i] == "}":
                depth -= 1
                if depth == 0:
                    return s[start + 1:i], i + 1
        return s[start + 1:], len(s)
    if s[start] == "\\":  # 单命令，如 \pi
        m = re.match(r"\\[a-zA-Z]+", s[start:])
        if m:
            return m.group(0), start + m.end()
    return s[start], start + 1


# ── 词法分析：把中间文本切成 token，再做隐式乘法 ──
_TOKEN_RE = re.compile(
    r"(?P<num>\d+\.\d+|\d+)"
    r"|(?P<name>[A-Za-z_][A-Za-z_0-9]*)"
    r"|(?P<op>\*\*|<=|>=|!=|==|//|[-+*/^(),\[\]{}=<>!|&;:])"
    r"|(?P<space>\s+)"
)


def _insert_implicit_mul(s: str) -> str:
    """在相邻 token 之间补 `*`：2x → 2*x，)( → )*(，pi x → pi*x，3sin(x) → 3*sin(x)。

    但 `sin(` 这种函数调用不补。用 token 流做，比正则可靠。
    """
    tokens: list[tuple[str, str]] = []
    pos = 0
    while pos < len(s):
        m = _TOKEN_RE.match(s, pos)
        if not m:
            tokens.append(("op", s[pos]))  # 不认识的字符原样保留，不要吞掉
            pos += 1
            continue
        kind = m.lastgroup
        tokens.append((kind, m.group()))
        pos = m.end()

    out: list[str] = []
    for i, (kind, val) in enumerate(tokens):
        if kind == "space":
            continue
        if out:
            prev_kind, prev_val = tokens[i - 1]
            if prev_kind == "space":
                # 跳过空格找上一个有意义的 token
                for j in range(i - 2, -1, -1):
                    if tokens[j][0] != "space":
                        prev_kind, prev_val = tokens[j]
                        break
            left_can_end = (
                prev_kind in ("num", "name") or
                (prev_kind == "op" and prev_val in (")", "]"))
            )
            right_can_start = (
                kind in ("num", "name") or
                (kind == "op" and val in ("(",))
            )
            if left_can_end and right_can_start:
                is_call = (kind == "op" and val == "(" and
                           prev_kind == "name" and prev_val in _FUNC_NAMES)
                is_power = (prev_kind == "op" and prev_val == "*" and
                            len(out) >= 1 and False)
                if not is_call and not is_power:
                    # `**` 后面紧跟的 ( 是幂的括号，不是乘法
                    if not (prev_kind == "op" and prev_val == "*" and
                            len(out) >= 1 and out[-1] == "**"):
                        out.append("*")
        out.append(val)
    return "".join(out)


def latex_to_text(tex: str, keep_units: bool = False) -> str:
    """把 LaTeX 数学式转成 SymPy 能 sympify 的文本。

    keep_units=False 时会剥掉 `dx`/`dt` 这类微分符号（积分求解器会自己抽）。
    """
    s = strip_math_delims(tex)

    # ── 1. 矩阵环境先转成可解析形式：行内用逗号、行间用分号 ──
    s = re.sub(
        r"\\begin\{(?:p|b|v|B|V)?matrix\}(.*?)\\end\{(?:p|b|v|B|V)?matrix\}",
        lambda m: "matrix@@" + m.group(1).replace("&", ",").replace("\\\\", ";") + "@@",
        s, flags=re.DOTALL,
    )

    # ── 2. 嵌套展开 \frac 与 \sqrt ──
    s = _expand_wrappers(s)

    # ── 3. 积分/求和/极限的算子与上下限 ──
    #     替换成带空格的符号名，避免和相邻字母粘连（n\sin → n*sin，不是 nsin）
    s = re.sub(r"\\(?:iint|iiint|oint|int)\s*(?:_\{[^{}]*\}|_[^\s{}])?\s*(?:\^\{[^{}]*\}|\^[^\s{}])?",
               " INTEGRAL ", s)
    s = re.sub(r"\\sum\s*(?:_\{[^{}]*\}|_[^\s{}])?\s*(?:\^\{[^{}]*\}|\^[^\s{}])?", " Sum ", s)
    s = re.sub(r"\\prod\s*(?:_\{[^{}]*\}|_[^\s{}])?\s*(?:\^\{[^{}]*\}|\^[^\s{}])?", " Product ", s)
    s = re.sub(r"\\lim\s*(?:_\{[^{}]*\}|_[^\s{}])?", " LIMIT ", s)
    s = re.sub(r"\\partial", "PartialD", s)
    s = re.sub(r"\\mathrm\{d\}", "d", s)
    s = re.sub(r"\\operatorname\{([^{}]*)\}", r"\1", s)

    # ── 4. 函数命令（必须在丢弃 \命令 之前）──
    #     同样补空格：n\sin(x) 必须变成 n * sin(x)
    for k, v in _FUNCTIONS:
        s = re.sub(re.escape(k) + r"(?![a-zA-Z])", " " + v + " ", s)

    # ── 5. 字体/间距/定界符命令 ──
    for cmd in (r"\left", r"\right", r"\big", r"\Big", r"\bigg", r"\Bigg",
                r"\mathbf", r"\mathrm", r"\mathit", r"\text", r"\mathcal",
                r"\mathbb", r"\boxed", r"\displaystyle", r"\limits", r"\boldsymbol"):
        s = re.sub(re.escape(cmd) + r"\s*", "", s)
    s = (s.replace(r"\,", " ").replace(r"\;", " ").replace(r"\!", "")
          .replace(r"\quad", " ").replace(r"\qquad", " ").replace("~", " "))

    # ── 6. 希腊字母与符号 ──
    for k, v in sorted(_GREEK.items(), key=lambda kv: -len(kv[0])):
        s = s.replace(k, v)
    for k, v in _TEXT_SUBS:
        s = s.replace(k, v)

    # ── 7. 上标 ──
    s = re.sub(r"\^\{([^{}]*)\}", r"**(\1)", s)
    s = re.sub(r"\^(\w)", r"**\1", s)
    s = s.replace("^", "**")

    if not keep_units:
        s = re.sub(r"(?<=[a-zA-Z0-9\)\]])\s*[*\s]?\bd\s*([a-zA-Z])\b\s*$", "", s)
        s = re.sub(r"\bd\s*([a-zA-Z])\s*$", "", s)

    # ── 8. 清掉剩余未知命令，花括号降级为圆括号 ──
    s = re.sub(r"\\[a-zA-Z]+", "", s)
    s = s.replace("{", "(").replace("}", ")")

    # ── 8b. |x| → Abs(x)，且 | 必须成对 ──
    if s.count("|") >= 2:
        s = re.sub(r"\|([^|]*)\|", r"Abs(\1)", s)

    # ── 9. 清掉残留的定界符与句末标点 ──
    #   题干里的 "… = x^{2}+y^{2}$," 会留下一串 $ 和句号，sympify 直接崩。
    s = s.replace("$", "")
    s = re.sub(r"[.。;；:：]+\s*$", "", s).strip()

    # ── 10. 隐式乘法 ──
    s = _insert_implicit_mul(s)

    # ── 10. 常数 e / pi ──
    s = re.sub(r"\be\s*\*\*", "E**", s)
    return s.strip()


def _expand_wrappers(s: str) -> str:
    """循环展开嵌套的 \\frac 和 \\sqrt。"""
    prev = None
    guard = 0
    while prev != s and guard < 40:
        guard += 1
        prev = s
        out = []
        i = 0
        while i < len(s):
            if s.startswith(r"\frac", i) or s.startswith(r"\dfrac", i) or s.startswith(r"\tfrac", i):
                cmd_len = len(r"\frac")
                if s.startswith(r"\dfrac", i):
                    cmd_len = len(r"\dfrac")
                elif s.startswith(r"\tfrac", i):
                    cmd_len = len(r"\tfrac")
                num, j = _find_group(s, i + cmd_len)
                den, k = _find_group(s, j)
                out.append("((" + num + ")/(" + den + "))")
                i = k
            elif s.startswith(r"\sqrt", i):
                j = i + len(r"\sqrt")
                if j < len(s) and s[j] == "[":
                    k = s.index("]", j)
                    deg = s[j + 1:k]
                    body, nxt = _find_group(s, k + 1)
                    out.append("((" + body + ")**(1/(" + deg + ")))")
                    i = nxt
                else:
                    body, nxt = _find_group(s, j)
                    out.append("sqrt(" + body + ")")
                    i = nxt
            else:
                out.append(s[i])
                i += 1
        s = "".join(out)
    return s


def parse_tex(tex: str, locals_map: Optional[dict] = None):
    """把一段 LaTeX 数学式转成 SymPy 表达式。失败返回 None。"""
    if tex is None:
        return None
    s = latex_to_text(tex)
    if not s:
        return None
    try:
        return sympify(s, locals=locals_map or {}, evaluate=True)
    except Exception:
        # 兜底：再试一次，这次让 sympify 自己去猜符号
        try:
            return sympify(s, evaluate=True)
        except Exception:
            return None


def parse_tex_matrix(tex: str):
    """解析 \\begin{pmatrix}...\\end{pmatrix} 或 [[1,2],[3,4]] 形式的矩阵。

    返回 sympy.Matrix，失败返回 None。
    """
    if not tex:
        return None
    s = strip_math_delims(tex)

    # A = ... 前缀
    m = re.search(r"\\begin\{(?:p|b|v|B|V)?matrix\}(.*?)\\end\{(?:p|b|v|B|V)?matrix\}", s, re.DOTALL)
    if m:
        body = m.group(1)
        rows = [r for r in re.split(r"\\\\", body) if r.strip()]
        data = []
        for r in rows:
            cells = [_strip_outer_braces(c.strip()) for c in r.split("&")]
            row = []
            for c in cells:
                e = parse_tex(c)
                if e is None:
                    return None
                row.append(e)
            data.append(row)
        try:
            return Matrix(data)
        except Exception:
            return None

    # [[1,2],[3,4]] / ((1,2),(3,4))
    m = re.search(r"[\[\(]\s*[\[\(](.*)[\]\)]\s*[\]\)]", s, re.DOTALL)
    if m:
        body = m.group(1)
        rows = re.split(r"[\]\)]\s*,\s*[\[\(]", body)
        data = []
        for r in rows:
            row = []
            for c in r.split(","):
                e = parse_tex(c)
                if e is None:
                    return None
                row.append(e)
            data.append(row)
        try:
            return Matrix(data)
        except Exception:
            return None
    return None


# ─────────────────────────────────────────────────────────────
# 2. 符号工具
# ─────────────────────────────────────────────────────────────

CANONICAL_SYMBOLS = ("x", "y", "z", "t", "n", "u", "v", "w", "s", "r", "h")


def auto_symbols(text: str, extra: Iterable[str] = ()) -> dict:
    """从题干里搜集出现的单字母变量，返回 {name: Symbol}。"""
    names = set(re.findall(r"\b([a-zA-Z])\b", text or ""))
    names |= {c for c in CANONICAL_SYMBOLS if c in (text or "")}
    names |= set(extra)
    # 去掉显然是常数的 e / i（除非题里明确用 e 做变量）
    keep_letters = {n for n in names if n not in ("c",)}
    return {n: Symbol(n) for n in sorted(keep_letters)}


def find_primary_var(text: str, default: str = "x") -> Symbol:
    """猜题干里的主变量：lim_{x->...} 的 x，或出现次数最多的单字母。"""
    m = re.search(r"(?:lim|LIMIT)\s*_?\s*\{?\s*([a-zA-Z])\s*(?:\\?to|->|→)", text or "")
    if m:
        return Symbol(m.group(1))
    m = re.search(r"(?:d\s*/\s*d|\\frac\{d\}\{d)\s*([a-zA-Z])", text or "")
    if m:
        return Symbol(m.group(1))
    counts: dict[str, int] = {}
    for ch in re.findall(r"\b([a-zA-Z])\b", text or ""):
        counts[ch] = counts.get(ch, 0) + 1
    counts.pop("e", None)
    if counts:
        return Symbol(max(counts, key=counts.get))
    return Symbol(default)


# ─────────────────────────────────────────────────────────────
# 3. 统一解答结构（与 starter kit 的 3_solutions.json 兼容）
# ─────────────────────────────────────────────────────────────

def _answer_latex(answer) -> str:
    if isinstance(answer, str):
        return answer
    try:
        return sympy.latex(answer)
    except Exception:
        return str(answer)


def sol(problem: dict, steps: list, answer, solver: str = "sympy",
        confidence: float = 1.0, sub_solutions: Optional[list] = None,
        verification: Optional[dict] = None, subject: Optional[str] = None) -> dict:
    """构造一条已解解答。"""
    d = {
        "problem_id": problem.get("id", "?"),
        "problem_text": problem.get("text", ""),
        "solved": True,
        "steps": steps or [],
        "answer": _answer_latex(answer),
        "answer_latex": _answer_latex(answer),
        "solver": solver,
        "confidence": confidence,
        "subject": subject or problem.get("subject") or problem.get("type"),
        "sub_solutions": sub_solutions or [],
    }
    if verification:
        d["verification"] = verification
    return d


def unsolved(problem: dict, reason: str, solver: str = "none",
             sub_solutions: Optional[list] = None, subject: Optional[str] = None) -> dict:
    """构造一条未解解答（必须写清楚为什么没解出来，评审时看得到）。"""
    return {
        "problem_id": problem.get("id", "?"),
        "problem_text": problem.get("text", ""),
        "solved": False,
        "steps": [],
        "answer": None,
        "answer_latex": "",
        "reason": reason,
        "solver": solver,
        "confidence": 0.0,
        "subject": subject or problem.get("subject") or problem.get("type"),
        "sub_solutions": sub_solutions or [],
    }


def sub_sol(sub: dict, steps: list, answer, solver: str = "sympy",
            solved: bool = True, confidence: float = 1.0) -> dict:
    """构造一条子题（(a)/(b)/(c)）解答。"""
    return {
        "problem_id": sub.get("id", "?"),
        "problem_text": sub.get("text", ""),
        "solved": solved,
        "steps": steps or [],
        "answer": _answer_latex(answer) if solved else None,
        "answer_latex": _answer_latex(answer) if solved else "",
        "solver": solver if solved else "none",
        "confidence": confidence if solved else 0.0,
        "sub_solutions": [],
    }


def sub_unsolved(sub: dict, reason: str) -> dict:
    d = sub_sol(sub, [], "", solved=False)
    d["reason"] = reason
    return d


def T(expr) -> str:
    """把 SymPy 表达式转成 LaTeX 字符串（供 steps 里内联）。"""
    return f"${sympy.latex(expr)}$"


def merge_subs_answer(sub_solutions: list) -> str:
    """把子题答案合并成一行 LaTeX，作为父题答案。"""
    parts = []
    for s in sub_solutions:
        label = str(s.get("problem_id", "")).split(".")[-1] or "?"
        if s.get("solved"):
            parts.append(f"\\text{{({label})}}\\ {s.get('answer_latex', '')}")
        else:
            parts.append(f"\\text{{({label})}}\\ \\text{{未解出}}")
    return ",\\quad ".join(parts)
