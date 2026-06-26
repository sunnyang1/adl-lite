# Phase 3 Future Work 评估报告

> **评估日期：** 2026-06-17  
> **评估基准：** Month 3 (v0.4.0-alpha) 已完成，590 测试通过，35 页论文，9 个定理  
> **约束前提：** Applied Ontology 论文提交仍是硬 deadline（Month 5）；Phase 3 实现**不能**影响论文提交

---

## 1. 评估框架

| 维度 | 权重 | 说明 |
|------|------|------|
| **论文受益** | 40% | 是否能让审稿人看到“作者确实有能力完成这些工作” |
| **实现风险** | 30% | 是否破坏向后兼容、是否引入新依赖、是否影响 590 测试 |
| **所需资源** | 20% | 人天、技能要求、外部依赖 |
| **已有基础** | 10% | 已有模块是否可以复用 |

**分类标准：**
- **高优先级**：论文受益高 + 风险低 + 已有基础 → 建议在论文提交前实现
- **中优先级**：论文受益中 + 风险可控 → 可以在论文提交后、审稿等待期实现
- **低优先级**：论文受益低或风险高 → 建议作为独立分支的 Future Work 保留

---

## 2. FW1–FW12 逐项评估

### 2.1 高优先级（建议提交前实现）

| ID | 描述 | 已有基础 | 剩余工作 | 估计人天 | 风险 | 论文受益 | 建议 |
|----|------|---------|---------|---------|------|---------|------|
| **FW3** | MARGIN EWMA 校准 | `calibration.py` 已有线性校准 + `MARGINCalibrator` | 添加 EWMA 滑动窗口、per-band 校准、时间衰减权重 | 3–4d | 低 | 高 | **提交前实现** — 审稿人会看到校准系统的完整演化路径，增强可信度 |
| **FW1** | OWL 2 DL 双向对齐 | `owl_export.py` 已导出 RDF/XML 和 Turtle | 添加 OWL → ADL 导入（RDF 解析 → EventChain），LogMapLite 验证 | 3–4d | 低 | 中-高 | **提交前实现** — 证明 OWL 是双向桥接而非单向导出 |
| **FW8** | RDF-star / SPARQL-star | `owl_export.py`, `jsonld_export.py` 已导出 | 添加 RDF-star 三元组标注（`<<s p o>>` 语法）和 SPARQL-star 查询 | 2–3d | 低 | 中 | **提交前实现** — 补充材料中可展示 2-3 个 RDF-star 三元组示例 |

### 2.2 中优先级（审稿等待期或独立分支实现）

| ID | 描述 | 已有基础 | 剩余工作 | 估计人天 | 风险 | 论文受益 | 建议 |
|----|------|---------|---------|---------|------|---------|------|
| **FW2** | 完整 DEDUP + Quality Gate | `near_duplicate.py` 已有 Jaccard/Levenshtein/embedding | 添加自动去重策略（合并而非仅检测）、信息增益质量门 | 4–5d | 中 | 中 | **审稿等待期** — 需要 careful design 避免误删 VALIDATE 事件 |
| **FW4** | DIDs + Linked Data Proofs | `key_registry.py` 已有 Ed25519 + `GitSignatureVerifier` + `TransparencyAnchor` | 添加 DID 解析器、LD-Proof 签名验证、W3C 兼容性测试 | 3–4d | 中 | 中 | **审稿等待期** — 外部依赖（DID 方法）可能影响可复现性 |
| **FW10** | TLA+ 无界证明 | 补充材料附录 I 已有 147 行有界规格 | 添加归纳证明策略（Invariant → TLC 无界验证），更新论文脚注 | 2–3d | 低 | 中 | **审稿等待期** — 纯形式化工作，不影响代码 |
| **FW11** | 1M 事件投影 | 已有 100k 验证（E21） | 生成 1M 事件链，验证线性外推假设，添加内存/时间基准 | 2–3d | 低 | 低 | **审稿等待期** — 工程验证而非科学突破，但填补论文中的诚实声明 |

### 2.3 低优先级（建议作为 Future Work 保留，不实现）

| ID | 描述 | 风险原因 | 论文受益 | 建议 |
|----|------|---------|---------|------|
| **FW5** | AML 专家评估 | 需要 IRB + 3–6 个月招募，时间成本 > 论文收益 | 高但不可行 | **保留为 Future Work** — 在论文中明确说明为独立研究 |
| **FW6** | SHACL 模板验证 | 论文已改为 Pydantic-based，实现 SHACL 会与论文主张矛盾 | 负 | **不实现** — 论文已明确使用 Pydantic |
| **FW7** | LLM 概念发现 | 需要 LLM 基础设施（OpenAI/Anthropic API），与“无外部依赖”原则冲突 | 中 | **不实现** — 可作为独立项目 |
| **FW9** | Staking 市场 | 博弈论设计 + 经济学模型，需要全新领域知识，与论文核心无关 | 中 | **不实现** — 可作为经济学/博弈论独立论文 |
| **FW12** | Coq/Iris 形式化 | 需要 Coq 专家 + 3–6 个月，时间成本极高 | 高但不可行 | **保留为 Future Work** — 论文中已诚实说明 |

---

## 3. 实施计划建议

### 3.1 方案 A：保守（提交前不做任何 Phase 3，Month 5 后独立分支）

**风险：** 最低。所有 Phase 3 保持为 Future Work 描述。  
**收益：** 审稿人可能质疑“作者是否真的有能力实现这些”。  
**适合：** 如果审稿反馈对代码-论文对齐非常满意，无需进一步证明。

### 3.2 方案 B：选择性（提交前实现 FW1 + FW3 + FW8）

**时间：** 3 周（约 8–10 人天）  
**风险：** 低。这三个都是已有模块的增量扩展。  
**收益：** 审稿人看到 3 个 Future Work 已有代码骨架，增强“作者团队有能力完成”的可信度。  
**建议：** 这是我们的推荐方案。

### 3.3 方案 C：全面（提交前实现 6 个 Future Work）

**时间：** 6–8 周（约 20–25 人天）  
**风险：** 中。可能引入回归测试失败，延迟论文提交。  
**收益：** 审稿人看到绝大多数 Future Work 已有代码，论文的“路线图”看起来可信。  
**风险：** 可能超出 5 个月 deadline，或导致 590 测试中部分失败。

---

## 4. 推荐方案：方案 B（选择性实现）

### 4.1 为什么选 B

1. **审稿人心理学**：Applied Ontology 审稿人关注的是“作者是否知道自己在做什么”，而非“是否所有 Future Work 都已完成”。3 个已实现 + 9 个已描述 = 完美的 balance。
2. **代码质量**：FW1, FW3, FW8 都是已有模块的增量扩展，测试覆盖容易维护，不会破坏 590 测试。
3. **时间预算**：Month 4 是提交准备（4 周），Month 5 是提交 + 缓冲（4 周）。在 Month 4 的第 1–2 周完成 FW1+FW3+FW8，然后转入匿名化和润色，时间充足。

### 4.2 具体实施计划

| 周 | 任务 | 产出 | 测试 |
|----|------|------|------|
| **Month 4, Week 1** | FW3: MARGIN EWMA | `calibration.py` 新增 `ewma_confidence()` 和 `epistemic_context()` | 5+ 新测试 |
| **Month 4, Week 2** | FW1: OWL 双向导入 | `owl_import.py` 新增 RDF/Turtle → EventChain 解析 | 5+ 新测试 |
| **Month 4, Week 2–3** | FW8: RDF-star | `rdfstar_export.py` 新增三元组标注导出 | 3+ 新测试 |
| **Month 4, Week 3** | 集成测试 | 确认 590 + 13 新测试全部通过 | 全绿 |
| **Month 4, Week 4** | 论文更新 | 更新 §7.2 Future Work 描述，标注 FW1/3/8 为“已有代码骨架” | 编译通过 |
| **Month 5** | 提交准备 | 匿名化、Artifact 打包、最终润色 | — |

### 4.3 风险缓解

- **如果 FW3 的 EWMA 复杂度超出预期**：降级为“简单滑动平均”，论文中诚实说明“当前为线性滑动平均，EWMA 为后续优化”。
- **如果 FW1 的 OWL 导入失败**：降级为“Turtle 导入”，OWL 的复杂性（blank nodes, reification）可以 defer。
- **如果测试失败**：立即回滚，保持原有代码不变，确保 590 测试始终通过。

---

## 5. 论文 §7.2 的更新建议

实施 FW1+FW3+FW8 后，§7.2 的 Future Work 列表应更新为：

| FW | 状态 | 论文表述 |
|----|------|---------|
| **FW1** | 部分实现 | OWL 2 DL bidirectional alignment: export implemented (Turtle/RDF/XML), import scaffolded with LogMapLite validation. |
| **FW2** | 部分实现 | Controlled forgetting: ARCHIVE events operational, embedding-based deduplication scaffolded (Jaccard/Levenshtein/embedding), quality gate pending. |
| **FW3** | 部分实现 | Calibration: linear scaled-mean operational, EWMA sliding-window and epistemic-context learning scaffolded. |
| **FW4** | 部分实现 | Identity layer: Ed25519 key registry + Git binding + transparency anchor operational, DIDs and Merkle/Verkle batch verification pending. |
| **FW5** | 未实现 | Domain-level expert evaluation scoped to independent IRB-approved study. |
| **FW6** | 不实现 | SHACL template validation replaced by Pydantic-based enforcement (design choice documented). |
| **FW7** | 未实现 | LLM-guided concept discovery with RAG injection and human-in-the-loop review. |
| **FW8** | 部分实现 | Semantic-web interoperability: OWL/Turtle/JSON-LD export operational, RDF-star bidirectional converter and SPARQL-star query scaffolded. |
| **FW9** | 未实现 | Ontological Assertion Market with staking-based validation and MARGIN-calibrated weights. |
| **FW10** | 部分实现 | Machine-checked proofs: bounded TLA+ spec verified (Appendix I), unbounded EventChain properties and full CRDT convergence proof pending. |
| **FW11** | 部分实现 | Scalability: 100k events empirically validated (E21), 1M projection and head-to-head nanopublication benchmark pending. |
| **FW12** | 未实现 | Coq/Iris formalization of ontological axioms and precondition decidability. |

---

## 6. 结论

| 方案 | 时间 | 风险 | 论文受益 | 建议 |
|------|------|------|---------|------|
| A（保守） | 0 | 最低 | 中 | 如果审稿反馈已足够好 |
| **B（选择性）** | 3周 | 低 | **高** | **推荐** — 3 个 Future Work 已有代码骨架，增强可信度 |
| C（全面） | 6–8周 | 中 | 高 | 不推荐 — 可能延迟提交 |

**下一步：** 请确认选择方案 A / B / C，或提出修改意见。如果选择 B，我们可以立即开始制定 FW3（MARGIN EWMA）的详细实现计划。
