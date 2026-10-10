---
name: homework-solver
description: 作业自动求解与排版流水线。把 PDF / Word / Markdown / 图片形式的作业，端到端变成一份可提交的 PDF 解答（含完整推导步骤）。确定性计算走 SymPy（线性代数 / 微积分 / 微分方程 / 大学物理 / 概率统计五个学科），证明题与概念题走国产大模型（DeepSeek / Qwen / Kimi），最后排版成 LaTeX + HTML + PDF。当用户说「帮我做这份作业」「把这份试卷解出来并排版」「作业自动求解」，或给出作业文件（.pdf/.docx/.md/图片）并要求生成解答 PDF 时使用。
---

# homework-solver — 作业自动求解与排版

## 这是什么

一条五段式流水线：

```
作业文件  →  ①摄入  →  ②解析  →  ③求解  →  ④排版  →  ⑤编译  →  可提交 PDF
             md/pdf    题号/公式   SymPy×5学科   tex/html/md   三级降级
             docx/图片  题型分类     +国产大模型
```

**核心设计**：不是把题目丢给大模型让它写答案，而是
**先让确定性计算引擎（SymPy）能算多少算多少，算不动的才交给大模型**，
并且大模型的答案要过置信度门槛，低于阈值宁可标「未解」。

## 什么时候用 / 不用

| 用 | 不用 |
|----|------|
| 有明确题号的作业文件（`Problem 1` / `1.` / `题 1`） | 无结构的散文式题目描述 |
| 理工科计算题、证明题、概念题 | 需要看图的几何作图题（本流水线不做图形输出） |
| 想批量拿一份排版好的答案 | 想要「一次就对、不用审」的最终稿——**必须人工审阅** |

> ⚠️ **本技能产出的是「草稿」而不是「终稿」。** 即使是 90% 正确率的配置，
> 也意味着每 10 题有 1 题需要你核对。用它省下抄题和排版的时间，而不是省下检查的时间。

## 快速上手

```bash
# 装依赖
pip install -r requirements.txt

# 配国产大模型（不配也能跑，只是概念题/证明题会标「未解」）
export DEEPSEEK_API_KEY=sk-...        # 或 DASHSCOPE_API_KEY / MOONSHOT_API_KEY

# 一条命令
python scripts/pipeline.py 作业.pdf out/ --course "线性代数" --student "张三"
# 产物: out/homework.pdf / homework.tex / homework.html / homework.md + 三个中间 JSON
```

## 五个 Stage 各自做什么

### Stage 1 · 文档摄入 `ingest.py`
`md/txt/tex` 直读；`pdf` 走 **pdfplumber → pdftotext → pypdf** 三级降级；
`docx` 走 python-docx（含表格与标题样式）；`png/jpg` 走 Tesseract OCR（需另装）。
PDF 抽取后会做清洗：连字断行合并、页码/页眉剔除、题号提升成 Markdown 结构。

**边界**：扫描件（无文本层）会**明确报错**并告诉你怎么装 OCR，不会静默返回空文本。

### Stage 2 · 题目解析 `parse_problems.py`
识别 `Problem N` / `Question N` / `题 N` / `N.` / `N)` 与子题 `(a)(b)(c)`，
抽取 `$...$` 与 `$$...$$` 公式，按关键词分类题型。
（本文件来自 starter kit，见 `Songpengfei_C4C_拿来说明.md`。）

### Stage 3 · 自动求解 `solve.py` + `solvers/`
先判学科，再按这个顺序尝试：

| 学科 | 模块 | 覆盖 |
|------|------|------|
| 线性代数 | `solvers/linalg.py` | 行列式/逆/秩/RREF/零空间/特征值特征向量/对角化/最小二乘/投影/Gram-Schmidt/LU/SVD/二次型 |
| 微积分（极限） | `solvers/calculus_limits.py` | starter kit 原样保留（1596 行） |
| 微积分（其余） | `solvers/calculus_core.py` | 导数/隐函数/不定定积分/反常积分/泰勒/收敛半径/级数判敛/梯度/散度/旋度/最值/体积/弧长 |
| 微分方程 | `solvers/ode.py` | 一阶可分离/线性/伯努利、二阶常系数齐次非齐次、初值问题、拉普拉斯变换 |
| 大学物理 | `solvers/physics.py` | 30 条公式：运动学/牛顿/圆周/功能/动量/万有引力/库仑/欧姆/热学/振动/波动/光 |
| 概率统计 | `solvers/probability.py` | 期望方差/二项泊松正态/条件概率贝叶斯/协方差相关/线性回归/假设检验 |
| 证明·概念·文字 | `solvers/conceptual.py` | 国产大模型，强制 JSON 输出 + 置信度门槛 + 可选二次复核 |

判定不出来 → 转下一个模块 → 都不行才交给大模型。

### Stage 4 · 排版 `render.py`
同一份 `3_solutions.json` 出三种：`.tex`（专业排版）、`.html`（浏览器直接看，也是 PDF 的中间产物）、`.md`（快速扫读）。
每题标注**用了哪个求解器**和**置信度**。

### Stage 5 · 编译 `compile_pdf.py`
三级降级，保证一定有 PDF：

1. **LaTeX**：`xelatex` / `lualatex` / `pdflatex` / `tectonic`（装了 TeX 时质量最好）
2. **浏览器**：Edge / Chrome / Chromium headless + 本地 MathJax 渲染公式（Windows/macOS 自带，零安装）
3. **reportlab**：纯 Python，公式降级成 Unicode 文本（最后兜底）

编译完自动校验：页数、文件大小、文本层字符数。

## 常见用法

```bash
# 只用 SymPy，完全不碰大模型（最快，完全离线）
python scripts/pipeline.py hw.md out/ --no-llm

# 让模型对自己的答案做二次独立复核（更慢更准）
python scripts/pipeline.py hw.pdf out/ --verify

# 换国产模型
python scripts/pipeline.py hw.pdf out/ --provider qwen --model qwen-max
python scripts/pipeline.py hw.pdf out/ --provider kimi

# 指定 PDF 路径（没装 LaTeX 时用浏览器打印）
python scripts/pipeline.py hw.pdf out/ --tier browser

# 看每道题走了哪条求解路径
python scripts/pipeline.py hw.pdf out/ --explain

# 对照标准答案打分（需要 ground_truth.json）
python scripts/verify.py out/3_solutions.json my_ground_truth.json --md report.md
```

## 题目格式要求

```markdown
## Problems

Problem 1. Compute the determinant of $A = \begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}$.

Problem 2. 求 $\lim_{x \to 0} \frac{\sin x}{x}$。
```

题号也支持 `1.` / `1)` / `题 1` / `Q1`。子题用 `(a) (b) (c)` 或 `a. b. c.`。

## 复现性与离线运行

所有大模型响应落盘缓存在 `.llm_cache/`。**命中缓存时完全不联网、不需要 API Key**，
所以评审者拿到这个技能包后，即使没有 Key 也能逐字节复现出我们当时生成的 PDF。

```bash
# 没有 API Key 也能跑（只要有 .llm_cache）
python scripts/pipeline.py 作业.pdf out/
```

## 已知边界

1. **不输出图形**：需要画函数图/电路图的题只给文字描述，不出图。
2. **扫描件需自备 OCR**：Tesseract 不在默认依赖里。
3. **PDF 丢上标会误读**：`x²` 被抽成 `x2` 时 SymPy 会当成变量名，此时流水线**主动放弃**
   转交大模型（见 `Songpengfei_C4C_AI日志.md` B4）。
4. **物理题需要题干显式给出数值**：靠「数值 + 单位 + 近邻量名」抽取，纯符号的物理推导做不了。
5. **大模型会编**：答案里出现题干没给过的数值时，靠 `verify.py` 的数值比对和
   人工抽查抓（见验证报告里的 P5.h 案例）。

## 文件索引

```
SKILL.md              本文件
config.yaml           默认配置
requirements.txt      依赖
scripts/
  pipeline.py         一键流水线（Stage 1-5）
  ingest.py           Stage 1 文档摄入
  parse_problems.py   Stage 2 题目解析
  solve.py            Stage 3 求解总调度
  solvers/            各学科求解器
  render.py           Stage 4 三路排版
  compile_pdf.py      Stage 5 三级降级编译 + 校验
  verify.py           对照标准答案打分
  llm_engine.py       国产大模型客户端（DeepSeek/Qwen/Kimi）
  classify.py         本体分类器（来自 starter kit）
  retrieve.py         本体检索器（来自 starter kit）
  bootstrap.py        依赖自检（来自 starter kit）
domains/              领域本体 YAML（starter 的 calculus_limits.yaml）
references/           LaTeX 模板 / SymPy 速查 / MathJax
tests/                单元测试
.llm_cache/           大模型响应缓存（复现性的关键）
```
