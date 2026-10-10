#!/usr/bin/env python3
"""
一键流水线：作业文件 → 可提交 PDF（Stage 1-5 串联）
====================================================
对比 starter kit 的 pipeline.py，这里多了：

    * PDF / Word 输入（starter 的三个 handler 是 NotImplementedError）
    * 混合求解路由（SymPy × 5 学科 + 国产大模型）
    * 三级 PDF 降级（没装 LaTeX 也能出 PDF）
    * 产物自检（页数 / 文本层 / 求解率）写进 summary.json，供验证报告引用
    * `--explain` 打印每道题走了哪条路径

用法:
    python pipeline.py <输入文件> <输出目录> [选项]

示例:
    python pipeline.py homework.pdf out/ --course "线性代数" --student "宋鹏飞"
    python pipeline.py hw.md out/ --no-llm --tier browser
    python pipeline.py mit_pset1.pdf out/ --explain --verify
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compile_pdf import compile_pdf, find_browser, find_latex_engine
from ingest import ingest
from llm_engine import LLMEngine, ResponseCache
from parse_problems import parse_problems
from render import render_all
from solve import detect_subject, normalize_problem, solve_all, summarize


def load_config(path: str | None) -> dict:
    if not path:
        # 默认找 skill 根目录的 config.yaml
        default = Path(__file__).resolve().parent.parent / "config.yaml"
        path = str(default) if default.exists() else None
    if not path or not Path(path).exists():
        return {}
    try:
        import yaml  # type: ignore
        return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def run_pipeline(input_path: str, out_dir: str, *, course="", student="", title="",
                 use_llm=True, verify_with_llm=False, min_confidence=0.4,
                 provider=None, model=None, use_cache=True, tier="auto",
                 basename="homework", explain=False, date_str=None,
                 embed_mathjax=True, verbose=False) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    print("=" * 66)
    print("🚀 C4C 作业自动求解流水线")
    print(f"   输入: {input_path}")
    print(f"   输出: {out_dir}")
    print(f"   引擎: {LLMEngine(provider=provider, model=model, cache=ResponseCache(enabled=use_cache)).describe()}")
    print(f"   PDF : tier={tier}（latex={'✓' if find_latex_engine() else '✗'}, "
          f"browser={'✓' if find_browser() else '✗'}）")
    print("=" * 66)

    result: dict = {"input": str(input_path), "output_dir": str(out_dir),
                    "started": time.strftime("%Y-%m-%dT%H:%M:%S")}

    # ── Stage 1 ──
    print("\n📄 Stage 1: 文档摄入")
    try:
        ingested = ingest(input_path)
    except NotImplementedError as e:
        print(f"   ❌ {e}")
        result["error"] = str(e)
        return result
    (out_dir / "1_ingested.json").write_text(
        json.dumps(ingested, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   ✅ {ingested['format']} / {ingested['handler']} / "
          f"{ingested['char_count']:,} 字符 / {len(ingested['sections'])} 段")
    result["stage1"] = {"format": ingested["format"], "handler": ingested["handler"],
                        "chars": ingested["char_count"], "sections": len(ingested["sections"])}

    # ── Stage 2 ──
    print("\n🔍 Stage 2: 题目解析")
    problems = parse_problems(ingested)
    (out_dir / "2_parsed.json").write_text(
        json.dumps(problems, ensure_ascii=False, indent=2), encoding="utf-8")
    if not problems:
        print("   ⚠️ 未识别到题目。支持的题号格式：'Problem N' / '题 N' / 'N.' / 'N)' / 'Q.N'")
    subj_dist: dict[str, int] = {}
    for p in problems:
        s = detect_subject(normalize_problem(p))
        subj_dist[s] = subj_dist.get(s, 0) + 1
    print(f"   ✅ {len(problems)} 道题")
    print(f"      学科分布: " + ", ".join(f"{k}×{v}" for k, v in sorted(subj_dist.items())))
    result["stage2"] = {"problems": len(problems), "subjects": subj_dist}

    if not problems:
        result["error"] = "no problems parsed"
        return result

    # ── Stage 3 ──
    print("\n🧮 Stage 3: 自动求解（SymPy × 5 学科 + 国产大模型）")
    engine = LLMEngine(provider=provider, model=model,
                       cache=ResponseCache(enabled=use_cache), enabled=use_llm,
                       verbose=verbose)
    solutions = solve_all(problems, engine, use_llm=use_llm,
                          verify_with_llm=verify_with_llm,
                          min_confidence=min_confidence, verbose=verbose)
    (out_dir / "3_solutions.json").write_text(
        json.dumps(solutions, ensure_ascii=False, indent=2), encoding="utf-8")

    summ = summarize(solutions)
    print(f"   ✅ 已解 {summ['solved']}/{summ['total']} ({summ['rate']*100:.1f}%)")
    for k, v in sorted(summ["by_solver"].items(), key=lambda kv: -kv[1]):
        print(f"        {k:<30} {v}")
    if explain:
        print("   ── 逐题路径 ──")
        for s in solutions:
            mk = "✅" if s.get("solved") else "❌"
            info = str(s.get("answer_latex") or s.get("reason") or "")[:58]
            print(f"      {mk} {str(s['problem_id']):<10} [{str(s.get('solver')):<26}] {info}")
    result["stage3"] = summ

    # ── Stage 4 ──
    print("\n📝 Stage 4: 排版渲染（LaTeX + Markdown + HTML）")
    produced = render_all(solutions, out_dir, course=course, student=student,
                          title=title, date_str=date_str, basename=basename,
                          embed_mathjax=embed_mathjax)
    for k, v in produced.items():
        print(f"   ✅ {k:<5} {Path(v).name}")
    result["stage4"] = {k: str(v) for k, v in produced.items()}

    # ── Stage 5 ──
    print("\n📑 Stage 5: 编译与验证")
    comp = compile_pdf(out_dir, basename=basename, tier=tier, solutions=solutions,
                       course=course, student=student, title=title, date_str=date_str)
    for at in comp["attempts"]:
        print(f"   {'✅' if at['ok'] else '❌'} {at['tier']:<10} {at['message']}")
    if comp["ok"]:
        v = comp["validation"]
        print(f"   → {Path(comp['pdf']).name}  "
              f"{v.get('pages')} 页 / {v.get('size', 0):,} B / 文本层 {v.get('text_chars')} 字符")
    result["stage5"] = {k: comp[k] for k in ("ok", "tier", "engine", "pdf", "validation")}

    # ── 汇总 ──
    result["elapsed"] = round(time.time() - t_start, 1)
    result["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (out_dir / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 66)
    print(f"📊 完成  耗时 {result['elapsed']}s   "
          f"求解率 {summ['rate']*100:.1f}%   PDF={'✅' if comp['ok'] else '❌'}"
          f"（{comp['tier']}）")
    print(f"   产物目录: {out_dir}")
    print("=" * 66)
    return result


def main(argv=None):
    cfg = load_config(None)
    ap = argparse.ArgumentParser(description="C4C 作业自动求解流水线")
    ap.add_argument("input", help="输入文件 (md/txt/pdf/docx/图片)")
    ap.add_argument("out_dir", help="输出目录")
    ap.add_argument("--course", default=cfg.get("course", "Mathematics"))
    ap.add_argument("--student", default=cfg.get("student", "Student"))
    ap.add_argument("--title", default=cfg.get("title", "Homework Solutions"))
    ap.add_argument("--date", default=None)
    ap.add_argument("--basename", default="homework")
    ap.add_argument("--no-llm", action="store_true", help="禁用国产大模型（纯 SymPy）")
    ap.add_argument("--provider", default=None, choices=[None, "deepseek", "qwen", "kimi",
                                                         "openai-compatible"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--verify", action="store_true", help="LLM 答案二次自检")
    ap.add_argument("--min-confidence", type=float, default=0.4)
    ap.add_argument("--no-cache", action="store_true", help="不读响应缓存（会重新调用 API）")
    ap.add_argument("--tier", default="auto", choices=["auto", "latex", "browser", "reportlab"])
    ap.add_argument("--explain", action="store_true", help="打印逐题求解路径")
    ap.add_argument("--no-embed-mathjax", action="store_true",
                    help="HTML 不内联 MathJax（默认内联，便于单文件分发）")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    if not Path(args.input).exists():
        print(f"错误: 输入文件不存在 — {args.input}")
        return 1

    r = run_pipeline(
        args.input, args.out_dir, course=args.course, student=args.student,
        title=args.title, use_llm=not args.no_llm, verify_with_llm=args.verify,
        min_confidence=args.min_confidence, provider=args.provider, model=args.model,
        use_cache=not args.no_cache, tier=args.tier, basename=args.basename,
        explain=args.explain, date_str=args.date, verbose=args.verbose,
        embed_mathjax=not args.no_embed_mathjax,
    )
    return 0 if r.get("stage5", {}).get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
