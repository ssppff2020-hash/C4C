# C4C 正确性验证报告

> 作者：宋鹏飞（Songpengfei） ｜ 日期：2026-10-09
> 挑战 ID：`ch-20260717031447-k82c4m`
> 本文所有数字都可用 `README.md` 第五节的两条命令原样复现，不是估算。

---

## 一、结论速览

| # | 测试集 | 领域 | 引擎 | 条目 | 正确 | 正确率 |
|---|--------|------|------|------|------|--------|
| **A** | **MIT 18.06 PSET 1（真实作业）** | 线性代数（非极限） | **DeepSeek + SymPy** | 32 | **29** | **90.6%** |
| **B** | C4C 跨学科基准题集 | 线代/微积分/ODE/物理/概率 | **纯 SymPy（不调用大模型）** | 31 | **31** | **100%** |
| **A′** | Berkeley Worksheet 3+4（核心域回归） | 微积分极限 | SymPy（复用 starter 内核） | 18 | **17** | **94.4%** |
| **B′** | starter kit 自带示例作业 | 微积分极限 + 线代 + ODE | SymPy（starter 原版） | 10 | **1** | **10%** |
| **C′** | MIT 18.06 PSET 1 | 线性代数 | **starter kit 原版** | — | — | **无法启动** |

**基线对比（同一份文件、同一台机器）**

| 测试对象 | starter kit（Claude 时代的产物） | C4C（国产模型 + 扩展） |
|----------|--------------------------------|----------------------|
| MIT 18.06 PSET1（PDF） | ❌ Stage 1 直接报「PDF 摄入未实现」 | ✅ **29/32 = 90.6%**，产出可提交 PDF |
| C4C 跨学科基准 31 题 | ❌ **0/31** | ✅ **31/31 = 100%**（纯 SymPy） |
| starter 自带示例 10 题 | 1/10 = 10% | ✅ **10/10 = 100%** |
| Berkeley 极限（核心域） | 17/18 = 94.4% | ✅ **17/18 = 94.4%（逐题一致，零退化）** |

> 挑战文档里的 Claude 基线是「微积分极限域 94.4%」。本报告不做同域比较
> （小样本 + 那是 starter 自己声明的数字），而是**在同一个真实文件上做 A/B 对照**——
> 一份 PDF 作业，starter 读都读不了，C4C 交出 90.6% 的答案和一份可提交 PDF。

---

## 二、测试集 A：MIT 18.06 Problem Set 1（真实作业）

| 项 | 说明 |
|----|------|
| 原件 | [`samples/real/mit1806_pset1.pdf`](samples/real/mit1806_pset1.pdf) |
| 来源 | MIT 18.06 Linear Algebra, Spring 2020（Prof. Alan Edelman）官方课程网站 |
| 课程页 | https://web.mit.edu/18.06/www/Spring2020/ |
| 官方解答 | [`samples/real/mit1806_pset1_official-solutions.pdf`](samples/real/mit1806_pset1_official-solutions.pdf) |
| 标准答案 | [`samples/real/mit1806_pset1_ground_truth.json`](samples/real/mit1806_pset1_ground_truth.json)（逐条手工转录自官方解答） |
| 领域 | 线性代数 + 多元微积分预热（**明确不含微积分极限**，满足挑战的 Level 3 要求） |
| 输入格式 | **PDF**（文本型，由 pdfplumber 抽取） |
| 引擎 | DeepSeek `deepseek-chat`（OpenAI 兼容协议）+ SymPy |

### 2.1 逐条结果（32 条）

判定口径：`correct` 完全正确；`partial` 答对方法/概念但未给出所要求的最终形式；
`wrong` 答案与官方解答冲突；`unsolved` 未给出答案。

| 条目 | 判定 | 官方答案 | 本系统输出 | 由谁解出 |
|------|------|----------|-----------|----------|
| P1.a | ✅ | 1) unit vector | 1) unit vector | DeepSeek |
| P1.b | ✅ | 2) zero vector | 2) zero vector | DeepSeek |
| P1.c | ✅ | 4) all of the above | a, b, c 都正确（perpendicular, orthogonal, at right angles） | DeepSeek |
| P1.d | ❌ | 4) all of the above | （答成了整道题的汇总） | DeepSeek |
| P1.d2 | ✅ | True | True | DeepSeek |
| P1.e | ✅ | 2) 45 degrees | 45°（选项 2） | DeepSeek |
| P1.f | ✅ | 2 | det A = ±2 | DeepSeek |
| P2.a | ✅ | 3) plane not through 0 | 3) plane not through 0 | DeepSeek |
| P2.b | ✅ | (2,3,4) | (2,3,4) | DeepSeek |
| P2.c | ✅ | d) sphere | d) sphere | DeepSeek |
| P2.d | ❌ | **(2x,2y,2z)** | **(x,y,z)** | DeepSeek |
| P2.e | ✅ | (2,3,4) | $\begin{pmatrix}2\\3\\4\end{pmatrix}$ | **SymPy** |
| P2.f | ✅ | (2x,2y,2z) | ∇f = (2x, 2y, 2z) | DeepSeek（SymPy 主动让位，见 AI 日志 B4） |
| P2.g | ✅ | 平面 2x+3y+4z=2020 含原点的一侧 | 半空间 2x+3y+4z<2020 | DeepSeek |
| P3.a | ✅ | Yes | Yes, M₃(ℝ) is a real vector space | DeepSeek |
| P3.b | ✅ | No | No | DeepSeek |
| P3.c | ✅ | Yes | Yes | DeepSeek |
| P3.d | ✅ | Yes | Yes | DeepSeek |
| P3.e | ✅ | Yes | Yes | DeepSeek |
| P4.a | ✅ | Yes | Yes | DeepSeek |
| P4.b | ✅ | Yes | Yes, V={f \| f(0)=0} 是实向量空间 | DeepSeek |
| P4.c | ✅ | No | No | DeepSeek |
| P4.d | ✅ | Yes | Yes, V={f \| f(17)=0} 是实向量空间 | DeepSeek |
| P4.e | ✅ | No | No | DeepSeek |
| P5.a | ✅ | 225 | 225 | DeepSeek |
| P5.b | ✅ | 7.4162 / 31.2890 | √55 ≈ 7.416199 / √979 ≈ 31.288976 | DeepSeek |
| P5.c | ✅ | cos = 0.96964，θ = 14.1548° | cos θ = 0.9696，θ ≈ 14.17° | DeepSeek |
| P5.d | 🟡 | 用 `A\b` 解随机 4×4 方程组 | x = A⁻¹b | DeepSeek |
| P5.e | ✅ | 残差 ~1e-16 | b−Ax ≈ O(10⁻¹⁶) | DeepSeek |
| P5.f | ✅ | ×2⁵² 后是接近整数的数 | 接近整数的数 | DeepSeek |
| P5.g | ✅ | A² = [[30,36,42],[66,81,96],[102,126,150]] | **完全一致** | DeepSeek |
| P5.h | ❌ | (0.03496, 0.25162, 0.43774) | **(−0.5, 0.5, 0.5)** | DeepSeek |

**汇总**：正确 28 + 部分正确 1 = **29/32 = 90.6%**（加权正确率 89.1%）。
其中 P2.e 由 SymPy 精确求出，其余由 DeepSeek 求解。

### 2.2 三个错误 + 一个部分正确的根因（逐个交代，不合并成一句"准确率受限"）

#### ❌ P2.d —— 模型概念性错误
- **题**：球面 $x^2+y^2+z^2=1$ 的法向量是什么？
- **官方**：$(2x, 2y, 2z)$（梯度方向）
- **本系统**：$(x, y, z)$ —— 漏了系数 2。
- **根因**：纯模型推理错误。题目等价于问梯度，而紧邻的 P2.f 是在问 $x^2+y^2+z^2$ 的梯度，
  系统在 P2.f 答对了（∇f = (2x,2y,2z)），却在 P2.d 漏了系数。**同一个知识点，两问一对一错。**
- **为什么没被拦住**：`--verify` 的二次复核也没抓住——它只做"重算一致性"，
  没有把 P2.d 和 P2.f 的答案做交叉一致性检查。
- **改进方案**：同题组内若出现"同一表达式上两次求导/求梯度"，应做结果交叉校验并标红。
  已作为已知局限写入。

#### ❌ P5.h —— 模型在缺数据时编造数字（最危险的一类错误）
- **题**：给定具体的 3×3 矩阵 A 和向量 b（浮点数），求线性组合系数。
- **官方**：x = (0.03496, 0.25162, 0.43774)
- **本系统**：x = (−0.5, 0.5, 0.5)
- **根因**：**PDF 抽取时把 Julia 代码块里的矩阵数值丢了**（那几行是等宽字体排版的数字阵，
  pdfplumber 没能完整取出）。模型拿到的是"求这个矩阵的线性组合"但没有数值 →
  按"典型例题"编了一组整齐的数。
- **为什么没被拦住**：这道题**不该由模型解**——它本可以走 SymPy 精确求解，
  但输入数据在 Stage 1 就丢了。系统的置信度门槛也没触发（模型对自己编的答案信心很足）。
- **这暴露的真实缺陷**：**Stage 1 的抽取质量没有被校验**。
  现在 `verify.py` 的 `reject` 列表能事后抓到（报告里判错），但**事前没有拦截**。
- **改进方案**（已列入 roadmap）：Stage 3 增加"题干数值健全性检查"——
  题目要求数值答案但题干里一个数都没有 → 直接标未解，不问模型。

#### ❌ P1.d —— 输入解析产生的伪条目
- **题**：这道"题"在原件里根本不存在。PDF 中 `(c) ... d) all of the above.` 折行，
  解析器把尾行 `all of the above.` 当成了新的子题 `(d)`。
- **后果**：与真正的 `(d)` 撞 id（已用去后缀修复为 `d`/`d2`），且语义碎片被送去求解。
- **判定**：按标准答案表判错。**这是流水线的缺陷，不是模型的缺陷，如实记错。**
- **改进方案**：子题文本少于 4 个单词且不以大写字母开头时，应与上一子题合并。

#### 🟡 P5.d —— 部分正确
- 题目是 Julia 实操题（`x = A\b`，随机矩阵），没有唯一数值答案。
- 本系统答 `x = A⁻¹b`——**方法正确、数学等价**，但没有复现 Julia 的写法。
- 计入 `partial` 而非 `correct`，也不计为错误。

### 2.3 这道真实作业对"扩展学科"的验证意义

MIT PSET1 的价值在于它**不是一道为演示设计的题**：32 个小问里
包含选择题、判断题、向量空间判定、梯度计算、Julia 数值实验，
其中**只有 1 个能走 SymPy 精确路径**（P2.e），其余 31 个都必须由国产大模型完成。
这恰好证明了 C4C 的核心设计——**SymPy 与 LLM 的混合是有必要的，也不能互相替代**：
纯 SymPy 方案在 starter 上就是 0/32，纯 LLM 方案则会在数值题上失去可核验性。

---

## 三、测试集 B：C4C 跨学科基准题集（31 题，纯 SymPy，100%）

| 项 | 说明 |
|----|------|
| 题集 | [`samples/fixtures/domain_benchmark.md`](samples/fixtures/domain_benchmark.md) |
| 标准答案 | [`samples/fixtures/domain_benchmark_ground_truth.json`](samples/fixtures/domain_benchmark_ground_truth.json) |
| 引擎 | **纯 SymPy，`--no-llm`**（完全离线、零 API 成本、结果确定） |
| 明细报告 | [`output/benchmark/validation_benchmark.md`](output/benchmark/validation_benchmark.md) |

**设计意图**：把"扩展了哪些学科、扩展到什么程度"变成可量化的东西。
31 题覆盖 5 个学科，每题都有唯一、可手工复算的答案。

| 学科 | 题号 | 正确 |
|------|------|------|
| 线性代数 | P1–P8 | **8/8** |
| 微积分（导数/积分/级数/梯度） | P9–P15 | **7/7** |
| 微分方程（含拉普拉斯） | P16–P21 | **6/6** |
| 大学物理（力学/电磁/热/振动/波） | P22–P27 | **6/6** |
| 概率统计（期望/方差/分布/CDF） | P28–P31 | **4/4** |
| **合计** | | **31/31 = 100.0%** |

**同一批题在 starter kit 上：0/31 = 0%**（见 [`evidence/baseline_starter-on-benchmark.log`](evidence/baseline_starter-on-benchmark.log)）。

> ⚠️ **这个 100% 要说清楚它的边界**：基准题是**有标准答案的计算题**，
> 而且题型与我实现的求解分支一一对应。它衡量的是「确定性求解覆盖面」，
> **不能外推成"随便一份作业都能 100%"**。真实作业的正确率请以测试集 A（90.6%）为准。
> 这也正是我没有把它当作唯一证据、而是加做 MIT PSET1 的原因。

---

## 四、与 Claude 基线的对比（挑战明确要求）

挑战给出的 Claude 基线是：

| 测试集 | 领域 | Claude 版 starter kit |
|--------|------|----------------------|
| Berkeley Worksheet 3 | 切线 & ε-δ | 8/8 = 100% |
| Berkeley Worksheet 4 | 极限 | 9/10 = 90% |
| **核心域合计** | **微积分极限** | **17/18 = 94.4%** |
| 进阶挑战题（域外） | 积分/优化/组合/物理 | **2/5 = 40%** |

### 4.1 迁移到国产模型后，核心域有没有退化？——**实测：完全复现 94.4%**

starter kit 附带的 Berkeley Worksheet 3/4 原件不在本资料包内（`exemplar/` 目录为空），
但 `test_cases/` 里有两份等价的 Markdown 测试集。**同一份文件、同一台机器**分别跑两套流水线：

| 测试用例 | 域 | starter kit（Claude 基线） | **C4C（迁移后）** |
|----------|-----|---------------------------|------------------|
| `berkeley_test1_tangent_epsilon_delta.md` | 切线 & ε-δ | **8/8 = 100%** | **8/8 = 100%** ✅ |
| `berkeley_test2_limits.md` | 极限 | **9/10 = 90%** | **9/10 = 90%** ✅ |
| **核心域合计** | **微积分极限** | **17/18 = 94.4%** | **17/18 = 94.4%** ✅ |

**结论：核心域零退化，与挑战文档声明的 Claude 基线 17/18 = 94.4% 逐题一致。**

原因很简单，但值得明说：C4C 的极限求解路径**直接复用了 starter kit 的 `solve.py`**
（1596 行原封不动搬进 `solvers/calculus_limits.py`），迁移只发生在**域外**——
产品侧的 `pipeline.py` / `render.py` / 编译链换成了 C4C 的实现，
**极限求解内核一行没动**。这正是「拿来主义」的正确用法：**能不动的地方坚决不动**。

要复核：直接对照 starter kit 里的 `test1_answers_cn.pdf` / `test2_answers_cn.pdf`
（已复制到 `samples/fixtures/`），以及 `output/berkeley-test1/`、`output/berkeley-test2/` 的产物。

### 4.2 域外能力的提升（这才是迁移+扩展的价值所在）

| 能力 | Claude 版 starter kit | C4C（DeepSeek + SymPy） | 证据 |
|------|----------------------|------------------------|------|
| 微积分极限 | ✅ 94.4% | ✅ 原样保留（同一份代码） | `solvers/calculus_limits.py` |
| 积分 / 级数 | ⚠️ 域外（40% 档） | ✅ 覆盖 7 类（不定/定/反常/泰勒/收敛半径/判敛/梯度散度旋度） | 基准 P9–P15 = 7/7 |
| 线性代数 | ❌ 无 | ✅ 24 类操作 | 基准 P1–P8 = 8/8；MIT PSET1 90.6% |
| 微分方程 | ❌ 无 | ✅ 一阶/二阶/初值/拉普拉斯 | 基准 P16–P21 = 6/6 |
| 大学物理 | ❌ 无 | ✅ 30 条公式库 | 基准 P22–P27 = 6/6 |
| 概率统计 | ❌ 无 | ✅ 期望方差/分布/贝叶斯/回归/假设检验 | 基准 P28–P31 = 4/4 |
| **PDF 摄入** | ❌ `NotImplementedError` | ✅ pdfplumber→pdftotext→pypdf 三级 | MIT PSET1 成功摄入 4,749 字符 |
| **Word 摄入** | ❌ `NotImplementedError` | ✅ python-docx（段落+表格+样式） | `ingest.py` |
| **无 LaTeX 也能出 PDF** | ❌ 需要本机装 TeX | ✅ 三级降级（LaTeX→浏览器→reportlab） | 本机无 TeX，仍产出 3 页 PDF |
| **答案可核验** | ❌ 无对照机制 | ✅ `verify.py` 五档判定 + 置信度门槛 | 本报告 |

### 4.3 迁移质量：Claude ↔ DeepSeek 的实际差异（工程意义上的）

| 维度 | 观察 |
|------|------|
| 协议差异 | 几乎为零。两家都提供 OpenAI 兼容的 `/chat/completions`，**换 `base_url` + `model` 即可**。真正的迁移成本不在 SDK。 |
| 结构化输出 | DeepSeek 也会夹带 markdown 围栏和寒暄，**必须强制 JSON + 写一个容错的 `extract_json`**（三层兜底：直 parse → 去围栏 → 扫平衡花括号）。 |
| 拒答倾向 | 上下文不足时 DeepSeek 倾向于**明确拒答并说明缺什么**（而不是编）。这在本题里是优点——9 个拒答全部是"信息真的不足"，补上上下文后全部正常作答。 |
| 数值题可靠性 | 不稳定。P5.h 编造数值、P2.d 漏系数，都发生在数值题上。**结论：数值题必须走 SymPy，LLM 只做符号推理与解释。** |
| 延迟/成本 | 单题 1–3 秒，整份 PSET1（32 小问 + 二次复核）约 90 秒。响应全部落盘缓存，二次运行 3 秒。 |

---

## 五、验证方法本身的可信度

一个会把**正确答案判成错误**的验证器，其准确率数字毫无意义（开发中真的踩了这个坑，
见 [`Songpengfei_C4C_AI日志.md`](Songpengfei_C4C_AI日志.md) B8）。为此：

1. **判定规则显式化**：五档 `correct / partial / wrong / unsolved / manual`，
   规则写在 `verify.py` 顶部；`manual`（判不了）**不默认算对**，单独统计。
2. **不虚高的兜底**：`judge()` 遇到无法判定的情形一律返回 `manual`，
   在报告里单列并可由 `--llm-adjudicate` 交模型复核——**绝不静默计入正确**。
3. **有单元测试**：`tests/test_pipeline.py` 里有 9 条测试专门钉住打分逻辑
   （含"分数、列向量、LaTeX 噪声三种等价写法必须判对"，以及"判不出来必须是 manual 而不是 correct"）。
4. **标准答案有出处**：测试集 A 的标准答案逐条转录自 MIT 官方解答 PDF；
   测试集 B 的答案可手工复算。**没有一份标准答案是"我以为"**。

---

## 六、已知局限与改进路线

| # | 局限 | 影响 | 计划 |
|---|------|------|------|
| 1 | **PDF 抽取会丢等宽字体里的数字** | P5.h 因此判错（模型编造数值） | Stage 1 后加「题干数值健全性检查」：要数值答案但题干无数 → 直接标未解 |
| 2 | **同题组内不做交叉一致性检查** | P2.d 漏系数未被拦住 | 同表达式多次求梯度/导数时交叉校验 |
| 3 | **折行子题会被切成伪条目** | P1.d 判错 | 子题文本 < 4 词且首字母小写 → 合并到上一子题 |
| 4 | **物理题依赖题干显式数值** | 纯符号的物理推导做不了 | 增加符号形式的物理方程求解 |
| 5 | **不做图形输出** | 画图题只给文字描述 | 接 matplotlib 出函数图/向量场 |
| 6 | **扫描件需自备 Tesseract** | 本机未装，未测试 | 补 OCR 路径的端到端测试 |
| 7 | **Berkeley Worksheet 原件缺失** | 无法在同域上与 Claude 基线做严格 A/B | 若能拿到原件，补一份同域对照 |

---

## 七、复现命令

```bash
cd C4C

# ── 测试集 A：MIT 18.06 PSET1（真实作业，走缓存，无 API Key 也能跑）──
python skill-src/homework-solver/scripts/pipeline.py \
    samples/real/mit1806_pset1.pdf output/MIT18.06-PS1 \
    --course "18.06 Linear Algebra (MIT OCW, Spring 2020)" \
    --student "Songpengfei" --title "Problem Set 1 Solutions" --verify

python skill-src/homework-solver/scripts/verify.py \
    output/MIT18.06-PS1/3_solutions.json \
    samples/real/mit1806_pset1_ground_truth.json \
    --out output/MIT18.06-PS1/validation_mit_pset1.json \
    --md  output/MIT18.06-PS1/validation_mit_pset1.md \
    --llm-adjudicate
# 期望：条目 32｜正确 28／部分 1／错误 3｜宽松正确率 90.6%
# 注：--llm-adjudicate 也不需要 API Key（复核 prompt 与响应已在缓存里）

# ── 测试集 B：跨学科基准（纯 SymPy，完全离线）──
python skill-src/homework-solver/scripts/pipeline.py \
    samples/fixtures/domain_benchmark.md output/benchmark --no-llm
python skill-src/homework-solver/scripts/verify.py \
    output/benchmark/3_solutions.json \
    samples/fixtures/domain_benchmark_ground_truth.json
# 期望：条目 31｜正确 31｜100.0%

# ── 测试集 A′：核心域回归（Berkeley 极限，验证迁移零退化）──
python skill-src/homework-solver/scripts/pipeline.py \
    samples/fixtures/berkeley_test1_tangent_epsilon_delta.md output/berkeley-test1 --no-llm
# 期望：已解 8/8 (100.0%)
python skill-src/homework-solver/scripts/pipeline.py \
    samples/fixtures/berkeley_test2_limits.md output/berkeley-test2 --no-llm
# 期望：已解 9/10 (90.0%)
# → 合计 17/18 = 94.4%，与 starter kit 逐题一致

# ── 测试集 B′/C′：starter kit 基线 ──
STARTER=../_work/starter/c4c-homework-solver-starter
python $STARTER/scripts/pipeline.py $STARTER/examples/sample_homework.md /tmp/s
# 期望：已解 1 道 (10%)
python $STARTER/scripts/pipeline.py samples/fixtures/domain_benchmark.md /tmp/s3
# 期望：已解 0 道 (0%)
python $STARTER/scripts/pipeline.py samples/real/mit1806_pset1.pdf /tmp/s2
# 期望：❌ 摄入失败: PDF 摄入未实现
```
