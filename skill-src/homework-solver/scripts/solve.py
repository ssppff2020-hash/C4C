#!/usr/bin/env python3
"""
Stage 3: 自动求解（总调度）
============================
把 starter kit 那条「只有微积分极限」的求解链，扩成一条**混合路由**：

                     ┌──────────────────────────┐
     Problem  ──────►│ 0. 学科判定 detect_subject│
                     └───────────┬──────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
   ┌─────────┐            ┌─────────────┐          ┌────────────┐
   │ 确定性层 │            │ 术语/符号层  │          │ 推理层      │
   │ SymPy   │            │ SymPy       │          │ 国产大模型   │
   │ 24 个    │            │ calculus_   │          │ DeepSeek /  │
   │ 求解分支 │            │ limits      │          │ Qwen / Kimi │
   │ linalg  │            │ （starter   │          │ conceptual  │
   │ ode     │            │  原样保留）  │          │ .py        │
   │ calculus│            └─────────────┘          └────────────┘
   │ physics │                                          ▲
   │ prob    │────────── 确定性层解不出 ─────────────────┘
   └─────────┘

路由原则（对应 challenge 里「你需要决定哪些题用 SymPy，哪些用 LLM」）：
  1. **能确定性算的绝不用 LLM**：答案可核验、可复现、零成本。
  2. **LLM 只做 SymPy 做不了的**：证明、概念、建模、文字。
  3. **LLM 的答案要过置信度门槛**，低于阈值宁可标「未解」。

用法:
    python solve.py <2_parsed.json> <3_solutions.json> [--no-llm] [--verify] [--verbose]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from solvers import calculus_core, calculus_limits, conceptual, linalg, ode, physics, probability
from solvers.base import sol, unsolved
from llm_engine import LLMEngine, ResponseCache

# ─────────────────────────────────────────────────────────────
# 0. 题目归一化
# ─────────────────────────────────────────────────────────────

def normalize_problem(p: dict) -> dict:
    """统一字段：把 starter 的 math_expressions([{type,latex}]) 同时导出成
    math_exprs([str])，让新老求解器都能用；并补齐 id / text。

    ⚠️ **必须是幂等的**。早期版本每次都把正文里的 $...$ 追加进 math_exprs，
    于是递归求解时同一道题被 normalize 两次 → math_exprs 翻倍 →
    LLM 的 prompt 变了 → 缓存全部失效、离线复现失败（见 ai-log B13）。
    """
    if p.get("_normalized"):
        return p

    exprs = []
    for e in p.get("math_expressions") or []:
        if isinstance(e, dict):
            exprs.append(e.get("latex", ""))
        elif isinstance(e, str):
            exprs.append(e)

    # 正文里裸的 $...$ 也算候选表达式（去重，避免重复项）
    body = p.get("text", "") or ""
    exprs += re.findall(r"\$\$(.+?)\$\$", body, re.DOTALL)
    exprs += re.findall(r"\$(.+?)\$", body, re.DOTALL)

    seen, uniq = set(), []
    for e in exprs:
        if e and e not in seen:
            seen.add(e)
            uniq.append(e)
    p["math_exprs"] = uniq

    for s in p.get("sub_problems") or []:
        normalize_problem(s)
    p["_normalized"] = True
    return p


def dedupe_sub_ids(problem: dict) -> dict:
    """给重复的子题 id 加后缀。

    PDF 里 "(c) ... d) all of the above." 这种被折行的情况会让解析器
    生成两个 id 都是 'd' 的子题；重复 id 会让解答互相覆盖（见 ai-log B6）。
    """
    seen: dict[str, int] = {}
    for s in problem.get("sub_problems") or []:
        sid = str(s.get("id", "?"))
        if sid in seen:
            seen[sid] += 1
            s["id"] = f"{sid}{seen[sid]}"
        else:
            seen[sid] = 1
        s["_orig_id"] = sid
    return problem


# ─────────────────────────────────────────────────────────────
# 1. 学科判定
# ─────────────────────────────────────────────────────────────

_SUBJECT_RULES: list[tuple[str, list[str], int]] = [
    # (学科, 关键词(正则), 权重)
    ("ode", [r"微分方程", r"differential\s+equation", r"y\s*''", r"y\s*'", r"\bdy/dx\b",
             r"\\frac\{d[yx]\}", r"dsolve", r"初值问题", r"拉普拉斯|laplace"], 3),
    ("linalg", [r"矩阵", r"matrix", r"行列式", r"determinant", r"特征值", r"eigenval",
                r"特征向量", r"eigenvector", r"向量空间|vector\s+space", r"秩\b|\brank\b",
                r"线性相关|linearly", r"零空间|null\s*space", r"正交|orthogonal",
                r"\\begin\{(?:p|b|v|B|V)?matrix\}", r"对角化|diagonaliz", r"奇异值|\bSVD\b"], 3),
    ("probability", [r"概率|probabilit", r"期望|expectation|expected\s+value", r"方差|variance",
                     r"标准差|standard\s+deviation", r"分布|distribution", r"贝叶斯|bayes",
                     r"假设检验|hypothesis\s+test", r"回归|regression", r"相关系数|correlation",
                     r"随机变量|random\s+variable", r"二项|binomial", r"泊松|poisson",
                     r"正态|normal\s+distribution",
                     # 记号形式：X \sim N(0,1)、P(X<=1.96)、X~B(10,0.5)
                     r"[Xx]\s*(?:\\sim|~)\s*[NBUEP]", r"[Pp]\s*\(\s*[Xx]\s*[<>=≤≥]"], 3),
    ("physics", [r"物理|physics", r"牛顿|newton", r"焦耳|joule", r"速度|velocity",
                 r"加速度|acceleration", r"质量|\bmass\b", r"电荷|charge", r"电压|voltage",
                 r"电流|\bcurrent\b", r"电阻|resistor|resistance", r"电容|capacitor",
                 r"动量|momentum", r"摩擦|friction", r"重力|gravity",
                 r"库仑|coulomb", r"欧姆|ohm", r"波长|wavelength", r"功率|power"], 2),
    ("calculus_limits", [r"\\lim", r"\blim_", r"极限|\blimit\b", r"ε-δ|epsilon-delta|epsilon-\\delta",
                         r"切线|tangent\s+line", r"连续性|continuous\s+at", r"夹逼|squeeze"], 3),
    ("calculus", [r"导数|derivative|求导|differentiat", r"积分|integral|\bint\b", r"\\int",
                  r"泰勒|taylor|麦克劳林|maclaurin", r"级数|\bseries\b", r"收敛|diverge|converge",
                  r"梯度|gradient", r"散度|divergence", r"旋度|\bcurl\b", r"极值|maximu?m|minimu?m",
                  r"弧长|arc\s+length", r"体积|volume", r"偏导|partial\s+deriv"], 2),
]


def detect_subject(problem: dict) -> str:
    """给一道题判学科。返回学科名或 'unknown'。"""
    text = (problem.get("text") or "") + "\n" + "\n".join(problem.get("math_exprs") or [])
    scores: dict[str, int] = {}
    for subject, pats, weight in _SUBJECT_RULES:
        s = 0
        for pat in pats:
            if re.search(pat, text, re.IGNORECASE):
                s += weight
        if s:
            scores[subject] = s
    if not scores:
        return "unknown"

    # 有矩阵字面量时优先线代（很多线代题题干只有一句 "Compute ..."）
    if re.search(r"\\begin\{(?:p|b|v|B|V)?matrix\}", text) and "linalg" in scores:
        return "linalg"

    best = max(scores, key=lambda k: scores[k])
    return best


# ─────────────────────────────────────────────────────────────
# 2. 单题求解
# ─────────────────────────────────────────────────────────────

_SYMPY_ROUTER = {
    "linalg": linalg.solve,
    "ode": ode.solve,
    "physics": physics.solve,
    "probability": probability.solve,
    "calculus": calculus_core.solve,
    "calculus_limits": calculus_limits.solve_problem,
}


def solve_problem(problem: dict, engine: LLMEngine, *,
                  use_llm: bool = True,
                  verify_with_llm: bool = False,
                  min_confidence: float = 0.4,
                  verbose: bool = False,
                  _parent_text: str = None,
                  _siblings: list = None) -> dict:
    """一道题的完整求解：学科判定 → 确定性求解 → LLM 兜底。

    _parent_text / _siblings 由父题递归调用时注入，用于给 LLM 补上下文。
    """
    problem = normalize_problem(problem)
    dedupe_sub_ids(problem)
    if _parent_text:
        problem["parent_text"] = _parent_text
    if _siblings:
        problem["sibling_texts"] = _siblings

    if not (problem.get("text") or "").strip():
        return unsolved(problem, "题目文本为空", subject="unknown")

    subject = detect_subject(problem)
    logger = (lambda *a: print("   ", *a)) if verbose else (lambda *a: None)

    # ── a) 确定性层 ──
    modules = []
    primary = _SYMPY_ROUTER.get(subject)
    if primary is not None:
        modules.append((subject, primary))

    # 学科判定可能不准：再按 线代 → ODE → 概率 → 物理 → 微积分 的顺序补试
    fallback_order = ["linalg", "ode", "probability", "physics", "calculus", "calculus_limits"]
    for name in fallback_order:
        if name == subject:
            continue
        modules.append((name, _SYMPY_ROUTER[name]))

    for name, fn in modules:
        try:
            r = fn(problem)
        except Exception as e:  # noqa: BLE001
            logger(f"[{name}] 求解异常 {type(e).__name__}: {e}")
            continue
        if r is None:
            continue
        if r.get("solved"):
            r.setdefault("subject", name)
            logger(f"[{name}] ✓ {str(r.get('answer_latex'))[:60]}")
            return r
        # 该模块认领了但没解出：记下原因，继续找别的模块 / 最后交给 LLM
        logger(f"[{name}] 认领但未解出：{r.get('reason')}")
        fallback_reason = r.get("reason")

    # ── b) 子题独立求解（父题失败时逐个子题试） ──
    subs = problem.get("sub_problems") or []
    if subs:
        # 兄弟小问只看各自的「一句话题干」，别把整段大题重复塞进去
        siblings = [(str(s.get("id", "?")), (s.get("text") or "").strip()[:200])
                    for s in subs]
        parent_text = problem.get("text", "")
        sub_results = []
        for s in subs:
            child = {"id": s.get("id", "?"), "text": s.get("text", ""),
                     "math_expressions": s.get("math_expressions") or [],
                     "sub_problems": []}
            normalize_problem(child)
            sib = [(lbl, t) for lbl, t in siblings if lbl != str(s.get("id", "?"))]
            sub_results.append(solve_problem(
                child, engine, use_llm=use_llm, verify_with_llm=verify_with_llm,
                min_confidence=min_confidence, verbose=verbose,
                _parent_text=parent_text, _siblings=sib))
        n_ok = sum(1 for r in sub_results if r.get("solved"))
        if n_ok:
            parent = sol(problem, [], "", solver="mixed", sub_solutions=sub_results,
                         subject=subject)
            parent["solved"] = n_ok == len(sub_results) or n_ok >= 1
            parent["answer_latex"] = "\\quad ".join(
                f"\\text{{({r['problem_id']})}}\\ {r['answer_latex']}"
                for r in sub_results if r.get("solved"))
            parent["answer"] = parent["answer_latex"]
            parent["partial"] = n_ok < len(sub_results)
            parent["sub_solved"] = f"{n_ok}/{len(sub_results)}"
            return parent

    # ── c) 推理层：国产大模型 ──
    if use_llm:
        r = conceptual.solve_conceptual(problem, engine, min_confidence=min_confidence,
                                        verify_with_llm=verify_with_llm, verbose=verbose)
        r.setdefault("subject", subject)
        return r

    return unsolved(problem, "确定性求解器未覆盖，且本次运行禁用了 LLM（--no-llm）",
                    subject=subject)


# ─────────────────────────────────────────────────────────────
# 3. 批量求解
# ─────────────────────────────────────────────────────────────

def solve_all(problems: list, engine: LLMEngine = None, *,
              use_llm: bool = True, verify_with_llm: bool = False,
              min_confidence: float = 0.4, verbose: bool = False) -> list:
    if engine is None:
        engine = LLMEngine(cache=ResponseCache(), enabled=use_llm)
    results = []
    for p in problems:
        t0 = time.time()
        r = solve_problem(p, engine, use_llm=use_llm, verify_with_llm=verify_with_llm,
                          min_confidence=min_confidence, verbose=verbose)
        r["elapsed"] = round(time.time() - t0, 3)
        results.append(r)
    return results


def summarize(solutions: list) -> dict:
    total = len(solutions)
    solved = sum(1 for s in solutions if s.get("solved"))
    by_solver: dict[str, int] = {}
    by_subject: dict[str, list] = {}
    for s in solutions:
        sv = (s.get("solver") or "none").split("[")[0]
        by_solver[sv] = by_solver.get(sv, 0) + (1 if s.get("solved") else 0)
        key = s.get("subject") or "unknown"
        d = by_subject.setdefault(key, [0, 0])
        d[0] += 1 if s.get("solved") else 0
        d[1] += 1
    return {
        "total": total,
        "solved": solved,
        "rate": (solved / total) if total else 0.0,
        "by_solver": by_solver,
        "by_subject": {k: {"solved": v[0], "total": v[1]} for k, v in by_subject.items()},
    }


# ─────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(description="Stage 3: 自动求解（混合路由）")
    ap.add_argument("input", help="2_parsed.json")
    ap.add_argument("output", help="3_solutions.json")
    ap.add_argument("--no-llm", action="store_true", help="禁用国产大模型，只用 SymPy")
    ap.add_argument("--verify", action="store_true", help="LLM 答案二次自检（更慢更准）")
    ap.add_argument("--min-confidence", type=float, default=0.4)
    ap.add_argument("--provider", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    problems = json.loads(Path(args.input).read_text(encoding="utf-8"))
    engine = LLMEngine(provider=args.provider, model=args.model,
                       cache=ResponseCache(enabled=not args.no_cache),
                       enabled=not args.no_llm, verbose=args.verbose)

    print(f"[Stage 3] 自动求解：{len(problems)} 道题")
    print(f"  国产大模型：{engine.describe()}")
    print(f"  学科分布：", end="")
    dist: dict[str, int] = {}
    for p in problems:
        dist[detect_subject(normalize_problem(p))] = dist.get(detect_subject(normalize_problem(p)), 0) + 1
    print(", ".join(f"{k}×{v}" for k, v in sorted(dist.items())))

    sols = solve_all(problems, engine, use_llm=not args.no_llm,
                     verify_with_llm=args.verify, min_confidence=args.min_confidence,
                     verbose=args.verbose)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(sols, ensure_ascii=False, indent=2), encoding="utf-8")

    s = summarize(sols)
    print(f"\n  已解 {s['solved']}/{s['total']} ({s['rate']*100:.1f}%)")
    for sol_name, n in sorted(s["by_solver"].items(), key=lambda kv: -kv[1]):
        print(f"     {sol_name:<28} {n}")
    print(f"  输出：{args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
