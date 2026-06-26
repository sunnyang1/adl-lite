# ADL Lite 论文改稿计划（v3.0）

> **编制日期**: 2026-06-14  
> **验证日期**: 2026-06-14  
> **编制依据**: Peer Review Report + arXiv/Scholar 学术数据库检索（2024-2026）  
> **目标会议**: ESWC 2027 / ISWC 2027（备选 AAMAS 2027，预估截稿 2026-10-16）  
> **预计周期**: 4-6 周（全职工作量）  
> **验证状态**: 核心竞争论文已用 arXiv ID 交叉验证；未验证条目已标注 [未验证]

---

## 一、学术数据库竞争格局分析（基于检索结果）

### 1.1 直接竞争工作（必须在 Related Work 中深度对比）

| 工作 | 年份 | 核心特征 | 对 ADL Lite 的挤压效应 | 改稿应对策略 |
|------|------|----------|----------------------|-------------|
| **Talukdar et al.** (arXiv:2604.23090) | 2026 | 多智能体LLM本体工程（Domain Expert→Manager→Coder→QA）； artifact-driven；保险领域OWL评估 | 论文声称"LLM-native 多智能体治理"但实验中无真实LLM参与，Talukdar等已展示真实LLM生成OWL本体的能力 | 增加维度对比表；承认Talukdar等在自动化OWL生成上的优势；将ADL Lite定位为"文档原生治理层"而非"全自动本体生成器" |
| **X-HCOME / SimX-HCOME+** (Neurosymbolic AI journal, 2024) | 2024 | LLM增强的HCOME方法论；人类-LLM交替协作；SimX-HCOME+模拟三种角色(KW/DE/KE) | 同Talukdar等，但强调人类监督下的半自动化 | 同上；特别区分ADL Lite的"协作审计"定位与X-HCOME的"半自动化生成"定位 |
| **Krishna et al.** | 2025 | 多智能体LLM知识图谱策展和查询；多模态数据源 | 展示了真实多智能体协作在KG领域的实际应用 | 增加对比：Krishna聚焦于KG curation，ADL Lite聚焦于概念生命周期治理；两者互补而非竞争 |
| **Atlas** (Spoczynski & Melara) | 2025 | ML生命周期溯源与透明度框架；tamper-evident audit trails；工作流管理和自动化 | 在"tamper-evident provenance"和"生命周期管理"上与ADL Lite目标重叠；Atlas有实际ML系统验证 | 增加对比：Atlas面向ML模型生命周期，ADL Lite面向概念本体生命周期；两者在tamper-evident机制上可对比但应用领域不同 |
| **CHEKG** (Angelis et al.) | 2024 | 协作混合知识图谱工程方法论；模块化+公平性；不同 expertise 参与者协作 | 在"协作本体工程"方法论上提供了一种替代路径 | 引用CHEKG作为"协作本体工程"方法论的对比基准；强调ADL Lite的轻量级部署优势（pip install vs. 需要协调多方参与者） |
| **Trustworthy KGs** (Zhang et al.) | 2025 | 讨论"LLM A和LLM B在triple约束上的冲突"；KG质量评估实践 | 直接触及ADL Lite的核心问题（多智能体冲突解决），但仅从质量评估角度 | 在§6.2中增加引用，讨论ADL Lite的冲突记录机制如何回应Zhang等人的冲突检测问题 |

### 1.2 技术路线竞争者（Phase 3 计划被挤压）

| 工作 | 年份 | 核心特征 | 对 ADL Lite 的挤压效应 | 改稿应对策略 |
|------|------|----------|----------------------|-------------|
| **Blocklace** (Almeida & Shapiro) | 2024 | 通用BFT-CRDT；加密哈希DAG；O(\|V\|+\|E\|)验证；等价检测 | Phase 3 DAG设计与之高度相似；Blocklace已发表，ADL Lite的DAG设计不再具有先发原创性 | 明确将Blocklace定位为"传输层基准"；将ADL Lite的Phase 3 DAG重新定义为"Blocklace DAG + ADL Lite δ/γ应用语义层" |
| **Boldachev 2025** [未验证] | 2025 | 因果DAG（事件为节点，happens-before为边）；反应式守卫；分布式并发无全局协调 | 表达力上优于ADL Lite线性链；论文§2.4已承认这一点 [注：该论文未通过arXiv/Google Scholar验证，需作者确认] | 表达力上优于ADL Lite线性链；论文§2.4已承认这一点 | 强化线性链的"审计优先"trade-off论证；增加定量对比：线性链在验证速度和完整性上优于因果DAG的复杂性 |
| **UFO-B Executable** (Guizzardi et al.) | 2024 | 可执行一阶逻辑公理化；社会关联者、倾向性、制度事件 | ADL Lite的L4 Action块与UFO-B"制度事件"高度对应，但UFO-B提供完整FOL公理化 | 在§3.2.6中增加明确对比：YAML前置条件 vs. FOL公化化的trade-off；为什么ADL Lite选择轻量级而非完整FOL |
| **Nieto et al.** | 2024 (POPL) | Iris分离逻辑中形式化验证CRDT | 论文的7个定理为非形式化证明，而Nieto已实现机器验证CRDT | 在FW10中明确引用Nieto作为形式化验证目标；在Limitations中承认这一差距 |

### 1.3 可借鉴的正面工作（可引用来支持ADL Lite的论点）

| 工作 | 年份 | 可借鉴点 | 在论文中的引用位置 |
|------|------|----------|-----------------|
| **Garcia-Fernandez et al.** | 2025 | 人类-LLM协作本体扩展过程的潜力；揭示LLM在OE中的机会和局限 | §2.3（LLM-Native OE）中引用，支持"LLM在OE中的角色正在演变，ADL Lite提供了一种轻量级介入机制" |
| **Rodriguez & Rossana** | 2025 | LLM多智能体系统+嵌入验证用于ADAS知识图谱构建 | §2.3中引用，支持"嵌入验证+多智能体协作是KG领域的新兴方向" |
| **Boscariol et al.** | 2025 | 知识工程中的LLM行为理解；KG可用性验证 | §5.5（E5 planned）中引用，支持"KG可用性验证需要人类专家评估" |
| **Pan et al.** | 2023 (ACM CSUR) | 数据溯源在安全与隐私中的全面综述（101 citations） | §2.2中引用，强化provenance领域的权威性综述 |
| **Tavakoli et al.** | 2024 (54 citations) | 区块链数字孪生数据溯源；本体数据结构用于资产信息模型 | §2.2中引用，支持"tamper-evident provenance + ontology-based data structure"是活跃研究方向 |
| **Kocadag et al.** | 2025 | 区块链溯源系统综述；EP-PLAN ontology扩展 | §2.2中引用，作为provenance ontology的对比基准 |

---

## 二、改稿总体策略

### 2.1 核心定位调整

**从**: "ADL Lite 是一个事件优先的操作本体，代表 LLM-native 本体工程中的第四路线，填补了现有系统的空白。"

**调整为**: "ADL Lite 是一个面向 LLM 多智能体协作的**轻量级事件优先概念治理框架**，其核心贡献在于：(1) 将确定性推导语义（δ/γ）与加密哈希链完整性集成到 Markdown-native 文档中；(2) 提供无需外部工作流引擎或 OWL 推理器的声明式生命周期前置条件执行。ADL Lite 不替代全自动本体生成器（如 Talukdar 等的多智能体 LLM 方法），而是为其提供**轻量级治理和审计层**。"

### 2.2 声称缩减清单

| 原文声称 | 问题 | 修改方式 |
|----------|------|----------|
| "to our knowledge, no existing system combines all four properties" | 过于绝对，易被反例攻击 | 改为"within the open-source, pip-installable, Markdown-native tool space, no existing system we are aware of simultaneously satisfies all four while maintaining operational coherence" |
| "fourth route" | Talukdar 等 (arXiv:2604.23090) 已展示多智能体 LLM 协作本体工程 | 改为"a complementary governance layer for LLM-native ontology workflows" |
| "the primary contribution is an ontological analysis" | 本体论分析是支撑，但实验不足使其显得空泛 | 改为"the primary contributions are: (1) the operationalization of event-first semantics into a deployable, cryptographically enhanced governance mechanism; (2) an ontological analysis that situates this mechanism within BFO/DOLCE/UFO; (3) empirical validation of architectural correctness on real-world data volume" |
| "Phase 3 will explore a Blocklace-style hash DAG" | Blocklace已发表，此声称削弱原创性 | 改为"Phase 3 will integrate the Blocklace hash DAG as the transport layer, with ADL Lite's δ/γ semantics as the application layer" |
| "seven proved properties" | 证明为非形式化，且Theorem 5实际上证明的是脆弱性 | 改为"seven formally specified properties with rigorous proof sketches; machine verification planned for future work" |

### 2.3 实验补强优先级

1. **P0（必须完成）**: E17 - LLM Agent 实际参与实验（截至2026-06-14，论文中E5仍为'Planned'，E17尚未出现）
2. **P1（强烈推荐）**: E18 - 共谋脆弱性形式化分析与缓解实验（将负面结果转化为安全分析贡献）
3. **P1（强烈推荐）**: E19 - 简化的 head-to-head 基准对比（ADL Lite vs. nanopub + scripts vs. PROV-O + scripts）
4. **P2（建议完成）**: E20 - 长度 > 3 的随机采样测试（E2 扩展）
5. **P2（建议完成）**: E21 - TLA+ 验证范围扩展到长度 100-1000
6. **P3（如有时间）**: E22 - 开发者体验问卷（n ≥ 5）

---

## 三、分阶段改稿执行计划

### Stage 1: 声称校准与 Related Work 重构（Week 1-2）

#### 任务 1.1: 重写 §1.2（Research Gap）
- **目标**: 精确定位研究问题，避免被最新文献反驳
- **修改文件**: `sections/01_introduction.tex`
- **具体修改**:
  - 将研究问题拆分为两个更精确的子问题（RQ1/RQ2，见评审报告）
  - 在 §1.2 中增加一段，明确承认 Talukdar 等 (arXiv:2604.23090) 和 X-HCOME 在 LLM 辅助本体工程方面的进展，并说明 ADL Lite 与之互补（ governance layer vs. generation engine）
  - 在 §1.2 中增加一段，说明 Blocklace 在 BFT-CRDT-DAG 上的进展，并明确 ADL Lite Phase 3 将以其为传输层基准
- **新增引用**: `talukdar2026multillm`, `xhcome2024`, `blocklace2024`
- **验证标准**: 评审者阅读 §1.2 后不会认为作者对 2024-2025 年进展无知

#### 任务 1.2: 重写 §2.3（LLM-Native Ontology Engineering）
- **目标**: 增加与 Talukdar 等 (arXiv:2604.23090) / X-HCOME / Garcia-Fernandez 的维度对比
- **修改文件**: `sections/02_related_work.tex`
- **具体修改**:
  - 将现有 LLM-native OE 子节扩展为至少 2 页
  - 增加 **Table: Dimension Comparison of LLM-Native OE Approaches**，维度包括：
    - 自动化程度（全自动 / 人机协作 / 辅助工具）
    - 输出格式（OWL / Markdown+RDF / 纯文本）
    - 治理机制（外部工作流 / 内置前置条件 / 无）
    - 溯源完整性（无 / 日志 / 加密链）
    - 部署成本（企业级 / 轻量级 / 零安装）
    - 真实LLM参与验证（是 / 否）
  - 在表格下方明确标注：ADL Lite 是"轻量级内置治理 + 加密溯源"这一特定区间的唯一选择，而非 LLM-native OE 的全局最优解
- **新增引用**: `talukdar2026multillm`, `xhcome2024`, `garijo2025llmoe`, `garcia2025llmoe`
- **验证标准**: 读者能够清晰理解各系统的 trade-off，而非认为 ADL Lite "更好"

#### 任务 1.3: 重写 §2.4（Event-Centric Ontologies）SEO 对比
- **目标**: 强化线性链 vs. 因果 DAG 的 trade-off 论证
- **修改文件**: `sections/02_related_work.tex`
- **具体修改**:
  - 在 §2.4.2 中增加一段定量分析：
    - 线性链验证复杂度：O(n)，但保证总顺序
    - 因果 DAG 验证复杂度：O(|V|+|E|)，但允许部分顺序
    - 对于概念生命周期治理（需要明确的 REGISTER → VALIDATE → DEPRECATE 顺序），总顺序的语义权重高于表达力增益
  - 引用 Boldachev 2025 [未验证] 的"reactive guards"，并明确区分：其 guards 是 reactive（响应式），ADL Lite 的 preconditions 是 proactive（预防式）
- **新增引用**: `boldachev2025seo` [需作者确认标题/venue]
- **验证标准**: 评审者不会认为 ADL Lite 选择线性链是出于技术限制而非设计意图

#### 任务 1.4: 修正引用错误
- **目标**: 修复已知的引用错误和占位符
- **修改文件**: `references.bib`, `sections/02_related_work.tex`
- **具体修改**:
  - 将 `ref6` 替换为 `glimm2014hermit` + `sirin2007pellet`
  - 将 `ref7` 替换为 `hogan2021knowledge`
  - 将 `ref8` 替换为 `guha2016schemaorg`，并修正文本中的"over 40%"为"over 30%"
  - 将 `ref14` 替换为 `dendron2020`
  - 将 `ref16` 替换为 `foam2020`
  - 将 `ref59` 的引用文本从"CRDTs for knowledge graph editing"改为"real-time collaborative ontology editing using distributed version control techniques"，并引用 `hemid2024ontoeditor`
  - 删除 references.bib 中所有"REPLACES"占位符注释
- **验证标准**: `grep -c "REPLACES" references.bib` 返回 0

#### 任务 1.5: 新增 Atlas 和 CHEKG 对比
- **目标**: 将 2024-2025 provenance 和协作 KG 工作纳入对比
- **修改文件**: `sections/02_related_work.tex`
- **具体修改**:
  - 在 §2.2（Provenance, Trust）中增加 Atlas (Spoczynski & Melara, 2025) 的对比：
    - Atlas 面向 ML 生命周期 provenance，tamper-evident audit trails
    - ADL Lite 面向概念本体生命周期，确定性推导 + 加密链
    - 两者在 tamper-evident 目标上一致，但应用领域不同
  - 在 §2.3 中增加 CHEKG (Angelis et al., 2024) 的对比：
    - CHEKG 是多方协作的混合方法论，需要协调不同 expertise 的参与者
    - ADL Lite 是自动化前置条件 + 加密链，降低了对协调基础设施的需求
- **新增引用**: `spoczynski2025atlas`, `angelis2024chekg`
- **验证标准**: 新增引用在文中至少被引用一次，且在 related work 表格中出现

---

### Stage 2: 本体论分析深化（Week 2）

#### 任务 2.1: 修正 EventChain 早期使用的模糊性
- **目标**: 在 abstract 和 §1.1 中消除 EventChain 的歧义
- **修改文件**: `sections/abstract.tex`, `sections/01_introduction.tex`
- **具体修改**:
  - 在 abstract 中："concepts are modeled as append-only, cryptographically linked **event histories** (EventChain-records)"
  - 在 §1.1 首次引入 EventChain 时："An EventChain is both a process (the ordered sequence of event occurrences) and a record (the serialized information content entity); we disambiguate these senses in Section 3.2.5"
- **验证标准**: 读者在读到 §3.2.5 之前不会困惑于 EventChain 的类别归属

#### 任务 2.2: 增加与 UFO-B Executable 的明确对比
- **目标**: 解释为什么 YAML 前置条件而非 FOL 公理化
- **修改文件**: `sections/03_ontological_analysis.tex`
- **具体修改**:
  - 在 §3.2.6（Action as Planned Process）之后增加一个小节 §3.2.7：
    - **Title**: "Lightweight Preconditions vs. Full First-Order Logic: A Design Trade-off"
    - **内容**: 
      - UFO-B Executable 提供完整 FOL 公理化，支持复杂推理但要求 OWL 推理器
      - ADL Lite 的 YAML 前置条件是可判定的 O(1) 片段，无需外部推理器
      - 对于概念生命周期治理（有限事件类型、有限状态空间），FOL 的表达能力是过剩的
      - 代价：YAML 前置条件无法表达跨事件的全局约束（如"一个概念在 24 小时内只能被验证一次"）
      - 收益：部署成本为零（pip install），推理延迟可忽略（0.08 ms）
  - 引用 `guizzardi2024ufob`
- **验证标准**: 评审者理解这不是能力缺失而是设计选择

#### 任务 2.3: 强化两层本体论分析的可引用性
- **目标**: 使 §3.2.5 成为论文的标志性贡献，便于被引用
- **修改文件**: `sections/03_ontological_analysis.tex`
- **具体修改**:
  - 在 §3.2.5 末尾增加一个 "Summary Box"（用 LaTeX 的 tcolorbox 或类似环境）：
    - 用 3-4 句话总结两层区分的核心洞察：
      - 概念（GDC）依赖事件链记录（ICE），而非事件本身（occurrent）
      - 这消除了"GDC 不能依赖 occurrent"的范畴错误
      - 身份条件：概念由 genesis hash 确定；记录由内容和顺序确定；过程由时间部分确定
  - 在 §3.2.5 的 Axiom I1-I4 和 D1-D5 中，增加一个表格汇总所有公理
- **验证标准**: 读者可以用 1 分钟时间通过 Summary Box 掌握两层分析的核心

---

### Stage 3: 形式化语义与安全分析补强（Week 2-3）

#### 任务 3.1: 形式化分析 γ(C) 的共谋脆弱性
- **目标**: 将 E14 的负面结果转化为形式化安全分析贡献
- **修改文件**: `sections/04_architecture.tex`（新小节 4.5.1）
- **具体修改**:
  - 新增 **Lemma 1 (Collusion Vulnerability Upper Bound)**:
    - 设 k 个共谋者每个报告 confidence = 1.0
    - 则 γ(C) = min(1.0, c_base + 0.05 × (N_vals - 1))，其中 N_vals = k
    - 当 k ≥ 10 时，γ(C) = 1.0；当 k = 1 时，若 c_base = 0.99，则 γ(C) = 0.99
    - 因此，**k ≥ 1 即可控制状态转换**，这是 Phase 1 的结构性缺陷
  - 新增 **Lemma 2 (Minimum Validator Threshold Mitigation)**:
    - 若加入阈值 N_min = 3（即 VALIDATE 前置条件要求 N_vals ≥ 3）
    - 则单个共谋者无法触发 validated 状态；需要 k ≥ 3 的共谋联盟
    - 证明： trivial，由前置条件机制直接保证
  - 在 §4.5（Trust Model）中增加一个 "Security Analysis" 子小节，将上述引理纳入
- **验证标准**: 评审者不再认为这是一个被忽视的 bug，而是一个被形式化分析的安全结果

#### 任务 3.2: 修正 Theorem 5 的表述
- **目标**: 使 Theorem 5 不暗示系统对共谋攻击的脆弱性
- **修改文件**: `sections/04_architecture.tex`
- **具体修改**:
  - 在 Theorem 5 的 statement 中增加一个前提条件：
    - "Let γ(C) = c and let e_new be a VALIDATE event from a **new, non-colluding actor** with e_new.p.confidence ≥ c_base..."
  - 在 Theorem 5 的 proof 之后增加一个 Remark：
    - "Remark: Theorem 5 assumes non-colluding actors. In Phase 1, collusion is not prevented; see Lemma 1 (Section 4.5.1) for the collusion upper bound."
- **验证标准**: Theorem 5 的 statement 不会误导读者认为系统对共谋有抵抗力

#### 任务 3.3: 扩展 TLA+ 验证范围
- **目标**: 将 TLC 模型检验从长度 ≤ 20 扩展到至少 100
- **修改文件**: `sections/04_architecture.tex`（§4.4 脚注），`appendix_e.tex`
- **具体修改**:
  - 在 §4.4 的脚注中更新：
    - "TLC model checking (v2.18) verifies safety and liveness for chains of length ≤ 100 over the closed alphabet Σ."
  - 在 appendix_e.tex 中报告状态空间爆炸边界：
    - 长度 20: 状态数 ≈ X，验证时间 Y 秒
    - 长度 50: 状态数 ≈ X'，验证时间 Y' 秒
    - 长度 100: 状态数 ≈ X''，验证时间 Y'' 秒
    - 长度 > 100: 状态空间爆炸，需使用归纳证明或 Coq 处理
- **验证标准**: TLA+ 报告包含长度 100 的验证结果，且明确标注了状态空间边界

---

### Stage 4: 实验补强（Week 3-5，最耗时阶段）

#### 任务 4.1: 实现 E17 - LLM Agent 实际参与实验（P0）
- **目标**: 用真实 LLM 智能体替代合成事件注入，验证"多智能体"声称
- **修改文件**: 新建 `experiments/e17_llm_agent_governance.py`，`sections/05_empirical_validation.tex`
- **具体修改**:
  - **实验设计**:
    - 使用 GPT-4o-mini（或 Claude 3.5 Sonnet）作为 actor，通过 ADL Lite 的 Python API 实际提出、验证、废弃 AML 概念
    - 设计 3 个 LLM 智能体角色：Discoverer（发现模式）、Skeptic（质疑模式）、Validator（验证模式）
    - 每个智能体接收相同的 AML 交易数据子集，但系统提示不同（角色定义）
    - 运行 10 轮迭代，每轮允许每个智能体对 10 个候选概念执行一次操作（REGISTER / VALIDATE / DEPRECATE / EVIDENCE）
    - 记录所有生成的 EventChain，计算：
      - 概念覆盖率（LLM 发现的模式 vs. 已知 AML 模式）
      - 冲突率（不同 LLM 对同一概念持相反意见的比例）
      - 链完整性（VerifyIntegrity 通过率）
      - 前置条件违反率（LLM 尝试无效操作的比例）
  - **人类专家对比**:
    - 如果可能，邀请 1-2 名 AML 专家对 LLM 生成的概念进行评分（语义连贯性 1-5）
    - 如果人类专家不可行，使用 LLM-as-a-judge：GPT-4o 作为专家代理，对另一个 LLM 生成的概念进行评分，并报告评分一致性
  - **论文中报告**:
    - 在 §5.5 中增加 E17 子节
    - 报告覆盖率、冲突率、完整性、前置条件违反率
    - 报告 LLM 专家评分的均值和标准差
    - 明确说明：这是初步 proof-of-concept，不是大规模领域验证
- **验证标准**: 至少有一个 LLM 智能体成功生成了至少 5 个带有完整 EventChain 的概念，且所有链通过 VerifyIntegrity

#### 任务 4.2: 实现 E18 - 共谋脆弱性缓解实验（P1）
- **目标**: 形式化分析 + 实验验证简单缓解措施
- **修改文件**: 新建 `experiments/e18_collusion_mitigation.py`，`sections/05_empirical_validation.tex`
- **具体修改**:
  - **实验设计**:
    - 重现 E14：k 个共谋者，每个 confidence = 0.99，测量最终 γ(C) 和状态转换
    - 测试 3 种缓解策略：
      - (a) 最小验证者阈值 N_min = 2
      - (b) 最小验证者阈值 N_min = 3
      - (c) 置信度聚合改为中位数而非均值（对异常值更鲁棒）
    - 对每种策略，测量：
      - 正常操作成功率（非共谋场景下 VALIDATE 是否正常工作）
      - 共谋攻击成功率（k 个共谋者能否突破）
      - 误报率（合法验证者被错误拒绝的比例）
  - **论文中报告**:
    - 在 §5.5 中将 E14 升级为 "E14: Collusion Vulnerability Analysis and Mitigation"
    - 报告 E14a（无缓解）和 E14b-d（有缓解）的对比结果
    - 用表格呈现：N_min = 1/2/3/中位数 下的攻击成功率
- **验证标准**: 至少有一种缓解策略（如 N_min = 3）能将 k=1 的攻击成功率降至 0%

#### 任务 4.3: 实现 E19 - Head-to-Head 基准对比（P1）
- **目标**: 在相同治理任务上对比 ADL Lite、nanopub + 脚本、PROV-O + 脚本
- **修改文件**: 新建 `experiments/e19_governance_benchmark.py`，`sections/05_empirical_validation.tex`
- **具体修改**:
  - **实验设计**:
    - 定义 4 个标准治理任务（与 §5.6 相同）：
      - T1: Acceptance workflow（概念被 k 个验证者接受）
      - T2: Retraction workflow（已接受概念被废弃）
      - T3: Audit query（查询概念在某时刻的状态和验证者）
      - T4: Consensus threshold check（判断是否达到置信度阈值）
    - 对每种系统实现最小 viable 版本：
      - ADL Lite: 使用现有代码库
      - Nanopub + scripts: 用 Python 脚本实现 nanopub 的创建、验证、查询，使用 Trusty URIs
      - PROV-O + scripts: 用 Python + rdflib 实现 PROV-O activity 的创建、查询
    - 测量指标：
      - 开发者实现时间（代码行数、开发小时数）
      - 任务执行延迟（端到端，毫秒）
      - 错误率（实现过程中引入的 bugs 数量）
      - 任务完成正确率（是否按预期完成治理流程）
    - 由至少 2 名开发者（包括作者）独立实现，减少个人偏差
  - **论文中报告**:
    - 在 §5.6 中替换现有的 "methodological comparison" 为 "empirical comparison"
    - 报告表格：系统 × 任务 × 指标
    - 明确说明：nanopub 和 PROV-O 的实现在功能上不完整（无内置状态推导），但这是最接近的对比基准
- **验证标准**: 至少完成 3 个系统 × 4 个任务中的 12 个实验点，且 ADL Lite 在"开发者时间"和"任务正确率"上显著优于基线

#### 任务 4.4: E2 扩展 - 长度 > 3 的随机采样测试（P2）
- **目标**: 补充 E2 的 exhaustive coverage 缺口
- **修改文件**: 新建 `experiments/e2_extended_random.py`，`sections/05_empirical_validation.tex`
- **具体修改**:
  - 生成 10,000 条长度 4-10 的随机事件序列，覆盖生命周期事件类型
  - 对每条序列计算 δ(C)，并与 brute-force 模拟结果对比
  - 报告准确率、错误序列分布、错误模式
  - 在 §5.2 中增加："E2b: Randomized sampling for length > 3 confirms 10,000/10,000 correct"
- **验证标准**: 随机采样测试完成，且结果写入论文

#### 任务 4.5: 实验失败案例分析（P2）
- **目标**: 提高实验可信度，展示真实开发过程
- **修改文件**: `sections/05_empirical_validation.tex`
- **具体修改**:
  - 在 §5.7（Summary of Results）中增加一个 "Failure Case Analysis" 子小节
  - 报告至少 3 个开发过程中遇到的真实失败案例：
    - 案例 1: 早期 δ(C) 实现未正确处理空链，导致空链返回 "validated"（错误原因：未检查 C_life = []）
    - 案例 2: 早期 VerifyIntegrity 未检查 event_id 唯一性，导致重放攻击通过（错误原因：遗漏 well-formedness axiom 5）
    - 案例 3: Pydantic payload 验证捕获了 NaN 但遗漏了空字符串 actor，导致空 actor 被接受（错误原因：前置条件层未独立验证 actor 非空）
  - 对每个案例：描述症状、根因、修复方法、预防措施
- **验证标准**: 案例真实、详细、有教育意义，不是虚构的

---

### Stage 5: 讨论与写作精简（Week 4-5）

#### 任务 5.1: 压缩 Future Work
- **目标**: 将 §7.2 从 ~2 页压缩到 1 页
- **修改文件**: `sections/07_conclusion.tex`
- **具体修改**:
  - 从 12 个 FW 项中保留最核心的 5 个：
    - FW1: OWL 2 DL 公理化与 OBO Foundry 对齐（本体论基础）
    - FW3: MARGIN 置信度校准（解决 L3 安全漏洞）
    - FW4: Ed25519 + DIDs + Blocklace DAG 集成（认证与扩展）
    - FW5: 人类专家领域评估（E5 的延续）
    - FW10: TLA+/Coq 机器验证（形式化严谨性）
  - 其余 7 个 FW 项移至 GitHub 技术报告或补充材料
- **验证标准**: §7.2 在 PDF 中不超过 1 页（约 600 词）

#### 任务 5.2: 压缩非核心附录
- **目标**: 减少论文篇幅，聚焦核心贡献
- **修改文件**: `main.tex`, `sections/appendix_d.tex`, `sections/appendix_e.tex`, `sections/appendix_f.tex`
- **具体修改**:
  - 将 Appendix D（Experiment Runner）移至 GitHub 仓库的补充材料，论文中仅保留引用
  - 将 Appendix E（Proof Sketches）保留，但压缩到仅包含 Theorem 1-3 的详细证明，Theorem 4-7 的详细证明移至补充材料
  - 将 Appendix F（RDF-star Interoperability）保留，但压缩到 1 页
  - 目标：论文总页数从目前的 ~30 页（含附录）压缩到 ~22 页（含附录）
- **验证标准**: 论文在 15 页正文 + 7 页附录的目标范围内

#### 任务 5.3: 回应评审者问题的精炼
- **目标**: 使 §6.2 更紧凑，避免重复正文内容
- **修改文件**: `sections/06_discussion.tex`
- **具体修改**:
  - 将 Q1-Q8 的回应从目前的段落式改为表格 + 简短段落
  - 表格列：Question | Section Addressed | Status (Fully / Partially / Scoped to Future) | Key Modification
  - 每个问题下方保留 2-3 句话的总结，而非目前的段落
- **验证标准**: §6.2 在 PDF 中不超过 1.5 页

#### 任务 5.4: 修正术语一致性
- **目标**: 消除 EventChain 的早期歧义使用
- **修改文件**: `sections/abstract.tex`, `sections/01_introduction.tex`, `sections/03_ontological_analysis.tex`
- **具体修改**:
  - 在 abstract 中：使用 "event histories" 替代 "EventChains"，或明确标注 "EventChain-records"
  - 在 §1.1 中：第一次出现 EventChain 时加脚注说明两层含义
  - 在 §3.2.5 中：确保所有 EventChain 的使用都加了 "-process" 或 "-record" 后缀
- **验证标准**: `grep -n "EventChain" sections/*.tex | grep -v "EventChain-process\|EventChain-record\|EventChain_"` 在 §3.2.5 之前返回 0 个结果（或仅有 1 次首次引入）

---

### Stage 6: 新增实验的可选增强（Week 5-6，时间允许）

#### 任务 6.1: E20 - 开发者体验问卷（P3）
- **目标**: 提供主观可用性数据
- **设计**:
  - 招募 n ≥ 5 名有 Python 经验的开发者
  - 任务：使用 ADL Lite 和 PROV-O + rdflib 分别实现一个概念治理工作流
  - 问卷：SUS（System Usability Scale）+ NASA-TLX（工作负荷）+ 开放式反馈
  - 报告：SUS 评分、TLX 各维度评分、定性反馈主题
- **论文位置**: §5.6 末尾或 §6.3（Conceptual Modeling Contribution）中

#### 任务 6.2: E21 - LLM-as-a-Judge 评估（P3）
- **目标**: 如果 E5 人类专家不可行，提供替代方案
- **设计**:
  - 使用 GPT-4o 作为专家代理，对 LLM 生成的 AML 概念进行评分
  - 评分维度：semantic coherence, evidential sufficiency, audit completeness（与 E5 计划一致）
  - 同时让人类评分员对 20 个样本进行评分，计算 Pearson r 或 Spearman ρ
  - 如果 LLM 评分与人类评分相关性高（r > 0.7），则 LLM-as-a-Judge 可作为专家评估的代理
- **论文位置**: §5.5 的 E5 子节中，作为 "pilot study using LLM-as-a-judge"

---

## 四、文件修改清单

| 文件路径 | 修改类型 | 修改内容 | 优先级 |
|----------|----------|----------|--------|
| `sections/abstract.tex` | 重写 | 消除 EventChain 歧义；调整核心声称 | P1 |
| `sections/01_introduction.tex` | 重写 | RQ 拆分；承认 Talukdar 等 / X-HCOME；定位互补性 | P0 |
| `sections/02_related_work.tex` | 重写 | 增加 LLM-native OE 维度对比表；SEO trade-off 论证；Atlas/CHEKG 对比 | P0 |
| `sections/03_ontological_analysis.tex` | 深化 | Summary Box；UFO-B 对比；YAML vs FOL trade-off | P1 |
| `sections/04_architecture.tex` | 新增 | Lemma 1-2（共谋分析）；修正 Theorem 5；扩展 TLA+ 范围 | P0 |
| `sections/05_empirical_validation.tex` | 重写 | E17（LLM Agent）；E18（共谋缓解）；E19（head-to-head）；E2b（随机采样）；失败案例 | P0 |
| `sections/06_discussion.tex` | 精简 | 压缩 FW；Q1-Q8 表格化；压缩篇幅 | P1 |
| `sections/07_conclusion.tex` | 精简 | 压缩 FW 到 5 项；调整结论表述 | P1 |
| `references.bib` | 修正 | 修复所有占位符引用；新增 10+ 条 2024-2025 文献 | P0 |
| `main.tex` | 调整 | 压缩附录引用；调整篇幅 | P2 |
| `appendix_a.tex` | 保留 | 修正引用，保持完整 Turtle 示例 | P2 |
| `appendix_b.tex` | 保留 | 保持 SHACL 示例 | P2 |
| `appendix_c.tex` | 保留 | 保持对抗性测试 | P2 |
| `appendix_d.tex` | 移除 | 移至补充材料 | P3 |
| `appendix_e.tex` | 压缩 | 保留 Theorem 1-3 详细证明，其余移至补充材料 | P3 |
| `appendix_f.tex` | 压缩 | 压缩到 1 页 | P3 |
| `experiments/e17_llm_agent_governance.py` | 新建 | LLM Agent 实验实现 | P0 |
| `experiments/e18_collusion_mitigation.py` | 新建 | 共谋缓解实验实现 | P1 |
| `experiments/e19_governance_benchmark.py` | 新建 | Head-to-head 基准实现 | P1 |
| `experiments/e2_extended_random.py` | 新建 | E2 随机扩展测试 | P2 |

---

## 五、新增引用文献清单

| 引用键 | 作者 | 年份 | 标题 | 在论文中的引用位置 | 优先级 |
|--------|------|------|------|-------------------|--------|
| `spoczynski2025atlas` | Spoczynski, Melara et al. | 2025 | Atlas: A framework for ML lifecycle provenance & transparency | §2.2 Provenance | P0 |
| `angelis2024chekg` | Angelis, Moraitou et al. | 2024 | CHEKG: Collaborative and Hybrid Engineering of Knowledge Graphs | §2.3 Collaborative OE | P0 |
| `zhang2025trustworthykg` | Zhang, Koutsiana et al. | 2025 | Trustworthy knowledge graphs: Practices and approaches | §6.2 Q8 / §6.3 | P1 |
| `krishna2025collaborative` | Krishna, Malhotra, Shinde | 2025 | A collaborative Multi-Agent LLM Approach for KG Curation | §2.3 LLM-Native OE | P0 |
| `rodriguez2025adas` | Rodriguez, Rossana | 2025 | From Text to Trust: LLM Multi-Agent System for ADAS KG Construction | §2.3 LLM-Native OE | P1 |
| `boscariol2025kgllm` | Boscariol, Meschini, Tagliabue | 2025 | Knowledge engineering with LLMs for asset information management | §5.5 E5 | P2 |
| `pan2023provenance` | Pan, Stakhanova, Ray | 2023 | Data provenance in security and privacy (ACM CSUR) | §2.2 Provenance | P1 |
| `tavakoli2024blockchain` | Tavakoli, Yitmen et al. | 2024 | Blockchain-based digital twin data provenance | §2.2 Provenance | P2 |
| `kocadag2025trusted` | Kocadag, Pohl, Schreiber | 2025 | Trusted Provenance with Blockchain Technology (SLR) | §2.2 Provenance | P2 |
| `saxena2025blockchain` | Saxena | 2025 | Blockchain as a Governance Layer for AGI Ethics | §2.2 Governance | P3 |
| `kadel2025hdl` | Kadel | 2025 | HDL: Hybrid Decentralized Orchestration Layer for Ethical AI | §2.2 Governance | P3 |
| `tsai2025safeai` | Tsai, Zhang | 2025 | A Framework for Safe AI: Data Governance and Ecosystem Structure | §2.2 Governance | P3 |

---

## 六、质量验证清单（改稿完成后自检）

### 学术诚实性
- [ ] 所有声称均能在文中找到证据支持，无过度解读
- [ ] 所有负面结果（E14, E15, E16）被诚实报告，未被隐藏
- [ ] 所有"planned"未来工作被明确标注，未被伪装为已完成
- [ ] 所有引用文献均已被阅读或至少摘要阅读，非盲目堆砌

### 文献覆盖度
- [ ] 2024-2026 年 LLM-native OE 工作至少被引用 5 篇（Talukdar et al. arXiv:2604.23090, X-HCOME, Krishna, Garcia-Fernandez, Rodriguez）
- [ ] 2024-2025 年 CRDT/协作工作至少被引用 3 篇（Blocklace, SEO, CHEKG）
- [ ] 2024-2025 年 Provenance/溯源工作至少被引用 3 篇（Atlas, Pan, Tavakoli）
- [ ] 引用错误已全部修复（references.bib 中无 REPLACES 注释）

### 实验完整性
- [ ] 至少有一个实验涉及真实 LLM 智能体（E17）或人类专家（E5 pilot）
- [ ] 共谋脆弱性分析被形式化（Lemma 1）并测试缓解措施（E18）
- [ ] Head-to-head 基准至少完成 3 系统 × 4 任务中的 8 个实验点
- [ ] 失败案例至少报告 3 个，包含症状、根因、修复

### 形式化严谨性
- [ ] Theorem 5 已修正 collusion 前提
- [ ] TLA+ 已验证长度 ≤ 100
- [ ] 前置条件语言的可判定性有明确证明（Proposition）
- [ ] 两层本体论分析的公理（I1-I4, D1-D5）有完整表格汇总

### 篇幅控制
- [ ] 正文 ≤ 15 页（不含参考文献）
- [ ] 总页数（含附录）≤ 22 页
- [ ] Future Work ≤ 1 页
- [ ] Reviewer Questions 回应 ≤ 1.5 页

### 语言与格式
- [ ] EventChain 早期使用无歧义（abstract + §1.1）
- [ ] "operational ontology" 定义 ≤ 50 词，区分注释移至脚注
- [ ] 所有图表有清晰标题和正文引用
- [ ] 参考文献格式符合目标会议要求

---

## 七、风险与备选方案

| 风险 | 影响 | 备选方案 |
|------|------|----------|
| E17（LLM Agent）实验无法在 2 周内完成 | 严重：P0 任务缺失 | 方案 A：简化 E17 为"单 LLM actor 生成 5 个概念"的 pilot；方案 B：用 E21（LLM-as-a-judge）替代 |
| E19（head-to-head）开发者不可招募 | 中等：P1 任务缺失 | 方案 A：仅由作者完成所有实现，报告个人时间；方案 B：仅比较代码行数，不测量时间 |
| E18（共谋缓解）测试 N_min 后发现问题更复杂 | 中等：可能需要重新设计 γ(C) | 方案 A：仅报告 N_min 的初步效果，不声称解决；方案 B：将 γ(C) 的重新设计作为 Future Work（FW3 的一部分） |
| TLA+ 长度 100 验证状态空间爆炸 | 低：TLA+ 只是补充 | 方案 A：报告长度 50 的验证结果；方案 B：用归纳证明替代模型检验 |
| 论文篇幅压缩后丢失重要内容 | 中等：贡献被削弱 | 方案 A：将压缩内容移至 arXiv 技术报告，论文中引用；方案 B：申请目标会议的 long paper track（如果允许） |

---

> **计划总结**: 本改稿计划以"缩小声称、增加真实验证、深化对比、强化安全分析"为核心策略，分 6 个阶段在 4-6 周内完成。最关键的 P0 任务是：（1）§1.2 声称校准 + §2.3 相关文献对比重构；（2）§4.5 共谋脆弱性形式化分析；（3）E17 或 E5 pilot 实验。这三项任务直接回应评审报告中的 Major 问题，是论文能否通过 ESWC/ISWC 审稿的决定性因素。
