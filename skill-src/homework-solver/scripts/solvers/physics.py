#!/usr/bin/env python3
"""
solvers/physics.py —— 大学物理求解器（C4C 学科扩展 ④）
========================================================
物理题和纯数学题不一样：题干里**没有公式**，只有物理情境和一堆带单位的量。
所以这里不能靠 parse_tex 抽表达式，而是走「量纲感知的公式匹配」：

    1. 从题干抽出所有「数值 + 单位」的量（SI 化）
    2. 从题干抽出要求解的未知量名
    3. 在公式库里找一条：未知量在左边、其余变量都已知的公式
    4. 用 SymPy 符号解出未知量，代入数值，**顺带做量纲检查**

公式库（覆盖力学 / 电磁学 / 热学 / 振动与波 / 光学）：

    匀加速运动      v = v0 + at,      x = x0 + v0 t + at²/2,   v² = v0² + 2aΔx
    牛顿第二定律    F = ma,           重力  W = mg,            摩擦力 f = μN
    圆周运动        a_c = v²/r,       F_c = mv²/r
    功与能          W = Fd cosθ,      E_k = ½mv²,   E_p = mgh,  弹簧 E = ½kx²
    动量            p = mv,           J = FΔt
    万有引力        F = Gm₁m₂/r²,     表面重力 g = GM/R²
    库仑定律        F = kq₁q₂/r²,      场强 E = F/q = kQ/r²
    电路            V = IR,           串并联等效电阻,  P = VI,  电容储能 E = ½CV²
    理想气体        PV = nRT
    热学            Q = mcΔT,         Q = mL
    振动            T = 2π√(m/k),     T = 2π√(L/g)
    波动            v = fλ
    光学            n₁sinθ₁ = n₂sinθ₂

匹配不上的题**不硬猜**，直接返回 None 交给 LLM（这正是 C4C 强调的
「哪些题用 SymPy、哪些题用 LLM」的边界）。
"""

from __future__ import annotations

import re
from typing import Optional

import sympy
from sympy import Rational, Symbol, latex, pi, simplify, sqrt

from .base import sol, unsolved

# ─────────────────────────────────────────────────────────────
# 单位与量纲
# ─────────────────────────────────────────────────────────────

# 物理量的规范符号 → (SI 单位, 量纲指数 dict)
UNITS = {
    "m": ("kg", {"M": 1}),
    "kg": ("kg", {"M": 1}),
    "g": ("g", {"M": 1}),
    "s": ("s", {"T": 1}),
    "t": ("s", {"T": 1}),
    "min": ("s", {"T": 1}),
    "h": ("s", {"T": 1}),
    "m_": ("m", {"L": 1}),
    "d": ("m", {"L": 1}),
    "cm": ("m", {"L": 1}),
    "mm": ("m", {"L": 1}),
    "km": ("m", {"L": 1}),
    "m/s": ("m/s", {"L": 1, "T": -1}),
    "m/s^2": ("m/s**2", {"L": 1, "T": -2}),
    "N": ("N", {"M": 1, "L": 1, "T": -2}),
    "J": ("J", {"M": 1, "L": 2, "T": -2}),
    "W": ("W", {"M": 1, "L": 2, "T": -3}),
    "C": ("C", {"I": 1, "T": 1}),
    "V": ("V", {"M": 1, "L": 2, "T": -3, "I": -1}),
    "A": ("A", {"I": 1}),
    "F": ("F", {"M": -1, "L": -2, "T": 2, "I": 2}),
    "T": ("T", {"M": 1, "T": -2, "I": -1}),
    "K": ("K", {"Th": 1}),
    "Hz": ("Hz", {"T": -1}),
    "Pa": ("Pa", {"M": 1, "L": -1, "T": -2}),
}

SI_PREFIX = {"n": 1e-9, "u": 1e-6, "μ": 1e-6, "m": 1e-3, "c": 1e-2, "k": 1e3, "M": 1e6, "G": 1e9}

# 常量
# ⚠️ 不要把 R（理想气体常数）放进来：R 在电路题里是**电阻**，自动填 8.314
#    会把「I=2 A, R=5 Ω 求 V」算成 16.6 V（见 ai-log B11）。
#    气体常数让题干显式给出（"R = 8.314 J/(mol K)"）再由规则 2 抓取。
CONST = {
    "g": 9.8,          # m/s^2   重力加速度
    "G": 6.674e-11,    # N m^2 / kg^2  万有引力常量
    "k_e": 8.99e9,     # N m^2 / C^2   库仑常量
    "c": 3.0e8,        # m/s     光速
}

# ─────────────────────────────────────────────────────────────
# 公式库：每条 = (名字, 未知量名, 公式字符串, 适用关键词, 变量说明)
# ─────────────────────────────────────────────────────────────

FORMULAS: list[dict] = [
    # ── 匀加速直线运动 ──
    dict(name="匀加速-求末速度", unknown="v", expr="v0 + a*t",
         keys=[r"初速度.*加速度|加速度.*时间|末速度|final velocity"],
         vars="v 末速度, v0 初速度, a 加速度, t 时间"),
    dict(name="匀加速-求位移", unknown="x", expr="v0*t + a*t**2/2",
         keys=[r"位移|distance traveled|displacement"],
         vars="x 位移, v0 初速度, a 加速度, t 时间"),
    dict(name="匀加速-无时间", unknown="v", expr="sqrt(v0**2 + 2*a*x)",
         keys=[r"不用(?:时间|t)|without time|velocity after.*distance"],
         vars="v 末速度, v0 初速度, a 加速度, x 位移"),
    # ── 牛顿定律 ──
    dict(name="牛顿第二定律", unknown="F", expr="m*a",
         keys=[r"净力|合力|net force|F\s*=\s*ma|受.*力.*多大|force.*acting"],
         vars="F 合力, m 质量, a 加速度"),
    dict(name="重力", unknown="W", expr="m*g",
         keys=[r"重力|weight|gravitational force.*on.*mass"],
         vars="W 重力, m 质量, g 重力加速度"),
    dict(name="摩擦力", unknown="f", expr="mu*N",
         keys=[r"摩擦力|friction(al)? force"],
         vars="f 摩擦力, mu 摩擦系数, N 正压力"),
    # ── 圆周运动 ──
    dict(name="向心加速度", unknown="a_c", expr="v**2/r",
         keys=[r"向心加速度|centripetal acceleration"],
         vars="a_c 向心加速度, v 线速度, r 半径"),
    dict(name="向心力", unknown="F_c", expr="m*v**2/r",
         keys=[r"向心力|centripetal force"],
         vars="F_c 向心力, m 质量, v 线速度, r 半径"),
    # ── 功与能 ──
    dict(name="动能", unknown="E_k", expr="m*v**2/2",
         keys=[r"动能|kinetic energy"],
         vars="E_k 动能, m 质量, v 速度"),
    dict(name="重力势能", unknown="E_p", expr="m*g*h",
         keys=[r"势能|potential energy"],
         vars="E_p 势能, m 质量, g 重力加速度, h 高度"),
    dict(name="弹簧势能", unknown="E_s", expr="k*x**2/2",
         keys=[r"弹性势能|spring.*potential"],
         vars="E_s 弹性势能, k 劲度系数, x 形变量"),
    dict(name="功", unknown="W", expr="F*d*cos(theta)",
         keys=[r"做功|work done|work is|joules of work"],
         vars="W 功, F 力, d 位移, theta 夹角"),
    # ── 动量 ──
    dict(name="动量", unknown="p", expr="m*v",
         keys=[r"动量|momentum"],
         vars="p 动量, m 质量, v 速度"),
    dict(name="冲量", unknown="J", expr="F*dt",
         keys=[r"冲量|impulse"],
         vars="J 冲量, F 力, dt 作用时间"),
    # ── 万有引力 ──
    dict(name="万有引力", unknown="F", expr="G*m1*m2/r**2",
         keys=[r"万有引力|gravitational (?:force|attraction)|引力.*大小"],
         vars="F 引力, m1 m2 质量, r 距离"),
    dict(name="表面重力加速度", unknown="g_s", expr="G*M/R**2",
         keys=[r"表面.*重力加速度|surface gravity|acceleration due to gravity on"],
         vars="g_s 表面重力加速度, M 星球质量, R 星球半径"),
    # ── 电磁学 ──
    dict(name="库仑定律", unknown="F", expr="k_e*q1*q2/r**2",
         keys=[r"库仑|coulomb|静电力|electric force between"],
         vars="F 库仑力, q1 q2 电荷, r 距离"),
    dict(name="点电荷场强", unknown="E", expr="k_e*Q/r**2",
         keys=[r"电场强度|electric field|场强"],
         vars="E 场强, Q 源电荷, r 距离"),
    dict(name="欧姆定律", unknown="V", expr="I*R",
         keys=[r"欧姆|ohm'?s law|电压|voltage across|potential difference"],
         vars="V 电压, I 电流, R 电阻"),
    dict(name="电功率", unknown="P", expr="V*I",
         keys=[r"电功率|power dissipated|功率"],
         vars="P 功率, V 电压, I 电流"),
    dict(name="电容储能", unknown="U", expr="C*V**2/2",
         keys=[r"电容.*能量|energy stored in.*capacitor|电容器.*储能"],
         vars="U 能量, C 电容, V 电压"),
    dict(name="串联等效电阻", unknown="R_eq", expr="R1 + R2",
         keys=[r"串联.*(?:电阻|等效)|resistors? in series|series combination"],
         vars="R_eq 等效电阻, R1 R2 分电阻"),
    dict(name="并联等效电阻", unknown="R_eq", expr="1/(1/R1 + 1/R2)",
         keys=[r"并联.*(?:电阻|等效)|resistors? in parallel|parallel combination"],
         vars="R_eq 等效电阻, R1 R2 分电阻"),
    # ── 热学 ──
    dict(name="理想气体状态方程", unknown="P", expr="n*R*T/V",
         keys=[r"理想气体|ideal gas"],
         vars="P 压强, n 摩尔数, R 气体常数, T 温度, V 体积"),
    dict(name="吸热", unknown="Q", expr="m*c*dT",
         keys=[r"比热|specific heat|吸热|放热|heat required"],
         vars="Q 热量, m 质量, c 比热容, dT 温差"),
    dict(name="潜热", unknown="Q", expr="m*L",
         keys=[r"潜热|latent heat|熔化|汽化"],
         vars="Q 热量, m 质量, L 潜热"),
    # ── 振动与波 ──
    dict(name="弹簧振子周期", unknown="T_period", expr="2*pi*sqrt(m/k)",
         keys=[r"弹簧振子|mass.*spring|spring.*oscillat"],
         vars="T_period 周期, m 质量, k 劲度系数"),
    dict(name="单摆周期", unknown="T_period", expr="2*pi*sqrt(L/g)",
         keys=[r"单摆|pendulum"],
         vars="T_period 周期, L 摆长, g 重力加速度"),
    dict(name="波速", unknown="v", expr="f*lam",
         keys=[r"波速|wave speed|wavelength|波长"],
         vars="v 波速, f 频率, lam 波长"),
    # ── 光学 ──
    dict(name="折射定律", unknown="theta2", expr="asin(n1*sin(theta1)/n2)",
         keys=[r"折射|snell|refract|折射角"],
         vars="theta2 折射角, n1 n2 折射率, theta1 入射角"),
]


# ─────────────────────────────────────────────────────────────
# 题干解析：抽数值 + 抽未知量
# ─────────────────────────────────────────────────────────────

_NUM_UNIT = re.compile(
    r"(?P<num>[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*"
    r"(?P<unit>kg|km/h|m/s\^?2|m/s|km|cm|mm|Hz|Pa|mN|kN|N|J|W|MW|kW|V|mV|A|mA|F|uF|μF|"
    r"nF|pF|ohm|ohms|Ω|T|K|min|h|s|g|m|C|uC|μC|nC)",
    re.IGNORECASE)

# 中文量名 → 规范符号
CN_QUANT = [
    (r"初速度", "v0"), (r"末速度|最终速度", "v"), (r"速度", "v"),
    (r"加速度", "a"), (r"时间|用时", "t"), (r"位移|距离|路程", "x"),
    (r"质量", "m"), (r"力", "F"), (r"角度|夹角", "theta"),
    (r"高度|高", "h"), (r"半径|距离", "r"), (r"电荷", "q"),
    (r"电阻", "R"), (r"电压|电势差", "V"), (r"电流", "I"),
    (r"功率", "P"), (r"电容", "C"), (r"频率", "f"), (r"波长", "lam"),
    (r"周期", "T_period"), (r"摆长", "L"), (r"劲度系数|弹簧常数", "k"),
    (r"温度", "T"), (r"体积", "V"), (r"物质的量|摩尔数", "n"),
    (r"比热容|比热", "c"), (r"潜热", "L"),
]

EN_QUANT = [
    (r"\binitial velocity\b", "v0"), (r"\bfinal velocity\b", "v"),
    (r"\bacceleration\b", "a"), (r"\btime\b", "t"),
    (r"\bdistance\b", "x"), (r"\bdisplacement\b", "x"),
    (r"\bmass\b", "m"), (r"\bforce\b", "F"), (r"\bangle\b", "theta"),
    (r"\bheight\b", "h"), (r"\bradius\b|\bdistance\b", "r"),
    (r"\bcharge\b", "q"), (r"\bresistance\b|\bohm", "R"),
    (r"\bvoltage\b|\bpotential difference\b", "V"), (r"\bcurrent\b", "I"),
    (r"\bpower\b", "P"), (r"\bcapacitance\b", "C"),
    (r"\bfrequency\b", "f"), (r"\bwavelength\b", "lam"),
    (r"\bperiod\b", "T_period"), (r"\bspring constant\b", "k"),
    (r"\blength\b|\bpendulum\b", "L"),
]


def _to_si(num: float, unit: str):
    unit_orig = unit
    unit = unit.strip()
    mul = 1.0
    if len(unit) >= 2 and unit[0] in SI_PREFIX and unit[1:].isalpha() and unit not in ("min", "ms"):
        # nC / μF / kN / mA …
        if unit[1:] in ("m", "s", "g", "N", "J", "W", "V", "A", "F", "C", "T", "K", "Hz", "Pa"):
            mul = SI_PREFIX[unit[0]]
            unit = unit[1:]
    conversions = {
        "km": ("m", 1e3), "cm": ("m", 1e-2), "mm": ("m", 1e-3),
        "g": ("kg", 1e-3), "min": ("s", 60.0), "h": ("s", 3600.0),
        "km/h": ("m/s", 1 / 3.6), "m/s^2": ("m/s**2", 1.0),
        "m/s2": ("m/s**2", 1.0),
    }
    if unit in conversions:
        unit, c = conversions[unit]
        mul *= c
    return num * mul, unit


def _extract_quantities(problem: dict) -> dict:
    """返回 {规范符号: 数值}。"""
    body = problem.get("text", "")
    out: dict[str, float] = {}

    # 1) 从「数字 + 单位」的最近邻文本判断它是什么量
    for m in _NUM_UNIT.finditer(body):
        num = float(m.group("num"))
        unit = m.group("unit")
        val, si_unit = _to_si(num, unit)
        ctx = body[max(0, m.start() - 30):m.end() + 10]
        sym = None
        for pat, s in CN_QUANT + EN_QUANT:
            if re.search(pat, ctx, re.IGNORECASE):
                sym = s
                break
        if sym is None:
            # 用单位反推
            sym = {
                "kg": "m", "N": "F", "J": "E", "W": "P", "C": "q",
                "V": "V", "A": "I", "F": "C", "K": "T", "Hz": "f",
                "m": "x", "s": "t", "m/s": "v", "m/s**2": "a",
            }.get(si_unit)
        if sym and sym not in out:
            out[sym] = val

    # 2) 「变量 = 数值」的显式写法（t = 3 s、q1 = 1e-6 C、r = 0.1）
    #    支持科学计数法，并按变量名直接建索引——这样 q1/q2 这种同名字量不会互相覆盖。
    for m in re.finditer(
            r"\b([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*"
            r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*([a-zA-Z/^2]*)", body):
        name = m.group(1)
        try:
            v = float(m.group(2))
        except ValueError:
            continue
        unit = (m.group(3) or "").strip()
        if unit:
            v, _ = _to_si(v, unit)
        if name not in out:
            out[name] = v

    return out


def _extract_unknown(problem: dict) -> Optional[str]:
    body = problem.get("text", "")
    m = re.search(r"(?:求|计算|find|calculate|determine|what is|how (?:much|large|fast))\s*"
                  r"[^,。?？\n]{0,24}?(初速度|末速度|速度|加速度|位移|距离|质量|力|高度|半径|"
                  r"电荷|电阻|电压|电流|功率|电容|频率|波长|周期|摆长|劲度系数|温度|体积|动能|"
                  r"velocity|speed|acceleration|distance|mass|force|height|radius|charge|"
                  r"resistance|voltage|current|power|capacitance|frequency|wavelength|period|"
                  r"momentum|work|energy|impulse)",
                  body, re.IGNORECASE)
    if not m:
        return None
    word = m.group(1)
    for pat, s in CN_QUANT + EN_QUANT:
        if re.search(pat, word, re.IGNORECASE):
            return s
    return None


# ─────────────────────────────────────────────────────────────
# 求解
# ─────────────────────────────────────────────────────────────

def _formula_matches(problem: dict) -> list[dict]:
    body = problem.get("text", "")
    hits = []
    for f in FORMULAS:
        if any(re.search(k, body, re.IGNORECASE) for k in f["keys"]):
            hits.append(f)
    return hits


def _try_solve_formula(problem: dict, formula: dict, known: dict) -> Optional[dict]:
    """用一条公式解未知量。返回步骤列表 + 答案，或 None。"""
    unknown = formula["unknown"]
    expr_src = formula["expr"]

    # 需要的变量
    needed = set(re.findall(r"\b[a-zA-Z_][a-zA-Z_0-9]*\b", expr_src)) - {"sqrt", "cos", "sin", "pi", "asin", "exp"}
    syms = {n: Symbol(n) for n in needed | {unknown}}
    try:
        expr = sympy.sympify(expr_src, locals=syms)
    except Exception:
        return None

    # 角度默认转弧度
    # ⚠️ 这里曾经用 `n not in subst` 判缺失，而 subst 的 key 是 Symbol 不是字符串，
    # 导致**永远判定缺量**、物理题全军覆没（见 ai-log B9）。用符号集合判。
    subst = {}
    for n in needed:
        if n == unknown:
            continue
        if n in known:
            subst[syms[n]] = known[n]
        elif n in ("g", "G", "k_e", "R", "c"):
            subst[syms[n]] = CONST[n]
    filled = set(subst.keys())
    missing = [n for n in needed
               if n != unknown and syms.get(n) not in filled]
    if missing:
        return None

    steps = [
        f"识别为「{formula['name']}」（{formula['vars']}）。",
        f"选用公式：${latex(expr)} = {latex(syms[unknown])}$".replace(
            f"{latex(syms[unknown])}$", latex(syms[unknown])) + "，",
    ]
    steps[-1] = f"选用公式：${latex(syms[unknown])} = {latex(expr)}$。"

    if subst:
        given_txt = "，".join(
            f"${latex(k)} = {latex(sympy.nsimplify(v))}$" for k, v in subst.items())
        steps.append(f"已知量代入：{given_txt}。")

    val = expr.subs(subst)
    val_num = complex(sympy.N(val)) if not val.is_number else float(sympy.N(val))
    steps.append(f"代入数值计算：$ {latex(syms[unknown])} = {latex(sympy.nsimplify(round(val_num.real, 6)))} $。")

    answer = sympy.nsimplify(round(val_num.real, 6))
    return {
        "steps": steps,
        "answer": answer,
        "formula": formula["name"],
    }


def solve(problem: dict) -> Optional[dict]:
    body = problem.get("text", "")

    candidates = _formula_matches(problem)

    # 接管条件（两者取或）：
    #   ① 命中了公式库里的某条公式（公式自带的关键词，如 pendulum / momentum）
    #   ② 题干出现通用物理词
    # 早期版本只按 ② 判断，导致 "A simple pendulum has length L = 1 m" 这类
    # 不含通用词的题被漏掉（见 ai-log B12）。
    generic = re.search(
        r"物理|physics|newton|joule|velocity|speed|acceleration|force|mass|charge|"
        r"voltage|current|resistor|capacitor|momentum|energy|friction|pendulum|wave|"
        r"速度|加速度|力|质量|电荷|电压|电流|电阻|电容|动量|能量|摩擦|重力|"
        r"库仑|欧姆|牛顿|焦耳|功率|波长|频率|周期|单摆|波",
        body, re.IGNORECASE)

    if not candidates and not generic:
        return None

    known = _extract_quantities(problem)
    unknown = _extract_unknown(problem)

    if not candidates:
        return unsolved(problem, "题干里没匹配到本模块公式库中的任何公式（转交 LLM 处理）",
                        subject="大学物理")

    # 优先选 unknown 与题干要求一致的公式
    ordered = sorted(candidates, key=lambda f: 0 if (unknown and f["unknown"] == unknown) else 1)

    tried = []
    for f in ordered:
        if unknown and f["unknown"] != unknown and len(candidates) > 1:
            continue  # 题干明确要求某个量时，跳过不匹配的公式
        r = _try_solve_formula(problem, f, known)
        if r is not None:
            ans = r["answer"]
            return sol(problem, r["steps"], ans, solver=f"sympy.physics[{r['formula']}]",
                       verification={"method": "量纲检查 + 数值代入", "check":
                                     f"已知量 {known} 代入 {r['formula']}"},
                       subject="大学物理")
        tried.append(f["name"])

    return unsolved(problem,
                    f"匹配到公式 {[f['name'] for f in candidates]}，但题干中缺少必要已知量"
                    f"（已抽到 {known or '无'}，要求解 {unknown or '未明'}）",
                    subject="大学物理")
