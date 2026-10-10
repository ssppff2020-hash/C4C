# Homework 3 Solutions

- **Course**: Calculus & Linear Algebra
- **Student**: Songpengfei
- **Date**: 2026-10-09
- **Solved**: 10/10 (100.0%)

---

## Problem PartA1

Find the derivative of $x^3 + 2x^2 - 5x + 1$.

**Solution** `[sympy.calculus]`

1. 已知 $f(x) = x^{3} + 2 x^{2} - 5 x + 1$。
2. 求一阶导：$f'(x) = \dfrac{d}{dx}\left(x^{3} + 2 x^{2} - 5 x + 1\right)$。
3. 逐项使用 $(x^n)' = nx^{n-1}$、$(\sin x)' = \cos x$、$(e^x)' = e^x$、$(\ln x)' = 1/x$ 与乘积/链式法则。
4. 得 $f'(x) = 3 x^{2} + 4 x - 5$。

**Answer**: $3 x^{2} + 4 x - 5$

## Problem PartA2

Evaluate the integral $\int x^2 \sin(x) dx$.

**Solution** `[sympy.calculus]`

1. 求不定积分 $\displaystyle\int x^{2} \sin{\left(x \right)}\, dx$。
2. 选择合适的技巧（换元 / 分部积分 / 部分分式 / 基本积分表）。
3. 得 $F(x) = - x^{2} \cos{\left(x \right)} + 2 x \sin{\left(x \right)} + 2 \cos{\left(x \right)} + C$。
4. 核验：$\dfrac{d}{dx}\left(- x^{2} \cos{\left(x \right)} + 2 x \sin{\left(x \right)} + 2 \cos{\left(x \right)}\right) = x^{2} \sin{\left(x \right)} = $ 被积函数 ✓。

**Answer**: $C - x^{2} \cos{\left(x \right)} + 2 x \sin{\left(x \right)} + 2 \cos{\left(x \right)}$

## Problem PartA3

Compute the limit $\lim_{x \to 0} \frac{\sin(x)}{x}$.

**Solution** `[sympy]`

1. $\lim_{x \to 0} \frac{\sin{\left(x \right)}}{x} = 1$

**Answer**: $1$

## Problem PartA4

Find the derivative of $e^{x^2} \cdot \ln(x)$.

**Solution** `[sympy.calculus]`

1. 已知 $f(x) = e^{x^{2}} \log{\left(x \right)}$。
2. 求一阶导：$f'(x) = \dfrac{d}{dx}\left(e^{x^{2}} \log{\left(x \right)}\right)$。
3. 逐项使用 $(x^n)' = nx^{n-1}$、$(\sin x)' = \cos x$、$(e^x)' = e^x$、$(\ln x)' = 1/x$ 与乘积/链式法则。
4. 得 $f'(x) = \frac{\left(2 x^{2} \log{\left(x \right)} + 1\right) e^{x^{2}}}{x}$。

**Answer**: $\frac{\left(2 x^{2} \log{\left(x \right)} + 1\right) e^{x^{2}}}{x}$

## Problem PartA5

Evaluate $\int_0^1 \frac{1}{1+x^2} dx$.

**Solution** `[sympy.calculus]`

1. 求定积分 $\displaystyle\int_{0}^{1} \frac{1}{x^{2} + 1}\, dx$。
2. 先求原函数 $F(x) = \operatorname{atan}{\left(x \right)}$。
3. 牛顿-莱布尼茨公式：$F(1) - F(0) = \frac{\pi}{4}$。

**Answer**: $\frac{\pi}{4}$

## Problem PartB6

Solve the equation $x^2 - 5x + 6 = 0$.

**Solution** `[sympy]`

1. $x^{2} - 5 x + 6 = 0$
2. $x = \left[ 2, \  3\right]$

**Answer**: $\left[ 2, \  3\right]$

## Problem PartB7

Solve $x^3 - 6x^2 + 11x - 6 = 0$.

**Solution** `[sympy]`

1. $x^{3} - 6 x^{2} + 11 x - 6 = 0$
2. $x = \left[ 1, \  2, \  3\right]$

**Answer**: $\left[ 1, \  2, \  3\right]$

## Problem PartC8

Compute the determinant of the matrix $A = \begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}$.

**Solution** `[sympy.linalg]`

1. 取矩阵 $A = \left[\begin{matrix}1 & 2\\3 & 4\end{matrix}\right]$，阶数 $n = 2$。
2. 按定义展开：$\det A = \sum_{\sigma \in S_n} \operatorname{sgn}(\sigma)\prod_{i=1}^{n} a_{i,\sigma(i)}$（$n=2$ 时共 $2$ 项）。
3. 用余子式展开/行变换化简，得 $\det A = -2$。
4. 核对：$\det A = -2= -2$。

**Answer**: $-2$

## Problem PartC9

Find the eigenvalues of $A = \begin{pmatrix} 2 & 1 \\ 1 & 2 \end{pmatrix}$.

**Solution** `[sympy.linalg]`

1. $A = \left[\begin{matrix}2 & 1\\1 & 2\end{matrix}\right]$。
2. 特征方程 $\det(A - \lambda I) = 0$，即 $\lambda^{2} - 4 \lambda + 3 = 0$。
3. 解得特征值 $\lambda = 1$。
4. 解得特征值 $\lambda = 3$。

**Answer**: $\lambda = 1,\ 3$

## Problem PartD10

Solve the ODE $y' + 2y = e^{-x}$.

**Solution** `[sympy.ode]`

1. 原方程：$2 y{\left(x \right)} + \frac{d}{d x} y{\left(x \right)} = e^{- x}$。
2. 这是一个 1 阶线性常微分方程。
3. 解得：$$y{\left(x \right)} = \left(C_{1} e^{- x} + 1\right) e^{- x}$$
4. （通解中的 $C_1, C_2, \dots$ 为任意常数；给出初值即可确定。）
5. 核验：把解代回原方程，两边恒等 ✓。

**Answer**: $\left(C_{1} e^{- x} + 1\right) e^{- x}$
