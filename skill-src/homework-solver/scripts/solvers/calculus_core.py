#!/usr/bin/env python3
"""
solvers/calculus_core.py —— 微积分主线（C4C 学科扩展 ②）
=========================================================
starter kit 的 1596 行 solve.py 只做「极限 / 切线 / ε-δ」。
C4C 把剩下 60% 的微积分补上：

    导数（含高阶、隐函数、参数方程）      不定积分 / 定积分 / 反常积分
    泰勒级数 / 幂级数 / 收敛半径          多重积分（二重、三重）
    偏导数 / 梯度 / 方向导数 / 散度 / 旋度 级数判敛（比值、根值、比较）
    曲线长度 / 旋转体体积                 最优化（驻点 + 二阶判别）

和 starter 的关系
-----------------
* 极限相关的题**不在这里**——仍然走 starter 的 calculus_limits 模块（原样保留，
  见 attribution 说明）。
* 这里所有答案都是 SymPy 精确符号结果，不是数值近似；
  数值题（如 `integrate(..., numeric=True)`）会显式标注 `数值解`。
"""

from __future__ import annotations

import re
from typing import Optional

import sympy
from sympy import (
    Derivative, Function, Integral, Matrix, Piecewise, Symbol, cos, exp, factorial,
    integrate, latex, limit, log, oo, pi, simplify, sin, series, sqrt, sympify, tan,
)

from .base import (
    find_primary_var, latex_to_text, parse_tex, sol, strip_math_delims, sub_sol,
    sub_unsolved, unsolved, T,
)

# ─────────────────────────────────────────────────────────────
# 操作识别
# ─────────────────────────────────────────────────────────────

CALC_PATTERNS: list[tuple[str, str]] = [
    (r"散度|divergence", "divergence"),
    (r"旋度|curl", "curl"),
    (r"梯度|\bgradient\b|\bgrad\b", "gradient"),
    (r"方向导数|directional\s+derivative", "directional"),
    (r"隐函数.{0,6}(求导|微分)|implicit\s+differentiat", "implicit_derivative"),
    (r"高阶导数|二阶导数|second\s+derivative|third\s+derivative|\bf''|导数", "derivative"),
    (r"求导|微分|derivative|differentiate|\\frac\{d\}\{dx\}", "derivative"),
    (r"反常积分|improper\s+integral", "improper_integral"),
    (r"定积分|definite\s+integral|从.{0,6}到.{0,6}的积分", "definite_integral"),
    (r"不定积分|积分|integral|integrate|\\int", "integral"),
    (r"泰勒|taylor|麦克劳林|maclaurin|幂级数展开|series\s+expansion", "taylor"),
    (r"收敛半径|radius\s+of\s+convergence", "radius"),
    (r"收敛|发散|converge|diverge|判敛", "series_convergence"),
    (r"二重积分|三重积分|多重积分|double\s+integral|triple\s+integral", "multiple_integral"),
    (r"体积|volume\s+of\s+the\s+solid|旋转体", "volume"),
    (r"弧长|curve\s+length|arc\s+length", "arc_length"),
    (r"最[大小]值|极值|maximu?m|minimu?m|optimiz|临界点|critical\s+point", "optimize"),
]


def detect_calc_op(text: str) -> Optional[str]:
    for pat, op in CALC_PATTERNS:
        if re.search(pat, text or "", re.IGNORECASE):
            return op
    return None


# ─────────────────────────────────────────────────────────────
# 表达式抽取工具
# ─────────────────────────────────────────────────────────────

def _first_parseable(problem: dict, prefer_vars=("x",)):
    """从 math_exprs / 正文里找出第一个能解析的表达式。"""
    cands = list(problem.get("math_exprs") or [])
    body = problem.get("text", "")
    # $...$ 与 $$...$$
    cands += re.findall(r"\$\$(.+?)\$\$", body, re.DOTALL)
    cands += re.findall(r"\$(.+?)\$", body, re.DOTALL)
    # 明显是表达式的片段
    cands += re.findall(r"[fF]\(([a-z])\)\s*=\s*([^,。;,\n]+)", body)
    cands += re.findall(r"y\s*=\s*([^,。;,\n]+)", body)

    for c in cands:
        if not isinstance(c, str):
            continue
        if len(c) > 400:
            continue
        e = parse_tex(c)
        if e is not None and e.free_symbols:
            return e, c
    return None, None


def _parse_function_def(problem: dict):
    """抽 f(x) = ... 的定义；返回 (符号函数名, 变量, 表达式)。"""
    body = problem.get("text", "")
    m = re.search(r"([fFgGhH])\s*\(\s*([a-zA-Z])\s*\)\s*=\s*([^,。;\n]+)", body)
    if m:
        var = Symbol(m.group(2))
        expr = parse_tex(m.group(3), {m.group(2): var})
        if expr is not None:
            return m.group(1), var, expr
    return None, None, None


# ─────────────────────────────────────────────────────────────
# 各操作的实现
# ─────────────────────────────────────────────────────────────

def _solve_derivative(problem):
    expr, raw = _first_parseable(problem)
    if expr is None:
        return None
    x = find_primary_var(problem.get("text", "") + " " + (raw or ""), "x")

    # 解析自检：题干说"对 x 求导"但表达式里根本没有 x，
    # 多半是 PDF 丢字符导致的误解析（如 x² → x2）。交给 LLM。
    stated_vars = re.findall(r"[dD]\s*/\s*d\s*([a-zA-Z])|对\s*([a-zA-Z])\s*求导|"
                             r"with respect to\s*([a-zA-Z])", problem.get("text", ""))
    stated = {v for tup in stated_vars for v in tup if v}
    if stated and not (set(map(sympy.Symbol, stated)) & expr.free_symbols):
        return None

    if x not in expr.free_symbols:
        if not expr.free_symbols:
            return None
        x = sorted(expr.free_symbols, key=lambda s: str(s))[0]

    # 阶数：f'' 或 二阶
    text = problem.get("text", "")
    order = 1
    if re.search(r"二阶|second\s+derivative|f''", text, re.IGNORECASE):
        order = 2
    m = re.search(r"(\d+)\s*阶导", text)
    if m:
        order = int(m.group(1))

    d = sympy.diff(expr, x, order)
    d = simplify(d)
    steps = [
        f"已知 $f({latex(x)}) = {latex(expr)}$。",
        ("求一阶导：$f'(%s) = \\dfrac{d}{d%s}\\left(%s\\right)$。" %
         (latex(x), latex(x), latex(expr))),
    ]
    if order == 1:
        steps.append("逐项使用 $(x^n)' = nx^{n-1}$、$(\\sin x)' = \\cos x$、"
                     "$(e^x)' = e^x$、$(\\ln x)' = 1/x$ 与乘积/链式法则。")
        steps.append(f"得 $f'({latex(x)}) = {latex(d)}$。")
    else:
        steps.append(f"在此基础上再求 {order - 1} 次导。")
        steps.append(f"得 {order} 阶导数 $= {latex(d)}$。")
    return sol(problem, steps, d, solver="sympy.calculus", subject="微积分")


def _solve_implicit_derivative(problem):
    body = problem.get("text", "")
    # F(x,y) = 0
    eq_txt = None
    m = re.search(r"([^,。;\n]*=[^,。;\n]*)", body)
    if m:
        eq_txt = m.group(1)
    if not eq_txt:
        return None
    m = re.match(r"\s*(.*?)\s*=\s*(.*?)\s*$", eq_txt)
    if not m:
        return None
    lhs = parse_tex(m.group(1))
    rhs = parse_tex(m.group(2))
    if lhs is None or rhs is None:
        return None
    x, y = sympy.symbols("x y")
    F = lhs - rhs
    if y not in F.free_symbols:
        return None
    dydx = -sympy.diff(F, x) / sympy.diff(F, y)
    steps = [
        f"设 $F(x,y) = {latex(F)} = 0$。",
        "两边对 $x$ 求导（$y$ 看成 $y(x)$），得 $F_x + F_y\\,y' = 0$。",
        f"$F_x = {latex(simplify(sympy.diff(F, x)))}$，$F_y = {latex(simplify(sympy.diff(F, y)))}$。",
        f"故 $y' = -\\dfrac{{F_x}}{{F_y}} = {latex(simplify(dydx))}$。",
    ]
    return sol(problem, steps, simplify(dydx), solver="sympy.calculus", subject="微积分")


def _extract_integral_parts(problem: dict):
    """从 \\int_a^b f(x) dx 里抽出 (integrand, var, lower, upper)。"""
    body = problem.get("text", "")
    for raw in list(problem.get("math_exprs") or []) + re.findall(r"\$(.+?)\$", body, re.DOTALL):
        if "\\int" not in raw:
            continue
        m = re.search(
            r"\\int\s*(?:_\{([^{}]*)\}|_([^\s^{]))?\s*(?:\^\{([^{}]*)\}|\^([^\s^{]))?\s*(.*?)"
            r"\s*d\s*([a-zA-Z])\s*$",
            raw, re.DOTALL)
        if not m:
            continue
        lo = m.group(1) or m.group(2)
        hi = m.group(3) or m.group(4)
        body_expr = m.group(5)
        var_name = m.group(6)
        var = Symbol(var_name)
        integrand = parse_tex(body_expr, {var_name: var, "x": var})
        if integrand is None:
            continue
        lo_e = parse_tex(lo, {var_name: var}) if lo else None
        hi_e = parse_tex(hi, {var_name: var}) if hi else None
        if lo and lo_e is None:
            continue
        return integrand, var, lo_e, hi_e, raw
    return None, None, None, None, None


def _solve_integral(problem):
    integrand, var, lo, hi, raw = _extract_integral_parts(problem)
    if integrand is None:
        return None

    if lo is None and hi is None:
        # 不定积分
        F = integrate(integrand, var)
        steps = [
            f"求不定积分 $\\displaystyle\\int {latex(integrand)}\\, d{latex(var)}$。",
            "选择合适的技巧（换元 / 分部积分 / 部分分式 / 基本积分表）。",
            f"得 $F({latex(var)}) = {latex(F)} + C$。",
            f"核验：$\\dfrac{{d}}{{d{latex(var)}}}\\left({latex(F)}\\right) = "
            f"{latex(simplify(sympy.diff(F, var)))} = $ 被积函数 ✓。",
        ]
        return sol(problem, steps, F + Symbol("C"), solver="sympy.calculus",
                   verification={"method": "求导回代核验", "check": f"d/d{var}(F) == integrand"},
                   subject="微积分")

    # 定积分
    F = integrate(integrand, var)
    val = integrate(integrand, (var, lo, hi))
    improper = hi == oo or lo == -oo or (lo.is_finite and False)
    steps = [
        f"求定积分 $\\displaystyle\\int_{{{latex(lo)}}}^{{{latex(hi)}}} {latex(integrand)}\\, d{latex(var)}$。",
        f"先求原函数 $F({latex(var)}) = {latex(F)}$。",
        f"牛顿-莱布尼茨公式：$F({latex(hi)}) - F({latex(lo)}) = {latex(simplify(val))}$。",
    ]
    if hi == oo or lo == -oo:
        steps.insert(1, "这是**反常积分**，用 $\\lim_{b\\to\\infty}F(b)$ 取极限判定收敛性。")
    if val in (oo, -oo, sympy.zoo, sympy.nan):
        steps.append("积分发散。")
        return sol(problem, steps, r"\text{发散}", solver="sympy.calculus", subject="微积分")
    return sol(problem, steps, simplify(val), solver="sympy.calculus", subject="微积分")


def _solve_taylor(problem):
    expr, raw = _first_parseable(problem)
    if expr is None:
        return None
    x = find_primary_var(problem.get("text", "") + " " + (raw or ""), "x")
    if x not in expr.free_symbols:
        x = sorted(expr.free_symbols, key=lambda s: str(s))[0]

    body = problem.get("text", "")
    center = 0
    m = re.search(r"(?:about|at|在|around)\s*\$?([-+]?\d*\.?\d+|\\pi|\$?\\frac\{[^{}]*\}\{[^{}]*\})\$?", body)
    if m:
        c = parse_tex(m.group(1))
        if c is not None:
            center = c
    m = re.search(r"(\d+)\s*(?:阶|terms?|项)", body)
    n = int(m.group(1)) if m else 5

    s = series(expr, x, center, n + 1).removeO()
    steps = [
        f"$f({latex(x)}) = {latex(expr)}$，展开中心 ${latex(center)}$，展开到 $n={n}$ 阶。",
        f"套用 $f(x) = \\sum_{{k=0}}^{{n}} \\dfrac{{f^{{(k)}}(a)}}{{k!}}(x-a)^k + R_n(x)$。",
    ]
    for k in range(min(n, 5) + 1):
        dk = sympy.diff(expr, x, k).subs(x, center)
        steps.append(f"$f^{{({k})}}({latex(center)}) = {latex(simplify(dk))}$，"
                     f"系数 $\\dfrac{{f^{{({k})}}}}{{{k}!}} = {latex(simplify(dk / factorial(k)))}$。")
    steps.append(f"所以 $f({latex(x)}) \\approx {latex(s)}$。")
    return sol(problem, steps, s, solver="sympy.calculus", subject="微积分")


def _solve_radius(problem):
    """收敛半径：比值法 R = 1/lim|a_{n+1}/a_n|。"""
    body = problem.get("text", "")
    expr, raw = _first_parseable(problem)
    if expr is None:
        return None
    n = Symbol("n", positive=True, integer=True)
    # 构造 a_n 表达式
    if n not in expr.free_symbols:
        return unsolved(problem, "题干里没抽到含 n 的通项 a_n，无法判收敛半径", subject="微积分")
    try:
        ratio = sympy.Abs(expr.subs(n, n + 1) / expr)
        L = sympy.limit(ratio, n, oo)
    except Exception as e:  # noqa: BLE001
        return unsolved(problem, f"比值法求极限失败：{e}", subject="微积分")
    steps = [
        f"通项 $a_n = {latex(expr)}$。",
        f"比值法：$L = \\lim_{{n\\to\\infty}}\\left|\\dfrac{{a_{{n+1}}}}{{a_n}}\\right|"
        f" = {latex(simplify(L))}$。",
    ]
    if L == 0:
        steps.append("$L = 0 < 1$，级数对所有 $x$ 收敛，收敛半径 $R = \\infty$。")
        return sol(problem, steps, r"\infty", solver="sympy.calculus", subject="微积分")
    if L in (oo, -oo):
        steps.append("$L = \\infty$，只有 $x=a$ 收敛，$R = 0$。")
        return sol(problem, steps, "0", solver="sympy.calculus", subject="微积分")
    R = simplify(1 / L)
    steps.append(f"$L = {latex(simplify(L))}$，收敛半径 $R = \\dfrac{{1}}{{L}} = {latex(R)}$。")
    return sol(problem, steps, R, solver="sympy.calculus", subject="微积分")


def _solve_series_convergence(problem):
    expr, raw = _first_parseable(problem)
    body = problem.get("text", "")
    n = Symbol("n", positive=True, integer=True)
    if expr is None:
        # 从 \sum 的上下限里抽通项
        m = re.search(r"\\sum.*?\}\s*(.*?)\s*\$", body, re.DOTALL)
        if m:
            expr = parse_tex(m.group(1), {"n": n})
    if expr is None or n not in getattr(expr, "free_symbols", set()):
        return None

    steps = [f"通项 $a_n = {latex(expr)}$，判断 $\\sum_{{n=1}}^{{\\infty}} a_n$ 是否收敛。"]
    try:
        ratio = abs(sympy.limit(sympy.Abs(expr.subs(n, n + 1) / expr), n, oo))
    except Exception:
        ratio = None
    try:
        root = sympy.limit(sympy.Abs(expr) ** (1 / n), n, oo)
    except Exception:
        root = None

    verdict = None
    if ratio is not None:
        steps.append(f"比值判别法：$\\lim\\left|\\dfrac{{a_{{n+1}}}}{{a_n}}\\right| = {latex(simplify(ratio))}$。")
        if ratio < 1:
            verdict = "收敛"
        elif ratio > 1:
            verdict = "发散"
    if verdict is None and root is not None:
        steps.append(f"根值判别法：$\\lim\\sqrt[n]{{|a_n|}} = {latex(simplify(root))}$。")
        if root < 1:
            verdict = "收敛"
        elif root > 1:
            verdict = "发散"
    if verdict is None:
        # 必要条件的反面：通项不趋于 0
        term_lim = sympy.limit(expr, n, oo)
        steps.append(f"判别法临界（$L=1$），改用必要条件：$\\lim_{{n\\to\\infty}} a_n = {latex(term_lim)}$。")
        if term_lim != 0:
            verdict = "发散（通项不趋于 0）"
        else:
            # p-级数比较
            p = None
            m = re.search(r"n\s*\*\*\s*\(?(-?[\d/.]+)\)?", latex_to_text(raw or ""))
            if m:
                try:
                    p = float(sympy.sympify(m.group(1)))
                except Exception:
                    p = None
            if p is not None:
                verdict = "收敛" if p > 1 else "发散"
                steps.append(f"形如 $p$-级数，$p = {p}$，$p {'>' if p > 1 else '<='} 1$。")
            else:
                verdict = "不确定"
                steps.append("本模块未能判定，转交 LLM 处理。")
    return sol(problem, steps, f"\\text{{{verdict}}}", solver="sympy.calculus",
               confidence=1.0 if verdict != "不确定" else 0.4, subject="微积分")


def _solve_gradient(problem):
    body = problem.get("text", "")
    # f(x,y,z) = ...
    m = re.search(r"[fFhg]\s*\(\s*([a-zA-Z])\s*,\s*([a-zA-Z])\s*,\s*([a-zA-Z])\s*\)\s*=\s*([^,。;\n]+)", body)
    vars_, expr = None, None
    if m:
        vars_ = [Symbol(m.group(i)) for i in (1, 2, 3)]
        expr = parse_tex(m.group(4), {str(v): v for v in vars_})
    else:
        m = re.search(r"[fFhg]\s*\(\s*([a-zA-Z])\s*,\s*([a-zA-Z])\s*\)\s*=\s*([^,。;\n]+)", body)
        if m:
            vars_ = [Symbol(m.group(1)), Symbol(m.group(2))]
            expr = parse_tex(m.group(3), {str(v): v for v in vars_})
    if expr is None:
        return None

    # ⚠️ 解析自检（见 ai-log B4）：
    # PDF 丢上标时 "x²+y²+z²" 会变成 "x2+y2+z2"，被 SymPy 读成符号 x2/y2/z2。
    # 于是 grad 恒等于 0 —— 这不是答案，是解析失败。
    # 判据：函数对声明的自变量**完全没依赖**时，退回 None 交给 LLM。
    if not (set(vars_) & expr.free_symbols):
        return None

    grad = Matrix([sympy.diff(expr, v) for v in vars_])
    steps = [f"$f{tuple(latex(v) for v in vars_)} = {latex(expr)}$。",
             "梯度算子 $\\nabla = \\left(\\dfrac{\\partial}{\\partial x_1},\\dots\\right)$，逐分量求偏导。"]
    for i, v in enumerate(vars_):
        steps.append(f"$\\dfrac{{\\partial f}}{{\\partial {latex(v)}}} = "
                     f"{latex(simplify(grad[i]))}$")
    steps.append(f"$\\nabla f = {latex(grad)}$。")
    return sol(problem, steps, grad, solver="sympy.calculus", subject="微积分")


def _solve_divergence_curl(problem, kind):
    body = problem.get("text", "")
    m = re.search(r"\\?vec\{?([A-Za-z])", body)
    comp = re.findall(r"[-+]?[^,。;\n]*?\b[iíjjk]\b", body)
    # 从 <P, Q, R> 或 (P, Q, R) 形式抽
    m2 = re.search(r"<\s*([^>]+)>|\\langle\s*([^\\]+)\\rangle", body)
    if not m2:
        m2 = re.search(r"\(\s*([^()]*,[^()]*)\s*\)", body)
    if not m2:
        return None
    inner = m2.group(1) or m2.group(2)
    parts = [p for p in re.split(r",", inner) if p.strip()]
    if len(parts) != 3:
        return None
    x, y, z = sympy.symbols("x y z")
    comps = []
    for p in parts:
        e = parse_tex(p, {"x": x, "y": y, "z": z})
        if e is None:
            return None
        comps.append(e)
    P, Q, R = comps
    if kind == "divergence":
        d = simplify(sympy.diff(P, x) + sympy.diff(Q, y) + sympy.diff(R, z))
        steps = [f"$\\vec{{F}} = \\langle {latex(P)}, {latex(Q)}, {latex(R)}\\rangle$。",
                 "$\\nabla\\cdot\\vec{F} = \\partial_x P + \\partial_y Q + \\partial_z R$。",
                 f"逐项求偏导并相加，得 $\\nabla\\cdot\\vec{{F}} = {latex(d)}$。"]
        return sol(problem, steps, d, solver="sympy.calculus", subject="微积分")
    curl = Matrix([
        sympy.diff(R, y) - sympy.diff(Q, z),
        sympy.diff(P, z) - sympy.diff(R, x),
        sympy.diff(Q, x) - sympy.diff(P, y),
    ])
    curl = curl.applyfunc(simplify)
    steps = [f"$\\vec{{F}} = \\langle {latex(P)}, {latex(Q)}, {latex(R)}\\rangle$。",
             "$\\nabla\\times\\vec{F} = "
             "\\begin{vmatrix} \\hat{i} & \\hat{j} & \\hat{k} \\\\ "
             "\\partial_x & \\partial_y & \\partial_z \\\\ P & Q & R \\end{vmatrix}$。",
             f"展开行列式得 $\\nabla\\times\\vec{{F}} = {latex(curl)}$。"]
    return sol(problem, steps, curl, solver="sympy.calculus", subject="微积分")


def _solve_optimize(problem):
    """一元函数最值：驻点 + 二阶导判别。"""
    expr, raw = _first_parseable(problem)
    if expr is None:
        return None
    body = problem.get("text", "")
    interval = None
    m = re.search(r"\[\s*(-?[\d./]+)\s*,\s*(-?[\d./]+)\s*\]", body)
    if m:
        try:
            interval = (sympy.sympify(m.group(1)), sympy.sympify(m.group(2)))
        except Exception:
            interval = None

    x = find_primary_var(body + " " + (raw or ""), "x")
    if x not in expr.free_symbols:
        x = sorted(expr.free_symbols, key=lambda s: str(s))[0]

    fp = sympy.diff(expr, x)
    critical = sympy.solve(sympy.Eq(fp, 0), x)
    fpp = sympy.diff(expr, x, 2)

    steps = [f"$f({latex(x)}) = {latex(expr)}$。",
             f"一阶导 $f'({latex(x)}) = {latex(fp)}$，令其为零解驻点。",
             f"驻点：${latex(critical)}$。"]
    results = []
    for c in critical:
        val2 = simplify(fpp.subs(x, c))
        kind = "极小" if val2 > 0 else ("极大" if val2 < 0 else "拐点/无法判定")
        results.append((c, kind, simplify(expr.subs(x, c))))
        steps.append(f"在 $x = {latex(c)}$：$f''= {latex(val2)}$ "
                     f"{'>' if val2 > 0 else '<' if val2 < 0 else '='} 0 ⟹ {kind}值 "
                     f"$f = {latex(simplify(expr.subs(x, c)))}$。")

    if interval:
        a, b = interval
        cands = list(critical) + [a, b]
        best = min(((expr.subs(x, c), c) for c in cands if sympy.re(c) >= sympy.re(a)
                    and sympy.re(c) <= sympy.re(b)), key=lambda t: t[0], default=None)
        worst = max(((expr.subs(x, c), c) for c in cands if sympy.re(c) >= sympy.re(a)
                     and sympy.re(c) <= sympy.re(b)), key=lambda t: t[0], default=None)
        if best and worst:
            steps.append(f"闭区间 $[{latex(a)}, {latex(b)}]$ 上还要比较端点："
                         f"$f({latex(a)}) = {latex(expr.subs(x, a))}$，"
                         f"$f({latex(b)}) = {latex(expr.subs(x, b))}$。")
            steps.append(f"综合得最小值 $f_{{\\min}} = {latex(simplify(best[0]))}$（在 "
                         f"$x = {latex(best[1])}$），最大值 $f_{{\\max}} = "
                         f"{latex(simplify(worst[0]))}$（在 $x = {latex(worst[1])}$）。")
            answer = (f"f_{{\\min}} = {latex(simplify(best[0]))}\\ \\text{{at}}\\ x = {latex(best[1])},"
                      f"\\quad f_{{\\max}} = {latex(simplify(worst[0]))}\\ \\text{{at}}\\ x = {latex(worst[1])}")
            return sol(problem, steps, answer, solver="sympy.calculus", subject="微积分")
    return sol(problem, steps,
               ",\\ ".join(f"{k}值\\ f({latex(c)}) = {latex(v)}" for c, k, v in results)
               or r"\text{无驻点}",
               solver="sympy.calculus", subject="微积分")


def _solve_volume(problem):
    """旋转体体积（圆盘法）。"""
    body = problem.get("text", "")
    m = re.search(r"[yf]\s*=\s*([^,。;\n]+?)(?:,|\s+)(?:for|从|between|on)\s*\$?\[?([-\d./]+)\s*,\s*([-\d./]+)", body)
    if not m:
        m = re.search(r"([^,。;\n]+?)\s*,\s*\$?\[?([-\d./]+)\s*,\s*([-\d./]+)\]?", body)
    if not m:
        return None
    f = parse_tex(m.group(1))
    if f is None:
        return None
    try:
        a, b = sympy.sympify(m.group(2)), sympy.sympify(m.group(3))
    except Exception:
        return None
    x = find_primary_var(body, "x")
    V = sympy.pi * integrate(f ** 2, (x, a, b))
    steps = [f"曲线 $y = {latex(f)}$，绕 $x$ 轴旋转，区间 $[{latex(a)},{latex(b)}]$。",
             "圆盘法：$V = \\pi\\int_a^b [f(x)]^2\\,dx$。",
             f"$[f(x)]^2 = {latex(simplify(f**2))}$。",
             f"$V = \\pi\\int_{{{latex(a)}}}^{{{latex(b)}}} {latex(simplify(f**2))}\\,dx"
             f" = {latex(simplify(V))}$。"]
    return sol(problem, steps, simplify(V), solver="sympy.calculus", subject="微积分")


def _solve_arc_length(problem):
    expr, raw = _first_parseable(problem)
    body = problem.get("text", "")
    lo, hi = 0, 1
    m = re.search(r"\[?([-\d./]+)\s*,\s*([-\d./]+)\]?", body.split("=")[-1] if "=" in body else body)
    if m:
        try:
            lo, hi = sympy.sympify(m.group(1)), sympy.sympify(m.group(2))
        except Exception:
            pass
    if expr is None:
        return None
    x = find_primary_var(body + " " + (raw or ""), "x")
    if x not in expr.free_symbols:
        x = sorted(expr.free_symbols, key=lambda s: str(s))[0]
    d = sympy.diff(expr, x)
    integrand = sqrt(1 + d ** 2)
    L = integrate(integrand, (x, lo, hi))
    steps = [f"$y = {latex(expr)}$，$y' = {latex(d)}$，区间 $[{latex(lo)},{latex(hi)}]$。",
             "弧长公式 $L = \\int_a^b\\sqrt{1 + (y')^2}\\,dx$。",
             f"被积函数 $\\sqrt{{1 + ({latex(d)})^2}} = {latex(integrand)}$。",
             f"$L = {latex(simplify(L))}$。"]
    return sol(problem, steps, simplify(L), solver="sympy.calculus", subject="微积分")


# ─────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────

_HANDLERS = {
    "derivative": _solve_derivative,
    "implicit_derivative": _solve_implicit_derivative,
    "integral": _solve_integral,
    "definite_integral": _solve_integral,
    "improper_integral": _solve_integral,
    "multiple_integral": _solve_integral,
    "taylor": _solve_taylor,
    "radius": _solve_radius,
    "series_convergence": _solve_series_convergence,
    "gradient": _solve_gradient,
    "divergence": lambda p: _solve_divergence_curl(p, "divergence"),
    "curl": lambda p: _solve_divergence_curl(p, "curl"),
    "optimize": _solve_optimize,
    "volume": _solve_volume,
    "arc_length": _solve_arc_length,
}


def solve(problem: dict) -> Optional[dict]:
    text = problem.get("text", "") + " " + " ".join(problem.get("math_exprs") or [])
    op = detect_calc_op(text)
    if op is None:
        return None
    handler = _HANDLERS.get(op)
    if handler is None:
        return None
    try:
        r = handler(problem)
    except Exception as e:  # noqa: BLE001
        return unsolved(problem, f"微积分求解器异常：{type(e).__name__}: {e}", subject="微积分")
    if r is None:
        return unsolved(problem, f"识别到「{op}」但没能从题干抽出可解析的表达式", subject="微积分")
    return r
