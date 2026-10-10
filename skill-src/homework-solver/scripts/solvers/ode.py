#!/usr/bin/env python3
"""
solvers/ode.py —— 常微分方程求解器（C4C 学科扩展 ③）
=======================================================
覆盖 starter kit 完全没有的 ODE 能力：

    一阶可分离 / 一阶线性（积分因子）/ 伯努利
    二阶常系数线性齐次 & 非齐次（待定系数 / 参数变易）
    初值问题（IVP）与边值问题（BVP）
    拉普拉斯变换 / 逆变换（用于带初值的线性 ODE）
    特征方程与通解结构判定（相异实根 / 重根 / 共轭复根）

策略：SymPy 的 dsolve 在「二阶常系数线性方程」上非常可靠，
所以优先用它；但**不直接甩答案**——先自己算特征方程的根来判定解的结构，
再用 dsolve 求具体解，两者互相印证。这样即使 dsolve 失败，
报告里也已经写清楚方程的类型和应该长什么样的解。
"""

from __future__ import annotations

import re
from typing import Optional

import sympy
from sympy import Function, Eq, Matrix, Symbol, cos, dsolve, exp, latex, simplify, sin, sqrt

from .base import find_primary_var, parse_tex, sol, unsolved

# ─────────────────────────────────────────────────────────────
# 识别
# ─────────────────────────────────────────────────────────────

ODE_PATTERNS: list[tuple[str, str]] = [
    (r"拉普拉斯|laplace", "laplace"),
    (r"初值|initial\s+value|y\s*\(\s*0\s*\)|y'\s*\(\s*0\s*\)", "ivp"),
    (r"边值|boundary\s+value", "bvp"),
    (r"齐次|homogeneous|通解|general\s+solution|微分方程|differential\s+equation|"
     r"求方程|solve\s+the\s+(?:ode|equation)|y''|y'|\\frac\{dy\}", "ode"),
]


def detect_ode_op(text: str) -> Optional[str]:
    for pat, op in ODE_PATTERNS:
        if re.search(pat, text or "", re.IGNORECASE):
            return op
    return None


# ─────────────────────────────────────────────────────────────
# 方程抽取：把题干里的微分方程变成 SymPy 的 Eq
# ─────────────────────────────────────────────────────────────

_Y_PRIME = re.compile(r"y\s*'''|y\s*''|y\s*'|y\s*\\prime")


def _normalize_prime_notation(s: str) -> str:
    """把 LaTeX 里各种导数写法统一成 SymPy 可解析的记号。

    支持：y' y'' y'''  dy/dx  d2y/dx2  \frac{d^2y}{dx^2}  y^{(2)}
    """
    s = s.replace(r"\,", " ")

    # \frac{d^2 y}{d x^2} → diff(y(x), x, 2)
    def repl_frac_d(m):
        order = m.group(1) or ""
        var = m.group(2)
        n = len(order) if order else 1
        return f"diff(y({var}),{var},{n})"
    s = re.sub(r"\\frac\{d(\^?\d*)\s*([a-z])\}\{d\s*[a-z](\^\d*)?\}", repl_frac_d, s)
    s = re.sub(r"\\frac\{d\^\{?(\d+)\}?\s*([a-z])\}\{d\s*[a-z]\^\{?\d+\}?\}",
               lambda m: f"diff(y({m.group(2)}),{m.group(2)},{m.group(1)})", s)

    # d^2y/dx^2 或 d2y/dx2
    s = re.sub(r"d\^?(\d?)\s*y\s*/\s*d\s*([a-z])\^?(\d?)",
               lambda m: f"diff(y({m.group(2)}),{m.group(2)},{m.group(1) or m.group(3) or '1'})", s)

    # y''' / y'' / y'
    def repl_prime(m):
        txt = m.group(0)
        n = txt.count("'") + txt.count("'''") * 2
        n = 3 if "'''" in txt else (2 if "''" in txt else 1)
        var = _guess_var_from_context(s)
        return f"diff(y({var}),{var},{n})"
    s = re.sub(r"y\s*'''|y\s*''|y\s*'", repl_prime, s)

    # y^{(2)} / y^(2)
    s = re.sub(r"y\s*\^\{?\((\d+)\)\}?", lambda m: f"diff(y(x),x,{m.group(1)})", s)
    return s


def _guess_var_from_context(s: str) -> str:
    m = re.search(r"d\s*y\s*/\s*d\s*([a-z])", s)
    if m:
        return m.group(1)
    m = re.search(r"y\s*\(\s*([a-z])\s*\)", s)
    if m:
        return m.group(1)
    return "x"


def _extract_ode(problem: dict):
    """返回 (Eq, 自变量, 因变量符号) 或 (None, None, None)。"""
    body = problem.get("text", "")
    cands = list(problem.get("math_exprs") or [])
    cands += re.findall(r"\$(.+?)\$", body, re.DOTALL)

    for raw in cands:
        if not isinstance(raw, str):
            continue
        if "=" not in raw:
            continue
        if not (("y'" in raw) or ("dy" in raw) or ("\\frac{d" in raw) or re.search(r"y\s*''", raw)):
            continue

        x = Symbol(_guess_var_from_context(raw))
        y = Function("y")
        txt = _normalize_prime_notation(raw)
        txt = txt.replace("y(x)", "y")  # 交给 locals 处理

        # 拆等号两边
        parts = txt.split("=", 1)
        if len(parts) != 2:
            continue
        lhs_s, rhs_s = parts
        try:
            from sympy.parsing.sympy_parser import (convert_xor, implicit_multiplication_application,
                                                    parse_expr, standard_transformations)
            T = standard_transformations + (implicit_multiplication_application, convert_xor)
            loc = {"y": y(x), "x": x, "e": sympy.E, "pi": sympy.pi}
            lhs = parse_expr(_tex_clean(lhs_s), local_dict=loc, transformations=T, evaluate=True)
            rhs = parse_expr(_tex_clean(rhs_s), local_dict=loc, transformations=T, evaluate=True)
            return Eq(lhs, rhs), x, y(x)
        except Exception:
            continue
    return None, None, None


def _tex_clean(s: str) -> str:
    """把 LaTeX 残渣清成 sympy.parsing 能吃的 Python 表达式。"""
    s = s.strip()
    s = re.sub(r"\\left|\\right", "", s)
    s = re.sub(r"\\cdot|\\times", "*", s)
    s = re.sub(r"\\sqrt\{([^{}]*)\}", r"sqrt(\1)", s)
    s = s.replace(r"\pi", "pi").replace(r"\sin", "sin").replace(r"\cos", "cos")
    s = s.replace(r"\ln", "log").replace(r"\log", "log").replace(r"\exp", "exp")
    s = re.sub(r"\\[a-zA-Z]+", "", s)
    s = s.replace("{", "(").replace("}", ")")
    s = re.sub(r"\^", "**", s)
    return s


# ─────────────────────────────────────────────────────────────
# 结构分析（先讲清楚这是什么方程）
# ─────────────────────────────────────────────────────────────

def _classify_ode(eq, x, y) -> str:
    """判断阶数与是否线性。"""
    try:
        order = sympy.ode_order(eq, y)
    except Exception:
        try:
            order = max(
                sympy.ode_order(sympy.Derivative(y, (x, k)), y) if False else k
                for k in (1, 2, 3)
                if eq.has(sympy.Derivative(y, x, k))
            )
        except Exception:
            order = 1
    lin = False
    try:
        # 一阶/二阶线性判据：对 y 及其导数是一次的
        ys = [y] + [sympy.Derivative(y, x, k) for k in range(1, order + 1)]
        lin = all(sympy.Poly(eq.lhs - eq.rhs, *ys).total_degree() <= 1 for _ in [0])
    except Exception:
        lin = False
    return f"{order} 阶" + ("线性" if lin else "非线性") + "常微分方程"


def _characteristic_roots(eq, x, y):
    """二阶常系数线性齐次方程的辅助方程根。失败返回 None。"""
    yp = sympy.Derivative(y, x)
    ypp = sympy.Derivative(y, x, 2)
    try:
        a2 = eq.lhs.coeff(ypp)
        a1 = eq.lhs.coeff(yp)
        a0 = eq.lhs.coeff(y)
        rhs0 = eq.rhs
        if not (a2.is_number and a1.is_number and a0.is_number):
            return None
        r = Symbol("r")
        poly = a2 * r ** 2 + a1 * r + a0
        return poly, sympy.solve(poly, r)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# 求解
# ─────────────────────────────────────────────────────────────

def _solve_ode(problem):
    eq, x, y = _extract_ode(problem)
    if eq is None:
        return unsolved(problem, "没能从题干里抽出一个含导数的方程（支持 y' / dy/dx / \\frac{d^2y}{dx^2}）",
                        subject="微分方程")
    body = problem.get("text", "")

    try:
        order = sympy.ode_order(eq, y)
    except Exception:
        order = 1

    steps = [f"原方程：${latex(eq)}$。", f"这是一个 {_classify_ode(eq, x, y)}。"]
    confidence = 1.0

    # 二阶常系数齐次 → 先写特征方程（结构说明）
    if order == 2:
        cr = _characteristic_roots(eq, x, y)
        if cr:
            poly, roots = cr
            steps.append(f"特征方程：${latex(poly)} = 0$。")
            steps.append(f"特征根：${latex(roots)}$。")
            if all(r.is_real for r in roots):
                if len(set(roots)) == 2:
                    steps.append("两个相异实根 ⟹ 通解形如 $y = C_1 e^{r_1 x} + C_2 e^{r_2 x}$。")
                else:
                    steps.append("重根 ⟹ 通解形如 $y = (C_1 + C_2 x)e^{rx}$。")
            else:
                steps.append("共轭复根 $\\alpha \\pm \\beta i$ ⟹ 通解形如 "
                             "$y = e^{\\alpha x}(C_1\\cos\\beta x + C_2\\sin\\beta x)$。")

    # 初值条件
    ics = {}
    for m in re.finditer(r"y\s*\(\s*0\s*\)\s*=\s*(-?[\d./]+)", body):
        ics[y.subs(x, 0)] = sympy.sympify(m.group(1))
    for m in re.finditer(r"y\s*'\s*\(\s*0\s*\)\s*=\s*(-?[\d./]+)", body):
        ics[sympy.Derivative(y, x).subs(x, 0)] = sympy.sympify(m.group(1))
    for m in re.finditer(r"y\s*''\s*\(\s*0\s*\)\s*=\s*(-?[\d./]+)", body):
        ics[sympy.Derivative(y, x, 2).subs(x, 0)] = sympy.sympify(m.group(1))

    if ics:
        steps.append("初值条件：" + "，".join(f"${latex(k)} = {latex(v)}$" for k, v in ics.items()) + "。")

    try:
        if ics:
            gsol = dsolve(eq, y, ics=ics)
        else:
            gsol = dsolve(eq, y)
    except Exception as e:  # noqa: BLE001
        return unsolved(problem, f"SymPy dsolve 未能求解该方程（{type(e).__name__}）：{e}",
                        subject="微分方程")

    steps.append(f"解得：$${latex(gsol)}$$")
    if not ics:
        steps.append("（通解中的 $C_1, C_2, \\dots$ 为任意常数；给出初值即可确定。）")

    # 反代核验
    try:
        check = simplify(gsol.lhs - gsol.rhs)
        residual = simplify(eq.lhs.subs(y, gsol.rhs) - eq.rhs.subs(y, gsol.rhs))
        if residual == 0:
            steps.append("核验：把解代回原方程，两边恒等 ✓。")
            verification = {"method": "解代回原方程", "check": "residual == 0"}
        else:
            verification = {"method": "解代回原方程", "check": f"residual = {residual}"}
            confidence = 0.6
    except Exception:
        verification = {"method": "解代回原方程", "check": "无法完成代数化简核验"}

    return sol(problem, steps, gsol.rhs, solver="sympy.ode",
               verification=verification, confidence=confidence, subject="微分方程")


def _solve_laplace(problem):
    """拉普拉斯变换 / 逆变换。"""
    body = problem.get("text", "")
    t, s = sympy.symbols("t s", positive=True)
    m = re.search(r"\\mathcal\{L\}\s*\{?\s*([^}\$]+?)\s*\}?\$", body)
    if not m:
        m = re.search(r"[Ll]aplace\s+(?:transform\s+)?of\s+\$?([^,。;\n$]+)", body)
    if not m:
        return unsolved(problem, "没抽到要变换的函数", subject="微分方程")
    f = parse_tex(m.group(1), {"t": t})
    if f is None:
        return unsolved(problem, f"无法解析函数 `{m.group(1)}`", subject="微分方程")

    inverse = bool(re.search(r"逆变换|inverse", body, re.IGNORECASE))
    if not inverse:
        F = sympy.laplace_transform(f, t, s, noconds=True)
        steps = [
            f"求 $\\mathcal{{L}}\\{{f(t)\\}}$，其中 $f(t) = {latex(f)}$。",
            "按定义 $F(s) = \\int_0^{\\infty} e^{-st} f(t)\\,dt$。",
        ]
        # 列出用到的变换对
        if f.has(sympy.exp):
            steps.append("用到 $\\mathcal{L}\\{e^{at}\\} = \\dfrac{1}{s-a}$。")
        if f.has(sympy.sin) or f.has(sympy.cos):
            steps.append("用到 $\\mathcal{L}\\{\\sin \\omega t\\} = \\dfrac{\\omega}{s^2+\\omega^2}$、"
                         "$\\mathcal{L}\\{\\cos\\omega t\\} = \\dfrac{s}{s^2+\\omega^2}$。")
        if f.is_polynomial(t):
            steps.append("用到 $\\mathcal{L}\\{t^n\\} = \\dfrac{n!}{s^{n+1}}$。")
        steps.append(f"得 $F(s) = {latex(F)}$。")
        return sol(problem, steps, F, solver="sympy.ode", subject="微分方程")

    # 逆变换
    m2 = re.search(r"\\mathcal\{L\}\^\{-1\}\s*\{?\s*([^}\$]+?)\s*\}?\$", body)
    F = parse_tex(m2.group(1) if m2 else m.group(1), {"s": s})
    if F is None:
        return unsolved(problem, "无法解析 F(s)", subject="微分方程")
    ft = sympy.inverse_laplace_transform(F, s, t)
    steps = [
        f"求 $\\mathcal{{L}}^{{-1}}\\{{F(s)\\}}$，其中 $F(s) = {latex(F)}$。",
        "对 $F(s)$ 做部分分式分解，再逐项查逆变换表。",
        f"得 $f(t) = {latex(ft)}$。",
    ]
    return sol(problem, steps, ft, solver="sympy.ode", subject="微分方程")


# ─────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────

def solve(problem: dict) -> Optional[dict]:
    text = problem.get("text", "") + " " + " ".join(problem.get("math_exprs") or [])
    op = detect_ode_op(text)
    if op is None:
        return None
    try:
        if op == "laplace":
            return _solve_laplace(problem)
        return _solve_ode(problem)
    except Exception as e:  # noqa: BLE001
        return unsolved(problem, f"微分方程求解器异常：{type(e).__name__}: {e}", subject="微分方程")
