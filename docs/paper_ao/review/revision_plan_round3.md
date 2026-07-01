# ADL Lite Applied Ontology Major Revision — 系统修改计划

## 评审概述

- **推荐决定**: Major Revision
- **总体评分**: 6.8 / 10
- **核心瓶颈**: 本体论形式化深度与机器可验证性之间的张力

---

## 修改优先级清单

### 🔴 P1 — Major 修改（决定论文能否从 Major → Minor Revision）

| # | 维度 | 修改内容 | 当前状态 | 目标产出 |
|---|------|---------|---------|---------|
| 1 | 原创性 | 将核心本体论公理（I1–I4, D1–D5）中至少 2–3 个翻译为一阶逻辑片段 | 仅有自然语言叙述（§3.2.4） | 在正文中呈现 FOL 公式（D2 通用依赖、D5 无跨层身份） |
| 2 | 方法论 | 扩展 OWL 2 DL 片段（增加 L3 对象属性、SWRL/SPARQL 约束），使用 ROBOT 验证 | 仅 4 类+2 属性（appendix_a_owl_dl.tex） | 扩展为含 L3 谓词、生命周期事件约束的完整片段；报告 ROBOT 验证结果 |
| 3 | 方法论 | 报告 TLA+/Coq 机器验证的当前进展 | 已有 Coq 证明（Status.v 158 行, Chain.v 219 行）和 TLA+ 规范（EventChain.tla 199 行） | 在 §4.8/附录 I 中报告：Coq 已完成 T3、T7 证明；TLA+ 覆盖长度 ≤20 链；明确边界 |
| 4 | 结果 | 完成 E5 人类专家评估的 pilot 研究或报告进展 | 标注为 "planned" | 报告 IRB/招募进展，或至少提供 LLM-as-a-judge 定量信号 |

### 🟡 P2 — Minor 修改（提升质量但非决定性）

| # | 维度 | 修改内容 | 当前状态 | 目标产出 |
|---|------|---------|---------|---------|
| 5 | 原创性 | 增加 ADL Lite "operational" 机制与 UFO-B 可执行本体执行机制的形式化对比 | §3.6 有简短提及 | 新增表格或段落，明确列出 O(1) 前提、确定性推导、密码学完整性等机制 |
| 6 | 方法论 | 修正 "Horn-clause" 声称 | §3.6 和 §4.6 中使用 "Horn-clause fragment of FOL" | 改为 "variable-free ground fragment" 或 "propositional comparator language" |
| 7 | 结果 | 为 E2-ext 随机采样报告 95% 置信区间 | 报告 10,000/10,000 通过，无置信区间 | 计算并报告 95% CI = [99.97%, 100.0%] |
| 8 | 结果 | 在 E19 中增加测量方法标准化说明 | 附录 L 有任务定义和测量协议，但缺少冷启动/缓存/I/O 说明 | 补充标准化说明段落 |
| 9 | 写作 | 压缩正文至 30 页以内 | 正文 2318 行 LaTeX（约 49 页） | 将 REST API/MCP/Neo4j 细节压缩或移至补充材料 |
| 10 | 写作 | 在摘要和 §1.1 中明确 EventChain-record 与 EventChain-process 的区分 | 摘要中 "EventChains" 未区分 | 修改 abstract.tex 和 §1.1 的措辞 |

---

## 执行策略

### 阶段一：快速修复（1-2 天）
- [ ] Minor 6: 修正 "Horn-clause" 声称（全文搜索替换）
- [ ] Minor 7: 计算并添加 E2-ext 95% CI
- [ ] Minor 8: 补充 E19 测量标准化说明
- [ ] Minor 10: 修改摘要和 §1.1 的 EventChain 区分

### 阶段二：形式化深化（3-5 天）
- [ ] Major 1: 将 D2、D5 翻译为 FOL 片段（在 §3.2.4 中增加）
- [ ] Major 3: 扩展 TLA+/Coq 进展报告（附录 I）
- [ ] Minor 5: 增加 operational vs UFO-B 对比

### 阶段三：OWL 扩展（3-5 天）
- [ ] Major 2: 扩展 OWL 2 DL 片段（L3 对象属性、SWRL/SPARQL 约束）
- [ ] 运行 ROBOT 验证并报告结果
- [ ] 更新附录 A 和正文 §3.5

### 阶段四：实验与写作（2-3 天）
- [ ] Major 4: E5 进展报告或 LLM-as-a-judge 替代方案
- [ ] Minor 9: 压缩正文（将 REST API/MCP/Neo4j 移至补充材料）
- [ ] 重新编译并检查页数

### 阶段五：审阅与整合（1-2 天）
- [ ] 创建 reviewer_response_3.md
- [ ] 逐条检查所有修改
- [ ] 运行测试确保代码正确性
- [ ] 重新编译全文 PDF

---

## 关键资源映射

| 修改项 | 涉及文件 |
|-------|---------|
| Major 1 (FOL 公理) | `sections/03_ontological_analysis.tex` |
| Major 2 (OWL 扩展) | `supplementary/appendix_a_owl_dl.tex`, `sections/03_ontological_analysis.tex` |
| Major 3 (TLA+/Coq) | `supplementary/appendix_i_tla.tex`, `specs/`, `formal/coq/` |
| Major 4 (E5) | `sections/05_empirical_validation.tex` |
| Minor 5 (operational) | `sections/03_ontological_analysis.tex` |
| Minor 6 (Horn-clause) | `sections/03_ontological_analysis.tex`, `sections/04_architecture.tex` |
| Minor 7 (E2 CI) | `sections/05_empirical_validation.tex` |
| Minor 8 (E19) | `supplementary/appendix_l_e19_methodology.tex` |
| Minor 9 (压缩) | `sections/04_architecture.tex` (REST/MCP/Neo4j 部分) |
| Minor 10 (EventChain) | `sections/abstract.tex`, `sections/01_introduction.tex` |

---

## 修改后预期

- 正文压缩至 ~30 页
- 补充材料包含：完整 OWL 片段、ROBOT 验证报告、TLA+/Coq 证明细节、E19 方法学、FOL 公理片段
- 评审回应表：4 Major + 6 Minor = 10/10 项全部有明确回应
- 论文定位：从"突破"改为"轻量级事件优先能力治理框架"（务实定位）
