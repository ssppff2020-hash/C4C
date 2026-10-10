# 正确性验证报告（自动生成）

- 对照来源：MIT 18.06 Linear Algebra, Spring 2020 (Prof. Alan Edelman) — Problem Set 1
- 官方解答：https://web.mit.edu/18.06/www/Spring2020/psetsol1.pdf
- 题目条目：32

## 汇总

| 指标 | 值 |
|---|---|
| 自动判定条目 | 32 |
| 待人工裁决 | 0 |
| 完全正确 | 28 |
| 部分正确 | 1 |
| 错误 | 3 |
| 未解出 | 0 |
| **自动判定加权正确率** | **89.1%** |
| 宽松正确率（含部分正确） | 90.6% |

## 逐条明细

| 条目 | 判定 | 期望 | 实得 | 说明 | 求解器 |
|---|---|---|---|---|---|
| `P1.a` | ✅ correct | 1) unit vector | 1)\ \text{unit vector} | 命中选项「unit vector」 | llm:deepseek/deepseek-chat(cached) |
| `P1.b` | ✅ correct | 2) zero vector | 2)\ \text{zero vector} | 命中选项「zero vector」 | llm:deepseek/deepseek-chat(cached) |
| `P1.c` | ✅ correct | 4) all of the above | a, b, c \text{ 都正确（perpendicular, orthogonal, at right angle | 命中选项「a, b, c」 | llm:deepseek/deepseek-chat(cached) |
| `P1.d` | ❌ wrong | 4) all of the above | (a)\ 1)\ \text{unit vector};\ (b)\ 2)\ \text{zero vector};\  | LLM 裁决：题目实际为选择题 d) all of the above，学生答案未给出该选项，内容不对应。 | llm:deepseek/deepseek-chat(cached) |
| `P1.d2` | ✅ correct | True | \text{True} | 命中选项「true」 | llm:deepseek/deepseek-chat(cached) |
| `P1.e` | ✅ correct | 2) 45 degrees | 45^\circ\text{（选项 2）} | 命中选项「45」 | llm:deepseek/deepseek-chat(cached) |
| `P1.f` | ✅ correct | 2 | \det A = \pm 2 | 匹配可接受形式「2」 | llm:deepseek/deepseek-chat(cached) |
| `P2.a` | ✅ correct | 3) plane not through 0 | 3)\ \text{plane not through }0 | 命中选项「plane not through」 | llm:deepseek/deepseek-chat(cached) |
| `P2.b` | ✅ correct | (2,3,4) | (2,3,4) | 归一化后完全一致 | llm:deepseek/deepseek-chat(cached) |
| `P2.c` | ✅ correct | d) sphere | d) \text{sphere} | 命中选项「sphere」 | llm:deepseek/deepseek-chat(cached) |
| `P2.d` | ❌ wrong | (2x,2y,2z) | (x,y,z) | 命中了错误选项「(x,y,z)」 | llm:deepseek/deepseek-chat(cached) |
| `P2.e` | ✅ correct | (2,3,4) | \left[\begin{matrix}2\\3\\4\end{matrix}\right] | 匹配可接受形式「2,3,4」 | sympy.calculus |
| `P2.f` | ✅ correct | (2x,2y,2z) | \nabla f = (2x, 2y, 2z) | 匹配可接受形式「2x,2y,2z」 | llm:deepseek/deepseek-chat(cached) |
| `P2.g` | ✅ correct | the half-space on one side of the plane 2x+3y+4z=2020 that c | \text{半空间 } 2x+3y+4z<2020 | LLM 裁决：学生答案正确指出该不等式描述的是由平面 2x+3y+4z=2020 界定的半空间，与标准答案等价。 | llm:deepseek/deepseek-chat(cached) |
| `P3.a` | ✅ correct | Yes | \text{Yes, } M_3(\mathbb{R}) \text{ is a real vector space.} | 命中选项「yes」 | llm:deepseek/deepseek-chat(cached) |
| `P3.b` | ✅ correct | No | \text{No} | 命中选项「no」 | llm:deepseek/deepseek-chat(cached) |
| `P3.c` | ✅ correct | Yes | \text{Yes} | 命中选项「yes」 | llm:deepseek/deepseek-chat(cached) |
| `P3.d` | ✅ correct | Yes | \text{Yes} | 命中选项「yes」 | llm:deepseek/deepseek-chat(cached) |
| `P3.e` | ✅ correct | Yes | \text{Yes} | 命中选项「yes」 | llm:deepseek/deepseek-chat(cached) |
| `P4.a` | ✅ correct | Yes | \text{Yes} | 命中选项「yes」 | llm:deepseek/deepseek-chat(cached) |
| `P4.b` | ✅ correct | Yes | \text{Yes, } V=\{f\mid f(0)=0\} \text{ 是实向量空间} | 命中选项「yes」 | llm:deepseek/deepseek-chat(cached) |
| `P4.c` | ✅ correct | No | \text{No} | 命中选项「no」 | llm:deepseek/deepseek-chat(cached) |
| `P4.d` | ✅ correct | Yes | \text{Yes, } V=\{f\mid f(17)=0\} \text{ 是实向量空间} | 命中选项「yes」 | llm:deepseek/deepseek-chat(cached) |
| `P4.e` | ✅ correct | No | \text{No} | 命中选项「no」 | llm:deepseek/deepseek-chat(cached) |
| `P5.a` | ✅ correct | 225 | 225 | 归一化后完全一致 | llm:deepseek/deepseek-chat(cached) |
| `P5.b` | ✅ correct | 7.416198487095663 and 31.28897569432403 | \\|x\\|_2=\sqrt{55},\quad \\|y\\|_2=\sqrt{979} | 包含关键结论「sqrt(55)」 | llm:deepseek/deepseek-chat(cached) |
| `P5.c` | ✅ correct | cos = 0.9696384473317716, angle = 14.154828622612804 degrees | \cos\theta=\frac{225}{\sqrt{55}\sqrt{979}}\approx 0.969,\qua | LLM 裁决：余弦值与学生答案的分数形式及近似值一致，角度换算为度后也一致，仅精度略有差异。 | llm:deepseek/deepseek-chat(cached) |
| `P5.d` | 🟡 partial | 使用 A\b 解 Ax=b（随机矩阵，数值不固定） | x = A^{-1} b | LLM 裁决：数学上等价于 A\b，但题目要求用反斜杠运算符求解，学生用显式求逆，方法不符。 | llm:deepseek/deepseek-chat(cached) |
| `P5.e` | ✅ correct | 残差约为 1e-16 量级（舍入误差，不是 bug） | b-Ax \approx \mathcal{O}(10^{-16}) | 包含关键结论「10^{-16}」 | llm:deepseek/deepseek-chat(cached) |
| `P5.f` | ✅ correct | (b-A*x)*2^52 得到接近整数的可识别数值 | (b-A*x)\cdot 2^{52}\approx \text{接近整数的数} | LLM 裁决：学生答案与标准答案完全一致，均是将残差乘以 2^52 以放大舍入误差，得到接近整数的可识别数值。 | llm:deepseek/deepseek-chat(cached) |
| `P5.g` | ✅ correct | A^2 = [[30,36,42],[66,81,96],[102,126,150]]; A.^2 = [[1,4,9] | A^2=\begin{pmatrix}30&36&42\\66&81&96\\102&126&150\end{pmatr | 包含关键结论「A^2 = [[30,36,42],[66,81,96],[102,126,150]]; A.^2 = [[1,4,9],[16,25,36],[ | llm:deepseek/deepseek-chat(cached) |
| `P5.h` | ❌ wrong | x = (0.0349648997349724, 0.251622660194788, 0.43773815598541 | x = \begin{pmatrix} -0.5 \ 0.5 \ 0.5 \end{pmatrix} | 命中了错误选项「0.5」 | llm:deepseek/deepseek-chat(cached) |
