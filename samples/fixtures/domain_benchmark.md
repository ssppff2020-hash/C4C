# C4C Domain Benchmark — 跨 5 学科基准题集

> 用途：量化「从微积分极限扩展到 5 个学科」到底扩展了多少。
> starter kit 在同样这批题上只能做出第 9/10/11 题（极限域外全部 40% 或更低）。
> 每题都有唯一、可机器核验的答案（见 `domain_benchmark_ground_truth.json`）。

## Problems

Problem 1. Compute the determinant of the matrix $A = \begin{pmatrix} 2 & 1 & 0 \\ 1 & 3 & 1 \\ 0 & 1 & 4 \end{pmatrix}$.

Problem 2. Find the inverse of the matrix $A = \begin{pmatrix} 2 & 0 \\ 0 & 4 \end{pmatrix}$.

Problem 3. Find the eigenvalues of $A = \begin{pmatrix} 3 & 0 \\ 0 & -1 \end{pmatrix}$.

Problem 4. Find the rank of the matrix $A = \begin{pmatrix} 1 & 2 & 3 \\ 2 & 4 & 6 \\ 3 & 6 & 9 \end{pmatrix}$.

Problem 5. Solve the linear system $Ax = b$ where $A = \begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}$ and $b = \begin{pmatrix} 5 \\ 11 \end{pmatrix}$.

Problem 6. Compute the trace of $A = \begin{pmatrix} 5 & 1 \\ 2 & 3 \end{pmatrix}$.

Problem 7. Find the eigenvalues of $A = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}$.

Problem 8. Compute the determinant of $A = \begin{pmatrix} 1 & 0 & 0 \\ 0 & 2 & 0 \\ 0 & 0 & 3 \end{pmatrix}$.

Problem 9. Evaluate the indefinite integral $\int x e^{x} dx$.

Problem 10. Evaluate the definite integral $\int_0^1 x^{2} dx$.

Problem 11. Find the derivative of $x^{3}\ln(x)$.

Problem 12. Evaluate the improper integral $\int_0^{\infty} e^{-2x} dx$.

Problem 13. Find the Taylor series of $e^{x}$ about 0 up to order 4.

Problem 14. Calculate the gradient of $f(x,y,z) = x^{2} + y^{2} + z^{2}$.

Problem 15. Evaluate the indefinite integral $\int \frac{1}{1+x^{2}} dx$.

Problem 16. Solve the differential equation $y' = y$.

Problem 17. Solve the differential equation $y' + 2y = 0$.

Problem 18. Solve the differential equation $y'' - y = 0$.

Problem 19. Solve the differential equation $y'' + y = 0$.

Problem 20. Solve the differential equation $y' = 2x$ with $y(0) = 1$.

Problem 21. Find the Laplace transform of $e^{-2t}$.

Problem 22. A mass of 2 kg experiences an acceleration of 3 m/s^2. Find the net force.

Problem 23. A mass of 4 kg moves at a velocity of 3 m/s. Find the kinetic energy.

Problem 24. Two point charges $q1 = 1e-6$ C and $q2 = 2e-6$ C are separated by a distance $r = 0.1$ m. Find the Coulomb force between them.

Problem 25. A resistor carries a current of 2 A and has a resistance of 5 ohm. Find the voltage across it.

Problem 26. A simple pendulum has length $L = 1$ m. Find its period (take $g = 9.8$ m/s^2).

Problem 27. A wave has frequency 50 Hz and wavelength 2 m. Find the wave speed.

Problem 28. The following table gives the distribution of $X$. Find the expected value of $X$.

| x | p |
|---|---|
| 0 | 0.2 |
| 1 | 0.5 |
| 2 | 0.3 |

Problem 29. The following table gives the distribution of $X$. Find the variance of $X$.

| x | p |
|---|---|
| 0 | 0.2 |
| 1 | 0.5 |
| 2 | 0.3 |

Problem 30. Let $X \sim B(10, 0.5)$. Find the expected value of $X$.

Problem 31. Let $X \sim N(0,1)$. Compute $P(X <= 1.96)$.
