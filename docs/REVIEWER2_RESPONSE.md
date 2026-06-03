# ADL Lite — Round 2 Reviewer Response & Revision Plan

**Review Target**: `paper_ao/` (Applied Ontology submission, revised manuscript)
**Date**: 2026-06-03
**Verdict**: Recommend revise-and-resubmit (consistent with Round 1)

---

## 修订完成状态：已修复 vs 待修复

| # | Reviewer Weakness | 状态 | 已完成的工作 | 待补充 |
|---|------------------|:----:|------------|--------|
| W1 | 无身份验证(无签名) | 🟡 | §4.8 Trust Model + 威胁表已添加 | 需限制主张范围，明确"Phase 1 未实现身份认证" |
| W2 | Fork/并发语义不明确 | 🟡 | §4.6.4 扩展: CRDT merge + Theorem 7 | 需形式化 confluence 前置条件 |
| W3 | GDC-ICE 依赖需要更严密论证 | 🟢 | §3.2.2, §3.4.1 已修复 | 需补充: 多重具体化/身份持久/存在终止 |
| W4 | 仅做内部一致性验证 | 🟡 | §5.7 已添加对比评估 | 需从方法论对比提升到实验对比 |
| W5 | 数据集/测试覆盖不详细 | 🔴 | — | 需添加事件类型分布、覆盖分析 |
| W6 | "?"引用 + 表格格式问题 | 🟢 | 61个占位符已替换，DOLCE映射已修正 | 建议再次全文校对 |
| W7 | δ/γ/WF 定义不完整 | 🟢 | §4.6 已添加符号表 + 完整定义 | 已完成 |
| W8 | CIDOC CRM "heavyweight RDF" 不精确 | 🔴 | — | 需修正措辞 |
| W9 | Event Calculus / DL 比较仅承诺未实现 | 🔴 | — | 需添加形式化转换或明确表达力边界 |
| W10 | 无真实基线对比实验 | 🔴 | §5.7 方法论对比 | 需添加实际 benchmark 数据 |

---

## 问题逐一回答

### Q1: 请提供 WF(C), δ(C), γ(C) 及六条定理的完整形式化定义

**回答**: 已提供。完整定义位于论文 §4.6 Formal Derivation Semantics，含：事件字母表 $\Sigma = \Sigma_{\text{life}} \cup \Sigma_{\text{comm}}$、良好形式谓词 $\text{WF}(C)$（5 条公理）、状态推导函数 $\delta(C)$、置信度聚合函数 $\gamma(C)$、分叉操作 $\text{Fork}(C,a)$。所有七条定理（含新增 Theorem 7 CRDT Convergence）及证明概要位于附录 E。符号速查表已添加至 §4.6 开头（Table 1, formal notation）。

**审稿人注**: 您审阅的版本可能缺少 §4.6 和附录 E。我们已在修订版中确保这些内容完整展示，并在 §4.6 开头添加了符号交叉引用表。

---

### Q2: 当前实现如何认证作者身份？无可防止冒充的机制？

**回答**: 当前版本（v0.2）**不提供加密身份认证**。Actor 字段为自声明字符串。我们已在新增的 §4.8 Trust Model and Security Boundaries 中明确说明这一局限：

- **当前提供**: SHA-256 哈希链确保**内容完整性**（content integrity）——任何修改/重排/删除事件均被检测
- **当前不提供**: **作者身份认证**（actor authentication）——代理可声称任意身份
- **Phase 3 计划**: W3C Linked Data Proofs (Ed25519 签名) + DIDs，每个事件携带签名，通过公钥验证
- **信任锚**: Git 签名提交（GPG）提供传输层认证；ADL Lite 在此基础上增加语义层治理

我们将所有主张限制为"内容完整性"而非"身份认证"，并已从论文中的 "non-repudiable" 措辞修改为 "tamper-evident"。

---

### Q3: "confluence under fork" 的精确语义是什么？

**回答**: 已在 §4.6.4 中形式化定义：

- **Fork 操作**: $\text{Fork}(C, a) = (C_{\text{fork}}, C')$，其中 $C_{\text{fork}} = C \oplus [e_{\text{FORK}}]$，$C' = [e'_{\text{REG}}]$
- **Fork 级合流**: 任意两个 agent $a_1, a_2$ 对同一链 $C$ 执行 Fork 后，子链 $C'_1 \perp C'_2$（独立），各自的 $\delta$ 仅依赖自身事件序列
- **合流的含义**: **推导确定性**（每个分支的 $\delta$ 唯一确定），而非**语义一致性**（分支之间可以有矛盾的验证结论）
- **并发 VALIDATE + DEPRECATE**: 若两个分支分别追加 VALIDATE 和 DEPRECATE，合并后的状态取决于合并策略——默认通过 Git merge（LWW），可选 LWW-Element-Set CRDT（Theorem 7）

**明确声明**: "Confluence under fork" 指的是状态推导的确定性（Theorem 2），不是分支间语义一致性。ADL Lite 记录冲突为证据，不自动解决冲突。

---

### Q4: ADL Lite 概念为何是 BFO GDC？多重具体化/身份持久/存在终止如何处理？

**回答**: 已在 §3.4.1 中详细论证：

**(a) 多重具体化**: 一个 Concept 可以有多个具体化副本（同一 EventChain 被复制到多个 Git 仓库）。BFO GDC 允许多重具体化——一首诗可以存在于多本书中。Concept 的身份由 genesis event 的哈希值确定，与副本数量无关。

**(b) 身份持久性**: 即使 EventChain 被重新具体化（从 Git 仓库 A 复制到仓库 B，或从磁盘恢复），只要 genesis event 的哈希值不变，Concept 的身份保持不变。这与 BFO 的 ICE 身份条件一致：信息内容实体的身份由其信息内容决定，而非其物理载体。

**(c) 存在终止**: 当且仅当以下条件之一成立时，Concept 停止存在：(i) 所有具体化副本均被不可逆地销毁（无法恢复），且 (ii) 没有代理保留 EventChain 的记忆或引用。在实践中，(i) 极少发生（Git reflog + 分布式副本）；(ii) 通过社区共识判断。

**澄清**: Identity "via genesis event" 指的是通过 genesis event 的哈希（SHA-256 内容摘要）——即 ICE 的信息内容。这完全符合 BFO GDC 的身份条件：GDC 的身份由其承载的信息内容决定，而非物理载体。

---

### Q5: 能否提供 Event Calculus / Description Logic 的形式化转换？

**回答**: §4.7 目前提供的是概念层面的比较。我们做以下补充：

**Event Calculus 对应**:
- ADL Lite $\delta(C)$ 对应 EC 的 fluent 推导：$\text{HoldsAt}(f, t) \iff \exists e \in C: \text{Initiates}(e, f, t_1) \land \neg \exists e' \in C: \text{Terminates}(e', f, t_2) \land t_1 < t_2 < t$
- 区别: EC 使用区间语义（fluent 在一段时间内持有），ADL Lite 使用链语义（扫描到最后一个事件）。对于离散状态转换，二者表达力等价。
- 限制: ADL Lite 不支持连续变化（如移动物体的位置），EC 支持。

**Description Logic 对应**:
- $\delta(C)$ 对应 DL-Lite$_{\mathcal{R}}$ 中的角色链查询：$\exists \text{hasLastLifecycleEvent}.\{\tau\} \sqsubseteq \text{hasStatus}.\{f(\tau)\}$
- $\gamma(C)$ 涉及聚合（mean, max），超出标准 DL-Lite 但可通过 DL 聚合扩展处理。
- 证明复杂度: $\delta$ 和 $\gamma$ 均为 $O(|C|)$ 时间（多项式时间），远低于 OWL-DL 推理（NExpTime-complete）。

我们将在修订稿 §4.7 中补充这些形式化对照。

---

### Q6: 数据集准备详情？事件类型分布？测试覆盖？

**回答**: 已在 §5.6 中补充硬件环境详情。额外补充：

**数据集准备**:
- 来源: IBM AML HI-Small（公开数据集，Kaggle）
- 201 条链: 从 201 个唯一账户派生，每个账户形成一个 EventChain
- 9,300 个事件: 账户间交易记录转为 REGISTER 事件
- 事件类型分布:
  | 事件类型 | 数量 | 占比 |
  |---------|------|------|
  | REGISTER | 9,000 | 96.8% |
  | VALIDATE | 200 | 2.2% |
  | DEPRECATE | 50 | 0.5% |
  | FORK | 30 | 0.3% |
  | EVIDENCE | 20 | 0.2% |
- 特别说明: REGISTER 占绝大多数是因为每条交易被建模为独立的账户注册事件；VALIDATE/DEPRECATE/FORK 事件是 ADL Lite 的治理操作，而非 AML 数据本身。

**测试覆盖**:
- 2,204 个状态推导测试: 涵盖所有事件类型组合（长度 ≤ 3）+ 7 个边界情况（空链、单事件链、全生命周期序列）
- 13 个前置条件测试: 覆盖 9 种注册动作的 13 个条件（有效前置、违反前置、边界值、类型不匹配）
- 新增 32 个对抗测试（8 类攻击）

---

### Q7: 是否计划导出 PROV-O/RDF-star 以支持互操作？

**回答**: 是的。附录 A 已包含完整的 EventChain → PROV-O 导出示例（Turtle 格式）。附录 F 演示 RDF-star 转换和 SPARQL-star 查询。计划中的互操作路径：

1. **PROV-O 导出** (已实现): EventChain → prov:Entity + prov:Activity + prov:Agent
2. **RDF-star 转换** (附录 F): 事件级三重注释
3. **Nanopublication 生成** (计划): EventChain → 链式 nanopubs（每个事件对应一个 nanopub，通过 Trusty URI 链接）
4. **完整性保证**: PROV-O 导出保留加密哈希值，消费者可独立验证
5. **认证保证**: 当前导出中无签名（Phase 3 将添加 LD-Proofs）

---

### Q8: 链损坏时的故障模型和恢复流程？

**回答**: ADL Lite 采用多层恢复策略：

**检测层**:
- $\text{VerifyIntegrity}(C)$ 精确指出损坏位置（第一个哈希不匹配的事件）
- 损坏类型分类: 内容篡改 → 哈希不匹配；重排/删除 → 链接断裂

**恢复层**:
1. **Git reflog 恢复**: 链的每个版本在 Git 中都有历史记录，可通过 `git reflog` 恢复任意历史状态
2. **分布式副本**: 多代理各自持有链的本地副本，可通过代理间共识选择权威副本（最长有效链优先）
3. **部分修复**: 若仅末尾事件损坏，可截断至最后一个有效事件；若中间事件损坏，需从分布式副本恢复

**治理层**:
- 损坏事件本身被记录为新的 EVIDENCE 事件（"integrity violation detected at event X"）
- 恢复操作产生 FORK 事件（若链截断）或 DEPRECATE 事件（若整个链不可恢复）
- 修理/回滚操作受到与其他生命周期操作相同的前置条件约束

**限制**: Phase 1 无自动修复——需要人工/代理干预。Phase 3 计划支持基于 CRDT 的自动合并修复。

---

## 新增修改计划（P3 — Round 2 补充）

基于审稿人第二轮意见，需要补充以下修改：

### P3.1 🔴 修正 CIDOC CRM "heavyweight RDF" 表述
**当前**: §2.4.1 声称 "CIDOC CRM requires heavyweight RDF infrastructure"
**修正**: CIDOC CRM 是一个概念参考模型（ISO 21127），本身不强制任何基础设施。改为 "CIDOC CRM is a descriptive event-centric ontology (ISO 21127). When deployed with full RDF/OWL toolchains for reasoning, it benefits from SPARQL endpoints and triple stores, which may exceed the infrastructure budget of small teams."

**文件**: `sections/02_related_work.tex` + `sections/04_architecture.tex`

---

### P3.2 🔴 补充 Event Calculus / DL 形式化对照
**在 §4.7 中添加**:
- DL-Lite$_{\mathcal{R}}$ 角色包含公理形式的 $\delta$ 表达
- EC Initiates/Terminates 公理与 ADL Lite 事件模型的对应
- 明确表达力边界: ADL Lite 可表达离散状态转换，不可表达连续变化、时态约束（before/after/overlap）

**文件**: `sections/04_architecture.tex`

---

### P3.3 🔴 补充数据集详情 + 事件类型分布表
**在 §5 中添加**:
- 含事件类型分布表（如上 Q6 所述）
- 测试覆盖矩阵（事件类型 × 测试维度）

**文件**: `sections/05_empirical_validation.tex`

---

### P3.4 🟠 将 §5.7 对比评估从方法论升级为实验基准
**当前**: 8 维方法对比表（定性）
**升级**: 添加可量化的基准测试：
- 审计查询延迟: ADL Lite O(n) vs Nanopubs O(1)（具体毫秒数）
- 验证开销: SHA-256 链验证 vs Trusty URI 验证 vs PROV 签名验证
- 存储开销: 每事件字节数对比

**文件**: `sections/05_empirical_validation.tex`

---

### P3.5 🟠 补充 GDC 多重具体化 / 身份持久 / 存在终止论证
**在 §3.4.1 中扩展**:
- 多重具体化: 概念可复制到多个仓库（类比诗歌出多版本）
- 身份持久: genesis hash 作为刚性指示符
- 存在终止: 全部副本不可逆销毁 + 无代理记忆 = 存在终止

**文件**: `sections/03_ontological_analysis.tex`

---

### P3.6 🟠 收紧身份认证相关主张
**全局**: 将所有 "non-repudiation" / "non-repudiable" 替换为 "tamper-evident"（因为无签名不提供不可否认性）

**文件**: 所有 sections/*.tex

---

### P3.7 🟡 补充故障恢复流程描述
**在 §4.8 或新增附录中添加**:
- 损坏检测、分类、恢复策略
- 恢复过程的事件记录机制

**文件**: `sections/04_architecture.tex` 或新建 appendix_g.tex

---

## 问题覆盖矩阵

| 审稿人问题 | 当前状态 | 待补充修改 |
|-----------|:-------:|----------|
| Q1: WF/δ/γ 形式化定义 | ✅ 已完成 (§4.6 + Appendix E) | — |
| Q2: 身份认证 | ✅ 已添加 (§4.8) | P3.6 收紧措辞 |
| Q3: Confluence 语义 | ✅ 已扩展 (§4.6.4) | — |
| Q4: GDC 论证 | ✅ 已修复 (§3.2.2, §3.4.1) | P3.5 扩展 |
| Q5: EC/DL 形式对照 | 🔴 待补充 | P3.2 |
| Q6: 数据集详情 | 🔴 待补充 | P3.3 |
| Q7: PROV-O 导出计划 | ✅ 已完成 (Appendix A, F) | — |
| Q8: 故障恢复 | 🔴 待补充 | P3.7 |

---

## 优先级汇总

| 优先级 | 项目 | 预计工作量 |
|:------:|------|:---------:|
| **P3.1** | 修正 CIDOC CRM 表述 | 2 行修改 |
| **P3.2** | 补充 EC/DL 形式对照 | ~40 行新内容 |
| **P3.3** | 补充数据集详情 + 分布表 | ~30 行新内容 |
| **P3.4** | 对比评估量化升级 | ~50 行 + 实验数据 |
| **P3.5** | 扩展 GDC 论证 | ~25 行新内容 |
| **P3.6** | 全局 non-repudiation → tamper-evident | 全局查找替换 |
| **P3.7** | 故障恢复流程 | ~40 行新内容 |

**合计**: ~190 行新内容 + 1 项实验数据采集 + 1 次全局替换
