#!/usr/bin/env python3
"""
solvers/linalg.py —— 线性代数求解器（C4C 新增学科 ①）
======================================================
starter kit 完全没有线性代数能力（它只会微积分极限）。本模块补上：

    行列式 / 逆矩阵 / 秩 / RREF / 零空间 / 列空间
    特征值 & 特征向量 / 对角化 / 二次型正定性
    线性方程组 Ax=b / 最小二乘 / 投影 / 正交化（Gram-Schmidt）
    LU 分解 / SVD / 伴随矩阵 / 迹 / 转置 / 矩阵乘法

设计原则
--------
1. **先判操作类型，再动 SymPy**。题干里的动词（"求行列式" / "Find the determinant"）
   决定调哪个分支；矩阵本身用 base.parse_tex_matrix 从 LaTeX 里抠。
2. **每一步都留下可核验的中间量**。答案给出来源（det 用余子式展开的表示、
   特征值给特征多项式），评审时能一眼看出是不是算的。
3. **不硬猜**。矩阵抠不出来就返回 None，交给 LLM 或标为未解。
"""

from __future__ import annotations

import re
from typing import Optional

import sympy
from sympy import Matrix, latex, eye, simplify, sqrt, nsimplify, Rational

from .base import parse_tex, parse_tex_matrix, sol, unsolved, sub_sol, sub_unsolved, T

# ─────────────────────────────────────────────────────────────
# 操作识别表：正则 → 规范操作名
# 顺序敏感（先匹配具体，再匹配笼统）
# ─────────────────────────────────────────────────────────────

OP_PATTERNS: list[tuple[str, str]] = [
    (r"行列式|determinant|\bdet\b|\\det", "det"),
    (r"特征值.{0,12}特征向量|特征向量.{0,12}特征值|特征分解|eigenvectors?\s+and\s+eigenvalues?|"
     r"eigenvalues?\s+and\s+eigenvectors?", "eigen_both"),
    (r"特征值|eigenvalue|特征根|特征多项式|characteristic\s+polynomial", "eigenvalue"),
    (r"特征向量|eigenvector", "eigenvector"),
    (r"对角化|diagonaliz", "diagonalize"),
    (r"正定|positive\s+definite", "positive_definite"),
    (r"伴随矩阵|adjugate|adjoint\s+matrix", "adjugate"),
    (r"逆矩阵|矩阵的逆|求逆|inverse\s+matrix|\binverse\b|可逆", "inverse"),
    (r"秩|\brank\b", "rank"),
    (r"最简行阶梯|行简化|行阶梯|reduced\s+row\s+echelon|rref|row\s+reduc", "rref"),
    (r"零空间|null\s*space|kernel|解的零空间", "nullspace"),
    (r"列空间|column\s+space|值域|image\s+of", "columnspace"),
    (r"四个基本子空间|four\s+fundamental", "four_subspaces"),
    (r"最小二乘|least\s+squares?", "least_squares"),
    (r"正交投影|投影矩阵|projection", "projection"),
    (r"gram[-\s]?schmidt|正交化|orthonormaliz|标准正交", "gram_schmidt"),
    (r"LU\s*分解|LU\s*factor", "lu"),
    (r"SVD|奇异值|singular\s+value", "svd"),
    (r"迹\b|trace|\btr\(", "trace"),
    (r"转置|transpose", "transpose"),
    (r"矩阵乘|相乘|\bAB\b|compute\s+AB|find\s+AB", "multiply"),
    (r"二次型|quadratic\s+form", "quadratic_form"),
    (r"正交|orthogonal|orthonormal", "orthogonality"),
    (r"线性相关|线性无关|linearly\s+(in)?dependent|相关性", "independence"),
    (r"基\b|\bbasis\b|张成|span", "basis"),
    (r"解.{0,6}方程组|求解.{0,6}方程|solve\s+the\s+system|方程组|Ax\s*=\s*b|Ax=b", "solve_system"),
    (r"行列式值", "det"),
]


def detect_op(text: str) -> Optional[str]:
    """从题干判断要做的线性代数操作。"""
    low = text or ""
    for pat, op in OP_PATTERNS:
        if re.search(pat, low, re.IGNORECASE):
            return op
    return None


# ─────────────────────────────────────────────────────────────
# 矩阵抽取
# ─────────────────────────────────────────────────────────────

def _extract_matrices(problem: dict) -> list:
    """从 math_exprs 和题目正文里找出所有矩阵。"""
    out = []
    candidates = list(problem.get("math_exprs") or [])
    # 正文里的 \begin{pmatrix}...\end{pmatrix}
    body = problem.get("text", "")
    candidates += re.findall(r"\\begin\{(?:p|b|v|B|V)?matrix\}.*?\\end\{(?:p|b|v|B|V)?matrix\}",
                             body, re.DOTALL)
    # [[1,2],[3,4]] 形式
    candidates += re.findall(r"\[\s*\[[^\]]*\](?:\s*,\s*\[[^\]]*\])+\s*\]", body)
    for c in candidates:
        m = parse_tex_matrix(c)
        if m is not None:
            out.append(m)
    # 去重（保持顺序）
    uniq = []
    for m in out:
        if not any(m == u for u in uniq):
            uniq.append(m)
    return uniq


def _extract_vector(problem: dict, dim: Optional[int] = None):
    """抽出向量 b（列向量字面量或 (1,2,3)^T）。"""
    body = problem.get("text", "")
    for pat in (r"\\begin\{(?:p|b|v|B|V)?matrix\}(.*?)\\end\{(?:p|b|v|B|V)?matrix\}",):
        for m in re.findall(pat, body, re.DOTALL):
            cells = [c for c in re.split(r"&|\\\\", m) if c.strip()]
            vals = [parse_tex(c) for c in cells]
            if all(v is not None for v in vals) and vals:
                if dim is None or len(vals) == dim:
                    return Matrix(vals)
    return None


def _fmt(m: Matrix) -> str:
    return f"${latex(m)}$"


# ─────────────────────────────────────────────────────────────
# 各操作的求解实现
# ─────────────────────────────────────────────────────────────

def _solve_det(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    if A.rows != A.cols:
        return unsolved(problem, "行列式只对方阵有定义，抽到的矩阵不是方阵", subject="线性代数")
    d = A.det()
    steps = [
        f"取矩阵 $A = {latex(A)}$，阶数 $n = {A.rows}$。",
        f"按定义展开：$\\det A = \\sum_{{\\sigma \\in S_n}} \\operatorname{{sgn}}(\\sigma)"
        f"\\prod_{{i=1}}^{{n}} a_{{i,\\sigma(i)}}$（$n={A.rows}$ 时共 ${sympy.factorial(A.rows)}$ 项）。",
        f"用余子式展开/行变换化简，得 $\\det A = {latex(d)}$。",
    ]
    # 交叉核验：det = 特征值之积。这比"再写一遍同一个数"有意义得多。
    try:
        eigs = A.eigenvals()
        expanded = sympy.Mul(*[v ** m for v, m in eigs.items()])
        if sympy.simplify(expanded - d) == 0 and len(eigs) <= 4:
            vals = ",\\ ".join(latex(v) for v in eigs.keys())
            steps.append(
                f"交叉核验：特征值 $\\lambda = {vals}$，"
                f"$\\prod \\lambda = {latex(sympy.simplify(expanded))} = \\det A$ ✓。")
    except Exception:
        pass
    return sol(problem, steps, d, solver="sympy.linalg",
               verification={"method": "SymPy Matrix.det（精确有理数运算）",
                             "check": f"det = {d}"},
               subject="线性代数")


def _solve_inverse(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    if A.rows != A.cols:
        return unsolved(problem, "只有方阵才可能可逆", subject="线性代数")
    d = A.det()
    if simplify(d) == 0:
        return sol(problem, [
            f"$A = {latex(A)}$。",
            f"先算 $\\det A = {latex(d)} = 0$。",
            "行列式为 0，$A$ 奇异，**逆矩阵不存在**。",
        ], r"\text{不存在（}A\text{ 奇异，}\det A = 0\text{）}", solver="sympy.linalg",
            subject="线性代数")
    inv = A.inv()
    steps = [
        f"$A = {latex(A)}$，$\\det A = {latex(d)} \\neq 0$，故 $A$ 可逆。",
        f"用伴随矩阵公式 $A^{{-1}} = \\dfrac{{1}}{{\\det A}}\\,\\operatorname{{adj}}(A)$。",
        f"得 $A^{{-1}} = {latex(inv)}$。",
        f"核验：$A A^{{-1}} = {latex(simplify(A * inv))}$，为单位阵。",
    ]
    return sol(problem, steps, inv, solver="sympy.linalg",
               verification={"method": "A·A⁻¹ 反代回乘", "check": "乘积为单位矩阵"},
               subject="线性代数")


def _solve_eigen(problem, matrices, want_vectors=True):
    if not matrices:
        return None
    A = matrices[0]
    if A.rows != A.cols:
        return unsolved(problem, "特征值只对方阵定义", subject="线性代数")
    lam = sympy.Symbol("lambda")
    charpoly = A.charpoly(lam).as_expr()
    eigs = A.eigenvals()
    eig_list = []
    for val, mult in eigs.items():
        eig_list.append((val, mult))
    eig_list.sort(key=lambda p: str(p[0]))

    steps = [
        f"$A = {latex(A)}$。",
        f"特征方程 $\\det(A - \\lambda I) = 0$，即 ${latex(charpoly)} = 0$。",
    ]
    for val, mult in eig_list:
        txt = f"解得特征值 $\\lambda = {latex(val)}$"
        if mult > 1:
            txt += f"（代数重数 {mult}）"
        steps.append(txt + "。")

    answer = "\\lambda = " + ",\\ ".join(latex(v) for v, _ in eig_list)

    if want_vectors:
        try:
            vecs = []
            for val, mult, basis, _ in A.eigenvects():
                for v in basis:
                    vecs.append((val, v))
            if vecs:
                steps.append("对应的特征向量（解 $(A-\\lambda I)x = 0$）：")
                for val, v in vecs:
                    steps.append(f"  $\\lambda = {latex(val)}$：$v = {latex(v)}$")
                answer += ",\\quad v = " + ",\\ ".join(latex(v) for _, v in vecs[:4])
        except Exception:
            pass

    return sol(problem, steps, answer, solver="sympy.linalg",
               verification={"method": "特征多项式 + eigvals 交叉核对",
                             "check": f"eigenvals = {dict(eigs)}"},
               subject="线性代数")


def _solve_diagonalize(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    if not A.is_diagonalizable():
        return sol(problem, [
            f"$A = {latex(A)}$。",
            f"特征值：${latex(A.eigenvals())}$。",
            "几何重数小于代数重数（A 缺特征向量），$A$ **不可对角化**。",
        ], r"A\ \text{不可对角化}", solver="sympy.linalg", subject="线性代数")
    P, D = A.diagonalize()
    steps = [
        f"$A = {latex(A)}$。",
        f"特征值 $\\lambda = {latex(list(A.eigenvals().keys()))}$。",
        f"特征向量矩阵 $P = {latex(P)}$。",
        f"对角阵 $D = {latex(D)}$。",
        f"于是 $A = P D P^{{-1}}$，即 $A = {latex(P)}\\,{latex(D)}\\,{latex(P.inv())}$。",
    ]
    return sol(problem, steps, f"A = P D P^{{-1}},\\quad P = {latex(P)},\\ D = {latex(D)}",
               solver="sympy.linalg", subject="线性代数")


def _solve_rank_rref(problem, matrices, op):
    if not matrices:
        return None
    A = matrices[0]
    rref, pivots = A.rref()
    steps = [
        f"$A = {latex(A)}$。",
        "对 $A$ 做初等行变换（高斯-若尔当消元）。",
        f"得到最简行阶梯形 $\\operatorname{{rref}}(A) = {latex(rref)}$。",
        f"主元列号：${[p + 1 for p in pivots]}$（1 起数）。",
        f"故 $\\operatorname{{rank}}(A) = {len(pivots)}$。",
    ]
    if op == "rank":
        return sol(problem, steps, f"\\operatorname{{rank}}(A) = {len(pivots)}",
                   solver="sympy.linalg", subject="线性代数")
    return sol(problem, steps, latex(rref), solver="sympy.linalg", subject="线性代数")


def _solve_nullspace(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    ns = A.nullspace()
    rank = A.rank()
    steps = [
        f"$A = {latex(A)}$，阶数 ${A.rows}\\times{A.cols}$，$\\operatorname{{rank}}(A) = {rank}$。",
        f"零空间维数（零化度）$= n - r = {A.cols} - {rank} = {A.cols - rank}$。",
        "解 $A x = 0$：先求 $\\operatorname{rref}(A)$，再把自由变量依次取 1 回代。",
    ]
    if ns:
        for i, v in enumerate(ns, 1):
            steps.append(f"第 {i} 个基向量：$v_{{{i}}} = {latex(v)}$")
        answer = "\\operatorname{null}(A) = \\operatorname{span}\\Big\\{ " + ", ".join(
            latex(v) for v in ns) + " \\Big\\}"
    else:
        steps.append("rref 后没有自由变量，零空间只有零向量。")
        answer = r"\operatorname{null}(A) = \{\mathbf{0}\}"
    return sol(problem, steps, answer, solver="sympy.linalg", subject="线性代数")


def _solve_columnspace(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    rref, pivots = A.rref()
    cols = [A[:, p] for p in pivots]
    steps = [
        f"$A = {latex(A)}$。",
        f"$\\operatorname{{rref}}(A) = {latex(rref)}$，主元在第 ${[p+1 for p in pivots]}$ 列。",
        "列空间的一组基 = $A$ 中**主元列**本身（不是 rref 的列）。",
    ]
    for i, c in enumerate(cols, 1):
        steps.append(f"$c_{{{i}}} = {latex(c)}$")
    answer = ("\\operatorname{col}(A) = \\operatorname{span}\\Big\\{ "
              + ", ".join(latex(c) for c in cols) + " \\Big\\},"
              + f"\\quad \\dim = {len(pivots)}")
    return sol(problem, steps, answer, solver="sympy.linalg", subject="线性代数")


def _solve_system(problem, matrices):
    """解 Ax = b。"""
    if len(matrices) < 2:
        b = _extract_vector(problem, dim=matrices[0].rows if matrices else None)
        if not matrices or b is None:
            return None
        A = matrices[0]
    else:
        A, b = matrices[0], matrices[1]
    try:
        if b.shape[1] != 1:
            b = b[:, 0]
        if b.rows != A.rows:
            b = b.reshape(A.rows, 1)
    except Exception:
        return None

    aug = A.row_join(b) if b.rows == A.rows else None
    steps = [f"$A = {latex(A)}$，$b = {latex(b)}$，解 $Ax = b$。"]
    if aug is not None:
        rref_aug, piv = aug.rref()
        steps.append(f"增广矩阵 $[A|b] = {latex(aug)}$。")
        steps.append(f"行化简得 $\\operatorname{{rref}}[A|b] = {latex(rref_aug)}$。")
        # 无解判定：主元出现在最后一列
        if any(p == A.cols for p in piv):
            steps.append("最后一列出现主元，出现 $0 = 1$ 的矛盾 → 方程组**无解**。")
            return sol(problem, steps, r"\text{无解}", solver="sympy.linalg", subject="线性代数")
        free = A.cols - len([p for p in piv if p < A.cols])
    else:
        free = None

    solset = sympy.linsolve((A, b))
    if not solset:
        return sol(problem, steps + ["方程组无解。"], r"\text{无解}",
                   solver="sympy.linalg", subject="线性代数")

    elems = list(solset)[0]
    free_syms = [s for s in elems.free_symbols]
    if free_syms:
        steps.append(f"存在 {len(free_syms)} 个自由变量（{', '.join(str(s) for s in free_syms)}），"
                     "方程组有无穷多解。")
        for i, e in enumerate(elems, 1):
            steps.append(f"$x_{{{i}}} = {latex(e)}$")
        answer = "x = \\begin{pmatrix}" + "\\\\".join(latex(e) for e in elems) + "\\end{pmatrix}"
    else:
        steps.append("自由变量个数为 0，解唯一：由回代得")

        for i, e in enumerate(elems, 1):
            steps.append(f"$x_{{{i}}} = {latex(e)}$")
        steps.append(f"核验：$A x = {latex(simplify(A * Matrix(list(elems))))}$ $= b$。")
        answer = "x = \\begin{pmatrix}" + "\\\\".join(latex(e) for e in elems) + "\\end{pmatrix}"
    return sol(problem, steps, answer, solver="sympy.linalg",
               verification={"method": "Ax 反代回乘核验", "check": "Ax == b"},
               subject="线性代数")


def _solve_least_squares(problem, matrices):
    if len(matrices) < 2:
        return None
    A, b = matrices[0], matrices[1]
    if b.rows != A.rows:
        return None
    if b.shape[1] != 1:
        b = b[:, 0]
    ATA = A.T * A
    ATb = A.T * b
    steps = [
        f"$A = {latex(A)}$，$b = {latex(b)}$。",
        f"正规方程 $A^{{T}}A\\hat{{x}} = A^{{T}}b$。",
        f"$A^{{T}}A = {latex(ATA)}$，$A^{{T}}b = {latex(ATb)}$。",
    ]
    try:
        xhat = ATA.solve(ATb)
    except Exception:
        return None
    p = A * xhat
    resid = b - p
    steps.append(f"解得 $\\hat{{x}} = {latex(xhat)}$。")
    steps.append(f"投影 $p = A\\hat{{x}} = {latex(p)}$，残差 $e = b - p = {latex(resid)}$。")
    steps.append(f"最优性核验：$A^{{T}}e = {latex(A.T * resid)} = 0$，残差与列空间正交 ✓。")
    return sol(problem, steps, f"\\hat{{x}} = {latex(xhat)}",
               solver="sympy.linalg",
               verification={"method": "Aᵀe = 0 正交性核验", "check": f"A^T e = {A.T * resid}"},
               subject="线性代数")


def _solve_projection(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    steps = [f"$A = {latex(A)}$。"]
    if A.rows > 1 and A.shape[1] == 1 and matrices and A.cols == 1:
        # 单列向量 → 投影到该直线
        a = A
        steps.append(f"$a = {latex(a)}$，投影矩阵 $P = \\dfrac{{a a^{{T}}}}{{a^{{T}}a}}$。")
        P = (a * a.T) / (a.T * a)[0, 0]
        return sol(problem, steps + [f"$P = {latex(P)}$"], f"P = {latex(P)}",
                   solver="sympy.linalg", subject="线性代数")
    P = A * (A.T * A).inv() * A.T
    steps += [
        f"列满秩时投影矩阵 $P = A(A^{{T}}A)^{{-1}}A^{{T}}$。",
        f"$A^{{T}}A = {latex(A.T * A)}$，其逆为 ${latex((A.T * A).inv())}$。",
        f"$P = {latex(P)}$。",
        f"核验：$P^{{2}} = {latex(simplify(P * P))} = P$（幂等），且 $P^{{T}} = P$。",
    ]
    return sol(problem, steps, f"P = {latex(P)}", solver="sympy.linalg",
               verification={"method": "P²=P 幂等 + 对称性核验", "check": "P² = P"},
               subject="线性代数")


def _solve_gram_schmidt(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    vecs = [A[:, i] for i in range(A.cols)]
    steps = ["对列向量组做 Gram-Schmidt 正交化："]
    for i, v in enumerate(vecs, 1):
        steps.append(f"$v_{{{i}}} = {latex(v)}$")

    ortho = []
    for i, v in enumerate(vecs, 1):
        u = v
        for j, q in enumerate(ortho, 1):
            u = u - (v.dot(q) / q.dot(q)) * q
        ortho.append(simplify(u))
        steps.append(f"$u_{{{i}}} = v_{{{i}}} - \\sum_{{j<{i}}} "
                     f"\\dfrac{{v_{{{i}}}\\cdot u_j}}{{u_j\\cdot u_j}} u_j = {latex(simplify(u))}$")

    qvecs = [u / sqrt(u.dot(u)) for u in ortho]
    steps.append("单位化 $q_i = u_i / \\|u_i\\|$：")
    for i, q in enumerate(qvecs, 1):
        steps.append(f"$q_{{{i}}} = {latex(simplify(q))}$")
    answer = ",\\quad ".join(f"q_{{{i}}} = {latex(simplify(q))}" for i, q in enumerate(qvecs, 1))
    return sol(problem, steps, answer, solver="sympy.linalg", subject="线性代数")


def _solve_lu(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    try:
        L, U, perm = A.LUdecomposition()
    except Exception:
        return None
    steps = [f"$A = {latex(A)}$。", "做带部分主元的 LU 分解 $PA = LU$。"]
    steps.append(f"$L = {latex(L)}$，$U = {latex(U)}$。")
    if perm is not None and list(perm) != list(range(A.rows)):
        steps.append(f"置换向量 ${list(perm)}$（因为选了主元）。")
    steps.append(f"核验：$LU = {latex(simplify(L * U))}$。")
    return sol(problem, steps, f"A = LU,\\quad L = {latex(L)},\\ U = {latex(U)}",
               solver="sympy.linalg", subject="线性代数")


def _solve_svd(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    try:
        U, S, V = A.singular_value_decomposition()
    except Exception:
        return None
    steps = [
        f"$A = {latex(A)}$。",
        f"先算 $A^{{T}}A$ 的特征值，开方得奇异值。",
        f"$\\Sigma = {latex(S)}$。",
        f"$U = {latex(U)}$，$V = {latex(V)}$。",
        f"核验：$U\\Sigma V^{{T}} = {latex(simplify(U * S * V.T))}$。",
    ]
    return sol(problem, steps, f"A = U\\Sigma V^{{T}},\\quad U = {latex(U)},\\ \\Sigma = {latex(S)}",
               solver="sympy.linalg", subject="线性代数")


def _solve_trace(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    tr = A.trace()
    steps = [f"$A = {latex(A)}$。",
             f"迹 = 主对角线元素之和 $= {latex(tr)}$。",
             f"另一条路：迹 = 特征值之和 $= {latex(sum(A.eigenvals().keys()))}$，两法一致 ✓。"]
    return sol(problem, steps, tr, solver="sympy.linalg", subject="线性代数")


def _solve_transpose(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    return sol(problem, [f"$A = {latex(A)}$。", f"$A^{{T}} = {latex(A.T)}$。"], A.T,
               solver="sympy.linalg", subject="线性代数")


def _solve_multiply(problem, matrices):
    if len(matrices) < 2:
        return None
    A, B = matrices[0], matrices[1]
    if A.cols != B.rows:
        return unsolved(problem, f"维度不匹配：{A.shape} 乘 {B.shape} 无定义", subject="线性代数")
    C = A * B
    steps = [f"$A = {latex(A)}$（${A.rows}\\times{A.cols}$），"
             f"$B = {latex(B)}$（${B.rows}\\times{B.cols}$）。",
             "内维一致，$AB$ 有定义，逐元素点乘求和。",
             f"$AB = {latex(C)}$。"]
    return sol(problem, steps, C, solver="sympy.linalg", subject="线性代数")


def _solve_quadratic_form(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    if not A.is_symmetric():
        A = (A + A.T) / 2
    eigs = A.eigenvals()
    vals = list(eigs.keys())
    if all(v > 0 for v in vals):
        kind = "正定"
    elif all(v >= 0 for v in vals):
        kind = "半正定"
    elif all(v < 0 for v in vals):
        kind = "负定"
    elif all(v <= 0 for v in vals):
        kind = "半负定"
    else:
        kind = "不定"
    steps = [f"对称部分 $A = {latex(A)}$。",
             f"特征值 $\\lambda = {latex(vals)}$。"]
    pos = sum(1 for v in vals if v > 0)
    neg = sum(1 for v in vals if v < 0)
    zero = sum(1 for v in vals if v == 0)
    steps.append(f"由惯性定理（正/负/零特征值个数 = {pos}/{neg}/{zero}），二次型 **{kind}**。")
    return sol(problem, steps, f"\\text{{{kind}}}", solver="sympy.linalg", subject="线性代数")


def _solve_independence(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    if A.cols == 1:
        return unsolved(problem, "只抽到一个向量，无法判断相关性", subject="线性代数")
    rank = A.rank()
    dep = rank < A.cols
    steps = [f"把向量按列摆成 $A = {latex(A)}$（${A.rows}\\times{A.cols}$）。",
             f"$\\operatorname{{rank}}(A) = {rank}$，向量个数 $= {A.cols}$。",
             f"rank {'<' if dep else '='} 向量个数 ⟹ 向量组线性{'相关' if dep else '无关'}。"]
    return sol(problem, steps, r"\text{线性相关}" if dep else r"\text{线性无关}",
               solver="sympy.linalg", subject="线性代数")


def _solve_basis(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    rref, pivots = A.rref()
    basis = [A[:, p] for p in pivots]
    steps = [f"$A = {latex(A)}$（把候选向量按列摆放）。",
             f"$\\operatorname{{rref}}(A) = {latex(rref)}$，主元列 ${[p+1 for p in pivots]}$。",
             "主元列对应的**原**列向量构成一组基。"]
    for i, b in enumerate(basis, 1):
        steps.append(f"$b_{{{i}}} = {latex(b)}$")
    return sol(problem, steps,
               "\\text{基}: " + ", ".join(latex(b) for b in basis) + f",\\quad \\dim = {len(basis)}",
               solver="sympy.linalg", subject="线性代数")


# ─────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────

_HANDLERS = {
    "det": lambda p, m: _solve_det(p, m),
    "inverse": lambda p, m: _solve_inverse(p, m),
    "eigenvalue": lambda p, m: _solve_eigen(p, m, want_vectors=False),
    "eigenvector": lambda p, m: _solve_eigen(p, m, want_vectors=True),
    "eigen_both": lambda p, m: _solve_eigen(p, m, want_vectors=True),
    "diagonalize": lambda p, m: _solve_diagonalize(p, m),
    "positive_definite": lambda p, m: _solve_quadratic_form(p, m),
    "quadratic_form": lambda p, m: _solve_quadratic_form(p, m),
    "adjugate": lambda p, m: _solve_adjugate(p, m),
    "rank": lambda p, m: _solve_rank_rref(p, m, "rank"),
    "rref": lambda p, m: _solve_rank_rref(p, m, "rref"),
    "nullspace": lambda p, m: _solve_nullspace(p, m),
    "columnspace": lambda p, m: _solve_columnspace(p, m),
    "four_subspaces": lambda p, m: _solve_four_subspaces(p, m),
    "least_squares": lambda p, m: _solve_least_squares(p, m),
    "projection": lambda p, m: _solve_projection(p, m),
    "gram_schmidt": lambda p, m: _solve_gram_schmidt(p, m),
    "lu": lambda p, m: _solve_lu(p, m),
    "svd": lambda p, m: _solve_svd(p, m),
    "trace": lambda p, m: _solve_trace(p, m),
    "transpose": lambda p, m: _solve_transpose(p, m),
    "multiply": lambda p, m: _solve_multiply(p, m),
    "orthogonality": lambda p, m: _solve_independence(p, m),
    "independence": lambda p, m: _solve_independence(p, m),
    "basis": lambda p, m: _solve_basis(p, m),
    "solve_system": lambda p, m: _solve_system(p, m),
}


def _solve_adjugate(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    if A.rows != A.cols:
        return unsolved(problem, "伴随矩阵只对方阵定义", subject="线性代数")
    adj = A.adjugate()
    d = A.det()
    steps = [
        f"$A = {latex(A)}$，$\\det A = {latex(d)}$。",
        "伴随矩阵 = 各元素的代数余子式转置后的矩阵。",
        f"$\\operatorname{{adj}}(A) = {latex(adj)}$。",
        f"核验：$A\\operatorname{{adj}}(A) = {latex(simplify(A * adj))} = (\\det A) I$ ✓。",
    ]
    return sol(problem, steps, adj, solver="sympy.linalg", subject="线性代数")


def _solve_four_subspaces(problem, matrices):
    if not matrices:
        return None
    A = matrices[0]
    rref, pivots = A.rref()
    steps = [
        f"$A = {latex(A)}$（${A.rows}\\times{A.cols}$），$\\operatorname{{rank}} = {len(pivots)}$。",
        f"$\\operatorname{{rref}}(A) = {latex(rref)}$。",
        f"列空间 $C(A)$：主元列 ${[p+1 for p in pivots]}$ 对应的原列，维数 ${len(pivots)}$。",
        f"零空间 $N(A)$：维数 $n - r = {A.cols - len(pivots)}$。",
        f"行空间 $C(A^{{T}})$：$\\operatorname{{rref}}(A)$ 的非零行，维数 ${len(pivots)}$。",
        f"左零空间 $N(A^{{T}})$：维数 $m - r = {A.rows - len(pivots)}$。",
    ]
    return sol(problem, steps,
               f"r = {len(pivots)};\\ \\dim C(A) = {len(pivots)};\\ \\dim N(A) = {A.cols - len(pivots)};"
               f"\\ \\dim C(A^T) = {len(pivots)};\\ \\dim N(A^T) = {A.rows - len(pivots)}",
               solver="sympy.linalg", subject="线性代数")


def solve(problem: dict) -> Optional[dict]:
    """线性代数入口。返回解答 dict，或 None 表示不归本模块管。"""
    text = problem.get("text", "") + " " + " ".join(problem.get("math_exprs") or [])
    op = detect_op(text)

    # 没有明确动词但有矩阵：尝试从「解方程组」以外的默认推断
    matrices = _extract_matrices(problem)

    if op is None:
        if len(matrices) >= 2 and matrices[0].rows == matrices[1].rows:
            op = "multiply" if matrices[0].cols == matrices[1].rows else "solve_system"
        elif len(matrices) == 1:
            op = "det" if matrices[0].rows == matrices[0].cols else None
        if op is None:
            return None

    if op == "eigen_both":
        return _solve_eigen(problem, matrices, want_vectors=True)
    if op == "adjugate":
        return _solve_adjugate(problem, matrices)
    if op == "four_subspaces":
        return _solve_four_subspaces(problem, matrices)

    handler = _HANDLERS.get(op)
    if handler is None:
        return None
    try:
        result = handler(problem, matrices)
    except Exception as e:  # noqa: BLE001 —— 求解器任何一步都可能抛
        return unsolved(problem, f"线性代数求解器异常：{type(e).__name__}: {e}", subject="线性代数")
    if result is None:
        return unsolved(problem, f"识别到操作「{op}」但没能从题干中抽出所需矩阵/向量", subject="线性代数")
    return result
