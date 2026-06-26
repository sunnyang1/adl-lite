# ADL Lite 论文修改计划（基于新评审意见）

## 评审核心关切
评审认可论文的及时性、创新性和架构验证，但指出以下必须解决的关键问题：
1. **本体论矛盾**：GDC 不能依赖于 occurrent（BFO 约束），但论文声称 Concept "historically (rigidly) depends" on EventChain-process
2. **形式化语义不完整**：δ(C) 和 γ(C) 的完整数学定义、算法、证明/证明概要不足
3. **前置条件语言未完整指定**：缺少完整语法、操作符集和组合语义
4. **Fork/Confluence 语义过于简单**：LWW 策略缺乏正式分析
5. **撤销语义模糊**：置信度阈值如何影响 HoldsAt 未明确
6. **实验缺少基线比较**：缺少与 nanopublications+Trusty URIs 和 Git-signed 的控制研究
7. **认证路线图不明确**：DID/VC 迁移路径不清晰

---

## 修改计划（按优先级排序）

### P0: 解决本体论矛盾（最高优先级）
**评审意见**：论文声称 Concept 是 GDC，且 GDC 不能依赖于 occurrent（BFO 约束 D5），但论文又说 Concept "historically (rigidly) depends" on EventChain-process。

**修改方案**：
1. **在 §3.2.3（Two-Level Account）中澄清**：
   - Concept 的 GDC 依赖 **仅** 针对 EventChain-record（ICE），**绝不** 针对 EventChain-process（occurrent）
   - 明确声明：D5（No cross-level identity）禁止 GDC 依赖 occurrent，这一约束被严格遵守
2. **重新定义 "historical dependence"**：
   - 将 "historical dependence" 重新框定为 **非本体论的因果/谱系叙述**（causal/genealogical narrative），而非 Fine/GDC 意义上的存在依赖（existential dependence）
   - 表述改为："A concept causally originates from the EventChain-process that generated it, but ontologically depends only on the EventChain-record (ICE)."
   - 添加脚注区分：causal origin（发生学）vs. ontological dependence（存在论）
3. **在 §3.2.5（Ontological Dependence）中修正**：
   - D1（Historical dependence）改为："The Concept's **existence** depends on the EventChain-record (ICE), not on the EventChain-process."
   - 添加 D1a："The Concept's **genesis** (causal origin) is traceable to the EventChain-process, but this is a historical/genealogical fact, not an ontological dependence relation."
4. **在 §3.2.4（Comparison with Foundational Ontologies）中**：
   - 明确讨论这一偏差："Deviation 4: Historical vs. ontological dependence. We distinguish the causal origin of a concept (its genesis event) from its ontological bearer (the ICE record). This avoids the category mistake of making a GDC depend on an occurrent."

**验证方式**：检查 §3 中所有 "depend" 用词，确保没有 GDC→occurrent 的依赖声明。

---

### P1: 完整形式化 δ(C) 和 γ(C)
**评审意见**：缺少完整形式定义、精确算法和证明。

**修改方案**：
1. **在 §4.3（Formal Derivation Semantics）中提供完整定义**：
   - δ(C)：已提供，但需要更精确：明确 C_life 的定义、last(C_life) 的提取规则、空链的处理
   - γ(C)：提供 **三种变体** 的完整公式：
     - γ_default(C)：O(1) last-VALIDATE 策略（当前实现）
     - γ_agg(C)：bonus-formula aggregate（Appendix E 中的完整公式，需移到正文）
     - γ_cal(C)：calibrated confidence（加权平均公式）
2. **提供完整的状态转换矩阵**：
   - 5 状态 × 5 事件类型 = 25 个转换的完整表格
   - 标注哪些转换被前置条件禁止
3. **为 Theorem 1-6 提供完整的 Proof Sketches**：
   - Appendix E 已压缩，但评审要求更完整的证明
   - 在 §4.3 中为每个定理提供 1-2 段的核心证明思路（Proof Sketch），将完整细节保留在 Appendix E
   - 确保 Theorem 4-7 的正文证明概要足够让读者理解核心逻辑
4. **明确冲突解决策略**：
   - 在 δ(C) 定义中添加："When multiple lifecycle events exist, the **most recent** event (by timestamp, tie-broken by event_id lexicographic order) determines the status."
   - 在 γ(C) 定义中添加："When multiple VALIDATE events exist, the most recent one prevails. For per-actor aggregation, we take the maximum confidence per actor."

---

### P2: 前置条件语言完整语法
**评审意见**：需要完整的语法、操作符集和组合语义。

**修改方案**：
1. **在 §4.2.1（Formal Precondition Language）中添加完整 BNF**：
   ```
   rule ::= "<" field "," comparator "," value ">"
   field ::= identifier
   comparator ::= EQ | NEQ | GT | GTE | LT | LTE | IN | EXISTS
   value ::= scalar | set
   rule_list ::= rule | rule_list "AND" rule_list
   ```
2. **提供组合语义**：
   - 规则列表是合取（AND）关系
   - 短路求值：第一个失败的规则终止评估
   - 添加："The precondition language is a **variable-free ground fragment** with no quantification, no recursion, and no dynamic evaluation."
3. **在 Table 4（Comparator Semantics）中扩展**：
   - 为每个操作符提供示例规则
   - 添加 "支持的类型" 列（string, number, boolean, set）
4. **在 §4.2.2（Expressivity and Limitations）中提供完整生命周期守卫表**：
   - 列出所有 9 个注册动作的前置条件规则
   - 展示哪些转换被守卫，哪些超出表达能力
5. **在 Appendix 中提供完整的前置条件语法附录**（如果正文空间不足）

---

### P3: Fork/Confluence 语义
**评审意见**：LWW 过于简单，需要正式分析。

**修改方案**：
1. **在 §4.3 中提供正式定义**：
   - 定义全序关系 ≺：timestamp 主键，event_id 平局决胜
   - 明确假设：时间戳单调不减（每个 agent 的本地时钟单调）
   - 平局决胜：UUID 字典序比较提供确定性的全序
2. **在 §4.3 中分析并发冲突**：
   - 情况 1：VALIDATE + VALIDATE（同一 concept，不同 agents）→ 后者 wins，γ 更新
   - 情况 2：VALIDATE + DEPRECATE（同一 concept）→ 后者 wins，状态翻转
   - 情况 3：FORK + VALIDATE（父 concept）→ 两个事件都保留，但分叉后父链和新子链独立
3. **在 §4.5（CRDT Merge）中扩展**：
   - 明确说明："The default EventChain is strictly ordered; fork resolution uses last-write-wins. This is deterministic but brittle in distributed settings."
   - 讨论 LWW 的局限性：时间戳操纵、语义意图丢失
4. **在 §6 Limitations 中强化 L12**：
   - "L12. Brittle fork resolution: LWW with timestamp tie-breaking is deterministic but may not reflect semantic intent. CRDT-style convergence with semantic merge policies is planned for Phase 3."

---

### P4: 撤销语义
**评审意见**：置信度阈值如何影响 HoldsAt？

**修改方案**：
1. **在 §3.2.4（Relation as Relator）中澄清**：
   - 明确声明：HoldsAt(Relation(c1, c2, p), t) **不检查置信度**，只检查 Revoked 状态
   - 置信度是 **epistemic strength**（认知强度），不是 **existence condition**（存在条件）
   - 添加："A relation with confidence=0.0 is still a valid ICE; it exists as a record but carries zero epistemic weight."
2. **修改公式 (4) 和 (5)**：
   - 公式 (4) HoldsAt：保持当前定义，明确不依赖置信度
   - 公式 (5) Revoked：保持当前定义，使用 confidence=0.0 或 revoked=true
3. **添加对比讨论**：
   - 在 §3.2.4 的 "Note on revocation semantics" 中扩展：
     - 对比方案 A（epistemic weakening，当前方案）：保留完整审计，允许分级撤销
     - 对比方案 B（dedicated REVOKE 事件）：更清晰的 cessation 语义，但引入新事件类型
     - 声明：引入 REVOKE 事件不会影响已证明的性质（Theorems 1-6），因为 REVOKE 只是另一个通信事件，不触发生命周期转换
4. **在 §6 Limitations 中保留**：
   - "L6. Unstructured agent communication" 中的相关讨论

---

### P5: 实验基线比较
**评审意见**：需要与 nanopublications+Trusty URIs 和 Git-signed 的控制研究。

**修改方案**：
1. **扩展 E19 实验（§5.5）**：
   - 添加新的比较维度：
     - 创作摩擦（Authoring friction）：每个系统完成 4 个任务所需的 LOC、文档页数
     - 审计完整性（Audit completeness）：事件覆盖率、可追溯性
     - 冲突解决结果（Conflict resolution）：fork/merge 的语义清晰度
   - 与 Git-signed 工作流比较：Git + CI pipeline + YAML 状态机
2. **在 §5.5 中添加定性分析**：
   - 为什么 nanopublications 不适合生命周期治理：静态断言，无状态机
   - 为什么 PROV-O 不适合：缺少前置条件和状态转换
   - 为什么 Git-only 不适合：版本控制 ≠ 生命周期治理
3. **在 §5.5 中添加表格**：
   - 扩展 Table 8（E19 benchmark）或添加新表格
   - 列：任务类型、ADL Lite LOC、Nanopub LOC、PROV-O LOC、Git LOC
4. **如果篇幅不足**：
   - 将详细基线比较移至 Appendix F（RDF-star 附录已注释，可替换为 Baseline Comparison）
   - 在正文保留高层总结

---

### P6: 认证路线图
**评审意见**：需要更清晰的 DID/VC 迁移路径。

**修改方案**：
1. **在 §4.4.3（Minimal DID integration）中扩展**：
   - 明确说明当前实现：did:key 解析、Ed25519 签名、verify_signature()
   - 说明这是 **Phase 1.5** 的预实现，不是完整认证
2. **在 §6 Limitations 中强化 L4**：
   - "L4. Cryptographic authentication gap: The current implementation relies on self-declared string identifiers. Minimal did:key support is implemented (§4.4.3), but full W3C LD-Proofs + DIDs remain future work."
3. **在 §7（Conclusion）或 Roadmap 中提供清晰的三阶段路线图**：
   - Phase 1（当前）：协作审计模型，字符串标识符，哈希链完整性
   - Phase 1.5（已实现但未评估）：did:key 解析，Ed25519 签名，Git 提交签名绑定
   - Phase 2（计划）：完整 DID 注册表（did:web, did:ethr），关键轮换/撤销
   - Phase 3（未来）：BFT 传输层，CRDT 合并，Ontological Assertion Market（质押/惩罚）
4. **讨论认证如何改变形式化属性**：
   - 在 §4.4.3 或 §6 中："Authenticated identities would change the threat model: Sybil attacks (L3a) become impossible, and collusion cost rises to economic stakes (FW9)."

---

### P7: 其他修改（次要）

1. **表格格式**：检查所有表格的列宽和对齐，确保 PDF 中不溢出
2. **引用完整性**：确保所有引用的论文有完整元数据（作者、年份、标题）
3. **Abstract 微调**：如果修改了本体论声明，需要同步更新 Abstract 中的相关表述
4. **L3a 复杂共谋策略**：评审提到 staged injection、Sybil attack、coordinated confidence inflation，已在 §6 Limitations 中覆盖，但需要确保与 P0 的修改一致

---

## 修改优先级矩阵

| 优先级 | 修改项 | 影响章节 | 预计工作量 |
|--------|--------|----------|------------|
| P0 | 解决本体论矛盾 | §3.2.3, §3.2.5, §3.4 | 中等 |
| P1 | 完整形式化 δ/γ | §4.3, Appendix E | 中等 |
| P2 | 前置条件语言完整语法 | §4.2.1, §4.2.2, 新附录 | 中等 |
| P3 | Fork/Confluence 正式语义 | §4.3, §4.5, §6 L12 | 小 |
| P4 | 撤销语义澄清 | §3.2.4, §6 | 小 |
| P5 | 实验基线比较 | §5.5, Appendix F | 中等 |
| P6 | 认证路线图 | §4.4.3, §6 L4, §7 | 小 |
| P7 | 表格/引用/摘要 | 全文 | 小 |

---

## 风险评估

- **P0 本体论矛盾**：如果修改不当，可能动摇 §3 的核心论证。建议：先修改 §3.2.3 的 Two-Level Account，确保 D1 和 D5 的表述一致，然后全文搜索 "depend" 确保没有混淆。
- **P1 形式化**：如果添加过多公式，可能增加页数。建议：将详细公式放在 Appendix E，正文保留核心定义和 Proof Sketch。
- **P5 基线比较**：新实验可能需要时间。建议：如果无法运行新实验，基于现有 E19 数据做定性分析，并声明 "controlled study is in progress as future work (FW13)"。

---

## 页数控制

当前论文 48 页。修改可能增加页数，但可以通过以下方式抵消：
- 将 P1 的详细公式移至 Appendix E（已压缩，有空间）
- 将 P2 的完整语法移至新附录或保留在正文简短形式
- 将 P5 的详细基线比较移至 Appendix F
- 目标：保持 50 页以内
