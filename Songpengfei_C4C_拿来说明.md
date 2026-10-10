# C4C 拿来说明（Attribution）

> 作者：宋鹏飞（Songpengfei） ｜ 日期：2026-10-09
> 挑战要求：「必须从 starter kit 出发。说明你拿了什么、改了什么、
> Claude 版本与你的国产模型版本有何差异。」
> 本文逐文件交代。

---

## 一、总览：拿了什么、改了什么

```
starter kit（Claude 基线）              C4C（国产模型版）
─────────────────────────              ──────────────────────────────────
scripts/solve.py       1596 行   →      solvers/calculus_limits.py  【原样保留】
scripts/classify.py     314 行   →      scripts/classify.py         【原样保留】
scripts/retrieve.py     167 行   →      scripts/retrieve.py         【原样保留】
scripts/bootstrap.py    130 行   →      scripts/bootstrap.py        【保留但不再自动 pip】
scripts/parse_problems.py 372 行 →      scripts/parse_problems.py   【原样保留】
scripts/render_latex.py 345 行   →      scripts/render.py           【重写】
scripts/ingest.py       194 行   →      scripts/ingest.py           【重写】
scripts/pipeline.py     208 行   →      scripts/pipeline.py         【重写】
references/homework_template.tex →      references/homework_template.tex 【保留】
domain_skills/calculus_limits.yaml →    domains/calculus_limits.yaml 【保留】
                                        ─────────────────────────────────
                                        scripts/llm_engine.py       【新增】国产模型客户端
                                        scripts/solve.py            【新增】混合路由总调度
                                        scripts/compile_pdf.py      【新增】三级降级编译
                                        scripts/verify.py           【新增】正确性验证
                                        solvers/{linalg,ode,physics,probability,
                                                 calculus_core,conceptual}.py 【新增】
                                        domains/ ……                【新增】4 个新学科的知识文件
```

**一句话**：**能不动的地方一行没动**（极限求解内核、分类器、检索器、本体 YAML），
改动集中在「starter 明确留白的地方」和「starter 做不了的地方」。

---

## 二、逐项说明

### 2.1 【原样保留】`solvers/calculus_limits.py` ← starter `scripts/solve.py`

- **拿了什么**：全部 1596 行。包括 `safe_parse`、`solve_epsilon_delta`、
  `_solve_limit_subs`、`solve_limit`、`solve_tangent`、`solve_conceptual` 的模板分支、
  `_classify_sub` 等。
- **改了什么**：**一个字节都没改。** 只是重命名成 `calculus_limits.py`
  （因为它现在只是 5 个学科模块中的一个，名字必须表明它只管极限）。
  可以用下面这条命令核对：

  ```bash
  diff _work/starter/c4c-homework-solver-starter/scripts/solve.py \
       C4C/skill-src/homework-solver/scripts/solvers/calculus_limits.py
  # → 无输出（逐字节一致）
  ```
- **为什么不动**：这是**经过 Berkeley 真实试卷验证的核心域内核**（17/18 = 94.4%）。
  挑战实测：迁移后 C4C 在这两份测试集上仍是 8/8 与 9/10，**逐题一致**。
  「迁移」不该等于「重写」——**改一个已经验证过的内核，收益未知、风险确定**。
- **入口适配**：C4C 的调度器（`solve.py`）在路由到极限域时调用它的 `solve_problem()`；
  同时 C4C 的 `normalize_problem()` 会**同时提供** `math_expressions`（starter 期望的
  `[{type, latex}]` 结构）和 `math_exprs`（新求解器期望的 `[str]` 结构），
  所以两代求解器能共存而不需要改 starter 的代码。

### 2.2 【原样保留】`scripts/classify.py` / `scripts/retrieve.py` / `domains/calculus_limits.yaml`

- **拿了什么**：starter 的**本体（TBox）驱动的分类-检索架构**：
  18 条分类规则写在 YAML 里，代码只负责读规则、抽特征、匹配。
- **改了什么**：无——**逐字节一致**（`diff` 为 0 行）。
- **从中学到的、并沿用到新学科上的东西**：**「能力 = 领域知识覆盖度，不是代码复杂度」**。
  starter 的 README 里这句话是它最有价值的洞见。
  C4C 把它落到了实处——**新增的 4 个学科也全部用同一种组织方式**：
  知识（公式表、操作模式）写在声明式的数据里，求解逻辑保持通用。
  例如 `solvers/physics.py` 的 `FORMULAS` 就是一个 30 条的声明式公式库，
  加一条公式不需要理解求解器内部。

### 2.3 【重写】`scripts/ingest.py` ← starter `scripts/ingest.py`

- **starter 的状态**：`read_pdf_text` / `read_docx` / `read_image_ocr` 三个函数
  直接 `raise NotImplementedError("学生扩展点")`——**只有 Markdown 能用**。
- **改了什么**：
  | 能力 | starter | C4C |
  |------|---------|-----|
  | Markdown / TXT | ✅ | ✅ |
  | **PDF** | ❌ 未实现 | ✅ **pdfplumber → pdftotext → pypdf 三级降级** |
  | **Word .docx** | ❌ 未实现 | ✅ python-docx（段落 + 表格 + 标题样式） |
  | 图片 OCR | ❌ 未实现 | ⚠️ 走 pytesseract（需另装 Tesseract），缺失时**明确报错并给安装指引** |
  | PDF 文本清洗 | — | ✅ 连字断行合并 / 页眉页码剔除 / Unicode 规范化 / 题号提升成 Markdown 结构 |
- **验证**：MIT 18.06 PSET1（3 页 PDF，4,749 字符）成功摄入并解析出 **5 大题 32 小问**；
  starter 在同一个文件上直接报 `PDF 摄入未实现`。

### 2.4 【原样保留】`scripts/parse_problems.py` ← starter `scripts/parse_problems.py`

- **改了什么**：无。
- **为什么**：它的题号识别（`Problem N` / `题 N` / `N.` / `N)`）和公式抽取
  在 PDF 文本上表现良好（MIT PSET1 一次解析出 5 大题 32 小问）。
- **唯一的上游配合**：C4C 的 `ingest.py` 在 PDF/Word 抽取后**主动补一个 `## Problems` 标题**，
  因为 starter 的解析器靠 Markdown 标题分段，而 PDF 里没有标题。
  **不改解析器，改喂给它的输入**——这是更小的改动面。

### 2.5 【重写】`scripts/render_latex.py` → `scripts/render.py`

- **starter 的状态**：只出 `.tex`；只认「题目 + 解答」两段；
  答案直接塞 `latex()` 的结果（**不带 `$...$`**，见 AI 日志 B7）。
- **改了什么**：
  1. **三路输出**：`.tex`（专业排版）+ `.html`（浏览器直读，也是 PDF 的中间产物）+ `.md`；
  2. **新增求解元信息**：每题标注用了哪个求解器、置信度、验证方式——
     这是对挑战「输出可核验」要求的正面回应；
  3. **`ensure_math()`**：自动给裸 LaTeX 答案补 `$...$` 定界符；
  4. **中文支持**：`.tex` 侧用 ctexart（xelatex），`.html` 侧用系统 CJK 字体，
     都不需要用户额外配置。
- **保留了什么**：starter 的 `homework_template.tex` 结构与 `escape_latex` 的分段转义思路
  （`re.split(r"(\$\$.*?\$\$|\$.*?\$)", ...)` 保留数学段不转义）被沿用。

### 2.6 【重写】`scripts/pipeline.py` ← starter `scripts/pipeline.py`

- **starter 的状态**：五段串联，但 Stage 1 只能吃 Markdown，Stage 5 失败就让你上 Overleaf。
- **改了什么**：
  1. **不再自动 pip 安装**：starter 的 `bootstrap.ensure_dependencies()` 会在导入时
     自动 `pip install`。这在别人的机器上是**侵入性行为**，C4C 改成只检测 + 提示。
  2. **PDF 编译三级降级**（见 2.7）；
  3. **产物自检写进 `summary.json`**：页数、文本层字符数、各阶段统计，
     供验证报告直接引用；
  4. `--explain` 打印每道题的求解路径。

### 2.7 【新增】`scripts/compile_pdf.py` —— starter 完全没有这一级

- **starter 的做法**：`subprocess` 调 `pdflatex`，失败就打印「请上传 Overleaf」。
  而**学生机器上绝大多数没有 LaTeX**——这等于最后一步必定断掉。
- **C4C 的做法**：三级降级，保证一定有 PDF。
  | 级别 | 方案 | 依赖 | 本机是否可用 |
  |------|------|------|-------------|
  | Tier 1 | `xelatex` / `lualatex` / `pdflatex` / `tectonic` | 需装 TeX | ❌ 本机没有 |
  | Tier 2 | **Edge / Chrome headless + 本地 MathJax** | 系统自带 | ✅ **本机走这条** |
  | Tier 3 | `reportlab` + 系统 CJK 字体 | pip 装 | ⏸ 兜底 |
- **Tier 2 的巧思**：把作业渲染成 HTML，公式交给**随包分发的 MathJax**
  （`references/mathjax/tex-svg.js`，2.1 MB，渲染成 SVG 不依赖外部字体），
  再用浏览器 `--print-to-pdf` 打印。**零额外安装、公式质量接近 LaTeX、完全离线。**
  本机没有 TeX，仍然产出了 3 页的高质量 PDF。
- **Tier 3 的诚实**：`reportlab` 渲染不了 LaTeX 公式，所以它会把公式
  **降级成 Unicode 纯文本**（`\frac{1}{2}` → `(1)/(2)`，`\alpha` → `α`）。
  不好看，但**能用**——报告里会明确标注当前用的是哪一级。

### 2.8 【新增】`scripts/llm_engine.py` —— Claude → 国产模型的迁移落点

- **starter 的推理**在 Claude Code 里是隐式的：没有代码，就是 Claude 在会话里解题。
  所以"迁移"意味着**把这部分显式地代码化**。
- **设计**：
  - 三家国产模型统一走 OpenAI 兼容协议，只换 `base_url` + `model`（Provider 注册表）；
  - **强制结构化输出**（JSON schema），因为不强制的话国产模型会写散文；
  - **容错的 `extract_json`**（三层兜底：直 parse → 去 markdown 围栏 → 扫平衡花括号）；
  - **响应落盘缓存**，命中时不需要 API Key、不联网 → 可离线复现；
  - **优雅降级**：没有 Key 时不报错，只把该走的题标成「未配置 LLM 而未求解」。
- **迁移中最关键的一条经验**：**prompt 里必须带大题上下文**。
  把 PDF 拆出的小问单独丢给模型，它会拒答（因为信息真的不够）。
  补上「大题原文 + 兄弟小问」后，MIT PSET1 的拒答从 9 个降到 0 个。
  这一条对任何模型都成立，但在"碎片化输入"的场景下尤其致命。

### 2.9 【新增】5 个学科求解器

| 模块 | 行数 | 覆盖 |
|------|------|------|
| `solvers/base.py` | ~430 | LaTeX→SymPy 零依赖解析器、统一解答结构、符号工具 |
| `solvers/calculus_core.py` | ~560 | 导数/隐函数/不定定反常积分/泰勒/收敛半径/判敛/梯度/散度/旋度/最值/体积/弧长 |
| `solvers/linalg.py` | ~560 | 24 类操作：行列式→逆→秩→RREF→零空间→特征→对角化→最小二乘→投影→Gram-Schmidt→LU→SVD→二次型 |
| `solvers/ode.py` | ~340 | 一阶可分离/线性/伯努利、二阶常系数、初值问题、拉普拉斯变换 |
| `solvers/physics.py` | ~430 | 30 条公式：运动学/牛顿/圆周/功能/动量/万有引力/库仑/欧姆/热学/振动/波动/光学 |
| `solvers/probability.py` | ~420 | 期望方差/二项泊松正态/条件概率贝叶斯/协方差相关/回归/假设检验 |
| `solvers/conceptual.py` | ~150 | 国产大模型推理（证明/概念/文字题）+ 置信度门槛 + 二次复核 |

**共享的设计约束**（每个模块都必须遵守）：
1. `solve(problem) -> dict | None`；返回 `None` 表示「不归我管」；
2. 认领了但解不出，必须返回 **unsolved + 明确原因**，不能返回 `None` 装死；
3. **不确定就退出**——可疑的解析结果宁可交给下一个模块，也不输出（AI 日志 B4 的教训）。

### 2.10 【新增】`scripts/verify.py` —— starter 完全没有

starter 声明了 94.4% 的准确率，但**资料包里没有产生这个数字的代码**，
只有一份 `validation_report.md`（且该文件实际不在包内）。
C4C 把它做成**可复现的实验**：标准答案 JSON + 五档判定 + 方差/部分分的显式口径。

---

## 三、外部库：用了什么、为什么

| 库 | 用途 | 为什么不自己写 |
|----|------|---------------|
| **SymPy** | 全部符号计算 | 重造符号计算轮子是纯粹的浪费 |
| **pdfplumber** | PDF 文本抽取（首选） | 纯 Python、跨平台、保留版面 |
| **pdftotext** (poppler) | PDF 抽取（二级） | 比 pdfplumber 快，且 pdfplumber 对某些字体失败时它常常能出 |
| **pypdf** | PDF 抽取（三级） | 最轻量，最后的希望 |
| **python-docx** | Word 摄入 | 唯一成熟的 .docx 读写库 |
| **reportlab** | PDF 生成（兜底） | 纯 Python，无外部依赖，一定能装上 |
| **pypdfium2** | 编译后校验 PDF（页数/文本层） | 也是把 PDF 渲染成图做人工核对的工具 |
| **MathJax** (`tex-svg.js`) | 浏览器侧的公式渲染 | Apache-2.0，单文件、SVG 输出、**不依赖外部字体文件**，可离线 |
| **PyYAML** | 读 config.yaml 与领域本体 | 标准选择 |

**没有用 `openai` SDK**：直接用标准库 `urllib` 发 HTTP。
理由：学生的服务器环境常常装不上额外 SDK，而 OpenAI 兼容协议就是一个 POST。**零依赖更好活。**

**没有用 `sympy.parsing.latex.parse_latex`**：它依赖 `antlr4` 运行时（本机没有）。
所以 `solvers/base.py` 里手写了一个零依赖的 LaTeX→SymPy 转换器，
反而比 antlr 版本更可控（本项目的 15 个 bug 里有 3 个出在它身上，但每一个都修好并有单测钉住）。

---

## 四、Claude 版 vs 国产模型版：差异清单

| 维度 | Claude 版 starter kit | C4C 国产模型版 | 差异性质 |
|------|----------------------|---------------|---------|
| **推理引擎** | Claude（隐式，在会话里） | **DeepSeek**（显式代码，`llm_engine.py`） | 迁移的核心 |
| **可切换性** | 绑定 Claude Code | 改 `--provider` 即换 Qwen / Kimi | **架构升级** |
| **结构化输出** | 靠 Claude 自觉 | **强制 JSON + 三层容错解析** | 模型差异倒逼 |
| **答案可信度** | 无门槛 | **置信度 < 0.4 判为未解** + 可选二次复核 | 明确的可核验性 |
| **输入格式** | 仅 Markdown | Markdown / TXT / **PDF** / **Word** / 图片 | 补齐留白 |
| **学科覆盖** | 微积分极限 | 极限 + **微积分其余 + 线代 + ODE + 物理 + 概率** | 扩展 |
| **求解策略** | 全走 SymPy | **SymPy 优先，算不动才给 LLM，且要过置信度门槛** | 新的架构决策 |
| **PDF 输出** | 需本机装 TeX | **三级降级，无 TeX 也能出** | 可用性 |
| **正确性度量** | 一次性声明（94.4%） | **`verify.py` 可复现的逐条判定** | 可核验性 |
| **可复现性** | 无机制 | **响应缓存 → 离线逐字节复现** | 可复现性 |
| **核心域表现** | 17/18 = 94.4% | **17/18 = 94.4%（逐题一致）** | **零退化** |
| **域外表现** | 2/5 = 40%（自述） | MIT PSET1 真实作业 **29/32 = 90.6%** | 显著提升 |

---

## 五、许可与出处

| 内容 | 出处 | 许可 / 说明 |
|------|------|------------|
| starter kit 全部代码与本体文件 | 本挑战资料包 `materials/c4c-homework-solver-starter.zip` | 挑战方提供，供学生使用 |
| MIT 18.06 PSET 1 题目与官方解答 | https://web.mit.edu/18.06/www/Spring2020/ | MIT 课程公开材料，仅作教学验证用途 |
| Berkeley Math 1A Worksheet 3/4 测试集 | 随 starter kit 分发的 `test_cases/` | 同上 |
| MathJax 3 (`tex-svg.js`) | https://www.npmjs.com/package/mathjax | **Apache License 2.0**，已随包分发 |
| SymPy / pdfplumber / python-docx / reportlab / pypdfium2 | 各自官方仓库 | BSD / MIT / 各自开源许可 |
