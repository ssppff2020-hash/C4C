# 正确性验证报告（自动生成）

- 对照来源：C4C Domain Benchmark — 5 subjects (linear algebra / calculus / ODE / physics / probability)
- 官方解答：由 SymPy 独立复算 + 教材标准结果双重确认（见 README「结果复现」一节）
- 题目条目：31

## 汇总

| 指标 | 值 |
|---|---|
| 自动判定条目 | 31 |
| 待人工裁决 | 0 |
| 完全正确 | 31 |
| 部分正确 | 0 |
| 错误 | 0 |
| 未解出 | 0 |
| **自动判定加权正确率** | **100.0%** |
| 宽松正确率（含部分正确） | 100.0% |

## 逐条明细

| 条目 | 判定 | 期望 | 实得 | 说明 | 求解器 |
|---|---|---|---|---|---|
| `P1` | ✅ correct | 18 | 18 | 归一化后完全一致 | sympy.linalg |
| `P2` | ✅ correct | [0.5, 0, 0, 0.25] | \left[\begin{matrix}\frac{1}{2} & 0\\0 & \frac{1}{4}\end{mat | 期望数值全部出现 [0.5, 0.0, 0.0, 0.25] | sympy.linalg |
| `P3` | ✅ correct | -1 and 3 | \lambda = -1,\ 3 | 期望数值全部出现 [-1.0, 3.0] | sympy.linalg |
| `P4` | ✅ correct | 1 | \operatorname{rank}(A) = 1 | 分量逐个一致 [1.0] | sympy.linalg |
| `P5` | ✅ correct | x = (1, 2) | x = \begin{pmatrix}1\\2\end{pmatrix} | 期望数值全部出现 [1.0, 2.0] | sympy.linalg |
| `P6` | ✅ correct | 8 | 8 | 归一化后完全一致 | sympy.linalg |
| `P7` | ✅ correct | -1 and 1 | \lambda = -1,\ 1 | 期望数值全部出现 [-1.0, 1.0] | sympy.linalg |
| `P8` | ✅ correct | 6 | 6 | 归一化后完全一致 | sympy.linalg |
| `P9` | ✅ correct | (x-1)e^x + C | C + \left(x - 1\right) e^{x} | 包含关键结论「x - 1」 | sympy.calculus |
| `P10` | ✅ correct | 1/3 | \frac{1}{3} | 分量逐个一致 [0.3333333333333333] | sympy.calculus |
| `P11` | ✅ correct | x^2(3 ln x + 1) | x^{2} \left(3 \log{\left(x \right)} + 1\right) | 包含关键结论「3 log(x) + 1」 | sympy.calculus |
| `P12` | ✅ correct | 1/2 | \frac{1}{2} | 分量逐个一致 [0.5] | sympy.calculus |
| `P13` | ✅ correct | 1 + x + x^2/2 + x^3/6 + x^4/24 | \frac{x^{5}}{120} + \frac{x^{4}}{24} + \frac{x^{3}}{6} + \fr | 包含关键结论「x^{5}/120」 | sympy.calculus |
| `P14` | ✅ correct | (2x, 2y, 2z) | \left[\begin{matrix}2 x\\2 y\\2 z\end{matrix}\right] | 期望数值全部出现 [2.0, 2.0, 2.0] | sympy.calculus |
| `P15` | ✅ correct | atan(x) + C | C + \operatorname{atan}{\left(x \right)} | 包含关键结论「atan」 | sympy.calculus |
| `P16` | ✅ correct | y = C e^x | C_{1} e^{x} | 包含关键结论「e^{x}」 | sympy.ode |
| `P17` | ✅ correct | y = C e^{-2x} | C_{1} e^{- 2 x} | 包含关键结论「e^{- 2 x}」 | sympy.ode |
| `P18` | ✅ correct | y = C1 e^x + C2 e^{-x} | C_{1} e^{- x} + C_{2} e^{x} | 包含关键结论「e^{x}」 | sympy.ode |
| `P19` | ✅ correct | y = C1 cos x + C2 sin x | C_{1} \sin{\left(x \right)} + C_{2} \cos{\left(x \right)} | 包含关键结论「sin」 | sympy.ode |
| `P20` | ✅ correct | y = x^2 + 1 | x^{2} + 1 | 包含关键结论「x^{2} + 1」 | sympy.ode |
| `P21` | ✅ correct | 1/(s+2) | \frac{1}{s + 2} | 分量逐个一致 [1.0, 2.0] | sympy.ode |
| `P22` | ✅ correct | 6 N | 6 | 分量逐个一致 [6.0] | sympy.physics[牛顿第二定律] |
| `P23` | ✅ correct | 18 J | 18 | 分量逐个一致 [18.0] | sympy.physics[动能] |
| `P24` | ✅ correct | 1.798 N | \frac{899}{500} | 分量逐个一致 [1.798] | sympy.physics[库仑定律] |
| `P25` | ✅ correct | 10 V | 10 | 分量逐个一致 [10.0] | sympy.physics[欧姆定律] |
| `P26` | ✅ correct | 2.00709 s | \frac{200709}{100000} | 分量逐个一致 [2.00709] | sympy.physics[单摆周期] |
| `P27` | ✅ correct | 100 m/s | 100 | 分量逐个一致 [100.0] | sympy.physics[波速] |
| `P28` | ✅ correct | 1.1 | E(X) = 1.1 | 分量逐个一致 [1.1] | sympy.probability |
| `P29` | ✅ correct | 0.49 | \operatorname{Var}(X) = 0.49,\ \sigma = 0.7 | 数值一致（0.49） | sympy.probability |
| `P30` | ✅ correct | 5 | E(X) = 5 | 分量逐个一致 [5.0] | sympy.probability |
| `P31` | ✅ correct | 0.975 | 0.975002 | 匹配可接受形式「0.975」 | sympy.probability |
