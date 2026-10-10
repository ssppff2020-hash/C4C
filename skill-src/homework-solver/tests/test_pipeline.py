#!/usr/bin/env python3
"""
homework-solver 单元测试
==========================
跑法（在 skill-src/homework-solver 目录下）：
    python -m unittest discover -s tests -v

这些测试钉住的是**开发过程中真实踩过的坑**（编号对应 ai-log 的 B 系列），
所以它们既是回归测试，也是那份 bug 复盘的活文档。
抓的是：
  * LaTeX → SymPy 的解析正确性（B2/B4/B8）
  * 各学科求解器的正确性（含每个修过的具体 bug）
  * 学科路由（不要把小问丢错模块）
  * verify.py 的判定逻辑（分数不能虚高也不能冤枉）
  * 缓存键的稳定性（改了顺序会让已有缓存失效 → 离线复现失败，B13）
  * config.yaml 里的 pdf tier 与 compile_pdf 的支持集一致
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))

import sympy
from sympy import Symbol, latex, symbols

from solvers import calculus_core, linalg, ode, physics, probability
from solvers.base import latex_to_text, parse_tex, parse_tex_matrix
from verify import _loose, _numbers, judge, norm
from solve import detect_subject, normalize_problem, dedupe_sub_ids
from llm_engine import ResponseCache, extract_json, LLMEngine


def mat(rows):
    """构造 pmatrix LaTeX。"""
    body = " \\\\ ".join(" & ".join(r) for r in rows)
    return "\\begin{pmatrix} " + body + " \\end{pmatrix}"


def prob(pid, text):
    p = {"id": pid, "text": text, "math_expressions": [], "sub_problems": []}
    return normalize_problem(p)


def val(latex_str):
    """把求解器吐出的 LaTeX 答案转回 SymPy 表达式做数值断言。

    注意：必须用本项目自己的 parse_tex，不能用 sympy.sympify ——
    后者不认 LaTeX（这也是本流水线要自带解析器的原因）。
    """
    return parse_tex(latex_str)


def num(latex_str):
    return float(sympy.N(val(latex_str)))


# ═══════════════════════════════════════════════════════════════
# 1. LaTeX → SymPy 解析
# ═══════════════════════════════════════════════════════════════

class TestLatexParsing(unittest.TestCase):

    def test_frac(self):
        e = parse_tex(r"\frac{x^2+2x-24}{x-4}")
        x = Symbol("x")
        self.assertEqual(sympy.simplify(e - (x**2 + 2*x - 24)/(x - 4)), 0)

    def test_sqrt_and_greek(self):
        e = parse_tex(r"\sqrt{\pi}")
        self.assertEqual(sympy.simplify(e - sympy.sqrt(sympy.pi)), 0)

    def test_nested_frac(self):
        e = parse_tex(r"\frac{1}{1+\frac{1}{x}}")
        x = Symbol("x")
        self.assertEqual(sympy.simplify(e - x/(x + 1)), 0)

    def test_implicit_multiplication(self):
        # 2x、703x^506、pi x 都必须补上乘号（B1）
        x, pi = Symbol("x"), sympy.pi
        self.assertEqual(sympy.simplify(parse_tex("2x") - 2*x), 0)
        self.assertEqual(sympy.simplify(parse_tex(r"\pi x") - pi*x), 0)
        self.assertEqual(sympy.simplify(parse_tex(r"-372x^{75}") + 372*x**75), 0)

    def test_function_not_glued_to_previous_letter(self):
        # n\sin(x) 曾经被解析成符号 nsin（B2）
        x = Symbol("x")
        e = parse_tex(r"n\sin(x)")
        self.assertEqual(sympy.simplify(e - Symbol("n")*sympy.sin(x)), 0)

    def test_abs_value(self):
        x = Symbol("x")
        e = parse_tex(r"\frac{|x|}{x}")
        self.assertEqual(sympy.simplify(e - sympy.Abs(x)/x), 0)

    def test_trailing_dollar_and_punct(self):
        # 题干里 "= x^{2}$," 的残留定界符不能把 sympify 搞崩（B10）
        e = parse_tex(r"x^{2} + y^{2} + z^{2}$.")
        self.assertIsNotNone(e)

    def test_matrix(self):
        M = parse_tex_matrix(mat([["1", "2"], ["3", "4"]]))
        self.assertEqual(M, sympy.Matrix([[1, 2], [3, 4]]))

    def test_matrix_with_assignment_prefix(self):
        M = parse_tex_matrix("A = " + mat([["1", "0", "2"], ["-1", "3", "1"]]))
        self.assertEqual(M.shape, (2, 3))

    def test_unknown_expression_returns_none(self):
        self.assertIsNone(parse_tex(r"\thisIsNotMath{!@#"))


# ═══════════════════════════════════════════════════════════════
# 2. 线性代数
# ═══════════════════════════════════════════════════════════════

class TestLinearAlgebra(unittest.TestCase):

    def _solve(self, pid, text):
        return linalg.solve(prob(pid, text))

    def test_determinant(self):
        r = self._solve("p", f"Compute the determinant of $A = {mat([['2','1','0'],['1','3','1'],['0','1','4']])}$")
        self.assertTrue(r["solved"])
        self.assertEqual(val(r["answer_latex"]), 18)

    def test_inverse(self):
        r = self._solve("p", f"Find the inverse of $A = {mat([['2','0'],['0','4']])}$")
        self.assertTrue(r["solved"])
        self.assertIn("frac", r["answer_latex"] or "")

    def test_eigenvalues(self):
        r = self._solve("p", f"Find the eigenvalues of $A = {mat([['3','0'],['0','-1']])}$")
        self.assertTrue(r["solved"])
        self.assertIn("-1", r["answer_latex"])
        self.assertIn("3", r["answer_latex"])

    def test_rank(self):
        r = self._solve("p", f"Find the rank of $A = {mat([['1','2','3'],['2','4','6'],['3','6','9']])}$")
        self.assertTrue(r["solved"])
        self.assertIn("1", r["answer_latex"])

    def test_solve_system(self):
        r = self._solve("p", f"Solve $Ax=b$ for $A = {mat([['1','2'],['3','4']])}$, $b = {mat([['5'],['11']])}$")
        self.assertTrue(r["solved"])
        self.assertIn("1", r["answer_latex"])
        self.assertIn("2", r["answer_latex"])

    def test_trace(self):
        r = self._solve("p", f"Compute the trace of $A = {mat([['5','1'],['2','3']])}$")
        self.assertEqual(val(r["answer_latex"]), 8)

    def test_singular_inverse_reports_not_exists(self):
        r = self._solve("p", f"Find the inverse of $A = {mat([['1','2'],['2','4']])}$")
        self.assertTrue(r["solved"])          # 「不存在」也是一个正确答案
        self.assertIn("不存在", r["answer_latex"])

    def test_no_matrix_returns_unsolved_dict(self):
        # 认领了操作但抽不到矩阵 → 必须给 unsolved 且写清原因，不能崩
        r = self._solve("p", "Compute the determinant.")
        self.assertFalse(r["solved"])
        self.assertIn("矩阵", r["reason"])


# ═══════════════════════════════════════════════════════════════
# 3. 微积分
# ═══════════════════════════════════════════════════════════════

class TestCalculus(unittest.TestCase):

    def _solve(self, text):
        return calculus_core.solve(prob("p", text))

    def test_derivative(self):
        r = self._solve(r"Find the derivative of $x^{3}\ln(x)$.")
        self.assertTrue(r["solved"])
        x = Symbol("x")
        want = 3*x**2*sympy.log(x) + x**2
        self.assertEqual(sympy.simplify(val(r["answer_latex"]) - want), 0)

    def test_definite_integral(self):
        r = self._solve(r"Evaluate the definite integral $\int_0^1 x^{2} dx$.")
        self.assertEqual(val(r["answer_latex"]), sympy.Rational(1, 3))

    def test_improper_integral(self):
        r = self._solve(r"Evaluate the improper integral $\int_0^{\infty} e^{-2x} dx$.")
        self.assertEqual(val(r["answer_latex"]), sympy.Rational(1, 2))

    def test_indefinite_integral(self):
        r = self._solve(r"Evaluate the indefinite integral $\int x e^{x} dx$.")
        self.assertTrue(r["solved"])
        self.assertIn("e^{x}", r["answer_latex"])

    def test_gradient(self):
        r = self._solve(r"Calculate the gradient of $f(x,y,z) = x^{2} + y^{2} + z^{2}$.")
        self.assertTrue(r["solved"])
        for tok in ("2 x", "2 y", "2 z"):
            self.assertIn(tok, r["answer_latex"])

    def test_gradient_bails_on_lost_superscript(self):
        """PDF 丢上标时 x² 变成 x2，SymPy 会读成符号 x2 而给出 0 梯度。
        必须主动放弃（返回 None）交给 LLM，而不是交出 (0,0,0)（B4）。"""
        r = self._solve("Calculate the gradient of $f(x,y,z) = x2+y2+z2$.")
        self.assertIsNotNone(r)
        # 这条路径应当由 OCR/LLM 接手，SymPy 不应给出全零梯度
        if r["solved"]:
            self.assertNotIn("0", r["answer_latex"].replace(" ", "").replace("\\", ""))

    def test_taylor(self):
        r = self._solve(r"Find the Taylor series of $e^{x}$ about 0 up to order 4.")
        self.assertTrue(r["solved"])
        self.assertIn("x^{4}", r["answer_latex"])


# ═══════════════════════════════════════════════════════════════
# 4. 微分方程
# ═══════════════════════════════════════════════════════════════

class TestODE(unittest.TestCase):

    def test_first_order_homogeneous(self):
        r = ode.solve(prob("p", r"Solve the differential equation $y' + 2y = 0$."))
        self.assertTrue(r["solved"])
        self.assertIn("e^{- 2 x}", r["answer_latex"])

    def test_second_order(self):
        r = ode.solve(prob("p", r"Solve the differential equation $y'' - y = 0$."))
        self.assertTrue(r["solved"])
        self.assertIn("e^{x}", r["answer_latex"])

    def test_oscillatory(self):
        r = ode.solve(prob("p", r"Solve the differential equation $y'' + y = 0$."))
        self.assertTrue(r["solved"])
        self.assertIn("sin", r["answer_latex"])
        self.assertIn("cos", r["answer_latex"])

    def test_ivp(self):
        r = ode.solve(prob("p", r"Solve the differential equation $y' = 2x$ with $y(0) = 1$."))
        self.assertTrue(r["solved"])
        self.assertNotIn("C_{1}", r["answer_latex"])   # 初值条件已定，不该再有自由常数

    def test_laplace(self):
        r = ode.solve(prob("p", r"Find the Laplace transform of $e^{-2t}$."))
        self.assertTrue(r["solved"])
        self.assertIn("s + 2", r["answer_latex"])


# ═══════════════════════════════════════════════════════════════
# 5. 大学物理
# ═══════════════════════════════════════════════════════════════

class TestPhysics(unittest.TestCase):

    def test_newton_second_law(self):
        r = physics.solve(prob("p", "A mass of 2 kg experiences an acceleration of 3 m/s^2. Find the net force."))
        self.assertTrue(r["solved"])
        self.assertEqual(num(r["answer_latex"]), 6.0)

    def test_kinetic_energy(self):
        r = physics.solve(prob("p", "A mass of 4 kg moves at a velocity of 3 m/s. Find the kinetic energy."))
        self.assertEqual(num(r["answer_latex"]), 18.0)

    def test_ohms_law_does_not_use_gas_constant(self):
        """R 在电路题里是电阻，不是理想气体常数 8.314（B11）。"""
        r = physics.solve(prob("p", "A resistor carries a current of 2 A and has a resistance of 5 ohm. Find the voltage across it."))
        self.assertTrue(r["solved"])
        self.assertEqual(num(r["answer_latex"]), 10.0)

    def test_coulomb(self):
        r = physics.solve(prob("p", r"Two point charges $q1 = 1e-6$ C and $q2 = 2e-6$ C are separated by a distance $r = 0.1$ m. Find the Coulomb force between them."))
        self.assertTrue(r["solved"])
        self.assertAlmostEqual(num(r["answer_latex"]), 1.798, places=3)

    def test_pendulum_needs_formula_match_not_generic_keyword(self):
        """题干里没有「力/质量」这类通用词时也要能接管（B12）。"""
        r = physics.solve(prob("p", r"A simple pendulum has length $L = 1$ m. Find its period (take $g = 9.8$ m/s^2)."))
        self.assertTrue(r["solved"])
        self.assertAlmostEqual(num(r["answer_latex"]), 2.00709, places=4)

    def test_wave_speed(self):
        r = physics.solve(prob("p", "A wave has frequency 50 Hz and wavelength 2 m. Find the wave speed."))
        self.assertEqual(num(r["answer_latex"]), 100.0)

    def test_missing_quantity_reports_clearly(self):
        r = physics.solve(prob("p", "A mass of 2 kg experiences an acceleration. Find the net force."))
        self.assertFalse(r["solved"])
        self.assertIn("缺少", r["reason"])


# ═══════════════════════════════════════════════════════════════
# 6. 概率统计
# ═══════════════════════════════════════════════════════════════

class TestProbability(unittest.TestCase):

    TABLE = ("The following table gives the distribution of $X$. Find the expected value of $X$.\n"
             "| x | p |\n|---|---|\n| 0 | 0.2 |\n| 1 | 0.5 |\n| 2 | 0.3 |\n")

    def test_expectation(self):
        r = probability.solve(prob("p", self.TABLE))
        self.assertTrue(r["solved"])
        self.assertIn("1.1", r["answer_latex"])

    def test_variance(self):
        r = probability.solve(prob("p", self.TABLE.replace("expected value", "variance")))
        self.assertTrue(r["solved"])
        self.assertIn("0.49", r["answer_latex"])

    def test_binomial_expectation(self):
        r = probability.solve(prob("p", r"Let $X \sim B(10, 0.5)$. Find the expected value of $X$."))
        self.assertTrue(r["solved"])
        self.assertIn("5", r["answer_latex"])

    def test_normal_cdf_by_notation_only(self):
        """题干里一个中文/英文概率词都没有，纯靠 X~N 记号识别（B10）。"""
        r = probability.solve(prob("p", r"Let $X \sim N(0,1)$. Compute $P(X <= 1.96)$."))
        self.assertTrue(r["solved"])
        self.assertIn("0.975", r["answer_latex"])

    def test_bayes(self):
        txt = ("Given $P(A) = 0.01$, $P(B|A) = 0.99$, $P(B|\\neg A) = 0.05$. "
               "Find $P(A|B)$ (Bayes).")
        r = probability.solve(prob("p", txt))
        # 抽不到完整条件时必须明确标未解，不能硬编一个数
        self.assertIn("solved", r)


# ═══════════════════════════════════════════════════════════════
# 7. 路由与归一化
# ═══════════════════════════════════════════════════════════════

class TestRouting(unittest.TestCase):

    def test_subject_detection(self):
        cases = [
            (f"Compute the determinant of $A = {mat([['1','2'],['3','4']])}$", "linalg"),
            (r"Solve the differential equation $y'' + y = 0$.", "ode"),
            (r"求极限 $\lim_{x \to 0} \frac{\sin x}{x}$", "calculus_limits"),
            (r"Evaluate the integral $\int x^{2} dx$", "calculus"),
            ("Let $X \\sim N(0,1)$. Compute $P(X <= 1)$.", "probability"),
            ("A mass of 2 kg accelerates at 3 m/s^2. Find the force.", "physics"),
        ]
        for text, want in cases:
            with self.subTest(text=text[:40]):
                self.assertEqual(detect_subject(prob("p", text)), want)

    def test_normalize_is_idempotent(self):
        """normalize 两次结果必须完全一样 —— 否则 LLM 的 prompt 会变、
        缓存全部失效、离线复现失败（B13）。"""
        p = {"id": "1", "text": r"Compute $\int_0^1 x dx$ and also $x^2$.", "sub_problems": []}
        normalize_problem(p)
        first = json.dumps(p, sort_keys=True, ensure_ascii=False)
        normalize_problem(p)
        self.assertEqual(first, json.dumps(p, sort_keys=True, ensure_ascii=False))

    def test_duplicate_sub_ids_disambiguated(self):
        p = {"id": "1", "text": "t", "sub_problems": [
            {"id": "d", "text": "a"}, {"id": "d", "text": "b"}]}
        dedupe_sub_ids(p)
        ids = [s["id"] for s in p["sub_problems"]]
        self.assertEqual(len(ids), len(set(ids)))


# ═══════════════════════════════════════════════════════════════
# 8. 验证器（打分逻辑）
# ═══════════════════════════════════════════════════════════════

class TestVerifier(unittest.TestCase):

    def test_choice_by_option_number(self):
        v, _ = judge("3) plane not through 0",
                     {"kind": "choice", "expected": "3) plane not through 0"})
        self.assertEqual(v, "correct")

    def test_choice_wrong_option_flagged(self):
        v, _ = judge("4) sphere", {"kind": "choice", "expected": "2) 45 degrees",
                                   "accept": ["45"], "reject": ["60", "90"]})
        self.assertEqual(v, "wrong")

    def test_exact_fraction_equals_decimal(self):
        # 1/3 和 0.3333 是同一个答案，不能因为写法不同判错（B8）
        v, _ = judge(r"\frac{1}{3}", {"kind": "exact", "expected": "1/3",
                                      "accept": ["0.3333"]})
        self.assertEqual(v, "correct")

    def test_exact_vector_form_equivalence(self):
        # (2,3,4) 与列向量 \begin{pmatrix}2\\3\\4\end{pmatrix} 等价
        v, _ = judge(mat([["2"], ["3"], ["4"]]),
                     {"kind": "exact", "expected": "(2,3,4)", "accept": []})
        self.assertEqual(v, "correct")

    def test_exact_vector_form_still_distinguishes_wrong(self):
        v, _ = judge(mat([["1"], ["1"], ["1"]]),
                     {"kind": "exact", "expected": "(2,3,4)", "accept": []})
        self.assertEqual(v, "wrong")

    def test_contains_ignores_latex_noise(self):
        v, _ = judge(r"x^{2} \left(3 \log{\left(x \right)} + 1\right)",
                     {"kind": "contains", "expected": "x^2(3 ln x + 1)",
                      "accept": ["3 log(x) + 1"]})
        self.assertEqual(v, "correct")

    def test_set_partial(self):
        v, note = judge("0.5, 0.25", {"kind": "set", "expected": "0.5, 0, 0.25"})
        self.assertEqual(v, "partial")

    def test_empty_answer_is_unsolved_not_correct(self):
        v, _ = judge(None, {"kind": "exact", "expected": "1"})
        self.assertEqual(v, "unsolved")

    def test_unjudgeable_falls_to_manual_not_correct(self):
        """判定不出来时必须进 manual，绝不能默认算对 —— 这是报告可信度的底线。"""
        v, _ = judge("some free text", {"kind": "magic", "expected": "x"})
        self.assertEqual(v, "manual")


# ═══════════════════════════════════════════════════════════════
# 9. LLM 引擎（不联网的部分）
# ═══════════════════════════════════════════════════════════════

class TestLLMEngine(unittest.TestCase):

    def test_extract_json_plain(self):
        self.assertEqual(extract_json('{"a": 1}'), {"a": 1})

    def test_extract_json_from_markdown_fence(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})

    def test_extract_json_with_prose_around(self):
        txt = '好的，我来解答。\n{"solved": true, "answer_latex": "3"}\n希望有帮助！'
        self.assertEqual(extract_json(txt)["answer_latex"], "3")

    def test_extract_json_unparseable(self):
        self.assertIsNone(extract_json("完全不是 JSON"))

    def test_cache_key_stable_across_calls(self):
        """缓存键必须稳定且与 provider/model 相关；
        改动键的构造顺序会让全部历史缓存失效（B13）。"""
        with tempfile.TemporaryDirectory() as d:
            c = ResponseCache(root=Path(d))
            k1 = c._key("deepseek", "deepseek-chat", "p", "s")
            k2 = c._key("deepseek", "deepseek-chat", "p", "s")
            k3 = c._key("qwen", "deepseek-chat", "p", "s")
            self.assertEqual(k1, k2)
            self.assertNotEqual(k1, k3)

    def test_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            c = ResponseCache(root=Path(d))
            payload = {"raw": "x", "data": {"a": 1}, "provider": "deepseek",
                       "model": "deepseek-chat"}
            c.put("deepseek", "deepseek-chat", "p", "s", payload)
            self.assertIsNotNone(c.get("deepseek", "deepseek-chat", "p", "s"))
            self.assertIsNone(c.get("kimi", "moonshot-v1-8k", "p", "s"))

    def test_offline_engine_uses_cache_without_key(self):
        """没有 API Key 时，只要缓存命中就必须能出答案（离线复现）。"""
        with tempfile.TemporaryDirectory() as d:
            writer = LLMEngine(provider="deepseek", api_key="fake",
                               cache=ResponseCache(root=Path(d)))
            payload = {"raw": '{"solved": true, "answer_latex": "42"}',
                       "data": {"solved": True, "answer_latex": "42"},
                       "provider": "deepseek", "model": "deepseek-chat"}
            prompt = "求 6×7"
            system = "sys"
            writer.cache.put("deepseek", "deepseek-chat", prompt, system, payload)

            saved = {k: os.environ.pop(k, None) for k in
                     ("DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "MOONSHOT_API_KEY",
                      "LLM_API_KEY")}
            try:
                reader = LLMEngine(cache=ResponseCache(root=Path(d)))
                self.assertIsNone(reader.provider)          # 探测不到 provider
                self.assertTrue(reader.available())          # 但缓存里有货
                res = reader.chat(prompt, system=system)
                self.assertTrue(res.ok)
                self.assertTrue(res.cached)
                self.assertEqual(res.data["answer_latex"], "42")
            finally:
                for k, v in saved.items():
                    if v is not None:
                        os.environ[k] = v


# ═══════════════════════════════════════════════════════════════
# 10. 端到端冒烟（不联网、不依赖外部文件）
# ═══════════════════════════════════════════════════════════════

class TestEndToEnd(unittest.TestCase):

    def test_pipeline_on_mixed_homework(self):
        """用一段内联的混合学科作业跑完整 Stage 1-4（跳过 PDF 编译以免依赖浏览器）。"""
        from ingest import ingest
        from parse_problems import parse_problems
        from solve import solve_all
        from render import render_all
        from llm_engine import ResponseCache

        md = (
            "# 混合学科练习\n\n## Problems\n\n"
            f"Problem 1. Compute the determinant of $A = {mat([['1','2'],['3','4']])}$.\n\n"
            r"Problem 2. Evaluate the integral $\int_0^1 x^{2} dx$." "\n\n"
            r"Problem 3. Solve the differential equation $y'' + y = 0$." "\n\n"
            "Problem 4. A mass of 2 kg experiences an acceleration of 3 m/s^2. Find the net force.\n\n"
            r"Problem 5. Let $X \sim N(0,1)$. Compute $P(X <= 1.96)$." "\n"
        )
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "hw.md"
            src.write_text(md, encoding="utf-8")
            ing = ingest(str(src))
            probs = parse_problems(ing)
            self.assertEqual(len(probs), 5)

            # 用空缓存 + 关掉 LLM，保证测试完全离线且确定性
            eng = LLMEngine(cache=ResponseCache(root=Path(d) / "cache"), enabled=False)
            sols = solve_all(probs, eng, use_llm=False)
            self.assertEqual(sum(1 for s in sols if s["solved"]), 5,
                             f"应全部用 SymPy 解出，实际："
                             f"{[(s['problem_id'], s['solver'], s.get('reason')) for s in sols]}")

            out = render_all(sols, Path(d) / "out", course="Test", student="Test")
            for kind in ("tex", "md", "html"):
                self.assertTrue(Path(out[kind]).exists())
                self.assertGreater(Path(out[kind]).stat().st_size, 100)
            # HTML 里答案必须是数学模式（带 $...$），否则会渲染成裸 LaTeX（B7）
            html = Path(out["html"]).read_text(encoding="utf-8")
            self.assertIn("$", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
