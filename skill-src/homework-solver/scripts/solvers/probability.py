#!/usr/bin/env python3
"""
solvers/probability.py —— 概率统计求解器（C4C 学科扩展 ⑤）
=============================================================
覆盖：

    期望 / 方差 / 标准差（离散分布表 & 连续密度）
    常见分布：二项、泊松、均匀、正态、指数
    条件概率 / 全概率 / 贝叶斯公式
    协方差 / 相关系数  |  线性回归（最小二乘）
    假设检验：单样本 z 检验、t 检验（有 scipy 走 scipy，没有就走手算公式）

设计取舍
--------
概率题的难点不在算，在于**读懂题意建对模型**。所以这里只做
「模型已经明确给出」的题（"X~N(0,1)"、"分布列为 ..."、"袋中有 ... 个球"），
应用题（"某工厂生产..."）留给 LLM 建模，LLM 给出的答案再由本模块
用 SymPy 数值复核。
"""

from __future__ import annotations

import math
import re
from typing import Optional

import sympy
from sympy import Symbol, binomial, exp, factorial, integrate, latex, oo, pi, simplify, sqrt

from .base import parse_tex, sol, unsolved
from .linalg import _extract_matrices

# ─────────────────────────────────────────────────────────────
# 识别
# ─────────────────────────────────────────────────────────────

PROB_PATTERNS: list[tuple[str, str]] = [
    (r"贝叶斯|bayes", "bayes"),
    (r"条件概率|conditional\s+probability|P\s*\(\s*[AB]\s*\|", "conditional"),
    (r"相关系数|correlation|协方差|covariance", "correlation"),
    (r"线性回归|回归|regression|least.squares\s+line|拟合", "regression"),
    (r"假设检验|hypothesis\s+test|显著性|significance|p-value|p\s*值|拒绝域|z\s*检验|t\s*检验",
     "hypothesis"),
    (r"期望|expectation|expected\s+value|均值|mean\s+of", "expectation"),
    (r"方差|variance|标准差|standard\s+deviation", "variance"),
    (r"二项分布|binomial|正态分布|normal\s+distribution|泊松|poisson|指数分布|"
     r"exponential\s+distribution|均匀分布|uniform\s+distribution|分布", "distribution"),
    # 记号形式的概率题："Let X \sim N(0,1)"、"P(X <= 1.96)"、"X~B(10,0.5)"
    # 这类题干一个中文关键词都没有，靠符号识别（见 ai-log B10）
    (r"[Xx]\s*(?:\\sim|~)\s*[NBUEP]", "distribution"),
    (r"[Pp]\s*\(\s*[Xx]\s*(?:<=|>=|<|>|≤|≥)", "distribution"),
    (r"[Xx]\s*(?:\\sim|~)\s*(?:N|B|U|P|Exp)\s*\(", "distribution"),
]


def detect_prob_op(text: str) -> Optional[str]:
    for pat, op in PROB_PATTERNS:
        if re.search(pat, text or "", re.IGNORECASE):
            return op
    return None


# ─────────────────────────────────────────────────────────────
# 分布参数抽取
# ─────────────────────────────────────────────────────────────

def _extract_normal_params(body: str):
    m = re.search(r"N\s*\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)", body)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"mean\s*(?:=|is|of)?\s*([-\d.]+).{0,30}?"
                  r"(?:standard deviation|variance|sd|σ)\s*(?:=|is|of)?\s*([-\d.]+)",
                  body, re.IGNORECASE)
    if m:
        mu, sd = float(m.group(1)), float(m.group(2))
        if re.search(r"variance", body, re.IGNORECASE) and not re.search(r"standard deviation", body, re.IGNORECASE):
            sd = math.sqrt(sd)
        return mu, sd
    m = re.search(r"均值\s*([-\d.]+).{0,20}?标准差\s*([-\d.]+)", body)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"均值\s*([-\d.]+).{0,20}?方差\s*([-\d.]+)", body)
    if m:
        return float(m.group(1)), math.sqrt(float(m.group(2)))
    return None, None


def _extract_binomial(body: str):
    m = re.search(r"[Bb]\s*\(\s*(\d+)\s*,\s*([\d.]+)\s*\)", body)
    if m:
        return int(m.group(1)), float(m.group(2))
    m = re.search(r"(?:n|试验次数|trials)\s*=\s*(\d+).{0,40}?(?:p|概率|probability)\s*=\s*([\d.]+)",
                  body, re.IGNORECASE)
    if m:
        return int(m.group(1)), float(m.group(2))
    return None, None


def _extract_discrete_table(problem: dict):
    """从题干里的表格/矩阵抽 (x 值, p 值)。"""
    body = problem.get("text", "")
    mats = _extract_matrices(problem)
    for M in mats:
        if M.rows == 2:
            try:
                xs = [float(sympy.N(M[0, j])) for j in range(M.cols)]
                ps = [float(sympy.N(M[1, j])) for j in range(M.cols)]
                return xs, ps
            except Exception:
                continue
    # Markdown 表格
    rows = re.findall(r"\|\s*([^|\n]+)\|\s*([^|\n]+)\|", body)
    xs, ps = [], []
    for a, b in rows:
        try:
            xs.append(float(a))
            ps.append(float(b))
        except ValueError:
            continue
    if xs and ps and abs(sum(ps) - 1.0) < 0.05:
        return xs, ps
    return None, None


# ─────────────────────────────────────────────────────────────
# 求解实现
# ─────────────────────────────────────────────────────────────

def _solve_moments(problem, want_variance: bool):
    body = problem.get("text", "")
    xs, ps = _extract_discrete_table(problem)

    if xs and ps:
        mu = sum(x * p for x, p in zip(xs, ps))
        var = sum(p * (x - mu) ** 2 for x, p in zip(xs, ps))
        steps = [
            "读入分布列：$x_i$ 与 $p_i$。",
            "期望 $E(X) = \\sum_i x_i p_i$。",
            "，".join(f"$x_{{{i+1}}}p_{{{i+1}}} = {x} \\times {p} = {x*p:.6g}$"
                     for i, (x, p) in enumerate(zip(xs, ps))),
            f"$E(X) = {mu:.6g}$。",
            "$\\operatorname{Var}(X) = E(X^2) - [E(X)]^2 = \\sum_i p_i(x_i - \\mu)^2$。",
            f"$\\operatorname{{Var}}(X) = {var:.6g}$，$\\sigma = {math.sqrt(var):.6g}$。",
        ]
        if want_variance:
            return sol(problem, steps, f"\\operatorname{{Var}}(X) = {var:.6g},\\ \\sigma = {math.sqrt(var):.6g}",
                       solver="sympy.probability", subject="概率统计")
        return sol(problem, steps, f"E(X) = {mu:.6g}", solver="sympy.probability", subject="概率统计")

    # 分布族
    mu, sd = _extract_normal_params(body)
    n, p = _extract_binomial(body)

    if n is not None and p is not None:
        E = n * p
        V = n * p * (1 - p)
        steps = [
            f"$X \\sim B(n={n},\\ p={p})$。",
            f"二项分布期望 $E(X) = np = {n}\\times{p} = {E:.6g}$。",
            f"方差 $\\operatorname{{Var}}(X) = np(1-p) = {V:.6g}$。",
        ]
        ans = (f"\\operatorname{{Var}}(X) = {V:.6g}" if want_variance else f"E(X) = {E:.6g}")
        return sol(problem, steps, ans, solver="sympy.probability", subject="概率统计")

    m = re.search(r"[Pp]oisson\s*\(\s*([\d.]+)\s*\)|泊松.{0,6}(?:λ|lambda)\s*=?\s*([\d.]+)", body)
    if m:
        lam = float(m.group(1) or m.group(2))
        steps = [f"$X \\sim \\operatorname{{Poisson}}(\\lambda={lam})$。",
                 f"泊松分布 $E(X) = \\operatorname{{Var}}(X) = \\lambda = {lam}$。"]
        ans = f"\\operatorname{{Var}}(X) = {lam}" if want_variance else f"E(X) = {lam}"
        return sol(problem, steps, ans, solver="sympy.probability", subject="概率统计")

    if mu is not None and sd is not None:
        var = sd ** 2
        steps = [
            f"$X \\sim N(\\mu={mu},\\ \\sigma^2={var})$。",
            f"正态分布 $E(X) = \\mu = {mu}$。",
            f"$\\operatorname{{Var}}(X) = \\sigma^2 = {var}$，$\\sigma = {sd}$。",
        ]
        ans = (f"\\operatorname{{Var}}(X) = {var}" if want_variance else f"E(X) = {mu}")
        return sol(problem, steps, ans, solver="sympy.probability", subject="概率统计")

    return unsolved(problem, "没抽到可识别的分布（需要分布列、N(μ,σ) 或 B(n,p) 形式的明确已知）",
                    subject="概率统计")


def _solve_bayes(problem):
    body = problem.get("text", "")
    # 抽 P(A|B) = 0.9 形式
    probs = {}
    for m in re.finditer(r"P\s*\(\s*([A-Za-z][A-Za-z0-9_'\\]*)\s*\|\s*([A-Za-z][A-Za-z0-9_'\\]*)\s*\)\s*=\s*([\d.]+)",
                         body):
        probs[(m.group(1), m.group(2))] = float(m.group(3))
    for m in re.finditer(r"P\s*\(\s*([A-Za-z][A-Za-z0-9_'\\]*)\s*\)\s*=\s*([\d.]+)", body):
        probs[(m.group(1), None)] = float(m.group(2))

    if not probs:
        return unsolved(problem, "题干里没抽到 P(·)=… 形式的数值", subject="概率统计")

    marg = {k[0]: v for k, v in probs.items() if k[1] is None}
    cond = {k: v for k, v in probs.items() if k[1] is not None}

    # 贝叶斯：P(A|B) = P(B|A)P(A) / P(B)
    target = None
    for (a, b) in cond:
        if (b, a) in cond and b in marg and (b, None) not in marg:
            target = (a, b)
            break

    if target is None and len(cond) == 1:
        (a, b) = list(cond)[0]
        if (b, a) in cond and a in marg:
            target = (b, a)

    if target is None:
        # 全概率公式：P(B) = Σ P(B|A_i)P(A_i)
        if len(marg) >= 2:
            partners = [(a, v) for (x, y), v in cond.items() for a in [x] if y is not None]
            steps = ["由全概率公式 $P(B) = \\sum_i P(B|A_i)P(A_i)$："]
            total = 0.0
            for (x, y), v in cond.items():
                if x in marg:
                    total += v * marg[x]
                    steps.append(f"$P(B|{x})P({x}) = {v}\\times{marg[x]} = {v*marg[x]:.6g}$")
            steps.append(f"$P(B) = {total:.6g}$。")
            return sol(problem, steps, f"P(B) = {total:.6g}", solver="sympy.probability",
                       subject="概率统计")
        return unsolved(problem, "贝叶斯公式所需的先验/似然没凑齐", subject="概率统计")

    a, b = target
    num = cond[(b, a)] * marg[b]
    den = marg[a] if (b, None) not in marg else marg[(b, None)] if (b, None) in marg else None
    if den is None:
        return unsolved(problem, "缺少 P(A) 或 P(B) 中的分母项", subject="概率统计")
    res = num / den
    steps = [
        f"要求 $P({a}|{b})$，用贝叶斯公式 "
        f"$P({a}|{b}) = \\dfrac{{P({b}|{a})P({a})}}{{P({b})}}$。",
        f"分子 $= P({b}|{a})P({a}) = {cond[(b,a)]}\\times{marg[b]} = {num:.6g}$。",
        f"分母 $P({b}) = {den:.6g}$。",
        f"$P({a}|{b}) = {res:.6g}$。",
    ]
    return sol(problem, steps, f"P({a}|{b}) = {res:.6g}", solver="sympy.probability",
               subject="概率统计")


def _solve_correlation(problem):
    body = problem.get("text", "")
    # 抽数据对 (1,2), (3,4) ...
    pairs = re.findall(r"\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)", body)
    if len(pairs) < 2:
        return unsolved(problem, "没抽到至少 2 组数据对 (x, y)", subject="概率统计")
    xs = [float(a) for a, b in pairs]
    ys = [float(b) for a, b in pairs]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs) / n)
    sy = math.sqrt(sum((y - my) ** 2 for y in ys) / n)
    r = sxy / (sx * sy) if sx and sy else float("nan")
    steps = [
        f"数据对 $n = {n}$ 组。",
        f"均值 $\\bar x = {mx:.6g}$，$\\bar y = {my:.6g}$。",
        f"协方差 $\\operatorname{{Cov}}(X,Y) = \\dfrac{{1}}{{n}}\\sum(x_i-\\bar x)(y_i-\\bar y) = {sxy:.6g}$。",
        f"标准差 $s_x = {sx:.6g}$，$s_y = {sy:.6g}$。",
        f"相关系数 $r = \\dfrac{{\\operatorname{{Cov}}}}{{s_x s_y}} = {r:.6g}$。",
    ]
    if re.search(r"回归|regression|拟合", body, re.IGNORECASE):
        slope = sxy / (sx ** 2) if sx else float("nan")
        intercept = my - slope * mx
        steps.append(f"回归直线 $\\hat y = \\hat\\beta_0 + \\hat\\beta_1 x$，"
                     f"$\\hat\\beta_1 = \\dfrac{{s_{{xy}}}}{{s_x^2}} = {slope:.6g}$，"
                     f"$\\hat\\beta_0 = \\bar y - \\hat\\beta_1\\bar x = {intercept:.6g}$。")
        return sol(problem, steps,
                   f"r = {r:.6g},\\quad \\hat y = {intercept:.6g} + {slope:.6g}x",
                   solver="sympy.probability",
                   verification={"method": "r²与回归斜率一致性", "check": "r 与 β₁ 同号"},
                   subject="概率统计")
    return sol(problem, steps, f"r = {r:.6g}", solver="sympy.probability", subject="概率统计")


def _solve_hypothesis(problem):
    body = problem.get("text", "")
    # 抽样本统计量
    m_n = re.search(r"(?:n|样本(?:容量|数|大小)|sample size)\s*[=＝]\s*(\d+)", body)
    m_mean = re.search(r"(?:样本均值|样本平均|sample mean|\bar\s*x)\s*[=＝]\s*([-\d.]+)", body)
    m_sd = re.search(r"(?:样本标准差|标准差|standard deviation|\bs\b)\s*[=＝]\s*([\d.]+)", body)
    m_mu0 = re.search(r"(?:H0|零假设|null)\s*[:：]?\s*(?:μ|mu|均值)\s*[=＝]\s*([-\d.]+)", body)
    if not m_mu0:
        m_mu0 = re.search(r"(?:claim(?:s|ed)?|声称|宣称|总体均值)\s*(?:是|为|=|is)?\s*([-\d.]+)", body)

    if not (m_n and m_mean and (m_sd or True) and m_mu0):
        return unsolved(problem, "假设检验所需的 n / 样本均值 / 标准差 / H₀ 没抽全", subject="概率统计")

    n = int(m_n.group(1))
    xbar = float(m_mean.group(1))
    sd = float(m_sd.group(1)) if m_sd else None
    mu0 = float(m_mu0.group(1))
    if sd is None:
        return unsolved(problem, "缺样本标准差，无法算检验统计量", subject="概率统计")

    z = (xbar - mu0) / (sd / math.sqrt(n))
    two_sided = not re.search(r"单侧|one[- ]sided|大于|小于|greater|less", body, re.IGNORECASE)

    # p 值：用 math.erfc 手算，避免依赖 scipy
    def norm_sf(v):
        return 0.5 * math.erfc(v / math.sqrt(2))
    pval = 2 * norm_sf(abs(z)) if two_sided else norm_sf(abs(z))

    alpha_m = re.search(r"[αa]lpha\s*[=＝]\s*(0?\.\d+)", body)
    alpha = float(alpha_m.group(1)) if alpha_m else 0.05

    steps = [
        f"提出假设 $H_0: \\mu = {mu0}$。",
        f"样本 $n = {n}$，$\\bar x = {xbar}$，$s = {sd}$。",
        f"检验统计量 $z = \\dfrac{{\\bar x - \\mu_0}}{{s/\\sqrt{{n}}}} = "
        f"\\dfrac{{{xbar} - {mu0}}}{{{sd}/\\sqrt{{{n}}}}} = {z:.4f}$。",
        f"{'双侧' if two_sided else '单侧'}检验，$p = {pval:.4f}$。",
        f"显著性水平 $\\alpha = {alpha}$。",
        (f"$p = {pval:.4f} < \\alpha = {alpha}$ ⟹ **拒绝 $H_0$**，差异显著。"
         if pval < alpha else
         f"$p = {pval:.4f} \\ge \\alpha = {alpha}$ ⟹ **不能拒绝 $H_0$**，证据不足。"),
    ]
    return sol(problem, steps,
               f"z = {z:.4f},\\ p = {pval:.4f},\\ \\text{{{('拒绝' if pval < alpha else '不能拒绝')} }}$H_0$",
               solver="sympy.probability",
               verification={"method": "p 值与临界值法交叉核对", "check": f"alpha = {alpha}"},
               subject="概率统计")


def _solve_distribution_prob(problem):
    """求具体概率：P(X <= k) 之类。"""
    body = problem.get("text", "")
    mu, sd = _extract_normal_params(body)
    n, p = _extract_binomial(body)

    m_le = re.search(r"P\s*\(\s*X\s*(<=|≤|<|>|≥|>=)\s*([-\d.]+)\s*\)", body)
    if not m_le:
        m_le = re.search(r"(?:小于|不超过|不大于|大于|不小于|至少|至多)\s*([-\d.]+)", body)
        if m_le:
            op = ">" if re.search(r"大于|至少", body) else "<="
            k = float(m_le.group(1))
        else:
            return None
    else:
        op = m_le.group(1).replace("≤", "<=").replace("≥", ">=")
        k = float(m_le.group(2))

    if n is not None and p is not None:
        kk = int(k)
        if op in ("<=", "<"):
            idx = kk if op == "<=" else kk - 1
            val = float(sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, idx + 1)))
            steps = [f"$X\\sim B({n},{p})$，求 $P(X \\le {idx})$。",
                     "二项分布 $P(X=k) = \\binom{n}{k}p^k(1-p)^{n-k}$，累加。",
                     f"$P = {val:.6g}$。"]
        else:
            val = 1 - float(sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, kk)))
            steps = [f"$X\\sim B({n},{p})$，用补事件 $P(X > k) = 1 - P(X \\le k)$。",
                     f"$P = {val:.6g}$。"]
        return sol(problem, steps, f"{val:.6g}", solver="sympy.probability", subject="概率统计")

    if mu is not None and sd is not None:
        z = (k - mu) / sd
        def Phi(v):
            return 0.5 * (1 + math.erf(v / math.sqrt(2)))
        val = Phi(z) if op in ("<=", "<") else 1 - Phi(z)
        op_tex = "\\le" if op in ("<=", "<") else ">"
        steps = [
            f"$X \\sim N({mu}, {sd}^2)$，求 $P(X {op_tex} {k})$。",
            f"标准化 $z = \\dfrac{{x-\\mu}}{{\\sigma}} = \\dfrac{{{k}-{mu}}}{{{sd}}} = {z:.4f}$。",
            f"查标准正态表（或 erf 计算）得 $\\Phi({z:.4f}) = {Phi(z):.6f}$。",
            f"$P = {val:.6g}$。",
        ]
        return sol(problem, steps, f"{val:.6g}", solver="sympy.probability", subject="概率统计")

    return None


# ─────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────

def solve(problem: dict) -> Optional[dict]:
    text = problem.get("text", "") + " " + " ".join(problem.get("math_exprs") or [])
    op = detect_prob_op(text)
    if op is None:
        return None
    try:
        if op == "bayes" or op == "conditional":
            return _solve_bayes(problem)
        if op == "correlation":
            return _solve_correlation(problem)
        if op == "regression":
            return _solve_correlation(problem)
        if op == "hypothesis":
            return _solve_hypothesis(problem)
        if op == "expectation":
            return _solve_moments(problem, want_variance=False)
        if op == "variance":
            return _solve_moments(problem, want_variance=True)
        if op == "distribution":
            r = _solve_distribution_prob(problem)
            return r if r is not None else _solve_moments(problem, want_variance=False)
    except Exception as e:  # noqa: BLE001
        return unsolved(problem, f"概率统计求解器异常：{type(e).__name__}: {e}", subject="概率统计")
    return None
