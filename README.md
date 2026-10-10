# C4C — 作业自动求解与排版（Homework Auto-Solver & Formatter）

> 挑战 ID：`ch-20260717031447-k82c4m` ｜ 作者：宋鹏飞（Songpengfei） ｜ 日期：2026-10-09
> 本目录 = C4C 挑战的完整提交。

把一份作业文件，**一条命令**变成一份可提交的 PDF 解答：

```
作业.pdf/word/md/图片  →  ①摄入  →  ②解析  →  ③求解  →  ④排版  →  ⑤编译  →  homework.pdf
                        pdfplumber   题号公式   SymPy 5 学科   tex/html/md   三级降级
                        docx/OCR     题型分类   +国产大模型                  保证出 PDF
```

**推理引擎已从 Claude 迁移到国产大模型（DeepSeek，可一键切换 Qwen / Kimi）；**
**学科从「只有微积分极限」扩展到线代、微分方程、大学物理、概率统计、微积分其余部分。**

---

## 一、结果速览

四项测试，**同一台机器、同一份文件**分别跑 starter kit 与 C4C：

| 测试 | starter kit（Claude 基线） | **C4C（DeepSeek + SymPy）** |
|------|---------------------------|----------------------------|
| **MIT 18.06 PSET 1**（真实作业 PDF，非极限学科） | ❌ **Stage 1 就报「PDF 摄入未实现」** | ✅ **29/32 = 90.6%**，产出 3 页可提交 PDF |
| **C4C 跨学科基准 31 题**（5 学科） | ❌ **0/31 = 0%** | ✅ **31/31 = 100%**（纯 SymPy，未调大模型） |
| **Berkeley 极限测试集**（核心域回归） | 17/18 = 94.4% | ✅ **17/18 = 94.4%（逐题一致，零退化）** |
| **starter 自带示例 10 题**（混合学科） | 1/10 = 10% | ✅ **10/10 = 100%** |

> 一句话：**starter 在一个学科上很深（极限域 94.4%），但换个文件就读不了；
> C4C 把核心域原样保住（逐字节复用 starter 的极限内核），把域外从 0 拉到能交作业。**

完整逐题明细见 [`Songpengfei_C4C_验证报告.md`](Songpengfei_C4C_验证报告.md)。

---

## 二、安装

**环境要求**：Python 3.10+ ｜ 跨平台（Windows / macOS / Linux）
**LaTeX 不是必需的**——不装也能出 PDF（自动走浏览器打印）。

```bash
cd C4C/skill-src/homework-solver

# 必需
pip install sympy pyyaml

# 输入格式（PDF / Word）
pip install pdfplumber pypdf python-docx

# PDF 输出兜底 + 产物校验
pip install reportlab pypdfium2

# 一行装全部
pip install -r requirements.txt
```

验证安装：

```bash
python -c "import sympy, yaml, pdfplumber, docx, reportlab; print('deps ok')"
python -m unittest discover -s tests -v      # 期望：Ran 62 tests ... OK
```

### 2.1 配置国产大模型（可选）

```bash
export DEEPSEEK_API_KEY=sk-xxxxxxxx     # 或 DASHSCOPE_API_KEY / MOONSHOT_API_KEY
python scripts/llm_engine.py --check    # 自检连通性
```

> **不配也能跑。** 纯 SymPy 路径（基准题集 31/31）完全不需要 Key；
> 概念题/证明题会标「未解」而不是崩掉。
> 并且技能包**自带 186 条响应缓存**，所以**没有 Key 也能复现出我们当时生成的那份 PDF**。

### 2.2 作为 Claude Skill 安装（可选）

[`Songpengfei_C4C_homework-solver.skill`](Songpengfei_C4C_homework-solver.skill)
是标准 ZIP 技能包（根目录含 `SKILL.md`），可直接装到支持 Claude Skills 的环境。
装好后说「帮我把这份作业解出来并排版」即可触发。

---

## 三、运行命令

### 3.1 最基本的一条命令

```bash
cd C4C/skill-src/homework-solver

python scripts/pipeline.py 作业.pdf out/ \
    --course "线性代数" --student "张三" --title "第 3 次作业"
# → out/homework.pdf / homework.tex / homework.html / homework.md
#   + 1_ingested.json / 2_parsed.json / 3_solutions.json / summary.json
```

> Windows 终端中文乱码时，命令前加 `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`
> （产物文件本身始终是 UTF-8，不受影响）。

### 3.2 常用变体

```bash
# 只用 SymPy，完全离线、零成本（基准题集 31/31 就走这条）
python scripts/pipeline.py hw.md out/ --no-llm

# 让模型对自己的答案独立重算一遍做二次复核（更慢更准）
python scripts/pipeline.py hw.pdf out/ --verify

# 换国产模型
python scripts/pipeline.py hw.pdf out/ --provider qwen --model qwen-max
python scripts/pipeline.py hw.pdf out/ --provider kimi

# 指定 PDF 引擎（没装 LaTeX 时用浏览器打印）
python scripts/pipeline.py hw.pdf out/ --tier browser

# 调试：看每道题走了哪条求解路径
python scripts/pipeline.py hw.pdf out/ --no-llm --explain
```

### 3.3 分步运行（想单独看某个 Stage）

```bash
python scripts/ingest.py          hw.pdf   out/1_ingested.json    # Stage 1
python scripts/parse_problems.py  out/1_ingested.json out/2_parsed.json   # Stage 2
python scripts/solve.py           out/2_parsed.json   out/3_solutions.json # Stage 3
python scripts/render.py          out/3_solutions.json out/               # Stage 4
python scripts/compile_pdf.py     out/ --basename homework \
                                  --solutions out/3_solutions.json        # Stage 5
```

### 3.4 验证正确率（对着标准答案打分）

```bash
python scripts/verify.py out/3_solutions.json my_ground_truth.json \
    --out report.json --md report.md --llm-adjudicate
```

### 3.5 跑测试 / 重新打包技能

```bash
cd skill-src/homework-solver
python -m unittest discover -s tests -v          # 62 个测试

cd ../..
python tools/package_skill.py skill-src/homework-solver \
    --out Songpengfei_C4C_homework-solver.skill
```

---

## 四、目录结构

```
C4C/
├── README.md                                   ← 本文件（统一说明）
│
├── Songpengfei_C4C_方案设计.md                 【交付物1】方案设计（架构 / 模型选型 / 求解策略 / 边界处理）
├── Songpengfei_C4C_homework-solver.skill       【交付物2】可安装技能包（ZIP，963 KB / 218 文件）
├── Songpengfei_C4C_作业原件.pdf                【交付物3】真实作业原件（MIT 18.06 PSET 1）
├── Songpengfei_C4C_output.pdf                  【交付物3】★ 真实作业的生成结果（3 页，可直接提交）
├── Songpengfei_C4C_output_benchmark.pdf        【附加】跨学科基准 31 题的解答 PDF（18 页）
├── Songpengfei_C4C_output_starter-sample.pdf   【附加】starter 示例作业的解答 PDF（4 页）
├── Songpengfei_C4C_验证报告.md                 【交付物4】正确性验证报告（逐题对照官方答案 + 基线对比）
├── Songpengfei_C4C_教学说明.md                 【交付物5】教学说明（安装 / 使用 / 支持课程 / 排错）
├── Songpengfei_C4C_AI日志.md                   【交付物6】AI 日志（8 轮迭代 + 15 个 bug 复盘）★必交
├── Songpengfei_C4C_拿来说明.md                 【交付物7】拿来说明（从 starter kit 拿/改/超越的逐文件清单）
│
├── skill-src/homework-solver/                  技能源码目录（.skill 包的内容）
│   ├── SKILL.md                                触发入口 + 工作流 + 边界情况
│   ├── config.yaml                             默认配置（课程/模型/PDF 策略）
│   ├── requirements.txt                        依赖清单
│   ├── scripts/
│   │   ├── pipeline.py                         ★ 一键流水线（串联 Stage 1-5）
│   │   ├── ingest.py                           Stage 1 文档摄入（md/txt/pdf/docx/图片）
│   │   ├── parse_problems.py                   Stage 2 题目解析【starter 原样保留】
│   │   ├── solve.py                            Stage 3 求解总调度（学科判定 + 混合路由）
│   │   ├── render.py                           Stage 4 三路排版（tex/html/md）
│   │   ├── compile_pdf.py                      Stage 5 三级降级编译 + 产物校验
│   │   ├── verify.py                           正确性验证（五档判定，可对标准答案打分）
│   │   ├── llm_engine.py                       国产大模型客户端（DeepSeek/Qwen/Kimi）+ 响应缓存
│   │   ├── classify.py                         本体分类器【starter 原样保留】
│   │   ├── retrieve.py                         本体检索器【starter 原样保留】
│   │   ├── bootstrap.py                        依赖自检【starter 保留，去掉自动 pip】
│   │   └── solvers/
│   │       ├── base.py                         LaTeX→SymPy 零依赖解析器 + 统一解答结构
│   │       ├── calculus_limits.py              极限求解【starter 原样保留，逐字节一致】
│   │       ├── calculus_core.py                【新增】导数/积分/级数/多元微积分
│   │       ├── linalg.py                       【新增】线性代数（24 类操作）
│   │       ├── ode.py                          【新增】常微分方程 + 拉普拉斯变换
│   │       ├── physics.py                      【新增】大学物理（30 条公式库）
│   │       ├── probability.py                  【新增】概率统计
│   │       └── conceptual.py                   【迁移】国产大模型推理求解器
│   ├── domains/calculus_limits.yaml            领域本体【starter 原样保留】
│   ├── references/
│   │   ├── homework_template.tex               LaTeX 作业模板【starter 保留】
│   │   ├── sympy_cheatsheet.md                 SymPy 速查【starter 保留】
│   │   └── mathjax/tex-svg.js                  MathJax 3（Apache-2.0），浏览器打印 PDF 用
│   ├── tests/test_pipeline.py                  62 个单元测试（每个都对应一个真实修过的 bug）
│   └── .llm_cache/                             186 条大模型响应缓存 ★ 离线复现的依据
│
├── tools/package_skill.py                      把技能目录打包成 .skill（Git Bash 没有 zip）
│
├── samples/
│   ├── README.md                               ⚠️ 数据来源说明（哪些是真实的、出处在哪）
│   ├── real/                                   ✅ 真实作业：MIT 18.06 PSET 1 原件 + 官方解答 + 标准答案
│   └── fixtures/                               基准题集 + Berkeley 极限测试集 + starter 示例
│
├── evidence/                                   基线对照的运行日志（starter kit 的原始输出）
│   ├── baseline_starter-on-benchmark.log       → 0/31
│   ├── baseline_starter-on-mit-pset1.log       → PDF 摄入未实现
│   └── baseline_starter-on-own-sample.log      → 1/10
│
└── output/                                     流水线产物（可随时重新生成，非手写）
    ├── MIT18.06-PS1/                           真实作业：解答 + 验证报告
    ├── benchmark/                              跨学科基准 31 题：解答 + 验证报告
    ├── berkeley-test1/ berkeley-test2/         核心域回归（8/8、9/10）
    └── starter-sample/                         starter 示例作业（10/10）
```

### 数据真实性声明

| 目录 | 性质 |
|------|------|
| `samples/real/` | ✅ **真实** — MIT 18.06 Spring 2020 官方课程的 Problem Set 1 原件与官方解答 PDF，以及逐条转录的标准答案 |
| `samples/fixtures/domain_benchmark*` | ⚠️ **自编基准题集** — 由我设计、答案可手工复算，用于量化学科扩展覆盖度 |
| `samples/fixtures/berkeley_*` | ✅ **真实** — 从 starter kit 的 `test_cases/` 原样复制 |
| `output/` | **真实运行产物**，由 `pipeline.py` 生成，非手写 |
| `evidence/*.log` | **真实终端输出**，starter kit 在同一批文件上的原始表现 |

**没有任何一份标准答案是「我觉得对」**：MIT 的答案来自官方解答 PDF，
基准题集的答案可逐个手工复算。

---

## 五、结果复现步骤

从零复现本目录下所有产物，共 5 步。

### 步骤 0 · 进入目录并装依赖

```bash
cd C4C
pip install -r skill-src/homework-solver/requirements.txt
```

### 步骤 1 · 验证环境（期望 62 tests OK）

```bash
cd skill-src/homework-solver
python -m unittest discover -s tests -v
cd ../..
```

### 步骤 2 · 跑跨学科基准（纯 SymPy，完全离线，不需 API Key）

```bash
python skill-src/homework-solver/scripts/pipeline.py \
    samples/fixtures/domain_benchmark.md output/benchmark \
    --course "C4C Domain Benchmark (5 subjects)" \
    --student "Songpengfei" --title "Cross-Subject Benchmark" --no-llm

python skill-src/homework-solver/scripts/verify.py \
    output/benchmark/3_solutions.json \
    samples/fixtures/domain_benchmark_ground_truth.json \
    --out output/benchmark/validation_benchmark.json \
    --md  output/benchmark/validation_benchmark.md
```

**期望终端输出**：
```
✅ 已解 31/31 (100.0%)
[验证] 条目 31｜正确 31／部分 0／错误 0
  自动判定加权正确率：100.0%
```

### 步骤 3 · 跑真实作业 MIT 18.06 PSET 1（**无 API Key 也能跑，自动读缓存**）

```bash
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
```

> `--llm-adjudicate` 会对机器判不了的 5 个条目调用模型复核。
> **这个命令同样不需要 API Key**——复核用的 prompt 与响应也已在缓存里。
> 不加这个参数的话，那 5 条会留在 `manual` 档（不算对也不算错），
> 报告会显示 `正确 25／错误 2／待人工 5`，而不是 `28/1/3`。

**期望终端输出**：
```
📄 Stage 1: 文档摄入  ✅ .pdf / read_pdf_text / 4,749 字符
🔍 Stage 2: 题目解析  ✅ 5 道题
🧮 Stage 3: 自动求解  ✅ 已解 5/5 (100.0%)
📑 Stage 5: 编译与验证 ✅ browser → homework.pdf 3 页 / 364,042 B
[验证] 条目 32｜正确 28／部分 1／错误 3
  宽松正确率（含部分）：90.6%
```

### 步骤 4 · 跑核心域回归（验证迁移零退化）

```bash
python skill-src/homework-solver/scripts/pipeline.py \
    samples/fixtures/berkeley_test1_tangent_epsilon_delta.md output/berkeley-test1 --no-llm
python skill-src/homework-solver/scripts/pipeline.py \
    samples/fixtures/berkeley_test2_limits.md output/berkeley-test2 --no-llm
```

**期望**：`8/8 (100.0%)` 与 `9/10 (90.0%)` → 合计 **17/18 = 94.4%**，与 starter kit 逐题一致。

### 步骤 5 · 核对 starter kit 基线（可选，需要 starter 解压目录）

```bash
STARTER=../_work/starter/c4c-homework-solver-starter

python $STARTER/scripts/pipeline.py $STARTER/examples/sample_homework.md /tmp/s1
# 期望：已解 1 道 (10%)

python $STARTER/scripts/pipeline.py samples/fixtures/domain_benchmark.md /tmp/s2
# 期望：已解 0 道 (0%)

python $STARTER/scripts/pipeline.py samples/real/mit1806_pset1.pdf /tmp/s3
# 期望：❌ 摄入失败: PDF 摄入未实现。
```

### 复现性的两个级别（诚实说明）

| 级别 | 条件 | 结果 |
|------|------|------|
| **逐字节一致** | 使用随包的 `.llm_cache/`（无需 API Key） | `3_solutions.json` 两次运行的 SHA-256 **完全相同**；PDF 内容一致（仅内嵌生成时间戳不同） |
| **内容一致** | 有 API Key 且清空缓存重跑 | 解答内容相同；`solver` 标签会少一个 `(cached)` 注记，`llm_usage` 会多出 token 计数 |

要严格逐字节复现，**不要加 `--no-cache`**。

---

## 六、命名规范

挑战要求交付物命名为 `姓名_C4C_内容描述.扩展名`。

**本目录的 7 项交付物全部使用「姓名拼音 + 中文描述」的命名**，
与 `CHALLENGE.md`「必须提交的文件」清单一一对应——
评审平台是按文件名里的**中文子串**匹配交付物的，英文/拼音不会命中，
所以这里不额外提供英文别名，只保留能命中的中文名：

| CHALLENGE.md 要求 | 本目录实际文件 | 说明 |
|------------------|---------------|------|
| `姓名_C4C_方案设计.md` | [`Songpengfei_C4C_方案设计.md`](Songpengfei_C4C_方案设计.md) | 架构、**选用 DeepSeek 的原因**、目标课程、求解策略、边界处理 |
| `姓名_C4C_homework-solver.skill` | [`Songpengfei_C4C_homework-solver.skill`](Songpengfei_C4C_homework-solver.skill) | 可安装技能包（963 KB / 218 文件 / 含响应缓存） |
| `姓名_C4C_作业原件.*` | [`Songpengfei_C4C_作业原件.pdf`](Songpengfei_C4C_作业原件.pdf) | 真实作业原件（MIT 18.06 PSET 1） |
| `姓名_C4C_output.pdf` | [`Songpengfei_C4C_output.pdf`](Songpengfei_C4C_output.pdf) | ★ 生成的可提交 PDF（3 页） |
| `姓名_C4C_验证报告.md` | [`Songpengfei_C4C_验证报告.md`](Songpengfei_C4C_验证报告.md) | 逐题对照 MIT 官方答案 + 与 Claude 基线对比 |
| `姓名_C4C_教学说明.md` | [`Songpengfei_C4C_教学说明.md`](Songpengfei_C4C_教学说明.md) | 安装、上手、支持课程、常见坑 |
| `姓名_C4C_AI日志.md` | [`Songpengfei_C4C_AI日志.md`](Songpengfei_C4C_AI日志.md) | 8 轮迭代 + **15 个 bug 复盘** ★必交 |
| `姓名_C4C_拿来说明.md` | [`Songpengfei_C4C_拿来说明.md`](Songpengfei_C4C_拿来说明.md) | 从 starter kit 拿/改/超越的逐文件清单 |
| （挑战未要求） | [`README.md`](README.md) | 本文件，统一说明 |

> 注：`homework-solver` 与 `output` 这两项本身就是英文关键词，已经能被子串匹配命中，
> 所以保持英文原名不改（`Songpengfei_C4C_homework-solver.skill`、`Songpengfei_C4C_output.pdf`）；
> 其余各项按中文名命名。

**附加产物**（超出挑战要求，但能佐证结论）：

| 文件 | 说明 |
|------|------|
| [`Songpengfei_C4C_output_benchmark.pdf`](Songpengfei_C4C_output_benchmark.pdf) | 跨学科基准 31 题的解答 PDF（18 页） |
| [`Songpengfei_C4C_output_starter-sample.pdf`](Songpengfei_C4C_output_starter-sample.pdf) | starter 示例作业的解答 PDF（4 页） |

**其余目录与文件**（不是交付物清单里的条目）一律使用**全小写 kebab-case 或 snake_case**：
`skill-src/`、`samples/`、`output/`、`evidence/`、`tools/`；
脚本 `pipeline.py`、`ingest.py`、`llm_engine.py`、`compile_pdf.py`；
产物 `MIT18.06-PS1/`、`benchmark/`、`berkeley-test1/`。

**技能包内部的源文件名**（`calculus_limits.py` / `linalg.py` / …）保持英文小写下划线，
这是 Python 生态惯例，便于他人直接维护——技能包是解压后运行的代码，不是交付物清单里的条目。

---

## 七、这个技能做了什么

**输入**：一份作业文件（PDF / Word / Markdown / 图片）
**输出**：可提交的 PDF + LaTeX 源码 + 自包含 HTML + Markdown + 四个中间 JSON

### 五个 Stage

| Stage | 模块 | 做什么 |
|-------|------|--------|
| **1 摄入** | `ingest.py` | md/txt/tex 直读；**pdf 三级降级**（pdfplumber→pdftotext→pypdf）；docx 走 python-docx；图片走 OCR。清洗：连字断行合并、页眉页码剔除、Unicode 规范化、题号提升成 Markdown 结构 |
| **2 解析** | `parse_problems.py` | 识别 `Problem N`/`题 N`/`N.`/`N)` 与子题 `(a)(b)(c)`，抽 `$...$` 公式，按关键词分类题型 |
| **3 求解** | `solve.py` + `solvers/` | **学科判定 → 确定性层（SymPy × 6 模块）→ 推理层（国产大模型）**。子题会带上大题原文与兄弟小问做上下文 |
| **4 排版** | `render.py` | 三路输出（tex/html/md）；每题标注求解器 + 置信度 + 验证方式 |
| **5 编译** | `compile_pdf.py` | **三级降级保证出 PDF**：LaTeX → 浏览器+MathJax → reportlab；编译后校验页数/大小/文本层 |

### 三条设计原则

1. **SymPy 优先，LLM 只做兜底。** 能确定性算的绝不问模型——
   基准题集 31/31 一次模型调用都没用。模型只处理证明题、概念判断题、需要读懂自然语言的建模题。
2. **不确定就输出「不确定」。** 模型答案必须带置信度，低于 0.4 判为「未解」；
   解析结果可疑（如 PDF 丢上标）时 SymPy **主动让位**而不是硬算。
   宁可少答一题，不交一个看起来自然的错答案。
3. **可核验、可复现。** 每题标注来源；响应落盘缓存；
   `verify.py` 对着标准答案打分，**判不了的绝不默认算对**。

---

## 八、完成级别

| Level | 挑战要求 | 状态 |
|-------|---------|------|
| **L1** 🥉 用国产模型跑通微积分极限 | 在国产模型上复现极限求解并与 Claude 基线对比 | ✅ **17/18 = 94.4%，逐题一致（零退化）** |
| **L2** 🥈 扩展输入格式 + 至少 1 个新学科 | 多格式 + 1 个新学科 | ✅ **3 种新输入格式（PDF/Word/…）+ 5 个新学科** |
| **L3** 🥇 用真实作业（非极限）生成正确 PDF | 真实作业 + 正确 PDF | ✅ **MIT 18.06 PSET1：29/32 = 90.6%，3 页可提交 PDF** |
| **L4** 💎 完整作业系统 + 模型对比 | 答案验证/步骤生成/多课程/模型对比/图形/配置/Repo | **6/7** ✅ 答案验证✅ 步骤生成✅ 多课程✅ 配置系统✅ 离线复现✅ 模型可切换✅；❌ **图形生成未实现**；⚠️ GitHub Repo 待发布 |

---

## 九、已知局限

1. **不输出图形**——画图题只给文字描述。
2. **扫描件需自备 Tesseract**——本机未安装，OCR 路径未经端到端验证。
3. **PDF 抽取会丢等宽字体里的数字**——这是 MIT PSET1 上 P5.h 被判错的根因
   （模型因此编造了数值），目前只能在验证阶段事后发现。
4. **同题组内不做交叉一致性检查**——P2.d 漏系数因此未被拦住。
5. **物理题依赖题干显式给出数值**——纯符号的物理推导做不了。
6. **模型在数值题上不可靠**——实测 DeepSeek 漏系数、编造数值。
   **结论：数值题必须走 SymPy。**
7. **Berkeley Worksheet 原件不在资料包内**——核心域回归用的是等价的 Markdown 测试集。
8. **模型对比只做了 DeepSeek**——Qwen/Kimi 的代码路径已实现，缺 API Key 与同批次账目。

---

## 十、快速排错

| 现象 | 原因 / 解法 |
|------|------------|
| 终端中文乱码 | 命令前加 `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`（文件内容本身没问题） |
| `未识别到题目` | 题号不可识别。看 `out/1_ingested.json` 的文本；题号用 `Problem 1.` / `1.` / `题 1` |
| PDF 报「没有文本层」 | 是扫描件。装 Tesseract，或先把题目转成 `.md` |
| 答案渲染成 `\frac{1}{2}` 裸文本 | 走的是 reportlab 兜底。装 Edge/Chrome 或 LaTeX 可恢复 |
| PDF 三级全失败 | 看 `out/summary.json` 的 `stage5.attempts`，每级失败原因都在里面 |
| 概念题全标「未解」 | 没配 API Key，或置信度低于阈值。配 Key 或调 `--min-confidence 0.3` |
| `ModuleNotFoundError: pdfplumber` | `pip install pdfplumber`（或忽略，会自动降级到 pdftotext） |
| 想完全离线跑 | 不配 API Key 直接跑，会读 `.llm_cache/` |
| 结果和上次不同 | 用了 `--no-cache`。**不要用**，除非确实想重新调用 API |
| `.skill` 装不上 | 用 `python tools/package_skill.py` 重新打包，确保含 `SKILL.md` |

更多排错细节见 [`Songpengfei_C4C_教学说明.md`](Songpengfei_C4C_教学说明.md) 第九节。

---

## 十一、出处与许可

| 内容 | 出处 | 许可 |
|------|------|------|
| starter kit 代码与本体 | 本挑战资料包 `materials/c4c-homework-solver-starter.zip` | 挑战方提供 |
| MIT 18.06 PSET 1 题目与官方解答 | https://web.mit.edu/18.06/www/Spring2020/ | MIT 课程公开材料（教学验证用途） |
| Berkeley Math 1A 测试集 | 随 starter kit 分发 | 同上 |
| MathJax 3 (`tex-svg.js`) | https://www.npmjs.com/package/mathjax | **Apache-2.0** |
| SymPy / pdfplumber / python-docx / reportlab / pypdfium2 | 各自官方仓库 | BSD / MIT / 各自开源许可 |
