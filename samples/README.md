# samples/ —— 测试数据来源说明（重要）

本目录下的文件**不是同一性质的**。为了让评审能判断哪些结论可信到什么程度，
逐个标注来源与性质。

---

## `samples/real/` —— ✅ 全部真实

| 文件 | 来源 | 性质 |
|------|------|------|
| `mit1806_pset1.pdf` | MIT 18.06 Linear Algebra, Spring 2020（Prof. Alan Edelman）官方课程站<br>https://web.mit.edu/18.06/www/Spring2020/pset1.pdf | ✅ **真实课程的真实作业原件**，未做任何修改 |
| `mit1806_pset1_official-solutions.pdf` | 同上课程站<br>https://web.mit.edu/18.06/www/Spring2020/psetsol1.pdf | ✅ **官方解答**，标准答案的唯一来源 |
| `mit1806_pset1_ground_truth.json` | **我从上面那份官方解答 PDF 逐条手工转录** | ✅ 转录，非编造。每条都有 `expected` 字段 |

**为什么选 MIT 18.06 PSET 1 作为 Level 3 的真实作业测试**：

1. 是**真实课程的真实作业**，不是为演示构造的样本；
2. **官方解答公开**，正确性可以逐题对照，不用"我觉得对"；
3. 领域是**线性代数 + 多元微积分预热**，**明确不是微积分极限**，满足挑战的硬性要求；
4. 题型分布很"脏"——选择题、判断题、向量空间论证、梯度、Julia 数值实验都有，
   **32 个小问里只有 1 个能走 SymPy**，正好压测混合路由里大模型那一半。

---

## `samples/fixtures/` —— 真实与自编混合

| 文件 | 性质 | 来源 / 说明 |
|------|------|------------|
| `domain_benchmark.md` | ⚠️ **自编** | 我设计的 31 题跨学科基准，覆盖 5 个学科。**答案全部可以手工复算**，不依赖任何外部解答 |
| `domain_benchmark_ground_truth.json` | ⚠️ **自编** | 上述基准的标准答案。由 SymPy 独立复算 + 教材标准结果双重确认 |
| `berkeley_test1_tangent_epsilon_delta.md` | ✅ **真实** | 从 starter kit 的 `test_cases/` 原样复制（Berkeley Math 1A Worksheet 3 等价测试集） |
| `berkeley_test2_limits.md` | ✅ **真实** | 同上（Worksheet 4 等价测试集） |
| `test1_answers_cn.pdf` | ✅ **真实** | starter kit 附带的中文解答，核心域回归的对照物 |
| `test2_answers_cn.pdf` | ✅ **真实** | 同上 |
| `starter_sample_homework.md` | ✅ **真实** | starter kit 自带的示例作业（微积分 + 线代 + ODE 混合 10 题） |

### 关于自编基准题集的诚实说明

`domain_benchmark.md` 的 **100% 正确率必须正确理解它的边界**：

- ✅ 它衡量的是「**确定性求解的覆盖面**」——starter 在它上面是 0/31，C4C 是 31/31；
- ⚠️ 它**不能外推成「随便一份作业都能 100%」**：题型与我实现的求解分支一一对应，
  而且都是**有唯一标准答案的计算题**，没有证明题、没有文字应用题、没有画图题。

**真实作业的正确率请以 `samples/real/` 的 MIT PSET1（90.6%）为准。**
这也是我额外做那一份真实作业测试的原因——只报 100% 是不诚实的。

---

## `output/` —— 真实运行产物

`output/` 下的所有文件都由 `pipeline.py` / `verify.py` 真实跑出来，**不是手写的**。
想核对可以直接删掉整个目录重新生成（见根目录 `README.md` 第五节）。

`evidence/*.log` 是 starter kit 在同一批文件上的**原始终端输出**，
用来佐证「starter 0/31、1/10、PDF 无法摄入」这三个基线数字。

---

## 数据使用声明

- MIT 与 Berkeley 的课程材料**仅用于教学验证**，版权归原作者/机构所有。
- 本目录不与任何作业提交系统对接，不用于绕过学术诚信要求。
  `Songpengfei_C4C_教学说明.md` 第十一节明确提醒：**本工具产出的是草稿，
  正确率 90.6% 意味着每 10 题有 1 题需要人工核对。**
