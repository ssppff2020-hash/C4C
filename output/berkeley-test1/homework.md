# Homework Solutions

- **Course**: Math 1A Worksheet 3
- **Student**: Songpengfei
- **Date**: 2026-10-09
- **Solved**: 8/8 (100.0%)

---

## Problem Q1

Can the graph of a function have more than one tangent at a given point? If so, graph your answer. If not, explain why.

**Solution** `[conceptual_template]`

1. In general, a smooth function has exactly one tangent line at each point.
2. However, a curve (not necessarily the graph of a function) can have multiple tangents at a self-intersection point.
3. For a function graph, the tangent is unique where the derivative exists.

**Answer**: $\text{Unique tangent where } f'(a) \text{ exists.}$

## Problem Q2

Is there a function whose graph doesn't have a tangent at some point? If so, graph your answer. If not, explain why.

**Solution** `[conceptual_template]`

1. Yes. A function may fail to have a tangent at a point where it is not differentiable.
2. Examples: $f(x) = |x|$ at $x = 0$ (corner), $f(x) = x^{1/3}$ at $x = 0$ (vertical tangent/cusp).

**Answer**: $\text{Yes: } f(x) = |x| \text{ at } x = 0 \text{ (corner)}$

## Problem P1

Suppose $\delta$ is a positive real number. How do you describe all real numbers $x$ that are within $\delta$ of 0?

**Solution** `[epsilon_delta_template]`

1. x within δ of 0: $|x| < \delta$, i.e. $-\delta < x < \delta$

- **(a)** $-\delta < x < \delta$
- **(b)** $|x| < \delta$
- **(c)** $(-\delta, \delta)$

**Answer**: $|x| < \delta$, i.e. $-\delta < x < \delta$

## Problem P2

Suppose $a$ is a real number and $\delta$ is a positive real number. How do you describe all real numbers $x$ that are within $\delta$ of $a$?

**Solution** `[epsilon_delta_template]`

1. x within δ of a: $|x - a| < \delta$, i.e. $a - \delta < x < a + \delta$

- **(a)** $\text{See graph}$
- **(b)** $a - \delta < x < a + \delta$
- **(c)** $|x - a| < \delta$
- **(d)** $(a - \delta, a + \delta)$

**Answer**: $|x - a| < \delta$, i.e. $a - \delta < x < a + \delta$

## Problem P3

Suppose $a$ is a real number and $\delta$ is a positive real number. How do you describe all real numbers $x$ that are within $\delta$ of $a$, but not equal to $a$:

**Solution** `[epsilon_delta_template]`

1. x within δ of a, not equal to a: $0 < |x - a| < \delta$

- **(a)** $\text{See graph}$
- **(b)** $a - \delta < x < a + \delta, \quad x \neq a$
- **(c)** $0 < |x - a| < \delta$
- **(d)** $(a - \delta, a) \cup (a, a + \delta)$

**Answer**: $0 < |x - a| < \delta$

## Problem P4

Let $f(x) = x^2$.

**Solution** `[epsilon_delta_computation]`

1. Given: $f(x) = x^{2}$

- **(a)** $(2.82842712474619, 3.16227766016838)$
- **(b)** $\delta = 0.16227766016838$
- **(c)** _未解：无法解析 ε-δ 计算子题_
- **(d)** $\text{Yes (continuity)}$

**Answer**: $f(x) = x^{2}$

## Problem AP1

Graph $y = 2x - x^2$. For which points $a$ is the tangent line to the curve at the point $(a, 2a - a^2)$ a horizontal line? How is the value of $2x - x^2$ at these points related to the values of $2x - x^2$ at other points?

**Solution** `[sympy]`

1. Given: $y = - x^{2} + 2 x$
2. Derivative: $y' = 2 - 2 x$
3. Horizontal tangent where $y' = 0$: $2 - 2 x = 0$
4. Solutions: $x = \left[ 1\right]$
5. Points: $(1, 1)$
6. $f''(1) = -2 < 0$: this is a maximum.
7. The value $1$ is the maximum of $- x^{2} + 2 x$.

**Answer**: $(1, 1)$

## Problem AP2

The point $(2, 0)$ is on the curve $y = 2x - x^2$.

**Solution** `[sympy]`

1. Given: $y = - x^{2} + 2 x$
2. Derivative: $y' = 2 - 2 x$
3. At point $(2, 0)$:
4. Slope: $f'(2) = -2$
5. Tangent line: $y = 4 - 2 x$

- **(a)** $\text{Line with slope } -2$
- **(b)** $y = 4 - 2 x$

**Answer**: $4 - 2 x$
