# C4C 教学说明（怎么装、怎么用、支持哪些课）

> 作者：宋鹏飞（Songpengfei） ｜ 日期：2026-10-09
> 面向对象：**想用这个工具的同学 / 想把它改成自己课程的同学**。
> 目标：读完这一篇，30 分钟内能跑出第一份作业 PDF。

---

## 一、5 分钟上手

### 1.1 安装

```bash
# ① 装 Python 依赖（全部是纯 Python 包，不需要编译器）
cd C4C/skill-src/homework-solver
pip install -r requirements.txt

# ② 验证
python -c "import sympy, yaml; print('core ok')"
python -c "import pdfplumber; print('pdf ok')"
python -c "import docx; print('docx ok')"
python -c "import reportlab; print('pdf-out ok')"
```

> **LaTeX 是可选的，不装也能出 PDF**（会自动走浏览器打印这条路）。
> 想用高质量的 LaTeX 排版再装 TeX Live / MiKTeX / TinyTeX，装完自动生效。

### 1.2 配国产大模型（可选，但强烈建议）

```bash
# 三选一，配哪个都行
export DEEPSEEK_API_KEY=sk-xxxxxxxx      # https://platform.deepseek.com
export DASHSCOPE_API_KEY=sk-xxxxxxxx     # 通义千问 https://dashscope.console.aliyun.com
export MOONSHOT_API_KEY=sk-xxxxxxxx      # Kimi https://platform.moonshot.cn
```

Windows PowerShell：
```powershell
$env:DEEPSEEK_API_KEY="sk-xxxxxxxx"
```

> **不配也能跑**：纯 SymPy 路径完全不需要 Key，只是证明题/概念题会标「未解」。
> 另外本技能包**自带了响应缓存**，所以即使没有 Key，也能复现出我们当时生成的那份 PDF。

### 1.3 跑第一份作业

```bash
python scripts/pipeline.py 我的作业.pdf out/ \
    --course "线性代数" --student "张三" --title "第 3 次作业"
```

打开 `out/homework.pdf` —— 就完了。

---

## 二、命令行全参数

```bash
python scripts/pipeline.py <输入文件> <输出目录> [选项]
```

| 选项 | 默认 | 说明 |
|------|------|------|
| `--course NAME` | `Mathematics` | 课程名，印在 PDF 抬头 |
| `--student NAME` | `Student` | 姓名，印在 PDF 抬头 |
| `--title TITLE` | `Homework Solutions` | 作业标题 |
| `--date YYYY-MM-DD` | 今天 | 抬头日期 |
| `--basename NAME` | `homework` | 产物文件名前缀 |
| `--no-llm` | 关 | **完全不用大模型**，只用 SymPy（最快、最稳、零成本） |
| `--provider` | 自动探测 | `deepseek` / `qwen` / `kimi` / `openai-compatible` |
| `--model` | 该 provider 默认 | 例：`deepseek-reasoner` / `qwen-max` |
| `--verify` | 关 | 让模型对自己的答案**独立重算一遍**做二次复核（慢约一倍） |
| `--min-confidence` | `0.4` | 低于此置信度的答案判为「未解」 |
| `--no-cache` | 关 | 忽略响应缓存，强制重新调用 API（会花钱） |
| `--tier` | `auto` | PDF 引擎：`auto` / `latex` / `browser` / `reportlab` |
| `--explain` | 关 | 打印每道题走了哪条求解路径（调试用） |
| `--no-embed-mathjax` | 关 | HTML 不内联 MathJax（默认内联成单文件，方便分发） |

**常用组合**：

```bash
# 只想快速检查题目解析对不对（不求解，看 2_parsed.json）
python scripts/pipeline.py 作业.pdf out/ --no-llm --explain

# 考试前的冲刺：要最准，不在乎慢
python scripts/pipeline.py 作业.pdf out/ --verify --min-confidence 0.6

# 换模型
python scripts/pipeline.py 作业.pdf out/ --provider qwen --model qwen-max

# 作业是扫描件（需要先装 Tesseract）
python scripts/pipeline.py 扫描件.jpg out/
```

---

## 三、支持的输入格式

| 格式 | 状态 | 依赖 |
|------|------|------|
| `.md` / `.txt` / `.tex` | ✅ 直接读 | 无 |
| `.pdf`（文本型） | ✅ 三级降级 | pdfplumber（推荐）/ pdftotext / pypdf |
| `.pdf`（扫描型） | ⚠️ 需 OCR | 先转成图片，或装 Tesseract |
| `.docx` / `.doc` | ✅ | python-docx |
| `.png` / `.jpg` / `.tiff` | ⚠️ 需 OCR | pytesseract + Tesseract-OCR 可执行文件 |

**装 OCR（可选）**：

```bash
pip install pytesseract Pillow
# 再装 Tesseract 可执行文件：
#   Windows  https://github.com/UB-Mannheim/tesseract/wiki
#   macOS    brew install tesseract tesseract-lang
#   Linux    sudo apt install tesseract-ocr tesseract-ocr-chi-sim
```
> 中文识别要装中文语言包（`chi_sim`）。

---

## 四、作业文件要长什么样

### 4.1 推荐的格式

```markdown
# 线性代数 第 3 次作业

## Problems

Problem 1. Compute the determinant of $A = \begin{pmatrix} 2 & 1 \\ 1 & 3 \end{pmatrix}$.

Problem 2. 求 $\lim_{x \to 0} \frac{\sin x}{x}$。

Problem 3. 求解微分方程 $y'' + y = 0$。

(a) 求通解。
(b) 若 $y(0)=1, y'(0)=0$，求特解。
```

### 4.2 支持的题号格式

| 写法 | 例子 |
|------|------|
| 英文题号 | `Problem 1.` / `Problem 1:` / `Question 2` |
| 中文题号 | `题 1.` / `第 1 题` |
| 纯数字 | `1.` / `1)` |
| 带前缀 | `Q1.` / `P1.` |
| 子题 | `(a)` `(b)` `(c)` 或 `a.` `b.` `c.` |
| 段落标题 | `## Problems` / `## Questions` / `## Additional Problems` / `## Part A` |

**公式必须用 `$...$` 或 `$$...$$` 包起来**，否则会被当成普通文字。

### 4.3 PDF 作业的注意点

从 PDF 抽文本时，**上标常常会丢**：`x²+y²+z²` 可能变成 `x2+y2+z2` 甚至 `x�+y�+z�`。

本系统对这种情况的处理是：**检测到可疑就主动放弃，转交大模型**，
而不是硬算出一个看起来自然的错答案。如果你发现某道题答案明显不对，
先去看 `out/2_parsed.json` 里这道题的文本是不是已经残缺了。

**如果 PDF 质量实在太差**，最省事的办法是：把题目手打（或复制）成 `.md` 再喂进来。
流水线的其它四段完全一样，只是 Stage 1 变成"直接读文本"。

---

## 五、支持哪些课程

### 5.1 已实现（有测试覆盖）

| 学科 | 能做 | 覆盖率证据 |
|------|------|-----------|
| **线性代数** | 行列式、逆、秩、RREF、零空间、列空间、特征值/特征向量、对角化、二次型正定性、伴随矩阵、最小二乘、投影、Gram-Schmidt 正交化、LU、SVD、迹、转置、矩阵乘法、线性相关性、基、解方程组 | 基准 8/8；MIT PSET1 90.6% |
| **微积分（极限）** | 极限、切线、ε-δ（**starter 原样保留**） | Berkeley 17/18 = 94.4% |
| **微积分（其余）** | 导数（含高阶/隐函数）、不定/定/反常积分、泰勒级数、收敛半径、级数判敛、梯度、散度、旋度、最值、旋转体体积、弧长 | 基准 7/7 |
| **微分方程** | 一阶（可分离/线性/伯努利）、二阶常系数齐次与非齐次、初值问题、拉普拉斯变换与逆变换 | 基准 6/6 |
| **大学物理** | 匀加速运动、牛顿定律、摩擦力、圆周运动、功与能、弹簧、动量冲量、万有引力、库仑定律、场强、欧姆定律、电功率、电容储能、串并联电阻、理想气体、比热/潜热、弹簧振子、单摆、波速、折射定律（**30 条公式**） | 基准 6/6 |
| **概率统计** | 期望/方差/标准差、二项/泊松/正态/均匀分布、条件概率、贝叶斯、全概率、协方差、相关系数、线性回归、单样本 z 检验 | 基准 4/4 |

### 5.2 部分支持

| 学科 | 能做什么 | 限制 |
|------|---------|------|
| 证明题 | 有模板匹配（ε-δ、连续性、IVT、固定点等） | 复杂证明靠模型，正确率取决于模型 |
| 概念/文字题 | 由国产大模型回答 | 会标注置信度，低置信度判为未解 |
| 多元微积分 | 梯度/散度/旋度、二重三重积分 | 曲线曲面积分未实现 |
| 数值方法 | 不专门支持 | 一般能靠 SymPy 数值求解兜住 |

### 5.3 不支持

| 类型 | 说明 |
|------|------|
| 画图题 | **不输出图形**，只给文字描述 |
| 编程题 | 不给代码答案（除非题目本质是数学题） |
| 需要看图才能做的几何题 | 依赖图像理解，本流水线不做 |

---

## 六、换一门课怎么改

**三种由易到难的改法：**

### 改法 1：只换抬头（0 行代码）

```bash
python scripts/pipeline.py 作业.pdf out/ --course "电磁学" --student "李四"
```

或改 `config.yaml`：
```yaml
course: "电磁学"
student: "李四"
title: "作业三"
```

### 改法 2：加物理公式（改几行数据）

打开 `scripts/solvers/physics.py`，在 `FORMULAS` 列表里加一条：

```python
dict(name="安培力", unknown="F", expr="B*I*L*sin(theta)",
     keys=[r"安培力|magnetic force on a wire"],
     vars="F 安培力, B 磁感应强度, I 电流, L 长度, theta 夹角"),
```

**不需要读懂求解器内部**——公式库是声明式的，加完就能用。

### 改法 3：加一个新学科（写一个模块）

1. 在 `scripts/solvers/` 下新建 `我的学科.py`，实现：
   ```python
   def solve(problem: dict) -> dict | None:
       """返回解答 dict 表示接管；返回 None 表示不归我管。"""
   ```
   用 `from .base import sol, unsolved` 构造返回值。
2. 在 `scripts/solvers/__init__.py` 的 `__all__` 里加上模块名。
3. 在 `scripts/solve.py` 的 `_SYMPY_ROUTER` 和 `_SUBJECT_RULES` 里注册。

**必须遵守的两条约定**（整个项目的安全底线）：
- 认领了但解不出来 → 返回 `unsolved(...)` 并写清楚原因，**不能返回 `None` 装死**；
- 解析结果可疑 → **返回 `None` 让下一个模块接**，不要硬输出。

---

## 七、输出产物说明

跑一次会得到：

```
out/
├── 1_ingested.json      Stage 1 产物：抽取出的原始文本 + 分段
├── 2_parsed.json        Stage 2 产物：结构化的题目列表  ← 解析出问题时先看这个
├── 3_solutions.json     Stage 3 产物：每题的分步解答 + 答案 + 求解器 + 置信度
├── homework.tex         LaTeX 源码（可上传 Overleaf 编译）
├── homework.html        自包含 HTML（含内联 MathJax，可直接发微信/邮件）
├── homework.md          Markdown（快速扫读 / 粘贴到别处）
├── homework.pdf         ★ 可提交的 PDF
└── summary.json         全流程统计：各阶段耗时、解题率、PDF 校验结果
```

**PDF 抬头会标注解题率**（`Solved: 29/32 (90.6%)`），每题下方标注用了哪个求解器。

---

## 八、验证答案对不对

想让机器帮你对着标准答案打分：

**① 写一份标准答案 JSON**（照 `samples/` 里的格式）：

```json
{
  "source": "我的课 第3次作业",
  "official_solutions": "老师给的参考答案.pdf",
  "items": [
    {"id": "P1", "expected": "18", "kind": "exact"},
    {"id": "P2", "expected": "(2,3,4)", "accept": ["2,3,4"], "kind": "exact"},
    {"id": "P3", "expected": "Yes", "accept": ["yes", "是"], "kind": "choice"}
  ]
}
```

`kind` 有五种：`exact`（数值/符号相等）、`set`（结果集合）、`contains`（含关键结论）、
`choice`（选择题）、`manual`（必须人工看）。

**② 跑验证**：

```bash
python scripts/verify.py out/3_solutions.json my_ground_truth.json \
    --md report.md --llm-adjudicate
```

`--llm-adjudicate` 会把机器判不了的条目交给国产模型复核。
**机器判不了的绝不会默认算对**——都会进 `manual` 单列出来。

---

## 九、快速排错

| 现象 | 原因 / 解法 |
|------|------------|
| 终端中文乱码 | 命令前加 `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`（产物文件本身始终是 UTF-8） |
| `未识别到题目` | 题目没有可识别的题号。检查 `out/1_ingested.json` 里的文本；题号用 `Problem 1.` / `1.` / `题 1` |
| PDF 摄入报错「没有文本层」 | 是扫描件。装 Tesseract OCR，或先把题目转成 `.md` |
| 答案渲染成 `\frac{1}{2}` 这样的裸文字 | 说明走的是 reportlab 兜底。装 Edge/Chrome 或 LaTeX 可恢复 |
| PDF 编译三级别全失败 | 看 `out/summary.json` 的 `stage5.attempts`，里面记了每一级失败的原因 |
| 概念题全标「未解」 | 没配 API Key，或模型置信度低于阈值。配 Key 或调 `--min-confidence 0.3` |
| 大模型调用很慢 | 第一次是正常的（每题 1–3 秒）。之后走缓存，整份作业 3 秒内 |
| 结果和上次不一样 | 用了 `--no-cache`，或改了 prompt。**不要用 `--no-cache`**，除非确实想重新调用 |
| 想完全离线跑 | 不配 API Key 直接跑，会自动读 `.llm_cache/` |
| 物理题答案离谱 | 检查题干是否显式给出了所有数值；物理求解器靠「数值 + 单位」抽取 |
| 换模型后没有回复 | 检查对应环境变量；用 `python scripts/llm_engine.py --check` 自检 |

**自检命令**：

```bash
# 探测当前能用哪个国产模型
python scripts/llm_engine.py --check

# 只测 1 道题，看模型回什么
python scripts/llm_engine.py --ask "求 lim_{x->0} sin(3x)/x"

# 跑单元测试（62 个，含每个历史 bug 的回归）
python -m unittest discover -s tests -v
```

---

## 十、把它当 Claude Skill 用

`Songpengfei_C4C_homework-solver.skill` 是标准 ZIP 格式的技能包
（根目录含 `SKILL.md`），可直接装到支持 Claude Skills 的环境。
装好后说「**帮我把这份作业解出来并排版**」并给出文件路径即可触发。

包内结构与本目录一致，`.llm_cache/` 也已打包进去，
所以**在没有 API Key 的机器上也能复现出同样的结果**。

---

## 十一、最后一句提醒

⚠️ **这个工具产出的是「草稿」，不是「终稿」。**

它省下的是**抄题、排版、编译**的时间，不是**检查**的时间。
实测 90.6% 的正确率意味着**每 10 题有 1 题需要你核对**。
交作业前请务必过一遍——尤其是数值题（模型在数值上不可靠，这是本项目的实测结论）。

**正确的用法**：用它把 3 小时的作业压缩成 15 分钟的审阅。
**错误的用法**：不看直接交。
