# Homework Solutions

- **Course**: Math 1A Worksheet 4
- **Student**: Songpengfei
- **Date**: 2026-10-09
- **Solved**: 9/10 (90.0%)

---

## Problem Q1

Suppose $f$ is a function and $L$ and $a$ are real numbers.

**Solution** `[sympy_limit]`

1. See sub-problems for individual limit computations.

- **(a)** $\forall \varepsilon > 0, \exists \delta > 0: 0 < |x-a| < \delta \Rightarrow |f(x)-L| < \varepsilon$
- **(b)** $\text{See graph}$
- **(c)** $\text{See graph}$
- **(d)** $\text{See graph}$

**Answer**: $\text{See sub-problems}$

## Problem Q2

Is $\infty$ a number? What does $\lim_{x \to a} f(x) = \infty$ mean? Does $\lim_{x \to a} f(x) = \infty$ mean that the limit exists?

**Solution** `[conceptual_template]`

1. $\infty$ is \textbf{not} a real number.
2. $\lim_{x \to a} f(x) = \infty$ means that $f(x)$ grows without bound as $x \to a$.
3. The limit does \textbf{not exist} in the usual sense; we say the limit ``equals infinity'' as a shorthand for divergence.

**Answer**: $\infty \text{ is not a number. The limit does not exist.}$

## Problem Q3

What does the Squeeze Theorem say? Draw a picture illustrating this theorem.

**Solution** `[conceptual_template]`

1. \textbf{Squeeze Theorem:} If $g(x) \le f(x) \le h(x)$ for all $x$ near $a$ (except possibly at $a$), and $\lim_{x \to a} g(x) = \lim_{x \to a} h(x) = L$, then $\lim_{x \to a} f(x) = L$.
2. Intuitively: if $f$ is ``squeezed'' between two functions that both converge to $L$, then $f$ must also converge to $L$.

**Answer**: $\text{If } g(x) \le f(x) \le h(x) \text{ and } \lim g = \lim h = L, \text{ then } \lim f = L.$

## Problem Q4

What do we mean by $\lim_{x \to a^-} f(x) = L$? What is meant by $\lim_{x \to a^+} f(x) = L$? Graph a function $y = f(x)$ and some point $x = a$ where $\lim_{x \to a^-} f(x) \neq \lim_{x \to a^+} f(x)$. Find an algebraic expression for such a function.

**Solution** `[conceptual_template]`

1. $\lim_{x \to a^-} f(x) = L$: the \textbf{left-hand limit}. As $x$ approaches $a$ from values \emph{less than} $a$, $f(x)$ approaches $L$.
2. $\lim_{x \to a^+} f(x) = L$: the \textbf{right-hand limit}. As $x$ approaches $a$ from values \emph{greater than} $a$, $f(x)$ approaches $L$.
3. The two-sided limit $\lim_{x \to a} f(x) = L$ exists if and only if both one-sided limits exist and are equal.
4. Example: $f(x) = \begin{cases} x & x < 0 \\ x+1 & x \ge 0 \end{cases}$ at $a = 0$: $\lim_{x \to 0^-} f(x) = 0 \neq 1 = \lim_{x \to 0^+} f(x)$.

**Answer**: $\lim_{x \to a^-} f(x): \text{from below}; \quad \lim_{x \to a^+} f(x): \text{from above}$

## Problem P1

(a) Is the limit of a sum always the sum of the limits? Give an example where $\lim_{x \to a}[f(x) + g(x)]$ exists even though neither $\lim_{x \to a} f(x)$ nor $\lim_{x \to a} g(x)$ exist.

**Solution** `[conceptual_template]`

1. No, the limit of a sum is \emph{not} always the sum of the limits.
2. The \textbf{Sum Law} requires both individual limits to exist: $\lim[f(x)+g(x)] = \lim f(x) + \lim g(x)$ \emph{if both limits exist}.
3. \textbf{Counterexample:} Let $f(x) = \frac{1}{x}$ and $g(x) = -\frac{1}{x}$. Neither $\lim_{x \to 0} f(x)$ nor $\lim_{x \to 0} g(x)$ exists, but $\lim_{x \to 0}[f(x)+g(x)] = \lim_{x \to 0} 0 = 0$.

**Answer**: $\text{No. } f(x)=1/x,\; g(x)=-1/x: \lim[f+g]=0 \text{ but } \lim f, \lim g \text{ DNE}$

## Problem P2

(a) Find $\lim_{x \to 0^+}(\frac{1}{x} - \frac{1}{|x|})$, $\lim_{x \to 0^-}(\frac{1}{x} - \frac{1}{|x|})$, and $\lim_{x \to 0}(\frac{1}{x} - \frac{1}{|x|})$, if they exist.

**Solution** `[sympy]`

1. $\lim_{x \to 0^+} - \frac{1}{\left|{x}\right|} + \frac{1}{x} = 0$
2. $\lim_{x \to 0^-} - \frac{1}{\left|{x}\right|} + \frac{1}{x} = -\infty$
3. $\lim_{x \to 0} - \frac{1}{\left|{x}\right|} + \frac{1}{x} = 0$

- **(b)** $0$
- **(c)** $\text{DNE}$

**Answer**: $0$

## Problem P3

For what kinds of functions can one evaluate the limit $\lim_{x \to a} f(x)$ by just plugging in $x = a$? Give an example of a function $f(x)$ for which the limit $\lim_{x \to a} f(x)$ exists and can be evaluated, yet for which this substitution doesn't work.

**Solution** `[conceptual_template]`

1. \textbf{Continuous functions} allow direct substitution: $\lim_{x \to a} f(x) = f(a)$.
2. This includes polynomials, rational functions (at non-zero denominator points), trigonometric, exponential, and logarithmic functions at points in their domain.
3. Example where limit exists but substitution fails: $f(x) = \frac{x^2 - 1}{x - 1}$ at $x = 1$. Direct substitution gives $\frac{0}{0}$, but $\lim_{x \to 1} \frac{x^2-1}{x-1} = \lim_{x \to 1}(x+1) = 2$.

**Answer**: $\text{Continuous functions: } \lim_{x \to a} f(x) = f(a)$

## Problem AP1

Below are listed three limits. Match the best method to each limit and evaluate each limit.

**Solution** `[sympy_limit]`

1. See sub-problems for individual limit computations.

- **(a)** $-20$
- **(b)** $10$
- **(c)** $0$

**Answer**: $\text{See sub-problems}$

## Problem AP2

Using a calculator, try to guess $\lim_{n \to \infty} n \sin(\frac{\pi}{n})$. (Remember that $n$ is in radians, not degrees!)

**Solution** `[sympy]`

1. $\lim_{x \to \infty} n \sin{\left(\frac{\pi}{n} \right)} = \pi$

**Answer**: $\pi$

## Problem AP3

Draw a circle of radius 1. Inscribe a regular $n$-gon inside it.

> ⚠️ **未解出**：确定性求解器未覆盖，且本次运行禁用了 LLM（--no-llm）
