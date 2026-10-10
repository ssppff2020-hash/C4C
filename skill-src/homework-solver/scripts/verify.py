#!/usr/bin/env python3
"""
正确性验证（Correctness Verification）
========================================
C4C 的 rubric 第一项是「求解正确率」，第三项信号是「输出可核验」。
光说「我们解了 32 道题」没有意义——必须有**对照**。

本模块把「对照」做成可复现的实验：
    输入：3_solutions.json  +  ground_truth.json（标准答案，来自课程官方解答）
    输出：逐题的判定（correct / partial / wrong / unsolved / manual）+ 汇总正确率

判定方式按题型分四种：
    choice   选择题：抽选项编号或关键词做匹配
    exact    精确表达式：归一化后比较（去 $、\left、空格、括号）
    contains 语义包含：答案里是否出现关键结论
    set      结果集合：把 {a,b,c} 拆开比对（顺序无关）
    manual   需要人工裁决（计入分母，单列出来，不偷偷算对）

**诚实原则**：判定不出来的绝不默认算对，一律进 `manual` 并在报告里列出，
由人（或 LLM 二次裁决，见 --llm-adjudicate）逐条确认。

用法:
    python verify.py <3_solutions.json> <ground_truth.json> [--out report.json]
                     [--llm-adjudicate]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


# ─────────────────────────────────────────────────────────────
# 归一化
# ─────────────────────────────────────────────────────────────

_LATEX_NOISE = [
    # ⚠️ 分数必须在删除反斜杠**之前**展开成 a/b，
    # 否则 \frac{1}{2} 会变成 "frac12"，数值比对全线失效（见 ai-log B8）。
    (r"\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)"),
    # 矩阵环境名整体去掉，否则 "begin(matrix)2,3,4end(matrix)" 里的字母会污染数值抽取
    (r"\\begin\{[a-zA-Z*]+\}", ""), (r"\\end\{[a-zA-Z*]+\}", ""),
    # ⚠️ 矩阵/向量的行列分隔符必须**先**变成逗号，
    # 否则后面把反斜杠整体删掉时 `2\\3\\4` 会粘成 `234`。
    (r"\\\\", ","), (r"&", ","),
    (r"\\left", ""), (r"\\right", ""), (r"\\!", ""), (r"\\,", ""), (r"\\;", ""),
    (r"\\displaystyle", ""), (r"\\text\{", "{"), (r"\\mathrm\{", "{"),
    (r"\\operatorname\{", "{"), (r"\\quad", " "), (r"\\qquad", " "),
    (r"\\cdot", "*"), (r"\\times", "*"), (r"\{", "("), (r"\}", ")"),
    (r"\\", ""), (r"\$", ""), (r"\s+", ""),
]

_ANSWER_WORDS = {
    "yes": "yes", "是": "yes", "true": "yes", "对": "yes", "成立": "yes",
    "no": "no", "否": "no", "false": "no", "错": "no", "不成立": "no",
}


def norm(s) -> str:
    """把答案归一化成可比较的小写紧凑串。"""
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKC", s)
    s = s.lower().strip()
    # 去 LaTeX 噪声
    for pat, rep in _LATEX_NOISE:
        s = re.sub(pat, rep, s)
    # 统一 min/max 写法
    s = s.replace("∞", "oo").replace("inf", "oo")
    # 数字归一化：2.0 → 2，0.50 → 0.5
    def _trunc(m):
        try:
            v = float(m.group(0))
            return f"{v:g}"
        except ValueError:
            return m.group(0)
    s = re.sub(r"\d+\.\d+", _trunc, s)
    return s


def norm_math(s) -> str:
    """更激进的数学归一化：只留字母数字和基本运算符。"""
    s = norm(s)
    return re.sub(r"[^0-9a-z+\-*/=.^()|,{}<>]", "", s)


def _loose(s) -> str:
    """最宽松的归一化：只留字母和数字（用于「关键结论是否出现」）。"""
    return re.sub(r"[^0-9a-z]", "", norm(s))


def _eval_chunk(chunk: str):
    """把 "899/500" "1/2" "-3" "0.25" 这样的片段算成一个数；算不出返回 None。"""
    c = chunk.strip().strip("[]{}").strip()
    c = c.replace("−", "-").replace("×", "*")
    # 只在整段被一对圆括号完整包住时才脱掉括号；
    # "(1)/(2)" 这种必须保留，否则会退化成两个独立的数 [1, 2]。
    while c.startswith("(") and c.endswith(")"):
        depth = 0
        wrapped = True
        for i, ch in enumerate(c):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i != len(c) - 1:
                    wrapped = False
                    break
        if not wrapped:
            break
        c = c[1:-1].strip()
    if not c or not re.fullmatch(r"[-+]?[\d./*+\s()]+", c):
        return None
    try:
        # 只允许数字和四则运算，用小步求值避免 eval
        import ast
        node = ast.parse(c, mode="eval")

        def ev(n):
            if isinstance(n, ast.Expression):
                return ev(n.body)
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
                return float(n.value)
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
                v = ev(n.operand)
                return v if isinstance(n.op, ast.UAdd) else -v
            if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult,
                                                              ast.Div)):
                a, b = ev(n.left), ev(n.right)
                if isinstance(n.op, ast.Add):
                    return a + b
                if isinstance(n.op, ast.Sub):
                    return a - b
                if isinstance(n.op, ast.Mult):
                    return a * b
                return a / b if b else None
            return None
        v = ev(node)
        return float(v) if v is not None else None
    except Exception:
        return None


def _numbers(s: str) -> list[float]:
    """抽出答案里的数值序列，能识别分数与四则表达式。

    为什么不能只扫数字：`\\frac{1}{2}` 和 `0.5` 是同一个答案，
    `\\frac{899}{500}` 和 `1.798` 也是。只扫数字会把它们判成不同（见 ai-log B8）。
    """
    t = norm(s)
    parts = re.split(r"[,;、\s]+", t)
    out: list[float] = []
    for p in parts:
        if not p:
            continue
        v = _eval_chunk(p)
        if v is not None:
            out.append(v)
        else:
            # 片段里混着符号（如 "x^2(3"）→ 退回纯数字扫描
            for m in re.finditer(r"[-+]?\d+(?:\.\d+)?", p):
                try:
                    out.append(float(m.group(0)))
                except ValueError:
                    pass
    return out


# ─────────────────────────────────────────────────────────────
# 判定
# ─────────────────────────────────────────────────────────────

def judge(answer, item: dict) -> tuple[str, str]:
    """返回 (verdict, 说明)。verdict ∈ correct/partial/wrong/unsolved/manual。"""
    if answer is None or str(answer).strip() == "":
        return "unsolved", "没有产出答案"

    kind = item.get("kind", "manual")
    expected = item.get("expected", "")
    accept = [str(a) for a in (item.get("accept") or [])]
    reject = [str(r) for r in (item.get("reject") or [])]
    a_norm, e_norm = norm(answer), norm(expected)

    # 先查一票否决（模型答成了常见的错选项）
    for r in reject:
        if norm(r) and norm(r) in a_norm:
            return "wrong", f"命中了错误选项「{r}」"

    if kind == "choice":
        # 选项号：expected 形如 "2) ..." → 找 "2)" 或独立数字 2
        m = re.match(r"\s*([1-9])\s*\)?", expected)
        keys = list(accept)
        if m:
            keys.append(m.group(1))
        for k in keys:
            if norm(k) and norm(k) in a_norm:
                return "correct", f"命中选项「{k}」"
        # 模型直接答文字（"orthogonal" vs "all of the above"）→ 算部分正确
        if e_norm and any(w in a_norm for w in re.findall(r"[a-z]{4,}", e_norm)):
            return "partial", "答出了概念但未给出选项编号"
        # 答案明确选了**另一个**选项（"4) sphere" vs 期望 "2) 45 degrees"）
        # 这种情况是判错，不是「判不了」——否则错误率会被静默藏进 manual 里。
        if re.match(r"\s*[1-9]\s*[).]", str(answer)) or re.match(r"\s*[a-dA-D]\s*[).]", str(answer)):
            return "wrong", f"选择了别的选项（期望 {expected!r}）"
        return "manual", "选项匹配不确定，需人工裁决"

    if kind == "exact":
        if norm_math(answer) == norm_math(expected):
            return "correct", "归一化后完全一致"
        for a in accept:
            if norm_math(a) and norm_math(a) in norm_math(answer):
                return "correct", f"匹配可接受形式「{a}」"
        # 向量 / 矩阵形式的等价表示：
        #   期望 "(2,3,4)"，实得 \begin{pmatrix}2\\3\\4\end{pmatrix} 或 [2,3,4]^T
        # 教材里行向量、列向量、矩阵三种写法都算对，不能因为记号不同判错（见 ai-log B8）。
        ne, na = _numbers(expected), _numbers(answer)
        if ne and len(ne) == len(na) and all(
                abs(x - y) <= 1e-6 * max(1.0, abs(y)) for x, y in zip(na, ne)):
            return "correct", f"分量逐个一致 {ne}"
        if na and ne and len(ne) == 1 and abs(na[0] - ne[0]) < 1e-6 * max(1.0, abs(ne[0])):
            return "correct", f"数值一致（{ne[0]:g}）"
        return "wrong", f"期望 {expected!r}，实得 {str(answer)[:60]!r}"

    if kind == "set":
        ne = _numbers(expected)
        na = _numbers(answer)
        if not ne:
            return "manual", "标准答案里没解析出数值，需人工裁决"
        hit = [any(abs(a - e) <= 1e-6 * max(1.0, abs(e)) for a in na) for e in ne]
        if all(hit):
            return "correct", f"期望数值全部出现 {ne}"
        if any(hit):
            miss = [e for e, h in zip(ne, hit) if not h]
            return "partial", f"命中 {sum(hit)}/{len(ne)}，缺 {miss}"
        return "wrong", f"期望 {ne}，实得 {na}"

    if kind == "contains":
        # 用「只留字母数字」的宽松归一化比对，避开 LaTeX 括号/空格的干扰：
        #   `3 \log{\left(x \right)} + 1` 与 `3 log(x) + 1` 必须视为同一个结论。
        a_loose = _loose(answer)
        for k in [expected] + accept:
            kk = _loose(k)
            if kk and kk in a_loose:
                return "correct", f"包含关键结论「{k}」"
        return "manual", "关键结论未直接命中，需人工读"

    if kind == "choice_set":
        # 一组子题都是选择题：expected 是 {label: 期望}
        return "manual", "choice_set 应由外层逐项展开"

    return "manual", "未指定判定方式，需人工裁决"


JUDGE_WEIGHT = {"correct": 1.0, "partial": 0.5, "wrong": 0.0, "unsolved": 0.0, "manual": None}


# ─────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────

def _index_solutions(solutions: list) -> dict:
    """把 solutions 摊平成 {problem_id: {...}}，子题用 'P1.a' 索引。"""
    idx = {}
    for s in solutions:
        pid = str(s.get("problem_id", "?"))
        idx[pid] = s
        for sub in s.get("sub_solutions") or []:
            idx[f"{pid}.{sub.get('problem_id')}"] = sub
    return idx


def verify(solutions: list, ground_truth: dict, llm_adjudicate=None) -> dict:
    idx = _index_solutions(solutions)
    items_out = []
    for item in ground_truth.get("items", []):
        key = item["id"]
        node = idx.get(key)
        answer = None
        if node:
            answer = node.get("answer_latex") or node.get("answer")
        verdict, why = judge(answer, item)
        if verdict == "manual" and llm_adjudicate is not None:
            adj = llm_adjudicate(item, answer)
            if adj:
                verdict, why = adj[0], "LLM 裁决：" + adj[1]
        items_out.append({
            "id": key, "expected": item.get("expected"),
            "got": (str(answer)[:200] if answer else ""),
            "kind": item.get("kind", "manual"),
            "verdict": verdict, "note": why,
            "solver": (node or {}).get("solver"),
        })

    counted = [i for i in items_out if JUDGE_WEIGHT[i["verdict"]] is not None]
    score = sum(JUDGE_WEIGHT[i["verdict"]] for i in counted)
    by_verdict: dict[str, int] = {}
    for i in items_out:
        by_verdict[i["verdict"]] = by_verdict.get(i["verdict"], 0) + 1

    return {
        "source": ground_truth.get("source", ""),
        "official_solutions": ground_truth.get("official_solutions", ""),
        "items": items_out,
        "summary": {
            "total": len(items_out),
            "auto_judged": len(counted),
            "manual_pending": by_verdict.get("manual", 0),
            "by_verdict": by_verdict,
            # 自动判定部分的加权正确率（partial 记 0.5）
            "auto_accuracy": (score / len(counted)) if counted else None,
            "correct": by_verdict.get("correct", 0),
            "partial": by_verdict.get("partial", 0),
            "wrong": by_verdict.get("wrong", 0),
            "unsolved": by_verdict.get("unsolved", 0),
            # 宽松口径：correct + partial 都算「可接受」
            "lenient_accuracy": ((by_verdict.get("correct", 0) + by_verdict.get("partial", 0))
                                 / len(items_out)) if items_out else None,
        },
    }


def render_markdown(rep: dict) -> str:
    s = rep["summary"]
    lines = [
        f"# 正确性验证报告（自动生成）",
        "",
        f"- 对照来源：{rep['source']}",
        f"- 官方解答：{rep['official_solutions']}",
        f"- 题目条目：{s['total']}",
        "",
        "## 汇总",
        "",
        "| 指标 | 值 |",
        "|---|---|",
        f"| 自动判定条目 | {s['auto_judged']} |",
        f"| 待人工裁决 | {s['manual_pending']} |",
        f"| 完全正确 | {s['correct']} |",
        f"| 部分正确 | {s['partial']} |",
        f"| 错误 | {s['wrong']} |",
        f"| 未解出 | {s['unsolved']} |",
        f"| **自动判定加权正确率** | "
        f"**{s['auto_accuracy']*100:.1f}%** |" if s["auto_accuracy"] is not None else "| 加权正确率 | n/a |",
        f"| 宽松正确率（含部分正确） | "
        f"{(s['lenient_accuracy'] or 0)*100:.1f}% |",
        "",
        "## 逐条明细",
        "",
        "| 条目 | 判定 | 期望 | 实得 | 说明 | 求解器 |",
        "|---|---|---|---|---|---|",
    ]
    icon = {"correct": "✅", "partial": "🟡", "wrong": "❌", "unsolved": "⬜", "manual": "❓"}
    for i in rep["items"]:
        exp = str(i["expected"]).replace("|", "\\|")[:60]
        got = str(i["got"]).replace("|", "\\|")[:60]
        note = str(i["note"]).replace("|", "\\|")[:80]
        lines.append(f"| `{i['id']}` | {icon.get(i['verdict'], '?')} {i['verdict']} | "
                     f"{exp} | {got} | {note} | {i['solver'] or ''} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="正确性验证：解答 vs 标准答案")
    ap.add_argument("solutions", help="3_solutions.json")
    ap.add_argument("ground_truth", help="ground_truth.json")
    ap.add_argument("--out", default=None, help="输出 JSON 报告路径")
    ap.add_argument("--md", default=None, help="同时输出 Markdown 报告")
    ap.add_argument("--llm-adjudicate", action="store_true",
                    help="对 manual 条目调用国产模型二次裁决")
    args = ap.parse_args(argv)

    solutions = json.loads(Path(args.solutions).read_text(encoding="utf-8"))
    gt = json.loads(Path(args.ground_truth).read_text(encoding="utf-8"))

    adj = None
    if args.llm_adjudicate:
        from llm_engine import LLMEngine, ResponseCache
        eng = LLMEngine(cache=ResponseCache())

        def adj(item, answer):
            res = eng.chat(
                "你是阅卷助教。判断学生答案是否与标准答案等价。"
                "只返回 JSON：{\"verdict\":\"correct\"|\"partial\"|\"wrong\"|\"unsolved\","
                "\"reason\":\"一句话\"}\n\n"
                f"题目：{item.get('question','')}\n"
                f"标准答案：{item.get('expected','')}\n"
                f"学生答案：{answer}\n")
            if not res.ok or not res.data:
                return None
            v = str(res.data.get("verdict", "")).lower()
            if v in JUDGE_WEIGHT:
                return (v, str(res.data.get("reason", "")))
            return None

    rep = verify(solutions, gt, llm_adjudicate=adj)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(rep, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text(render_markdown(rep), encoding="utf-8")

    s = rep["summary"]
    print(f"[验证] {rep['source']}")
    print(f"  条目 {s['total']}｜自动判定 {s['auto_judged']}｜待人工 {s['manual_pending']}")
    print(f"  正确 {s['correct']}／部分 {s['partial']}／错误 {s['wrong']}／未解 {s['unsolved']}")
    if s["auto_accuracy"] is not None:
        print(f"  自动判定加权正确率：{s['auto_accuracy']*100:.1f}%")
    print(f"  宽松正确率（含部分）：{(s['lenient_accuracy'] or 0)*100:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
