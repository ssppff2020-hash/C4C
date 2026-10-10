# Cross-Subject Benchmark

- **Course**: C4C Domain Benchmark (5 subjects)
- **Student**: Songpengfei
- **Date**: 2026-10-09
- **Solved**: 31/31 (100.0%)

---

## Problem P1

Compute the determinant of the matrix $A = \begin{pmatrix} 2 & 1 & 0 \\ 1 & 3 & 1 \\ 0 & 1 & 4 \end{pmatrix}$.

**Solution** `[sympy.linalg]`

1. 取矩阵 $A = \left[\begin{matrix}2 & 1 & 0\\1 & 3 & 1\\0 & 1 & 4\end{matrix}\right]$，阶数 $n = 3$。
2. 按定义展开：$\det A = \sum_{\sigma \in S_n} \operatorname{sgn}(\sigma)\prod_{i=1}^{n} a_{i,\sigma(i)}$（$n=3$ 时共 $6$ 项）。
3. 用余子式展开/行变换化简，得 $\det A = 18$。
4. 交叉核验：特征值 $\lambda = 3,\ 3 - \sqrt{3},\ \sqrt{3} + 3$，$\prod \lambda = 18 = \det A$ ✓。

**Answer**: $18$

## Problem P2

Find the inverse of the matrix $A = \begin{pmatrix} 2 & 0 \\ 0 & 4 \end{pmatrix}$.

**Solution** `[sympy.linalg]`

1. $A = \left[\begin{matrix}2 & 0\\0 & 4\end{matrix}\right]$，$\det A = 8 \neq 0$，故 $A$ 可逆。
2. 用伴随矩阵公式 $A^{-1} = \dfrac{1}{\det A}\,\operatorname{adj}(A)$。
3. 得 $A^{-1} = \left[\begin{matrix}\frac{1}{2} & 0\\0 & \frac{1}{4}\end{matrix}\right]$。
4. 核验：$A A^{-1} = \left[\begin{matrix}1 & 0\\0 & 1\end{matrix}\right]$，为单位阵。

**Answer**: $\left[\begin{matrix}\frac{1}{2} & 0\\0 & \frac{1}{4}\end{matrix}\right]$

## Problem P3

Find the eigenvalues of $A = \begin{pmatrix} 3 & 0 \\ 0 & -1 \end{pmatrix}$.

**Solution** `[sympy.linalg]`

1. $A = \left[\begin{matrix}3 & 0\\0 & -1\end{matrix}\right]$。
2. 特征方程 $\det(A - \lambda I) = 0$，即 $\lambda^{2} - 2 \lambda - 3 = 0$。
3. 解得特征值 $\lambda = -1$。
4. 解得特征值 $\lambda = 3$。

**Answer**: $\lambda = -1,\ 3$

## Problem P4

Find the rank of the matrix $A = \begin{pmatrix} 1 & 2 & 3 \\ 2 & 4 & 6 \\ 3 & 6 & 9 \end{pmatrix}$.

**Solution** `[sympy.linalg]`

1. $A = \left[\begin{matrix}1 & 2 & 3\\2 & 4 & 6\\3 & 6 & 9\end{matrix}\right]$。
2. 对 $A$ 做初等行变换（高斯-若尔当消元）。
3. 得到最简行阶梯形 $\operatorname{rref}(A) = \left[\begin{matrix}1 & 2 & 3\\0 & 0 & 0\\0 & 0 & 0\end{matrix}\right]$。
4. 主元列号：$[1]$（1 起数）。
5. 故 $\operatorname{rank}(A) = 1$。

**Answer**: $\operatorname{rank}(A) = 1$

## Problem P5

Solve the linear system $Ax = b$ where $A = \begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}$ and $b = \begin{pmatrix} 5 \\ 11 \end{pmatrix}$.

**Solution** `[sympy.linalg]`

1. $A = \left[\begin{matrix}1 & 2\\3 & 4\end{matrix}\right]$，$b = \left[\begin{matrix}5\\11\end{matrix}\right]$，解 $Ax = b$。
2. 增广矩阵 $[A|b] = \left[\begin{matrix}1 & 2 & 5\\3 & 4 & 11\end{matrix}\right]$。
3. 行化简得 $\operatorname{rref}[A|b] = \left[\begin{matrix}1 & 0 & 1\\0 & 1 & 2\end{matrix}\right]$。
4. 自由变量个数为 0，解唯一：由回代得
5. $x_{1} = 1$
6. $x_{2} = 2$
7. 核验：$A x = \left[\begin{matrix}5\\11\end{matrix}\right]$ $= b$。

**Answer**: $x = \begin{pmatrix}1\\2\end{pmatrix}$

## Problem P6

Compute the trace of $A = \begin{pmatrix} 5 & 1 \\ 2 & 3 \end{pmatrix}$.

**Solution** `[sympy.linalg]`

1. $A = \left[\begin{matrix}5 & 1\\2 & 3\end{matrix}\right]$。
2. 迹 = 主对角线元素之和 $= 8$。
3. 另一条路：迹 = 特征值之和 $= 8$，两法一致 ✓。

**Answer**: $8$

## Problem P7

Find the eigenvalues of $A = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}$.

**Solution** `[sympy.linalg]`

1. $A = \left[\begin{matrix}0 & 1\\1 & 0\end{matrix}\right]$。
2. 特征方程 $\det(A - \lambda I) = 0$，即 $\lambda^{2} - 1 = 0$。
3. 解得特征值 $\lambda = -1$。
4. 解得特征值 $\lambda = 1$。

**Answer**: $\lambda = -1,\ 1$

## Problem P8

Compute the determinant of $A = \begin{pmatrix} 1 & 0 & 0 \\ 0 & 2 & 0 \\ 0 & 0 & 3 \end{pmatrix}$.

**Solution** `[sympy.linalg]`

1. 取矩阵 $A = \left[\begin{matrix}1 & 0 & 0\\0 & 2 & 0\\0 & 0 & 3\end{matrix}\right]$，阶数 $n = 3$。
2. 按定义展开：$\det A = \sum_{\sigma \in S_n} \operatorname{sgn}(\sigma)\prod_{i=1}^{n} a_{i,\sigma(i)}$（$n=3$ 时共 $6$ 项）。
3. 用余子式展开/行变换化简，得 $\det A = 6$。
4. 交叉核验：特征值 $\lambda = 1,\ 2,\ 3$，$\prod \lambda = 6 = \det A$ ✓。

**Answer**: $6$

## Problem P9

Evaluate the indefinite integral $\int x e^{x} dx$.

**Solution** `[sympy.calculus]`

1. 求不定积分 $\displaystyle\int x e^{x}\, dx$。
2. 选择合适的技巧（换元 / 分部积分 / 部分分式 / 基本积分表）。
3. 得 $F(x) = \left(x - 1\right) e^{x} + C$。
4. 核验：$\dfrac{d}{dx}\left(\left(x - 1\right) e^{x}\right) = x e^{x} = $ 被积函数 ✓。

**Answer**: $C + \left(x - 1\right) e^{x}$

## Problem P10

Evaluate the definite integral $\int_0^1 x^{2} dx$.

**Solution** `[sympy.calculus]`

1. 求定积分 $\displaystyle\int_{0}^{1} x^{2}\, dx$。
2. 先求原函数 $F(x) = \frac{x^{3}}{3}$。
3. 牛顿-莱布尼茨公式：$F(1) - F(0) = \frac{1}{3}$。

**Answer**: $\frac{1}{3}$

## Problem P11

Find the derivative of $x^{3}\ln(x)$.

**Solution** `[sympy.calculus]`

1. 已知 $f(x) = x^{3} \log{\left(x \right)}$。
2. 求一阶导：$f'(x) = \dfrac{d}{dx}\left(x^{3} \log{\left(x \right)}\right)$。
3. 逐项使用 $(x^n)' = nx^{n-1}$、$(\sin x)' = \cos x$、$(e^x)' = e^x$、$(\ln x)' = 1/x$ 与乘积/链式法则。
4. 得 $f'(x) = x^{2} \left(3 \log{\left(x \right)} + 1\right)$。

**Answer**: $x^{2} \left(3 \log{\left(x \right)} + 1\right)$

## Problem P12

Evaluate the improper integral $\int_0^{\infty} e^{-2x} dx$.

**Solution** `[sympy.calculus]`

1. 求定积分 $\displaystyle\int_{0}^{\infty} e^{- 2 x}\, dx$。
2. 这是**反常积分**，用 $\lim_{b\to\infty}F(b)$ 取极限判定收敛性。
3. 先求原函数 $F(x) = - \frac{e^{- 2 x}}{2}$。
4. 牛顿-莱布尼茨公式：$F(\infty) - F(0) = \frac{1}{2}$。

**Answer**: $\frac{1}{2}$

## Problem P13

Find the Taylor series of $e^{x}$ about 0 up to order 4.

**Solution** `[sympy.calculus]`

1. $f(x) = e^{x}$，展开中心 $0$，展开到 $n=5$ 阶。
2. 套用 $f(x) = \sum_{k=0}^{n} \dfrac{f^{(k)}(a)}{k!}(x-a)^k + R_n(x)$。
3. $f^{(0)}(0) = 1$，系数 $\dfrac{f^{(0)}}{0!} = 1$。
4. $f^{(1)}(0) = 1$，系数 $\dfrac{f^{(1)}}{1!} = 1$。
5. $f^{(2)}(0) = 1$，系数 $\dfrac{f^{(2)}}{2!} = \frac{1}{2}$。
6. $f^{(3)}(0) = 1$，系数 $\dfrac{f^{(3)}}{3!} = \frac{1}{6}$。
7. $f^{(4)}(0) = 1$，系数 $\dfrac{f^{(4)}}{4!} = \frac{1}{24}$。
8. $f^{(5)}(0) = 1$，系数 $\dfrac{f^{(5)}}{5!} = \frac{1}{120}$。
9. 所以 $f(x) \approx \frac{x^{5}}{120} + \frac{x^{4}}{24} + \frac{x^{3}}{6} + \frac{x^{2}}{2} + x + 1$。

**Answer**: $\frac{x^{5}}{120} + \frac{x^{4}}{24} + \frac{x^{3}}{6} + \frac{x^{2}}{2} + x + 1$

## Problem P14

Calculate the gradient of $f(x,y,z) = x^{2} + y^{2} + z^{2}$.

**Solution** `[sympy.calculus]`

1. $f('x', 'y', 'z') = x^{2} + y^{2} + z^{2}$。
2. 梯度算子 $\nabla = \left(\dfrac{\partial}{\partial x_1},\dots\right)$，逐分量求偏导。
3. $\dfrac{\partial f}{\partial x} = 2 x$
4. $\dfrac{\partial f}{\partial y} = 2 y$
5. $\dfrac{\partial f}{\partial z} = 2 z$
6. $\nabla f = \left[\begin{matrix}2 x\\2 y\\2 z\end{matrix}\right]$。

**Answer**: $\left[\begin{matrix}2 x\\2 y\\2 z\end{matrix}\right]$

## Problem P15

Evaluate the indefinite integral $\int \frac{1}{1+x^{2}} dx$.

**Solution** `[sympy.calculus]`

1. 求不定积分 $\displaystyle\int \frac{1}{x^{2} + 1}\, dx$。
2. 选择合适的技巧（换元 / 分部积分 / 部分分式 / 基本积分表）。
3. 得 $F(x) = \operatorname{atan}{\left(x \right)} + C$。
4. 核验：$\dfrac{d}{dx}\left(\operatorname{atan}{\left(x \right)}\right) = \frac{1}{x^{2} + 1} = $ 被积函数 ✓。

**Answer**: $C + \operatorname{atan}{\left(x \right)}$

## Problem P16

Solve the differential equation $y' = y$.

**Solution** `[sympy.ode]`

1. 原方程：$\frac{d}{d x} y{\left(x \right)} = y{\left(x \right)}$。
2. 这是一个 1 阶线性常微分方程。
3. 解得：$$y{\left(x \right)} = C_{1} e^{x}$$
4. （通解中的 $C_1, C_2, \dots$ 为任意常数；给出初值即可确定。）
5. 核验：把解代回原方程，两边恒等 ✓。

**Answer**: $C_{1} e^{x}$

## Problem P17

Solve the differential equation $y' + 2y = 0$.

**Solution** `[sympy.ode]`

1. 原方程：$2 y{\left(x \right)} + \frac{d}{d x} y{\left(x \right)} = 0$。
2. 这是一个 1 阶线性常微分方程。
3. 解得：$$y{\left(x \right)} = C_{1} e^{- 2 x}$$
4. （通解中的 $C_1, C_2, \dots$ 为任意常数；给出初值即可确定。）
5. 核验：把解代回原方程，两边恒等 ✓。

**Answer**: $C_{1} e^{- 2 x}$

## Problem P18

Solve the differential equation $y'' - y = 0$.

**Solution** `[sympy.ode]`

1. 原方程：$- y{\left(x \right)} + \frac{d^{2}}{d x^{2}} y{\left(x \right)} = 0$。
2. 这是一个 2 阶线性常微分方程。
3. 特征方程：$r^{2} - 1 = 0$。
4. 特征根：$\left[ -1, \  1\right]$。
5. 两个相异实根 ⟹ 通解形如 $y = C_1 e^{r_1 x} + C_2 e^{r_2 x}$。
6. 解得：$$y{\left(x \right)} = C_{1} e^{- x} + C_{2} e^{x}$$
7. （通解中的 $C_1, C_2, \dots$ 为任意常数；给出初值即可确定。）
8. 核验：把解代回原方程，两边恒等 ✓。

**Answer**: $C_{1} e^{- x} + C_{2} e^{x}$

## Problem P19

Solve the differential equation $y'' + y = 0$.

**Solution** `[sympy.ode]`

1. 原方程：$y{\left(x \right)} + \frac{d^{2}}{d x^{2}} y{\left(x \right)} = 0$。
2. 这是一个 2 阶线性常微分方程。
3. 特征方程：$r^{2} + 1 = 0$。
4. 特征根：$\left[ - i, \  i\right]$。
5. 共轭复根 $\alpha \pm \beta i$ ⟹ 通解形如 $y = e^{\alpha x}(C_1\cos\beta x + C_2\sin\beta x)$。
6. 解得：$$y{\left(x \right)} = C_{1} \sin{\left(x \right)} + C_{2} \cos{\left(x \right)}$$
7. （通解中的 $C_1, C_2, \dots$ 为任意常数；给出初值即可确定。）

**Answer**: $C_{1} \sin{\left(x \right)} + C_{2} \cos{\left(x \right)}$

## Problem P20

Solve the differential equation $y' = 2x$ with $y(0) = 1$.

**Solution** `[sympy.ode]`

1. 原方程：$\frac{d}{d x} y{\left(x \right)} = 2 x$。
2. 这是一个 1 阶线性常微分方程。
3. 初值条件：$y{\left(0 \right)} = 1$。
4. 解得：$$y{\left(x \right)} = x^{2} + 1$$
5. 核验：把解代回原方程，两边恒等 ✓。

**Answer**: $x^{2} + 1$

## Problem P21

Find the Laplace transform of $e^{-2t}$.

**Solution** `[sympy.ode]`

1. 求 $\mathcal{L}\{f(t)\}$，其中 $f(t) = e^{- 2 t}$。
2. 按定义 $F(s) = \int_0^{\infty} e^{-st} f(t)\,dt$。
3. 用到 $\mathcal{L}\{e^{at}\} = \dfrac{1}{s-a}$。
4. 得 $F(s) = \frac{1}{s + 2}$。

**Answer**: $\frac{1}{s + 2}$

## Problem P22

A mass of 2 kg experiences an acceleration of 3 m/s^2. Find the net force.

**Solution** `[sympy.physics[牛顿第二定律]]`

1. 识别为「牛顿第二定律」（F 合力, m 质量, a 加速度）。
2. 选用公式：$F = a m$。
3. 已知量代入：$m = 2$，$a = 3$。
4. 代入数值计算：$ F = 6 $。

**Answer**: $6$

## Problem P23

A mass of 4 kg moves at a velocity of 3 m/s. Find the kinetic energy.

**Solution** `[sympy.physics[动能]]`

1. 识别为「动能」（E_k 动能, m 质量, v 速度）。
2. 选用公式：$E_{k} = \frac{m v^{2}}{2}$。
3. 已知量代入：$v = 3$，$m = 4$。
4. 代入数值计算：$ E_{k} = 18 $。

**Answer**: $18$

## Problem P24

Two point charges $q1 = 1e-6$ C and $q2 = 2e-6$ C are separated by a distance $r = 0.1$ m. Find the Coulomb force between them.

**Solution** `[sympy.physics[库仑定律]]`

1. 识别为「库仑定律」（F 库仑力, q1 q2 电荷, r 距离）。
2. 选用公式：$F = \frac{k_{e} q_{1} q_{2}}{r^{2}}$。
3. 已知量代入：$q_{1} = \frac{1}{1000000}$，$q_{2} = \frac{1}{500000}$，$r = \frac{1}{10}$，$k_{e} = 8990000000$。
4. 代入数值计算：$ F = \frac{899}{500} $。

**Answer**: $\frac{899}{500}$

## Problem P25

A resistor carries a current of 2 A and has a resistance of 5 ohm. Find the voltage across it.

**Solution** `[sympy.physics[欧姆定律]]`

1. 识别为「欧姆定律」（V 电压, I 电流, R 电阻）。
2. 选用公式：$V = I R$。
3. 已知量代入：$I = 2$，$R = 5$。
4. 代入数值计算：$ V = 10 $。

**Answer**: $10$

## Problem P26

A simple pendulum has length $L = 1$ m. Find its period (take $g = 9.8$ m/s^2).

**Solution** `[sympy.physics[单摆周期]]`

1. 识别为「单摆周期」（T_period 周期, L 摆长, g 重力加速度）。
2. 选用公式：$T_{period} = 2 \pi \sqrt{\frac{L}{g}}$。
3. 已知量代入：$g = \frac{49}{5}$，$L = 1$。
4. 代入数值计算：$ T_{period} = \frac{200709}{100000} $。

**Answer**: $\frac{200709}{100000}$

## Problem P27

A wave has frequency 50 Hz and wavelength 2 m. Find the wave speed.

**Solution** `[sympy.physics[波速]]`

1. 识别为「波速」（v 波速, f 频率, lam 波长）。
2. 选用公式：$v = f lam$。
3. 已知量代入：$f = 50$，$lam = 2$。
4. 代入数值计算：$ v = 100 $。

**Answer**: $100$

## Problem P28

The following table gives the distribution of $X$. Find the expected value of $X$.

| x | p |
|---|---|
| 0 | 0.2 |
| 1 | 0.5 |
| 2 | 0.3 |

**Solution** `[sympy.probability]`

1. 读入分布列：$x_i$ 与 $p_i$。
2. 期望 $E(X) = \sum_i x_i p_i$。
3. $x_{1}p_{1} = 0.0 \times 0.2 = 0$，$x_{2}p_{2} = 1.0 \times 0.5 = 0.5$，$x_{3}p_{3} = 2.0 \times 0.3 = 0.6$
4. $E(X) = 1.1$。
5. $\operatorname{Var}(X) = E(X^2) - [E(X)]^2 = \sum_i p_i(x_i - \mu)^2$。
6. $\operatorname{Var}(X) = 0.49$，$\sigma = 0.7$。

**Answer**: $E(X) = 1.1$

## Problem P29

The following table gives the distribution of $X$. Find the variance of $X$.

| x | p |
|---|---|
| 0 | 0.2 |
| 1 | 0.5 |
| 2 | 0.3 |

**Solution** `[sympy.probability]`

1. 读入分布列：$x_i$ 与 $p_i$。
2. 期望 $E(X) = \sum_i x_i p_i$。
3. $x_{1}p_{1} = 0.0 \times 0.2 = 0$，$x_{2}p_{2} = 1.0 \times 0.5 = 0.5$，$x_{3}p_{3} = 2.0 \times 0.3 = 0.6$
4. $E(X) = 1.1$。
5. $\operatorname{Var}(X) = E(X^2) - [E(X)]^2 = \sum_i p_i(x_i - \mu)^2$。
6. $\operatorname{Var}(X) = 0.49$，$\sigma = 0.7$。

**Answer**: $\operatorname{Var}(X) = 0.49,\ \sigma = 0.7$

## Problem P30

Let $X \sim B(10, 0.5)$. Find the expected value of $X$.

**Solution** `[sympy.probability]`

1. $X \sim B(n=10,\ p=0.5)$。
2. 二项分布期望 $E(X) = np = 10\times0.5 = 5$。
3. 方差 $\operatorname{Var}(X) = np(1-p) = 2.5$。

**Answer**: $E(X) = 5$

## Problem P31

Let $X \sim N(0,1)$. Compute $P(X <= 1.96)$.

**Solution** `[sympy.probability]`

1. $X \sim N(0.0, 1.0^2)$，求 $P(X \le 1.96)$。
2. 标准化 $z = \dfrac{x-\mu}{\sigma} = \dfrac{1.96-0.0}{1.0} = 1.9600$。
3. 查标准正态表（或 erf 计算）得 $\Phi(1.9600) = 0.975002$。
4. $P = 0.975002$。

**Answer**: $0.975002$
