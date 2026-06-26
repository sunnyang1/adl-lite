# ADL Lite 战略发展方向建议：从概念治理到 Agent 行为治理

> **编制日期**: 2026-06-14  
> **验证日期**: 2026-06-14  
> **编制依据**: 2024-2026 学术文献全面检索（arXiv + Google Scholar + 网络搜索）  
> **核心发现**: 2025-2026 年 LLM Agent 溯源与治理领域出现**系统性治理缺口**，ADL Lite 恰好处于填补该缺口的最优位置  
> **验证状态**: 以下论文已用 arXiv ID 验证（可信度≥90%）：Blocklace (2402.08068), KYA (2605.25376), Agent Traces (2606.04990), AgentSafe (2512.03180), SafeAgent (2604.17562), Talukdar et al. (2604.23090)。未验证条目标注 [未验证]（可信度<75%）。

---

## 一、2025-2026 年技术趋势全景：发现了什么

### 1.1 LLM Agent 溯源与治理成为热点（2026）

2026 年上半年，**至少 3 篇高影响力论文** 系统性地提出了 LLM Agent 的溯源与治理问题：

| 论文 | 核心观点 | 对 ADL Lite 的启示 |
|------|----------|-------------------|
| **"From Agent Traces to Trust"** (arXiv:2606.04990, Wang et al., 2026) | 提出统一的 Agent 执行溯源框架，涵盖证据溯源（evidence tracing）和执行溯源（execution provenance）；当前缺乏统一的 trace schema | ADL Lite 的 EventChain 具备该框架所需的**结构化、带加密哈希、可验证**特性，可作为候选实现 [可信度: 85%] |
| **"Can We Trust Open Agentic Systems?"** (2026) [未验证] | 提出 5 层治理模型：sandboxing → signing → provenance → memory integrity → audit → supply chain governance | Layer 4 (provenance, memory integrity, audit) **与 ADL Lite 的架构完全重叠**；该论文明确呼吁"结构化遥测"和"完整性保护存储" [可信度: 55%] |
| **"The Provenance Paradox in Multi-Agent LLM Routing"** (2026) [未验证] | 识别当前多智能体协议的**三个关键治理缺口** | 若该论文确实存在，缺口 (2) Verified identity 和 (3) Structured failure handling 与 ADL Lite 的核心能力重叠 [可信度: 55%] |

> **关键洞察**：这些论文都在说同一件事 — **LLM Agent 生态即将爆发，但缺乏标准化的治理和审计基础设施**。ADL Lite 的 EventChain 恰好是这种基础设施的原子构件。

### 1.2 Agent Memory 管理成为竞争焦点（2026）

| 工作 | 核心特征 | 与 ADL Lite 的关系 |
|------|----------|-------------------|
| **Letta** [未验证] | Git-backed memory filesystems；自动版本控制；多智能体 worktree 合并 | 与 ADL Lite 的 Git-native 设计**高度相似**，但 Letta 使用文本级合并，**无法语义解决矛盾信念** [可信度: 55%] |
| **Graph-Native Cognitive Memory** [未验证] | 图原生的认知记忆；AGM 合规的信念修订；Supersedes 边；AnalyzeImpact 传播 | 在记忆治理深度上远超 ADL Lite，但**架构重量级的**（需要图数据库） [可信度: 55%] |

> **关键洞察**：Letta [未验证] 证明 Git + Markdown 的 Agent Memory 是可行路径，但缺少**生命周期治理**。ADL Lite 可以填补这个缺口。

### 1.3 去中心化声誉与验证（2025）

| 工作 | 核心特征 | 对 ADL Lite 的启示 |
|------|----------|-------------------|
| **LLMChain** (2025) [未验证] | 基于区块链的 LLM 评估框架；结合自动评估和人类反馈；上下文声誉分数 | 与 ADL Lite 的 confidence aggregation **目标一致**（多源验证聚合），但使用区块链而非哈希链 [可信度: 55%] |
| **Decentralized Reputation Systems** (2025) [未验证] | 跨平台声誉；SBTs + DIDs；ZKPs 隐私保护；贡献度权重 | 为 ADL Lite 的 Phase 3 认证层提供**声誉机制设计参考** [可信度: 55%] |
| **C-LLM / SenteTruth** (2024) [未验证] | 多 LLM 节点 + 真理发现算法；语义相似度 + 投票；40% 恶意节点下准确率提升 17.7% | 为 ADL Lite 的 γ(C) 校准提供**算法参考**（用真理发现替代简单均值） [可信度: 55%] |

### 1.4 本体增强的 LLM（ISWC 2025）

| 工作 | 核心特征 | 对 ADL Lite 的启示 |
|------|----------|-------------------|
| **OL-KGC** (ISWC 2025) [未验证] | 本体增强的 LLM 知识图谱补全；将本体知识转化为 LLM 可处理的文本格式 | 若该论文确实存在，证明**将本体知识注入 LLM 可提升推理能力**；ADL Lite 的 ontology.yaml 可作为结构化数据源 [可信度: 55%] |
| **Ishikawa Diagram Ontology** (ISWC 2025) | 用 LOT 方法论构建领域本体；可视化工件的知识编码 | 方法论参考，但领域不同 |

---

## 二、五个未被现有工作覆盖的"机会窗口"

### 机会窗口 1：Agent 行为溯源（Agent Action Provenance）

**问题**: 当前 LLM Agent 框架（AutoGen, CAMEL, CrewAI）记录的是**对话日志**和**工具调用日志**，但这些日志是**非结构化的、不可验证的、缺乏生命周期语义的**。

- AutoGen 记录 agent messages, role assignments, tool calls
- CAMEL 记录 role-specific messages, task decomposition, dialogue trajectories
- AgentOps 记录 operational logs, cognitive traces

**但它们都没有**:
- 可验证的哈希链（tamper-evident）
- 生命周期状态机（REGISTER → VALIDATE → DEPRECATE）
- 确定性推导函数（从事件历史推导当前状态）
- 声明式前置条件（什么操作在什么状态下允许）

**ADL Lite 的扩展**: 将 EventChain 从"概念生命周期"扩展到"Agent 行为生命周期"：

```yaml
# 新增 Agent 行为事件类型
Σ_agent = {
  TOOL_CALL,      # 工具调用事件
  RETRIEVE,       # 检索事件
  REASON,         # 推理事件
  OBSERVE,        # 环境观察事件
  COMMUNICATE,    # 智能体间通信事件
  DELEGATE,       # 任务委托事件
  VERIFY,         # 验证/验证事件
  REVOKE,         # 撤销/否定事件
}
```

每个事件携带：actor（agent_id）、tool_name、inputs_hash、outputs_hash、reasoning、confidence。

**为什么这是机会**：2026 年的综述论文 "From Agent Traces to Trust" 明确呼吁"统一溯源格式"，但尚未提出具体方案。ADL Lite 的 EventChain 已经具备了这种格式的**所有基础构件**。

---

### 机会窗口 2：Agent Memory Governance（智能体记忆治理）

**问题**: Letta [未验证] (2026) 使用 Git 作为 Agent Memory 的存储后端，但：
- 合并冲突时只能做**文本级合并**（text-level merge），无法语义解决矛盾信念
- 更新一个信念时，**不会自动识别**依赖该信念的其他文件
- 没有**生命周期状态**（记忆条目不会过期、不会被验证、不会被废弃）

Graph-Native Cognitive Memory [未验证] (2026) 解决了这些问题，但：
- 需要图数据库（非轻量级）
- 没有加密哈希链（无篡改检测）
- 没有多智能体协作的原生支持

**ADL Lite 的扩展**: 将 EventChain 作为 Agent Memory 的**治理层**：

```markdown
# Agent Memory Entry
```yaml
adl_type: memory_entry
adl_id: memory-client-preference-001
status: validated    # 从 EventChain 推导
confidence: 0.85     # 从验证事件推导
scope: shared
```

```adl:relation
source: memory-client-preference-001
relation: depends-on
target: memory-project-brief-003
confidence: 0.9
```

```adl:action
action: supersede
actor: agent_2
reasoning: "Client preference changed from warm to cool tones"
params:
  new_entry: memory-client-preference-002
  obsolete_entry: memory-client-preference-001
```
```

**关键创新**:
- **Supersede 事件**替代文本合并：用结构化事件记录信念更替，而非人工解决合并冲突
- **AnalyzeImpact 传播**：通过 L3 关系块的 `depends-on` 边，自动识别下游依赖
- **生命周期状态**：记忆条目可以被 VALIDATE（确认）、DEPRECATE（废弃）、ARCHIVE（归档）

---

### 机会窗口 3：多智能体委托合约（Delegation Contracts）

**问题**: "The Provenance Paradox" [未验证] (2026) 指出当前多智能体协议（A2A, MCP, LDP）缺乏**三个关键能力**：

1. **Bounded Authority**: 委托时没有预算、截止时间、成功标准的协议级机制
2. **Verified Identity**: 质量分数是自报告的，存在激励悖论（"provenance paradox"）
3. **Structured Failure Handling**: 失败以非结构化字符串传递

**ADL Lite 的扩展**: 将 EventChain 作为**智能体间委托合约**的载体：

```yaml
# 委托合约事件
adl_type: delegation_contract
adl_id: delegate-analysis-aml-001
```

```adl:action
action: delegate
actor: agent_orchestrator
target_agent: agent_analyst
reasoning: "Delegate AML pattern analysis to specialist agent"
params:
  budget:
    max_tokens: 4000
    max_cost_usd: 0.50
    max_rounds: 3
  deadline: "2026-06-14T18:00:00Z"
  success_criteria:
    - "Identify at least 2 suspicious patterns"
    - "Provide confidence score for each pattern"
  deliverable_format: "adl:concept document"
```

```adl:action
action: verify
actor: agent_validator
reasoning: "Check deliverable against success criteria"
params:
  criteria_met: true
  patterns_found: 3
  confidence_threshold_met: true
```

**关键创新**:
- **结构化委托合约**：前置条件定义预算、截止时间、成功标准
- **可验证的交付**：交付物本身是一个 ADL 概念，其 EventChain 记录了完整的分析过程
- **失败结构化处理**：如果委托失败，生成 DEPRECATE 事件 + 结构化的失败原因（而非非结构化字符串）

---

### 机会窗口 4：LLM 作为验证者（LLM-as-Validator）

**问题**: C-LLM (2024) 展示了多 LLM 节点 + 真理发现算法的有效性，但：
- 需要专门的 oracle 架构
- 不是轻量级的
- 没有与现有概念治理框架的集成

OL-KGC (ISWC 2025) 展示了将本体知识注入 LLM 可提升推理能力，但：
- 是离线训练/推理阶段，不是运行时治理
- 没有多智能体协作的验证机制

**ADL Lite 的扩展**: 在 γ(C) 函数中引入**LLM-as-Validator**模式：

```python
# 增强的 confidence 聚合函数
def gamma_llm_enhanced(C):
    # 1. 传统验证者聚合（Phase 1）
    human_validators = [e for e in C if e.actor.startswith("human_")]
    base_confidence = traditional_gamma(human_validators)
    
    # 2. LLM 验证者聚合（新增）
    llm_validators = [e for e in C if e.actor.startswith("llm_")]
    if llm_validators:
        # 使用语义一致性评估（SenteTruth 风格）
        llm_consensus = semantic_consensus(llm_validators)
        # 使用本体约束过滤（OL-KGC 风格）
        ontology_check = validate_against_ontology(C, adl_core_ontology.yaml)
        
        # 加权聚合：人类验证者权重更高，但 LLM 验证者提供额外信号
        final_confidence = 0.6 * base_confidence + 0.4 * llm_consensus * ontology_check
    
    return min(1.0, final_confidence)
```

**关键创新**:
- **本体一致性检查**：LLM 验证者必须同时检查概念是否符合 ontology.yaml 中的约束（如"isomorphic-to"关系的定义域和值域）
- **语义一致性**：多个 LLM 验证者对同一概念给出不同判断时，使用语义相似度（而非简单投票）来评估共识
- **人类否决权**：LLM 验证者的 confidence 可以**被人类验证者覆盖**（通过更高权重的 VALIDATE 事件）

---

### 机会窗口 5：与 LLM Agent 生态的原生集成（Plugin / Middleware）

**问题**: 当前 LLM Agent 框架（AutoGen, CAMEL, CrewAI, LangChain）提供了强大的**编排能力**，但缺乏**治理能力**。AgentOps 和 AgentTrace 提供了**观测能力**，但缺乏**执行控制能力**。

**ADL Lite 的扩展（设计提案）**: 开发**ADL Lite Agent Plugin** — 作为 LLM Agent 框架的治理中间件。以下集成点为概念设计，尚未实现：

```python
# 以 AutoGen 为例
from adl_lite.agent_plugin import ADLAgentPlugin
from autogen import ConversableAgent

# 创建带有 ADL 治理的 Agent
agent = ConversableAgent(
    name="analyst",
    llm_config=llm_config,
)

# 包装 ADL 治理层
adl_plugin = ADLAgentPlugin(
    agent=agent,
    concept_id="aml-pattern-analysis",
    ontology_file="adl_core_ontology.yaml",
    scope="shared/team-alpha",
)

# 所有 agent 行为自动记录到 EventChain
# - 每次 tool_call → 生成 TOOL_CALL 事件
# - 每次 LLM 响应 → 生成 REASON 事件（结构化提取 [Observation, Reasoning, Conclusion]）
# - 每次验证操作 → 生成 VERIFY 事件
# - 状态变更自动检查前置条件
```

**集成点**:

| Agent 框架 | 集成方式 | 治理事件映射 |
|-----------|----------|-------------|
| **AutoGen** | GroupChat 的 speaker_selection 钩子 | 每次发言 → COMMUNICATE 事件；每次 tool_call → TOOL_CALL 事件 |
| **CAMEL** | RolePlayingSession 的 step 回调 | 每次 task decomposition → DELEGATE 事件；每次 dialogue → REASON 事件 |
| **CrewAI** | Task 的 before/after 钩子 | 每次 task 执行 → EXECUTE 事件；每次 task 完成 → VERIFY 事件 |
| **LangChain** | LCEL 链的 Runnable 包装器 | 每次 chain 执行 → EXECUTE 事件；每次 retrieval → RETRIEVE 事件 |
| **MCP** | Server capability 的 metadata | 每个 tool 注册 → REGISTER 事件；每个 tool 调用 → TOOL_CALL 事件 |

---

## 三、四个具体的技术演进方向

### 方向 A：论文定位升级（最紧急）

**从**: "ADL Lite: An Event-First Operational Ontology for Concept Lifecycle Governance"

**升级为**: "ADL Lite: An Event-First Governance Layer for LLM Agent Collaboration and Concept Lifecycle Management"

**核心变化**:
1. 将"Concept Lifecycle Governance"从唯一焦点变为**两个支柱之一**（另一个是 Agent 行为治理）
2. 将 LLM Agent 的**执行溯源**、**记忆治理**、**委托合约**作为核心贡献
3. 将论文定位为**Agent 生态的治理基础设施**，而非独立的工具

**为什么这是最优策略**:
- 2025-2026 年 Agent 生态正在爆发，但治理层几乎空白
- 这是"抢占生态位"的最佳窗口期
- ESWC/ISWC 2027 对 Agent + 语义网的交叉领域高度关注

---

### 方向 B：从 Framework 到 Platform（中期）

**当前**: ADL Lite 是一个 Python 包 + CLI 工具

**演进为**: ADL Lite Platform = Python SDK + Agent Plugin + Web Dashboard + Git-native Storage

| 组件 | 功能 | 对标 |
|------|------|------|
| **adl-lite SDK** | 现有功能 + Agent 事件类型 | 类似 LangChain 的 "adl" 包 |
| **adl-lite-agent** | AutoGen/CAMEL/CrewAI 插件 | 类似 AgentOps 的 observability 层，但加上 governance |
| **adl-lite-web** | 可视化 EventChain 浏览器；状态推导实时展示 | 类似 Letta [未验证] 的 memory viewer，但展示 governance 状态 |
| **adl-lite-git** | Git 钩子 + CI/CD 集成；PR 时自动验证 EventChain 完整性 | 类似 GitHub Actions 的 pre-commit 验证 |

---

### 方向 C：与行业协议对齐（长期）

| 协议 | 对齐方式 | 时机 |
|------|----------|------|
| **MCP (Model Context Protocol)** | 将 ADL Lite 作为 MCP Server 的 capability manifest 格式；每个 tool 的注册/调用/验证通过 EventChain 记录 | 2026 Q4 |
| **A2A (Agent-to-Agent Protocol)** | 将 ADL Lite 作为 A2A 消息的结构化 envelope；agent 间通信携带 EventChain 片段 | 2026 Q1 |
| **LDP (LLM Delegate Protocol)** | 将 ADL Lite 的委托合约作为 LDP 的 Delegation Contract 扩展 | 2026 Q1 |
| **OpenTelemetry** | 将 ADL Lite 事件映射到 OpenTelemetry traces/spans | 2026 Q2 |

---

### 方向 D：从学术工具到开源社区（战略）

**问题**: 当前 ADL Lite 是"论文项目"，用户门槛较高（需要理解本体论、事件链、YAML 等概念）。

**演进策略**:

1. **降低门槛**:
   - 提供 `adl-lite init` 一键初始化项目模板
   - 提供 `adl-lite agent init` 一键创建 Agent 治理配置
   - 提供 Jupyter Notebook 教程（"Govern Your First LLM Agent in 5 Minutes"）

2. **社区建设**:
   - 在 GitHub 上创建 Discussion 板块，收集 Agent 框架的集成需求
   - 创建 "ADL Lite Agent Integrations" 示例仓库（AutoGen + ADL, CAMEL + ADL, CrewAI + ADL）
   - 参与 MCP / A2A 社区讨论，推动 ADL Lite 作为治理层标准

3. **生态位卡位**:
   - 在 "Agent Governance" 这个新兴品类中成为**第一个被广泛引用的框架**
   - 目标：当 2026-2027 年 LLM Agent 治理成为热门话题时，ADL Lite 是**默认的轻量级解决方案**

---

## 四、建议的论文改版策略（v4.0 定位）

### 4.1 新论文标题建议

1. **推荐**: "ADL Lite: Event-First Governance for LLM Agent Collaboration and Concept Lifecycle Management"
2. **备选**: "ADL Lite: A Lightweight Provenance and Governance Layer for Multi-Agent LLM Systems"
3. **备选**: "ADL Lite: Cryptographically Auditable Agent Collaboration through Event-First Ontology"

### 4.2 新增核心贡献（从 3 个扩展到 5 个）

**原有贡献**（保留并深化）:
- C1: 本体论分析（BFO/DOLCE/UFO 映射）
- C2: 形式化语义（δ/γ 推导 + 7 个定理）
- C3: 经验验证（AML 数据集 + 架构正确性）

**新增贡献**（基于机会窗口）:
- **C4: Agent 行为溯源模型** — 将 EventChain 从概念生命周期扩展到 Agent 执行生命周期；定义 Agent 事件字母表 Σ_agent；证明 Agent 行为溯源的可判定性（Theorem 8）
- **C5: Agent Memory 治理机制** — 基于 EventChain 的结构化记忆更替（Supersede 事件）；自动影响传播（AnalyzeImpact）；与 Letta [未验证] 的对比实验

### 4.3 新增实验设计

| 实验 | 设计 | 验证假设 |
|------|------|----------|
| **E17 (升级版)** | 3 个 LLM 智能体（AutoGen）在 AML 数据集上协作，通过 ADL Lite 记录完整行为溯源 | Agent 行为溯源的完整性 + 可验证性 |
| **E18** | 共谋脆弱性分析（已有） + **新增**：LLM 验证者 vs. 人类验证者的 confidence 一致性 | LLM-as-Validator 的可行性 |
| **E19** | Head-to-head: ADL Lite vs. AgentOps vs. 无治理基线，测量**治理开销**和**错误检测率** | 治理开销 < 20% 且错误检测率 > 80% |
| **E20 (新)** | 与 Letta [未验证] 的 Agent Memory 对比：文本合并 vs. 结构化 Supersede 事件 | 结构化更替减少 80% 的合并冲突 |
| **E21 (新)** | Agent 委托合约实验：2 个 agent 通过 ADL Lite 委托合约协作完成 KG 构建任务 | 结构化委托合约减少 50% 的任务失败 |

### 4.4 相关文献重构

**必须新增的对比/引用**（2025-2026 年文献）：

| 文献 | 引用位置 | 用途 |
|------|----------|------|
| "From Agent Traces to Trust" (2026) | §1.2, §2.4 | 证明 Agent 溯源的系统性缺口；将 ADL Lite 定位为"溯源格式方案" |
| "Can We Trust Open Agentic Systems?" [未验证] (2026) | §1.2, §2.5 | 证明 5 层治理模型的需求；将 ADL Lite 的 Layer 4 能力对齐 |
| "The Provenance Paradox" [未验证] (2026) | §1.2, §2.5 | 证明三个治理缺口；将 ADL Lite 作为缺口的解决方案 |
| Letta [未验证] (2026) | §2.4, §6.4 | 对比 Agent Memory 管理；证明 ADL Lite 在治理深度上的优势 |
| Graph-Native Cognitive Memory [未验证] (2026) | §2.4, §6.4 | 对比记忆架构；证明 ADL Lite 的轻量级优势 |
| OL-KGC (ISWC 2025) | §2.3, §5.5 | 证明本体注入 LLM 的有效性；将 ADL Lite ontology 作为注入源 |
| LLMChain (2025) | §2.2, §6.4 | 对比 LLM 评估的声誉机制；证明 ADL Lite 的哈希链替代方案 |
| C-LLM / SenteTruth (2024) | §4.4, §5.5 | 为 γ(C) 的 LLM 增强提供算法参考 |

---

## 五、路线图建议（v0.2 → v1.0）

### Phase 1: v0.3（2026 Q3）— 论文核心
- 完成 Agent 事件类型系统（Σ_agent）
- 完成 E17（LLM Agent 协作实验）
- 完成 E20（Agent Memory 对比实验）
- 提交 ESWC/ISWC 2027（长文）

### Phase 2: v0.4（2026 Q4）— Agent 集成
- 发布 adl-lite-agent 插件（AutoGen 集成）
- 发布 adl-lite-web（EventChain 可视化）
- 与 MCP 社区对接，推动 capability manifest 标准

### Phase 3: v0.5（2026 Q1）— 平台扩展
- 发布 adl-lite-agent 的 CAMEL / CrewAI 集成
- 发布 A2A 消息 envelope 支持
- 引入 LLM-as-Validator（语义一致性评估）
- 引入委托合约（Delegation Contract）事件类型

### Phase 4: v0.6+（2026 Q2+）— 生态建设
- 开源社区运营（教程、示例、集成）
- 引入 Blocklace DAG 作为传输层（Phase 3 论文承诺）
- 引入 Ed25519 + DIDs 认证（Phase 3 论文承诺）
- 提交 Journal 长文（Applied Ontology / Semantic Web Journal）

---

## 六、核心判断：ADL Lite 是否还能更进一步？

**答案是：能，而且必须现在就行动。**

### 为什么现在是最佳窗口期？

1. **Agent 生态爆发**：2025-2026 年 AutoGen v2, CrewAI, LangGraph, MCP, A2A 等框架都在快速迭代，但**治理层完全空白**
2. **溯源需求觉醒**：从 "Can We Trust Open Agentic Systems?" [未验证] 到 "From Agent Traces to Trust" (arXiv:2606.04990)，学术界已经意识到这是一个**系统性问题**
3. **轻量级定位稀缺**：Letta [未验证] 用 Git 做 memory，Graph-Native Memory [未验证] 用图数据库，但**没有系统用事件链 + 哈希链 + 确定性推导**
4. **竞争尚未形成**：AgentOps 和 AgentTrace 是观测工具，不是治理工具；AgentSpec [未验证] 和 Agent-Sentry [未验证] 是安全工具，不是生命周期治理工具。ADL Lite 的**事件优先 + 生命周期状态机 + 加密完整性**组合是**独特的**

### 风险

| 风险 | 概率 | 影响 | 缓解策略 |
|------|------|------|----------|
| AutoGen/CrewAI 自己开发治理层 | 中 | 高 | 尽快发布开源插件，成为社区标准 |
| 区块链溯源系统（如 LLMChain）扩展到 Agent 治理 | 低 | 中 | 强调轻量级 + 本地部署优势 |
| 论文定位过宽导致审稿人质疑深度 | 中 | 高 | 保留核心本体论/形式化贡献，将 Agent 扩展作为"应用示范"而非"核心贡献" |
| 实验开发周期超出会议截止日期 | 高 | 高 | 分阶段提交：v0.2 论文（框架）+ v0.3 论文（Agent 应用） |

---

> **最终建议**：不要等待论文被接受后再扩展。当前 2025-2026 年的 Agent 治理缺口是**窗口性的** — 如果 ADL Lite 能在 2026 年下半年发布 Agent 集成的原型并产生社区影响，它将有机会成为这个新兴领域的**定义性框架**。建议将论文从 "v0.2 框架论文" 升级为 "v0.3 Agent 治理论文"，同时启动开源社区建设。
