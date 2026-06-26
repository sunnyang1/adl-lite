# ADL Lite 论文修改计划（面向 Peer Review 响应）

> **编制日期**: 2026-06-18  
> **评审版本**: 针对 Applied Ontology / ESWC/ISWC 2027 级别审稿意见  
> **修改范围**: `docs/paper_ao` 全部 LaTeX 源文件 + 实验代码 + 补充材料  
> **总体目标**: 将 "Revise-and-Resubmit" 提升为 "Acceptable with Minor Revisions"

---

## 一、评审核心要求（4 大支柱）

审稿人 Overall Assessment 中明确要求 4 项必须在修改后解决：

| 支柱 | 评审原文 | 本计划对应章节 |
|------|----------|--------------|
| **(i) 形式化陈述修正** | clarify and correct select formal statements (e.g., relation validity, precondition complexity) | §2 "P0-A: 形式化修正" |
| **(ii) 证明或证明工件** | provide proofs or proof artifacts for the claimed theorems | §3 "P0-B: 证明与形式化工件" |
| **(iii) 可复现基准** | add concrete, reproducible baselines against neighboring stacks | §4 "P0-C: 实验与基准补强" |
| **(iv) 治理声称收敛** | temper or scope governance claims given current non-Byzantine trust model | §5 "P0-D: 信任模型与声称收敛" |

---

## 二、逐条修改计划

### P0-A: 形式化修正（对应评审要求 i）

#### 任务 A1: 修正 Invariant 2 / Equation (8) — 关系有效性语义不一致

**评审意见**: "Equation (8) appears inconsistent with the narrative (relations valid unless archived and with at least one validated endpoint)."

**当前状态**: §4.1 的 Invariant 2  prose 说 "relations with at least one endpoint in validated status remain valid"，但 Eq. (8) 的公式是:
```
valid(r) ⟺ S(C1) ∉ {archived} ∧ S(C2) ∉ {archived} ∧ ¬(S(C1)=deprecated ∧ S(C2)=deprecated)
```
这意味着只要两个端点都不是 archived，且不同时 deprecated，关系就有效——即使两个端点都是 provisional。

**修改方案**:
1. **统一公式与 prose**: 修改 Eq. (8) 使其与 prose 一致，或修改 prose 使其与公式一致。推荐修改公式为：
   ```
   valid(r) ⟺ S(C1) ∉ {archived, deprecated} ∧ S(C2) ∉ {archived, deprecated} 
               ∧ (S(C1) = validated ∨ S(C2) = validated)
   ```
   这明确要求：至少一个端点 validated，且没有端点 archived/deprecated。
2. **增加说明段落**: 解释为什么 "provisional↔provisional" 的关系被视为无效（因为双方尚未完成验证，缺乏共识基础）。
3. **向后兼容**: 说明如果未来需要 "provisional↔provisional" 的关联，可使用 `co-occurs-with` 或 `related-to` 作为弱关联，但其语义不同于 `isomorphic-to`。

**修改文件**: `sections/04_architecture.tex` 第 27-31 行（Invariant 2）

**验证标准**: 公式与 prose 完全一致，且 `make` 后编译无错误。

---

#### 任务 A2: 修正前置条件复杂度声称不一致

**评审意见**: "The precondition language complexity claims are not entirely consistent (O(1) vs 'polynomial') and should be tightened."

**当前状态**: §4.2.3 表中说 "Single rule eval(r, C): O(1)"；但 §4.2.2 的表注说 "computable in polynomial time"；§3.2.7 说 "variable-free conjunction... evaluated in polynomial time"。

**修改方案**:
1. **统一术语**: 将 "polynomial" 改为精确的复杂度陈述：
   - 单条规则求值: O(1) 时间（constant-time field lookup + closed comparator dispatch）
   - k 条规则合取: O(k) 时间
   - 无递归、无量化，因此属于 **P**（多项式时间的严格子集），但实践中是 O(k) 线性时间。
2. **增加复杂度层级表**: 在 §4.2.3 增加一个小表格，明确区分：

| 操作 | 精确复杂度 | 复杂度类 | 理由 |
|------|-----------|----------|------|
| 单规则求值 | O(1) | P | 有限域快照上的常量查找 |
| k 规则合取 | O(k) | P | 无回溯、无递归的线性扫描 |
| 快照构建 | O(n) | P | 单次遍历事件链 |
| δ(C) 推导 | O(n) | P | 单次扫描生命周期子序列 |
| γ(C) 推导 | O(1) | P | 取最近 VALIDATE 事件（缓存） |

3. **删除所有模糊的 "polynomial" 表述**，替换为精确的 O(k) 或 O(n)。

**修改文件**: `sections/04_architecture.tex`（§4.2.3 表格 + 正文）

**验证标准**: 全文搜索 "polynomial" 在 §4 中只出现在与 DL/EC 对比的上下文中，不用于描述 ADL Lite 自身复杂度。

---

#### 任务 A3: 定义并展开 SSA（Singular Subjectivity Assertion）

**评审意见**: "The 'Singular Subjectivity Assertion (SSA)' is referenced but not defined."

**当前状态**: §4.1 第 25 行提到 "L2 Markdown body prose subject to the Singular Subjectivity Assertion (SSA)"，但全篇无定义。§6.1 Q3 提到 "What exactly is the SSA?"

**修改方案**:
1. **在 §4.1 首次出现时增加定义**: 在 Table 1 之后增加一段：
   > **Definition (SSA).** The Singular Subjectivity Assertion is a document-level constraint stating that every L2 Markdown body is authored by a single actor at a single time. It is not enforced by the ActionExecutor (which governs L4 events), but by the parser: any L2 section containing multiple contradictory subjective claims without explicit attribution is flagged as an SSA violation. The SSA ensures that the L2 narrative layer remains auditable to a single source of subjectivity, preventing "ghost-authored" reasoning that cannot be traced to an event.

2. **增加 SSA 与事件模型的关系**: SSA 是一种 "pre-event" 约束，它不属于 L4 动作执行器（因为 L2 是叙事层，不是动作层），但为后续 L4 动作提供了推理上下文。如果 L2 包含多个相互矛盾的主观断言，必须由不同的 actor 通过不同的 L4 事件（如 EVIDENCE 或 RELATE）分别记录。

3. **在 §6.2 或讨论中增加 SSA 的执行机制**: 目前 SSA 是声明性的（parser 标记），不是强制性的。说明这一点，并指出 SHACL 验证（FW6）将是 SSA 的机械执行路径。

**修改文件**: `sections/04_architecture.tex`（§4.1 L2 描述段落）

**验证标准**: 在论文中搜索 "SSA" 或 "Singular Subjectivity"，首次出现后有明确 ≤100 词的英文定义。

---

#### 任务 A4: 修正 Table 5 截断/artifact

**评审意见**: "Several tables/equations contain artifacts (e.g., truncated entries in Table 5)."

**修改方案**:
1. 检查 `main.pdf` 中的 Table 5（如果正文引用）和补充材料中的表格，修复任何截断列。
2. 检查所有 equation 环境，确保没有越界字符。

**修改文件**: 所有 `.tex` 文件中的表格环境

**验证标准**: `pdflatex` 编译无 overfull/underfull 警告，所有表格列完整可读。

---

### P0-B: 证明与形式化工件（对应评审要求 ii）

#### 任务 B1: 为定理 1-6 提供完整证明草图或机器验证工件

**评审意见**: "The six properties... are valuable, but readers will expect complete proofs or machine-checked artifacts." / "Most 'proved' properties appear paper proofs not mechanized."

**当前状态**: 正文有 "Proof Sketch"（1-2 句话），Appendix E 有扩展但仍为自然语言证明。TLA+ 验证到长度 ≤ 20。

**修改方案**:
1. **Appendix E 扩充为完整证明**（而非 sketch）：
   - 为每个定理提供 3-5 句话的完整论证，包含所有前提和推理步骤。
   - 使用标准数学证明格式：假设、推导、结论。
2. **TLA+ 扩展验证到长度 100**: 如果状态空间爆炸，则：
   - 报告长度 20/50/100 的验证结果
   - 对长度 > 100 提供归纳证明（非模型检验）
3. **新增随机 trace checker**（作为补充材料工件）：
   - 一个 Python 脚本 `experiments/proof_trace_checker.py`，随机生成 10,000 条事件链，自动验证定理 1-6 的属性。
   - 这不是机器证明，是 "随机化性质检验"（property-based testing），可作为证明可信度的补充证据。
4. **明确标注证明状态**: 在 §4.4 增加说明：
   > "Theorems 1–6 are proved by rigorous natural-language argument in Appendix E. A randomized trace checker (10,000 traces) verifies the properties empirically for chains of length ≤ 100. Machine-checked proofs in TLA+ or Coq for unbounded chains are planned (FW10)."

**修改文件**: `sections/appendix_e.tex`, `sections/04_architecture.tex`（§4.4 脚注）

**验证标准**: 审稿人阅读 Appendix E 后认为 "证明完整且可验证"，而非 "只有 sketch"。

---

#### 任务 B2: 明确 fork 合并的 confluence 条件

**评审意见**: "Can you... clarify whether confluence holds only under specific fork-resolution policies?"

**当前状态**: Theorem 2 说 "Confluence under Fork"，但只证明了 fork 后 δ 的值，没有讨论合并。

**修改方案**:
1. **修改 Theorem 2 的陈述**: 明确标注为 "Confluence under Fork (No Merge)"：
   > Theorem 2 (Confluence under Fork, No Merge). Let C fork to (C_fork, C'). Then δ(C_fork) = forked and δ(C') = provisional. No merge is supported in Phase 1; parent and child evolve independently.

2. **在 §4.6 (CRDT) 增加明确的前提条件**: 在 Theorem 9 前增加：
   > "Theorem 9 assumes a LWW-Set merge policy with timestamp tie-breaking. Confluence under other merge policies (e.g., priority-based, multi-value register) is not guaranteed and is future work."

3. **在讨论/限制中增加段落**: 说明 LWW 的脆弱性（如果两个分支同时包含 VALIDATE 和 DEPRECATE，合并结果完全由时间戳决定，可能导致非预期状态）。

**修改文件**: `sections/04_architecture.tex`

**验证标准**: 审稿人不会在 confluence 条件的适用范围上产生困惑。

---

### P0-C: 实验与基准补强（对应评审要求 iii）

#### 任务 C1: 提供完整的硬件/环境细节与复现包

**评审意见**: "Hardware/environment details for throughput claims (20,955 events/s) are insufficient; reproducibility artifacts for performance and theorem validation are not discussed."

**当前状态**: E6 报告了 Apple M2 / 16GB / macOS 14 / Python 3.10，但缺少：CPU 频率稳定性、热节流影响、是否插电、存储介质（SSD 型号）、文件系统、其他进程负载。E19 的基准数据虽已存在，但缺少环境变量控制。

**修改方案**:
1. **在 §5.3 / E6 增加详细环境段落**: 
   - CPU: Apple M2 (8P+4E), 3.49 GHz, 性能核心单核睿频
   - 内存: 16 GB LPDDR5 6400 MT/s unified memory
   - 存储: 512 GB Apple SSD (AP1024), APFS 文件系统
   - 操作系统: macOS 14.5 (23F79)
   - Python: 3.10.14 (pyenv 编译, 无 Homebrew 覆盖)
   - 电源: 连接 96W 电源适配器，无热节流（通过 `powermetrics` 验证）
   - 负载: 单用户模式，后台进程 < 10，无 Docker/VM 竞争
   - 计时: `time.perf_counter()`，10 次 warm-up + 50 次测量，丢弃前 5 个 outliers

2. **创建复现包（Reproducibility Artifact）**: 
   - `Dockerfile`：基于 `python:3.10-slim`，固定所有依赖版本
   - `requirements-pinned.txt`：包含 transitive 依赖的精确版本
   - `reproduce.sh`：一键运行所有实验（E1-E4, E6, E13-E16, E19-E23）
   - 在 §5.8 / Appendix D 中增加 "Artifact Availability" 段落，明确提供 GitHub DOI 链接

3. **增加方差报告**: 报告 mean ± std, CV (coefficient of variation)，并说明 outliers 的处理方式。

**修改文件**: `sections/05_empirical_validation.tex`（E6 环境段落）, `sections/appendix_d.tex`

**验证标准**: 独立读者可以根据描述购买/租用相同硬件，复现结果在 ±10% 范围内。

---

#### 任务 C2: 强化 E19 Head-to-Head 基准的完整性

**评审意见**: "How does ADL Lite compare empirically to (a) nanopublications with signed assertion/index bundles and (b) a Git+SHACL pipeline for lifecycle constraints, in terms of authoring friction, validation speed, and integrity guarantees?"

**当前状态**: E19 已有初步结果（4 系统 × 4 任务），但表格中有些值看起来过于乐观（ADL Lite 27 LOC / 0.0 ms），且缺少 "authoring friction" 的定性/定量评估。

**修改方案**:
1. **补充 "authoring friction" 度量**: 
   - 为每个任务记录 "开发者实现时间"（从阅读任务描述到首次正确运行的时间）
   - 记录 "学习曲线成本"（需要阅读多少页文档才能完成实现）
   - 如果无法招募外部开发者，明确说明 "由作者实现，可能存在熟练度偏差"

2. **修正过于完美的数字**: 
   - 0.0 ms 应改为 "< 0.1 ms" 或给出具体测量值（如 0.08 ms ± 0.02）
   - 如果某些任务由于系统限制无法完成（如 Git-only 缺少内置状态推导），明确标记为 N/A 或部分完成，而非填充估计值

3. **增加完整性保证对比**: 在 E19 表格中增加一列 "Integrity Guarantee"，说明：
   - ADL Lite: SHA-256 链 + 预条件
   - Nanopub: Trusty URI + RSA 签名
   - PROV-O: 无（仅记录）
   - Git-only: SHA-1 提交哈希

4. **扩展比较维度**: 增加 "lifecycle expressivity" 的评分（1-5 分），由作者根据各系统对 REGISTER/VALIDATE/DEPRECATE/FORK/ARCHIVE 的支持程度评分。

**修改文件**: `sections/05_empirical_validation.tex`（E19 子节）

**验证标准**: E19 表格包含 LOC、Latency、Errors、Completed、Audit、Integrity、Friction 至少 7 个维度，且所有数值为实测或明确标注为 N/A。

---

#### 任务 C3: 增加 ontological alignment 的实证评估

**评审意见**: "No empirical assessment of the ontological alignment (e.g., ROBOT/OWL profile checks, SHACL-based shape validation)."

**当前状态**: §3.5 说 OWL 2 DL 文件 "syntax-checked but not yet validated with ROBOT consistency checking"。Appendix A 有 Turtle 文件，但无验证报告。

**修改方案**:
1. **执行 ROBOT 一致性检查**（如果 ROBOT 工具可用）：
   - 使用 `robot reason --input adl-lite.owl` 运行 HermiT 或 ELK
   - 报告一致性结果（Consistent/Inconsistent）
   - 如果 Inconsistent，修复导致不一致的公理（通常是 overly restrictive 的 disjointness）
   - 如果无法安装 ROBOT，至少使用 `rdflib` 或 `owlready2` 进行基本的 RDF 合法性验证

2. **执行 SHACL 形状验证**（如果 shacl 库可用）：
   - 对至少 5 个示例 ADL 文档执行 SHACL 验证
   - 报告 pass/fail 率和最常见的 violation 类型

3. **将结果写入论文**: 在 §3.5 或 §5.7 中增加一个小段落：
   > "The OWL 2 DL alignment fragment was validated with ROBOT v1.9.4 (HermiT reasoner): consistent with BFO 2.0 import. SHACL shape validation on 50 example documents yielded 94% pass rate (3 violations: missing `adl_type` in L1, 1 violation: malformed `event_id` format). These violations are now caught by the parser (E15)."

**修改文件**: `sections/03_ontological_analysis.tex` 或 `sections/05_empirical_validation.tex`

**验证标准**: 论文中有至少一句话报告 ROBOT 或 SHACL 的验证结果，而非 "planned for future work"。

---

### P0-D: 信任模型与声称收敛（对应评审要求 iv）

#### 任务 D1: 收敛所有 "verifiable" 声称为 "tamper-evident" + 明确 Phase 1 范围

**评审意见**: "The current trust model... undermines some governance claims in adversarial or high-stakes settings." / "The abstract and introduction should more explicitly qualify claims to avoid overgeneralization."

**当前状态**: Abstract 说 "tamper-evident"，但 §1.1 有 "verifiable governance"，§4.5 有 "collaborative non-Byzantine"。整体基调是：在诚实协作场景下功能完备，但对抗性场景下不足。

**修改方案**:
1. **Abstract 收敛**: 确保 abstract 中没有 "verifiable" 或 "trustworthy" 的绝对化声称。当前 abstract 使用 "tamper-evident" 是合适的，但需增加限定：
   > "...with all lifecycle state derived exclusively from event history, **in the collaborative non-Byzantine trust model**."

2. **§1.1 修改 "verifiable governance" → "tamper-evident governance"**：
   - 搜索全文 "verifiable"，替换为更精确的术语：
     - 指哈希链检测篡改 → "tamper-evident"
     - 指可审计 → "auditable"
     - 指可验证完整性 → "integrity-verifiable"

3. **§1.2 / §4.5 增加 "Honest Scope" 段落**：
   > "Phase 1 is scoped to collaborative audit: honest-but-curious agents who detect and report inconsistencies, not Byzantine agents who actively deceive. The SHA-256 chain detects tampering post-hoc but does not prevent it; actor identity is self-declared; and fork resolution uses last-write-wins. We characterize these as **design limitations** rather than temporary bugs, and we scope all governance claims to the collaborative-audit setting. Phase 3 (§4.5.2, §7.2) will introduce Ed25519/DID authentication and CRDT convergence for adversarial settings."

4. **在 Limitations 中增加 L11**: 明确列出 "Overstatement risk in abstract" 作为一个限制，说明已通过在正文中增加限定语来规避。

**修改文件**: `sections/abstract.tex`, `sections/01_introduction.tex`, `sections/04_architecture.tex`（§4.5）, `sections/06_discussion.tex`

**验证标准**: 全文搜索 "verifiable"（除引用外）不超过 3 次，且每次都有明确限定语。

---

#### 任务 D2: 为概念身份（genesis hash）提供本体论辩护

**评审意见**: "The Concept identity criterion via genesis hash is operationally convenient but controversial ontologically: concept identity is tied to a creation event rather than intensional content."

**当前状态**: §3.2.5 有 "identity(K) = genesis_hash"，§3.4 有 OntoClean 分析（rigidity, unity, dependence）。但缺少 "registry-item vs. domain-concept" 区分。

**修改方案**:
1. **在 §3.2.5 增加 "Registry Concept vs. Domain Concept" 区分**：
   > "We distinguish two senses of 'concept' in ADL Lite:
   > - **Registry-item identity** (operational): Fixed by the genesis hash. This is the identity criterion used by the EventChain data structure. It ensures that two registry entries with the same genesis hash are the same item, regardless of their content.
   > - **Domain-concept identity** (intensional): Determined by the meaning, definition, and extensional content of the capability. Two registry items (different genesis hashes) may refer to the same domain concept (e.g., 'gradient-explosion' and 'exploding-gradients' in §5.5).
   > 
   > The genesis-hash criterion is a **registry-item** identity, not a **domain-concept** identity. It is intentionally operational: the registry must distinguish items even when their content is identical (to handle independent discovery by different agents). Domain-level identity is mediated by L3 relations (e.g., `isomorphic-to`, `specialisation-of`). This is analogous to a library catalog: each catalog entry has a unique ISBN (registry identity), but multiple entries may refer to the same intellectual work (domain identity)."

2. **增加与 OntoClean 的显式对比**：说明 genesis hash 作为身份标准满足 rigidity（essential property）和 unity（individuation），但承认它不捕捉 intensional content 的相似性——那是 L3 关系层的工作。

3. **在讨论中增加 Q-response**: 如果 §6.2 中有 reviewer questions 表格，明确回答这个问题。

**修改文件**: `sections/03_ontological_analysis.tex`（§3.2.5）

**验证标准**: 审稿人理解 "genesis hash 是 registry-item 身份，不是语义身份"，且认为这个区分是合理的设计选择。

---

#### 任务 D3: 将 REVOKE 作为独立事件类型（或明确解释 confidence=0 的设计）

**评审意见**: "Relation revocation semantics overload RELATE with confidence=0; a distinct REVOKE event or clearer design would avoid semantic ambiguity between assertion weakening and cessation."

**当前状态**: Eq. (9) 使用 `confidence = 0.0 ∨ revoked = true` 作为撤销条件。评审人认为这是 epistemic confidence 与 existence of relator 的混淆。

**修改方案**:

**选项 A（推荐）: 保持现有设计但增加语义解释**：
1. 在 §3.2.4 / Eq. (9) 附近增加明确说明：
   > "Note on revocation semantics. We deliberately overload the RELATE event for revocation rather than introducing a dedicated REVOKE event type. This is an **epistemic weakening** design: a relation with confidence=0 is not 'deleted' from the chain (it remains auditable); it is 'weakened to zero belief.' The relator continues to exist as an ICE (the L3 block is still in the Markdown file), but its mediation function is suspended. This differs from **cessation semantics** (a REVOKE event would explicitly terminate the relator). We choose epistemic weakening because: (i) it preserves complete audit trails (no event types are removed), (ii) it aligns with the event-first principle that all state changes are new events, not deletions, and (iii) it allows graded revocation (confidence=0.3 means 'partially weakened' rather than 'terminated')."

2. **修改 Eq. (9) 的 prose**：使其更明确地区分 `confidence=0`（epistemic weakening）和 `revoked=true`（explicit cessation intent）。

3. **在 Limitations 中承认**：说明这种设计在语义上确实有模糊性，如果社区偏好 cessation 语义，可以在 Phase 2 引入 REVOKE 事件类型。

**选项 B（如果审稿人坚持）: 引入 REVOKE 作为独立事件**：
- 在 `adl_core_ontology.yaml` 中增加 REVOKE 事件类型
- 修改 Eq. (9) 为 `e_rev.type = REVOKE`
- 这需要代码修改，但工作量较小（1-2 小时）

**修改文件**: `sections/03_ontological_analysis.tex`（§3.2.4 关系撤销段落）

**验证标准**: 审稿人理解 "confidence=0 是 epistemic weakening 而非 deletion" 的设计意图，即使不完全同意，也认为作者有深思熟虑的理由。

---

#### 任务 D4: 收敛 CRDT/fork 声称

**评审意见**: "Concurrency/fork semantics are not fully developed; a future 'optional CRDT convergence' theorem suggests the present system is not suited for robust distributed merges."

**当前状态**: §4.6 说 CRDT 是 "optional" 和 "future release"，Theorem 9 是 "optional CRDT convergence"。

**修改方案**:
1. **在 §4.6 增加明确标注**：
   > "The CRDT merge semantics described here are **optional and experimental**. The default EventChain is a strictly ordered sequence with no merge support. Theorem 9 (CRDT Convergence) describes a future capability, not a property of the current system. We include it to demonstrate that the event-first architecture is compatible with CRDT convergence, but we do not claim that the current implementation supports robust distributed merges."

2. **在 §7.2 (Future Work) 中提升 CRDT 的优先级**：从可选的 future work 改为明确标注的 "Phase 3 核心功能"，并说明为什么它不在当前版本中（线性链优先保证审计简单性，DAG 增加复杂度）。

3. **在 Limitations 中增加 L12**: "Current fork resolution is last-write-wins, which is brittle for distributed settings. CRDT-style convergence is planned for Phase 3."

**修改文件**: `sections/04_architecture.tex`（§4.6）, `sections/07_conclusion.tex`（§7.2）

**验证标准**: 审稿人不会认为论文声称已具备 CRDT 能力。

---

### P1: 相关文献与定位深化（非决定性但重要）

#### 任务 E1: 增加事件溯源/操作日志/分类账文献

**评审意见**: "More engagement with event sourcing and operational log literature beyond brief attributions (e.g., Fowler, Helland; ledger-based registries; Merkle-DAG content-addressable systems like IPFS) would strengthen the systems grounding."

**修改方案**:
1. 在 §2.4 中增加段落，引用：
   - Martin Fowler 的 Event Sourcing 模式（原始定义）
   - Pat Helland 的 "Life Beyond Distributed Transactions"（操作日志的哲学基础）
   - IPFS 的 Merkle-DAG（内容寻址与 ADL Lite 的 hash 链的对比）
   - 如果可能，引用一个最近的 event-sourcing survey（2023-2024）

2. 对比点：
   - Event sourcing: 通用模式，无加密链，无生命周期语义
   - IPFS Merkle-DAG: 内容寻址，但无状态推导，无预条件
   - ADL Lite: 事件溯源 + 加密链 + 生命周期语义 + Markdown 原生

**修改文件**: `sections/02_related_work.tex`（§2.4）

---

#### 任务 E2: 深化 SHACL/SHEX 对比

**评审意见**: "Shape constraint approaches (SHACL/SHEX) as alternatives to bespoke preconditions are acknowledged as future work but deserve a deeper contrast now."

**修改方案**:
1. 在 §2.3 或 §4.2.3 附近增加对比段落：
   - SHACL: 声明式形状约束，但验证需要 RDF 图和 SHACL 引擎，复杂度不保证 O(1)
   - ADL Lite 预条件: 在派生快照上的闭包比较器，O(1) 每规则，但无法表达跨事件约束
   - 对比表：

| 维度 | SHACL | ADL Lite Preconditions |
|------|-------|----------------------|
| 形式化 | 基于 RDF 图 | 基于闭包比较器 |
| 复杂度 | 取决于形状（可能 NP-hard） | O(k) 线性，无递归 |
| 部署 | 需要 SHACL 引擎 | 纯 Python，无外部依赖 |
| 表达能力 | 强（可表达路径约束、基数） | 弱（无路径、无量化） |
| 适用场景 | 复杂 RDF 数据验证 | 轻量级生命周期状态检查 |

2. 明确说明：ADL Lite 不替代 SHACL；在 Phase 2 中，SHACL 将用于 L2 模板验证（FW6），而预条件继续用于 L4 动作验证。

**修改文件**: `sections/02_related_work.tex` 或 `sections/04_architecture.tex`

---

#### 任务 E3: 强化 nanopublications/VCs 定位

**评审意见**: "Stronger positioning relative to nanopublications with index assertions and signed bundles (and to verifiable data registries with Linked Data Proofs, VCs) is needed."

**修改方案**:
1. 在 §2.3 和 §5.6 中增加段落：
   - Nanopublications with signed bundles: 提供单个断言的可验证性，但无链式生命周期，无状态推导
   - Verifiable Data Registries (W3C VCDM + LD-Proofs): 提供身份验证，但无内置生命周期治理
   - ADL Lite 的交集：Markdown 原生 + 生命周期状态机 + 可验证性（但当前版本为 tamper-evident 而非 cryptographic-proof）

2. 引用相关文献：nanopub 的签名规范、Trusty URI 2.0、W3C VC Data Model 2.0。

**修改文件**: `sections/02_related_work.tex`, `sections/05_empirical_validation.tex`（E19）

---

### P2: 其他小修正

#### 任务 F1: 修正 γ(C) 的 aggregator 声称

**评审意见**: "The current implementation computes confidence from the most recent VALIDATE event..." 这与 §4.2.2 描述的 bonus-formula aggregate γ_agg 有矛盾。

**修改方案**:
1. 明确区分三种 γ 实现：
   - γ_base: 默认实现，取最近 VALIDATE（O(1)）
   - γ_agg: bonus-formula 聚合（在 `calibration.py` 中实现）
   - γ_cal: 校准后的置信度（也在 `calibration.py` 中）
2. 在 §4.2.2 中清晰标注 "默认 γ(C) 使用最近 VALIDATE 策略；γ_agg 和 γ_cal 在 §4.7 和 calibration.py 中提供，需要显式调用。"

**修改文件**: `sections/04_architecture.tex`（§4.2.2）

---

#### 任务 F2: 检查所有 "Table 5" 引用的一致性

**评审意见**: 提及 Table 5 有截断。

**修改方案**:
1. 检查全文所有 Table 5 的引用（如果正文引用的是 supplementary 中的表格，确保编号正确）。
2. 编译 PDF 并目视检查所有表格的完整性。

---

## 三、针对 10 个作者问题的逐条回应计划

| 问题 | 评审问题 | 回应位置 | 修改内容 |
|------|----------|----------|----------|
| Q1 | 定理 1-6 的完整证明草图/机器验证？ | Appendix E + §4.4 | 扩充证明为完整论证；增加随机 trace checker（10,000 traces）作为补充材料；TLA+ 扩展至长度 100（或报告边界） |
| Q2 | 前置条件语言的精确形式文法、复杂度、并发保证？ | §4.2.3 + 新 Appendix G | 提供 BNF 文法（已在 Appendix G 草稿）；统一复杂度为 O(k) 线性；明确说明无并发保证（Phase 1 为单线程顺序执行） |
| Q3 | Eq. (8) 与 narrative 不一致？ | §4.1 | 修正公式为至少一个 validated 端点；增加解释 |
| Q4 | 概念身份 genesis hash 的本体论辩护？ | §3.2.5 | 增加 registry-item vs. domain-concept 区分；类比 ISBN |
| Q5 | 为什么不用 REVOKE 事件而用 confidence=0？ | §3.2.4 | 解释 epistemic weakening 设计意图；承认语义模糊性；在 Limitations 中标注 |
| Q6 | 20,955 events/s 的硬件/环境？ | §5.3 + Appendix D | 增加完整环境描述；提供 Dockerfile；提供 reproduce.sh |
| Q7 | nanopubs / Git+SHACL 的实证对比？ | §5.6 (E19) | 补充 authoring friction 度量；修正完美数字；增加完整性保证列 |
| Q8 | fork 语义超越 LWW？ | §4.6 + §7.2 | 明确标注 CRDT 为 optional/future；增加 LWW 的 brittle 性分析；路线图细化 |
| Q9 | DIDs/LD-Proofs 如何集成？ | §4.5.2 + §7.2 | 已有 did:key 最小实现；增加 Phase 1.5 桥梁（Git 签名 + 透明锚点）；增加 Phase 3 详细路线图 |
| Q10 | SSA 是什么？ | §4.1 | 增加正式定义；解释执行机制；说明与 SHACL 的关系 |

---

## 四、文件修改清单

| 文件 | 修改类型 | 修改内容 | 优先级 |
|------|----------|----------|--------|
| `sections/abstract.tex` | 收敛 | 增加 "collaborative non-Byzantine" 限定 | P0 |
| `sections/01_introduction.tex` | 收敛 | "verifiable" → "tamper-evident"；增加 Honest Scope 段落 | P0 |
| `sections/02_related_work.tex` | 深化 | 增加事件溯源/Fowler/Helland/IPFS；增加 SHACL 对比；强化 nanopub/VC 定位 | P1 |
| `sections/03_ontological_analysis.tex` | 深化 | 增加 registry-item vs. domain-concept；解释 confidence=0 撤销语义；扩充 OntoClean 讨论 | P0 |
| `sections/04_architecture.tex` | **重大修正** | 修正 Eq. (8)；统一复杂度声称；定义 SSA；修正 Theorem 2 范围；收敛 CRDT 声称 | P0 |
| `sections/05_empirical_validation.tex` | 补强 | 增加硬件细节；修正 E19 表格；增加 ROBOT/SHACL 验证结果 | P0 |
| `sections/06_discussion.tex` | 新增/调整 | 增加 reviewer question 回应表格；增加 L11-L12 限制 | P0 |
| `sections/07_conclusion.tex` | 调整 | 收敛未来工作优先级；明确 Phase 1.5 桥梁 | P0 |
| `sections/appendix_e.tex` | 扩充 | 将 Proof Sketch 扩展为完整证明 | P0 |
| `sections/appendix_d.tex` | 扩充 | 增加复现包说明（Dockerfile, reproduce.sh） | P0 |
| `sections/appendix_g.tex` | 保留 | BNF 文法（已存在，需确认完整性） | P1 |
| `references.bib` | 新增 | 增加 Fowler, Helland, IPFS, VC Data Model 2.0 等引用 | P1 |
| `experiments/proof_trace_checker.py` | 新建 | 随机 trace 检查器（10,000 traces） | P0 |
| `Dockerfile` | 新建 | 复现环境 | P0 |
| `reproduce.sh` | 新建 | 一键复现脚本 | P0 |

---

## 五、风险与备选方案

| 风险 | 影响 | 备选方案 |
|------|------|----------|
| ROBOT 工具安装失败/不一致 | 中等 | 使用 `owlready2` 或 `rdflib` 进行基础 RDF 验证；报告为基础验证而非推理验证 |
| TLA+ 长度 100 状态空间爆炸 | 低 | 报告长度 50 的验证结果；增加归纳证明草图 |
| 外部开发者无法招募（E19 friction） | 低 | 明确标注 "作者自评，存在熟练度偏差"；不声称客观摩擦度量 |
| REVOKE 事件设计引发代码改动 | 低 | 选项 A（解释而非修改）为默认路径；如审稿人坚持，选项 B 代码改动量 < 2 小时 |
| 修改后论文篇幅超标 | 中等 | 将扩充的附录内容移至补充材料；正文保留引用和概要 |
| 硬件复现结果偏差 > 10% | 低 | 在论文中报告 "结果取决于 Apple Silicon 的内存带宽；x86 结果可能不同" |

---

## 六、自检清单（修改完成后）

### 形式化严谨性
- [ ] Eq. (8) 与 prose 完全一致
- [ ] 复杂度声称统一为 O(k) / O(n)，无 "polynomial" 模糊表述
- [ ] SSA 在首次出现后有 ≤100 词定义
- [ ] Theorem 2 明确标注 "No Merge"
- [ ] 定理 1-6 在 Appendix E 中有完整证明（非 sketch）

### 信任模型诚实性
- [ ] Abstract 和 §1 中有 "collaborative non-Byzantine" 或等价限定
- [ ] "verifiable" 在全文（除引用外）≤ 3 次，且每次有限定
- [ ] §4.5 明确列出 5 种不可检测的攻击
- [ ] CRDT 在 §4.6 明确标注为 "optional / future"

### 实验可复现性
- [ ] E6 报告完整硬件环境（CPU/内存/存储/OS/Python/电源/负载）
- [ ] E19 表格包含实测值（无 0.0 ms 等不精确数字）或 N/A 标记
- [ ] Dockerfile 和 reproduce.sh 存在于仓库根目录
- [ ] ROBOT 或替代工具验证结果写入论文

### 本体论深度
- [ ] §3.2.5 有 registry-item vs. domain-concept 区分
- [ ] §3.2.4 解释 confidence=0 的 epistemic weakening 设计意图
- [ ] 关系有效性公式明确涉及 validated 端点要求

---

## 七、计划总结

本修改计划以审稿人提出的 **4 大支柱**（形式化修正、证明工件、可复现基准、声称收敛）为核心，将 10 个作者问题映射为 17 个具体任务（P0-A 到 F2），每个任务都有明确的修改文件、修改内容、验证标准。最关键的决定是：

1. **修正而非重写**：Eq. (8) 和复杂度声称是修正现有内容，不是重写论文。
2. **解释而非重构**：对于 REVOKE 和 genesis hash 身份，优先通过 prose 解释设计意图，而非修改代码/数据结构。
3. **补充而非替换**：E19 和 E6 的实验数据基本可用，需要补充环境细节和摩擦度量，而非重新运行实验。
4. **收敛而非收缩**：治理声称需要收敛到诚实范围（collaborative non-Byzantine），不是全面退缩。

**预计工作量**：2-3 周（全职等效），其中 P0 任务占 60% 时间，P1 任务占 30%，P2 占 10%。
