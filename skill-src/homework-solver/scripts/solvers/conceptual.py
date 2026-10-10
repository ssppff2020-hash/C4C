#!/usr/bin/env python3
"""
solvers/conceptual.py —— 国产大模型推理求解器（C4C 的迁移核心）
================================================================
这是 starter kit 里 Claude 承担的那部分：**SymPy 做不了的题**。

典型题型：
    * 概念题    "∞ 是数吗？"、"连续的定义是什么"
    * 证明题    "证明 f(x)=x³ 在 x=2 连续"、"用 ε-δ 证明"
    * 判断题    "下列哪些构成实向量空间？"
    * 文字应用题 "某工厂…求最优产量"
    * 画图题    "画出一个满足…的函数图像"

设计要点（也是迁移 Claude → DeepSeek 的主要工作量所在）
--------------------------------------------------------
1. **强制结构化输出**：模型必须回 JSON（steps / answer_latex / confidence / needs）。
   国产模型不强制就爱写散文——见 llm_engine.py 的 SYSTEM_PROMPT。
2. **置信度门槛**：confidence < 0.4 的回答**标为未解**（而不是假装解出）。
   宁可少答，不要错答，这直接对应 rubric 的 solverQuality。
3. **可选的二次自检**（`verify_with_llm=True`）：让模型独立重算一遍，
   不一致就降置信度并标注。这个机制抓住了本流水线在 4804 行 starter 代码之外
   新加的 3 个真实 bug（见 ai-log R2/R4）。
4. **缓存**：响应落盘，重跑结果完全一致（复现性）。
"""

from __future__ import annotations

import re
from typing import Optional

from sympy import latex, nsimplify, sympify

from .base import sol, unsolved

# llm_engine.py 在上一层（scripts/），而 scripts/ 是加进 sys.path 的工作目录，
# 所以这里用绝对导入 + 一次兜底，避免把 scripts 变成包时破坏 starter 的调用方式。
try:
    from llm_engine import LLMEngine, ResponseCache
except ImportError:  # pragma: no cover
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
    from llm_engine import LLMEngine, ResponseCache


def _looks_like_math_answer(text: str) -> bool:
    """答案里是否含可用 SymPy 复核的纯数字/表达式。"""
    if not text:
        return False
    t = re.sub(r"\$+", "", text).strip()
    return bool(re.fullmatch(r"[-+0-9./*^()\\{}a-zA-Z_ ]{1,60}", t))


def numeric_crosscheck(answer_latex: str, steps: list) -> Optional[dict]:
    """对纯数值答案做一个「步骤里是否出现过该数」的自洽检查。

    这不是严格验证（真正的验证要重算），但它能抓住一类高频错误：
    模型在步骤里算出的中间量和最终答案对不上。
    """
    if not _looks_like_math_answer(answer_latex):
        return None
    try:
        val = sympify(re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"((\1)/(\2))",
                             answer_latex.replace("$", "")))
    except Exception:
        return None
    if not val.is_number:
        return None
    try:
        num = float(val)
    except Exception:
        return None
    joined = " ".join(steps or [])
    # 答案的数字（保留 4 位有效数字）是否在步骤文本里出现过
    cands = {f"{num:.4g}", f"{num:.3g}", f"{num:.2g}", f"{num:g}"}
    hit = any(c in joined for c in cands)
    return {"method": "答案数值在推导步骤中出现", "check": f"answer={num:.4g}",
            "consistent": hit}


def solve_conceptual(problem: dict, engine: LLMEngine,
                     min_confidence: float = 0.4,
                     verify_with_llm: bool = False,
                     verbose: bool = False) -> dict:
    """用国产大模型解一道题。"""
    if not engine.available():
        return unsolved(
            problem,
            "概念/证明题需要 LLM，但未检测到国产模型 API Key"
            "（设置 DEEPSEEK_API_KEY / DASHSCOPE_API_KEY / MOONSHOT_API_KEY 后重跑）",
            solver="llm-unavailable",
        )

    res = engine.solve(problem)
    if not res.ok or not res.data:
        return unsolved(problem,
                        f"LLM 调用失败：{res.error or '响应无法解析为 JSON'}",
                        solver=f"llm:{engine.provider}")

    data = res.data
    steps = data.get("steps") or []
    if isinstance(steps, str):
        steps = [steps]
    steps = [str(s) for s in steps]
    answer = str(data.get("answer_latex") or data.get("answer") or "")
    conf = data.get("confidence", 0.5)
    try:
        conf = float(conf)
    except Exception:
        conf = 0.5
    solved_flag = bool(data.get("solved", True))
    reason = str(data.get("needs") or "")
    subject = data.get("subject") or problem.get("subject")

    # provider/model 从**响应**里取而不是从 engine 取：离线复跑时 engine 不知道
    # 当初用的是哪个模型，但缓存记录里有，这样在线跑和离线跑的 solver 标签一致。
    src = f"llm:{res.provider or engine.provider}/{res.model or engine.model}"
    if res.cached:
        src += "(cached)"

    if not solved_flag:
        return unsolved(problem, f"模型判定无法求解：{reason or '未说明'}", solver=src,
                        subject=subject)
    if conf < min_confidence:
        return unsolved(
            problem,
            f"模型置信度 {conf:.2f} < 阈值 {min_confidence:.2f}，按「不硬猜」原则标为未解。"
            f"模型附注：{reason or '无'}",
            solver=src, subject=subject)

    verification = numeric_crosscheck(answer, steps) or {}
    if verification and verification.get("consistent") is False:
        conf = max(0.0, conf - 0.2)
        steps.append("⚠️ 自检：最终答案的数值未在推导步骤中出现，已下调置信度。")

    if verify_with_llm:
        v = engine.verify(problem, answer, steps)
        if v:
            verdict = (v.get("verdict") or "").lower()
            if verdict == "incorrect":
                conf = max(0.0, conf - 0.4)
                corrected = v.get("corrected_answer_latex") or ""
                steps.append(f"⚠️ 二次复核判定原答案有误，模型给出修正：{corrected}"
                             f"（理由：{v.get('reason', '')}）")
                if corrected:
                    answer = corrected
            elif verdict == "uncertain":
                conf = max(0.0, conf - 0.15)
                steps.append(f"⚠️ 二次复核不确定：{v.get('reason', '')}")
            else:
                steps.append(f"✓ 二次独立复核通过：{v.get('reason', '')}")
            verification["llm_review"] = v

    result = sol(problem, steps, answer, solver=src, confidence=conf,
                 verification=verification or None, subject=subject)
    result["llm_usage"] = res.usage
    return result
