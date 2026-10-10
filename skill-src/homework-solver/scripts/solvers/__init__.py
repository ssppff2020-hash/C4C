"""
solvers/ —— C4C 学科求解器集合

    base.py             公共地基：LaTeX→SymPy 解析、统一解答结构
    calculus_limits.py  【拿来】starter kit 原样保留的微积分极限求解器（1596 行）
    calculus_core.py    【新增】导数/积分/级数/多元微积分
    linalg.py           【新增】线性代数
    ode.py              【新增】常微分方程 + 拉普拉斯变换
    physics.py          【新增】大学物理（公式匹配 + 量纲检查）
    probability.py      【新增】概率统计
    conceptual.py       【迁移】国产大模型推理求解器（替代 Claude）

每个模块都暴露 `solve(problem: dict) -> Optional[dict]`：
    返回 dict  = 本模块接管了这道题
    返回 None  = 不归我管，交给下一个模块
"""

__all__ = [
    "base",
    "calculus_limits",
    "calculus_core",
    "linalg",
    "ode",
    "physics",
    "probability",
    "conceptual",
]
