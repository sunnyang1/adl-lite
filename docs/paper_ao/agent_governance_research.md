# Agent Governance 品类深度研究报告：ADL Lite 的战略定位与机会窗口

> **编制日期**: 2026-06-14  
> **验证日期**: 2026-06-14  
> **数据来源**: arXiv (2024-2026)、Google Scholar、行业报告、OWASP、安全审计机构  
> **研究范围**: 学术框架、工业工具、协议标准、监管要求  
> **核心问题**: Agent Governance 品类中，ADL Lite 可以占据什么生态位？  
> **验证状态**: 以下论文已用 arXiv ID 验证：KYA (2605.25376), Agent Traces (2606.04990), AgentSafe (2512.03180), SafeAgent (2604.17562), Blocklace (2402.08068), Sello (2606.04193), TRISM (2026)。未验证条目标注 [未验证]。

---

## 一、品类定义：什么是 Agent Governance？

Agent Governance 不是单一工具，而是**覆盖 Agent 全生命周期的控制层**，从设计、部署、运行到退役。以下 5 层分类是**基于本分析构建的框架**，未引用外部权威分类，但综合了多篇 2025-2026 年论文的叙述：

| 层次 | 功能 | 典型工具/框架 | 学术代表 |
|------|------|-------------|----------|
| **L1 观测 (Observability)** | 日志、追踪、遥测、指标 | AgentOps, LangSmith, Galileo, Arize | AgentTrace, TRAIL, MAST |
| **L2 安全 (Security)** | 输入过滤、输出控制、访问控制、RBAC | NeMo Guardrails, Lakera, AWS Bedrock Guardrails | AgentSpec [未验证], TrustAgent, MCP Guardian |
| **L3 运行时执行 (Runtime Enforcement)** | 实时策略执行、异常检测、中断 | — | AgentGuardian [未验证], MI9 [未验证], Pro2Guard [未验证], ABC [未验证] |
| **L4 生命周期治理 (Lifecycle Governance)** | 注册、验证、版本控制、废弃、审计 | Dataiku Govern, miniOrange ALM | ADL Lite *(候选)* |
| **L5 溯源与合规 (Provenance & Compliance)** | 不可篡改的审计日志、合规报告、证据链 | Unique MCP Governance, GoHighLevel | "From Agent Traces to Trust", KYA |

> **关键洞察**：当前品类存在严重的**层次割裂**。观测工具只管记录，安全工具只管拦截，运行时工具只管执行，但没有任何系统将它们**连接起来**形成完整的生命周期链。这恰恰是 ADL Lite 的机会。

---

## 二、竞争格局全景：谁在做什么？

### 2.1 学术框架地图（2024-2026）

| 框架 | 年份 | 核心能力 | 定位 | 与 ADL Lite 的关系 |
|------|------|----------|------|-------------------|
| **KYA** (arXiv:2605.25376, Quadri, 2026) | 2026 | 框架无关信任层；HMAC 链；15+ 适配器；3 通道层级权限；pip-installable；veldt-kya on PyPI；~1,800 ops/sec | **L5 溯源 + L3 执行** | **最接近的竞争对手** — 但 KYA 是权限/策略执行，不是事件溯源/生命周期状态机 [可信度: 95%] |
| **AgentGuardian** [未验证] | 2026 | 基于 LiteLLM 的访问控制；学习 CFG 和行为模式；策略执行 | **L3 运行时执行** | 互补：AgentGuardian 做实时拦截，ADL Lite 做事件记录和生命周期推导 |
| **AgentSafe** (arXiv:2512.03180, Khan et al., 2025) | 2025 | 统一治理框架：设计时 + 运行时 + 审计控制；异常检测；可中断性 | **L2-L4 跨层** | 竞争：AgentSafe 是架构级治理，ADL Lite 是数据结构级治理；两者可互补 [可信度: 90%] |
| **MI9** [未验证] | 2025 | 运行时治理框架：6 组件（风险指数、语义遥测、授权监控、FSM 合规、漂移检测、分级遏制） | **L3 运行时执行** | 互补：MI9 监控"已部署 agent"的行为，ADL Lite 管理"agent 版本/能力"的准入边界 |
| **ABC** [未验证] | 2026 | 主动式行为契约；概率合规保证；合同 DSL；可组合性定理；漂移检测 | **L3 运行时执行** | 互补：ABC 是前摄式行为预期，ADL Lite 是后摄式事件记录；两者构成"预期-记录-验证"闭环 |
| **AgentSpec** [未验证] | 2026 | 可定制的运行时执行框架；规则 DSL；预防性和纠正性执行模式 | **L2 安全 + L3 执行** | 互补：AgentSpec 做实时安全规则执行，ADL Lite 做安全事件的持久化审计记录 |
| **Colosseum** [未验证] | 2026 | 审计多智能体共谋；秘密通道检测；联盟优势度量；LLM-as-a-judge | **L5 溯源 + 审计** | 互补：Colosseum 检测共谋，ADL Lite 记录和验证治理事件；ADL Lite 可为 Colosseum 提供结构化输入 |
| **AIR** [未验证] | 2026 | 事件响应 DSL：检测、遏制、恢复、根除；>90% 成功率 | **L3 事件响应** | 互补：AIR 是反应式，ADL Lite 是记录式；ADL Lite 记录的事件是 AIR 的输入证据 |
| **POLARIS** [未验证] | 2026 | 企业工作流的治理编排；类型化规划；验证器门控执行 | **L4 生命周期** | 竞争：POLARIS 是工作流级别的治理，ADL Lite 是概念/能力级别的治理；粒度不同 |
| **"From Agent Traces to Trust"** (arXiv:2606.04990, Wang et al., 2026) | 2026 | 统一溯源框架：证据溯源 + 执行溯源；提出统一 trace schema 的需求 | **L5 溯源理论** | **机会窗口**：该论文明确呼吁"统一溯源格式"，但**没有提出具体方案**。ADL Lite 的 EventChain 可以直接响应这个呼吁 [可信度: 90%] |
| **LTM Security Survey** [未验证] | 2026 | 长期记忆安全的系统性综述：持久性、状态性、传播性 | **L2 安全理论** | 可借鉴：ADL Lite 的 ARCHIVE 事件可用于记忆条目的生命周期管理 |

### 2.2 工业工具地图

| 工具/平台 | 类型 | 核心能力 | 治理缺口 |
|----------|------|----------|----------|
| **AgentOps** | 观测 | 结构化执行追踪、遥测、仪表板 | 无生命周期状态机；无篡改检测；无确定性推导 |
| **LangSmith** | 观测 | 提示版本控制、追踪、评估 | 同上；无 agent 生命周期治理 |
| **Galileo** | 观测 + 评估 | 日志、评估、偏见检测 | 同上 |
| **NeMo Guardrails** | 安全 | 输入/输出过滤、对话 rails | 无持久化审计；无事件链；无状态推导 |
| **AWS Bedrock Guardrails** | 安全 | 内容过滤、PII 检测、话题限制 | 同上；云厂商锁定 |
| **MCP Guardian** | 安全 | 认证、速率限制、WAF 扫描 | 日志无结构化；无生命周期；无哈希验证 |
| **Unique MCP Governance** | 安全 + 治理 | 人类在环、认证、注册表、审计日志 | 审计日志无加密完整性；无状态机；无确定性推导 |
| **Dataiku Govern** | 治理 | 审批工作流、审计追踪 | 企业级；非轻量级；无加密链 |
| **miniOrange ALM** | 治理 | 身份配置、访问编排、行为监控、自适应治理 | 企业 IAM 平台；非 Markdown-native；无事件链 |
| **LiteLLM** | 网关 | 模型路由、成本管理、策略执行 | 网关层；不管理 agent 概念/能力生命周期 |
| **GoHighLevel** | 合规 | 审计日志、trace history、合规评估 | 垂直领域（营销）；无通用性 |

### 2.3 协议与标准地图

| 协议/标准 | 状态 | 安全/治理能力 | 缺口 |
|-----------|------|-------------|------|
| **MCP** | 已发布 (Anthropic 2024) | 2025 年 OAuth 2.1 可选；无原生安全 | **OWASP MCP Top 10 (2025)** 明确列出：MCP08 缺乏审计和遥测；MCP 安全危机 (2026) 披露 20 万+ 漏洞实例 |
| **A2A** | 已发布 (Google 2025) | 无安全设计；无审计 | 同上 |
| **OpenTelemetry** | 成熟 | 分布式追踪标准 | 无语义溯源；无生命周期状态；无加密完整性 |
| **EU AI Act** | 生效中 | 要求透明度、可追溯性、风险分类 | 未指定具体技术实现；无 agent 特定条款 |
| **NIST AI RMF** | 发布 | GOVERN/MAP/MEASURE/MANAGE | 无 agent 特定操作化；无多智能体协调失败定义 |
| **OWASP MCP Top 10** | 2025 | 列出 10 大安全风险 | 仅指出问题，不提供解决方案框架 |
| **CoSAI** | 2025 | 提出分层防御模型 | 架构指南，无具体实现 |
| **ISO 42001** | 2025 | AI 管理系统标准 | 管理体系，非技术框架 |

---

## 三、ADL Lite 的差异化定位：在品类地图中的唯一性

### 3.1 四象限分析：Agent Governance 品类矩阵

```
                    高表达力
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
    │  Graph-Native    │  AgentSafe       │
    │  Cognitive       │  POLARIS         │
    │  Memory [未验证]  │  Dataiku Govern  │
    │                  │                  │
重  │──────────────────┼──────────────────│  轻
量  │                  │                  │  量
级  │                  │  ★ ADL Lite ★    │  级
    │  Blocklace       │  (Markdown-native,│
    │  (DAG+Blockchain)│  pip-installable, │
    │                  │  EventChain)      │
    │                  │                  │
    └──────────────────┼──────────────────┘
                       │
                    低表达力
         通用传输层 ←─────────────────→ 专用应用层
```
> 注：四象限中 Graph-Native Cognitive Memory、POLARIS 为 [未验证] 文献（截至 2026-06-14 未通过 arXiv/Google Scholar 验证）。

### 3.2 ADL Lite 的 5 个不可替代属性

在品类地图中，**没有任何其他系统同时具备以下 5 个属性**：

| 属性 | ADL Lite | 最接近的替代方案 | 为什么不可替代 |
|------|----------|-----------------|--------------|
| **1. Markdown-native** | 概念文档即 Markdown 文件 | Letta [未验证] (Git-backed Markdown) | Letta 是 memory 存储，不是 governance 结构；无生命周期状态机 |
| **2. 事件链 + 加密哈希** | SHA-256 链式验证 | KYA (HMAC 链) | KYA 是权限执行层，不是概念生命周期层；HMAC 用于认证，SHA-256 用于内容寻址 |
| **3. 确定性推导** | δ(C) 状态 + γ(C) 置信度 | 无直接对应 | 完全独特：从事件历史推导状态，而非存储可变状态 |
| **4. 声明式前置条件** | YAML 规则 + O(1) 评估 | AgentSpec [未验证] (规则 DSL) | AgentSpec 是运行时安全规则，ADL Lite 是准入/生命周期规则；AgentSpec 无加密完整性 |
| **5. 概念级粒度** | 每个概念一个 EventChain | 无直接对应 | 完全独特：现有系统要么管 agent 实例（MI9 [未验证]），要么管工作流（POLARIS [未验证]），要么管工具调用（MCP Guardian [未验证]），没有管"概念/能力"生命周期的 |

### 3.3 与最强竞争对手 KYA 的详细对比

**KYA (arXiv:2605.25376, Quadri, 2026)** 是 ADL Lite 在品类中最接近的竞争对手。以下对比基于 KYA 论文全文（179 KB PDF，已完整阅读） [可信度: 95%]：

| 维度 | KYA | ADL Lite |
|------|-----|----------|
| **目标** | 框架无关的信任层（身份 + 权限 + 溯源） | 事件优先的概念/能力治理层（生命周期 + 溯源 + 推导） |
| **数据结构** | HMAC 链（认证链）+ 4 门入站 apply 管道（Ed25519 签名、过期检查、only-tighten 组合、operator-approval-as-default） | SHA-256 链（内容寻址 + 篡改检测） |
| **事件类型** | 未明确分类；侧重于操作日志（invocation, evidence-chain, principal-signal） | 明确的生命周期事件（REGISTER/VALIDATE/DEPRECATE/FORK/ARCHIVE） |
| **状态推导** | 无 | 确定性 δ(C) 和 γ(C) |
| **前置条件** | Cedar-style 权限策略 + only-tighten 组合代数（有形式化 soundness lemma） | YAML 声明式生命周期规则（O(1) 可判定，无外部推理器） |
| **部署** | pip-installable（veldt-kya），Python 3.10+，SQLAlchemy 依赖，PG/SQLite/DuckDB/MySQL 四后端 | pip-installable，Python 3.10+，Pydantic + PyYAML |
| **性能** | p99 < 1ms（纯函数评分），并发 20 worker 下 ~1,800 ops/sec，HMAC 链完整性保持 | 未报告性能基准（需补充） |
| **适配器** | 15+ 框架（LangChain, CrewAI, AutoGen, MCP, OpenAI Agents, Claude SDK 等） | 目前无原生适配器（需开发） |
| **监管映射** | EU AI Act, NIST AI RMF, HIPAA, AIVSS | 尚未明确映射（计划中） |
| **粒度** | 系统级/操作级（principal-signal 层面） | 概念级/能力级 |
| **开源** | Apache 2.0（GitHub: veldtlabs/veldt-kya） | MIT |
| **反欺诈** | 检测到 89% 的 1,200 PyRIT/Garak 对抗探测；归因 Liang 拓扑引导多智能体攻击 | 无对抗探测能力（Phase 1 非对抗假设） |

**关键区分**：KYA 的 **KYP (Know Your Principal)** 统一了人类用户、AI agent、服务账户的信任评分，但评分维度是**权限风险**（read/write/admin/autonomous mode）而非**概念生命周期状态**。KYA 的 actor-agent runtime debit 机制是**动态信任衰减**，而 ADL Lite 的 γ(C) 是**静态置信度聚合**。两者互补：KYA 回答 "这个 agent 现在可信吗？"，ADL Lite 回答 "这个概念经过什么验证过程？" [可信度: 95%]。

---

## 四、ADL Lite 可以占据的 3 个细分生态位

### 生态位 1：Agent Capability Lifecycle Registry（Agent 能力生命周期注册表）

**问题**: 当前 agent 框架（AutoGen, CrewAI, LangChain）中，agent 的**能力（capabilities/tools/skills）** 没有生命周期管理。一个 agent 可以调用任何工具，工具的版本没有注册，工具的变更没有验证，工具的废弃没有审计。

**KYA 不能做**: KYA 管权限（"agent A 可以调用 tool X"），但不管工具本身的生命周期（"tool X 从 v1 升级到 v2 是否经过验证？"）。

**AgentSafe 不能做**: AgentSafe 管 agent 行为的运行时监控，但不管概念级别的能力演化。

**ADL Lite 可以做**:

```yaml
# 工具/能力注册
adl_type: capability
adl_id: tool-weather-forecast
status: validated    # 从 EventChain 推导
confidence: 0.92
version: 2.1
```

```adl:action
action: validate
actor: security_team
reasoning: "Weather forecast tool v2.1 passed security review and integration tests"
params:
  security_score: 0.95
  test_coverage: 0.88
```

```adl:action
action: deprecate
actor: platform_team
reasoning: "Weather forecast tool v1.x deprecated due to API provider shutdown"
params:
  migration_target: tool-weather-forecast-v2
  deprecation_date: "2026-12-01"
```

**价值主张**: "每一个被 Agent 调用的工具，都有一个加密可验证的 EventChain，记录其注册、验证、升级、废弃的完整历史。"

**集成点**:
- MCP Server 注册时 → 生成 REGISTER 事件
- MCP Server 安全审计后 → 生成 VALIDATE 事件
- MCP Server 发现漏洞时 → 生成 DEPRECATE 事件
- Agent 调用工具时 → 查询工具状态（δ(C)），拒绝调用 deprecated 工具

---

### 生态位 2：Multi-Agent Decision Provenance（多智能体决策溯源）

**问题**: "The Provenance Paradox" [未验证] (2026) 和 "From Agent Traces to Trust" (arXiv:2606.04990, 2026) 共同指出：当前多智能体系统的决策缺乏**可验证的溯源**。Agent A 建议 action X，Agent B 建议 action Y，Agent C 决定 action Z — 但为什么选择了 Z？谁支持了谁？谁反对了谁？证据在哪里？

**现有工具缺口**:
- AgentOps 记录执行轨迹，但**无结构化的共识/冲突记录**
- AutoGen 记录对话消息，但**无决策的生命周期状态**
- Colosseum [未验证] 检测共谋，但**不提供治理事件记录格式**

**ADL Lite 可以做**:

```yaml
# 多智能体决策事件
adl_type: decision
adl_id: decision-aml-alert-001
status: validated
confidence: 0.85
```

```adl:evidence
source: agent_analyst
relation: proposes
target: decision-aml-alert-001
confidence: 0.90
payload:
  reasoning: "Transaction pattern matches rapid-movement laundering"
  evidence_chain: [tx-001, tx-002, tx-003]
```

```adl:evidence
source: agent_skeptic
relation: challenges
target: decision-aml-alert-001
confidence: 0.70
payload:
  reasoning: "Transaction volume below threshold; could be legitimate business"
```

```adl:action
action: validate
actor: agent_arbiter
reasoning: "Arbitration: analyst evidence stronger than skeptic challenge"
params:
  consensus_method: weighted_confidence
  final_score: 0.85
```

**价值主张**: "每一个多智能体决策都有加密可验证的 EventChain，记录提议、质疑、验证、仲裁的完整过程，支持事后审计和合规报告。"

---

### 生态位 3：Agent Memory Governance（智能体记忆治理）

**问题**: "LTM Security Survey" (2026) [未验证] 识别了长期记忆的三个安全问题：
1. **Persistence**: 被污染的记忆条目可以跨无限会话被召回
2. **Statefulness**: 安全分析单位从孤立输入变为不断演化的记忆状态
3. **Propagation**: 在多智能体系统中，污染通过消息、共享存储、工具参数传播

**Letta 的局限**: Letta [未验证] 用 Git 做 memory 版本控制，但：
- 文本级合并无法语义解决矛盾信念
- 更新信念时不会自动识别下游依赖
- 没有记忆条目的生命周期状态（验证/废弃/归档）

**Graph-Native Memory 的局限**: Graph-Native Memory [未验证] 需要图数据库，非轻量级，无加密链。

**ADL Lite 可以做**:

```yaml
# 记忆条目治理
adl_type: memory_entry
adl_id: memory-client-preference-001
status: deprecated
confidence: 0.0
```

```adl:action
action: supersede
actor: agent_2
reasoning: "Client preference changed from warm to cool tones"
params:
  new_entry: memory-client-preference-002
  obsolete_entry: memory-client-preference-001
  cascade_update: true  # 自动更新下游依赖
```

```adl:relation
source: memory-project-brief-003
relation: depends-on
target: memory-client-preference-002
confidence: 0.95
```

**价值主张**: "每一个 Agent 记忆条目都有加密可验证的 EventChain，支持结构化的更替、自动影响传播、和生命周期状态管理。"

---

## 五、战略建议：ADL Lite 如何卡位

### 建议 1：与 KYA 建立互补关系而非竞争

**策略**: 在论文和开源社区中明确声明："KYA 解决权限问题，ADL Lite 解决生命周期问题。两者集成可实现完整的 Agent Governance 栈。"

**具体行动**:
- 在论文 §2 中增加 KYA 的对比分析，明确区分权限层和生命周期层
- 开发 `adl-lite-kya` 集成模块：KYA 的权限决策自动触发 ADL Lite 的治理事件
- 与 KYA 作者建立联系，探索联合发表论文或联合工具链的可能性

### 建议 2：成为 MCP 生态的治理层标准

**策略**: MCP 是当前最活跃的 Agent 协议，但其安全治理几乎空白（OWASP Top 10 列出了 10 大问题，但没有提供解决方案框架）。

**具体行动**:
- 开发 `adl-lite-mcp` 插件：
  - MCP Server 注册时自动生成 EventChain
  - MCP Tool 调用时自动验证工具状态（拒绝 deprecated）
  - MCP 审计日志自动导出为 EventChain
- 在 MCP 社区（Linux Foundation）中提交 ADL Lite 作为治理参考实现
- 与 MCP Safety Audit (Radosevich & Halloran, 2025) 的作者合作，将 ADL Lite 作为审计工具的数据格式

### 建议 3：定义"Agent Capability Registry" 子品类

**策略**: 在 ESWC/ISWC 论文中，将核心贡献从"Concept Lifecycle Governance"重新包装为"Agent Capability Lifecycle Governance"。

**论证逻辑**:
1. 现有 Agent Governance 框架（AgentSafe, MI9 [未验证], KYA）都关注**行为**或**权限**
2. 但没有任何框架关注**能力/工具**的生命周期 — 这是 agent 生态中被忽视的关键资产
3. 每个 MCP Server、每个 Tool、每个 Skill 都是一个需要治理的"能力"
4. ADL Lite 的 EventChain 是这种能力治理的天然数据结构

**论文定位升级**:
> "ADL Lite addresses a gap in the Agent Governance landscape: while existing frameworks govern agent behavior (AgentSafe, MI9 [未验证]) and permissions (KYA), none provide a lightweight, cryptographically verifiable lifecycle registry for the capabilities, tools, and skills that agents invoke. We introduce ADL Lite as the first capability-lifecycle governance layer for agentic systems."

### 建议 4：抢占"Agent Decision Provenance" 学术话语

**策略**: "From Agent Traces to Trust" (2026) 明确呼吁"统一溯源格式"，但**没有提出具体方案**。ADL Lite 可以填补这个空白。

**具体行动**:
1. 在论文中明确引用该论文，并声明："ADL Lite's EventChain provides a concrete instantiation of the unified provenance schema called for by [From Agent Traces to Trust]."
2. 在论文中展示如何将 AutoGen/CAMEL 的 agent 对话映射到 ADL Lite 的 EventChain
3. 定义 Agent 事件字母表 Σ_agent = {TOOL_CALL, RETRIEVE, REASON, COMMUNICATE, DELEGATE, VERIFY, REVOKE}，并证明其可判定性

### 建议 5：与 Agent 框架建立原生集成

**优先级**:
| 框架 | 优先级 | 理由 |
|------|--------|------|
| **CrewAI** | P0 | 强调"确定性流程"和"审计日志"，与 ADL Lite 理念最契合；开源 + 企业版 AMP |
| **AutoGen** | P1 | 微软背景；多智能体对话最灵活；但治理需求最迫切（对话是非结构化的） |
| **LangChain/LangGraph** | P2 | 生态最大；但 LCEL 已提供一定的追踪能力；差异化较小 |
| **MCP** | P0 | 协议级别；治理空白最大；如果能成为 MCP 的治理参考实现，影响最大 |

---

## 六、风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| KYA 扩展生命周期治理能力 | 中 | 高 | 与 KYA 建立合作而非对抗；强调 ADL Lite 的"概念级粒度"是 KYA 的"系统级粒度"的补充 |
| MCP 官方自己开发治理层 | 低 | 高 | MCP 设计哲学是"最小协议"，治理层应由生态构建；加速成为社区参考实现 |
| 学术界不认可"Capability Governance"为新子品类 | 中 | 中 | 在论文中建立充分的论证：引用 MCP 工具爆炸、OWASP Top 10、EU AI Act 对工具透明度的要求 |
| 工业界对 Markdown-native 不感兴趣 | 低 | 中 | 工业界对轻量级和可审计性高度感兴趣；Letta [未验证] 的 Git-backed Markdown 成功证明了这一点 |
| Agent 框架自己开发治理插件 | 高 | 中 | 这实际上是机会而非风险：如果 CrewAI/AutoGen 开发治理插件，ADL Lite 可以成为其**底层格式标准** |

---

## 七、结论：品类卡位的时机

Agent Governance 品类正在**快速形成**但**尚未固化**。2025-2026 年的关键信号：

1. **OWASP MCP Top 10** 的发布标志着 Agent 安全治理被正式纳入安全行业议程
2. **"From Agent Traces to Trust"** 的发表标志着学术界承认 Agent 溯源是系统性问题
3. **KYA、AgentSafe、MI9 [未验证]** 的密集出现标志着"Agent Governance"作为一个学术子领域正在诞生
4. **AgentOps、Galileo、LangSmith** 的成熟标志着观测层已饱和，但**治理层**几乎空白

**ADL Lite 的窗口期**:
- 如果能在 **2026 年下半年**发布 `adl-lite-mcp` 和 `adl-lite-crewai` 集成，并产生社区影响
- 如果能在 **ESWC/ISWC 2027** 提交以"Agent Capability Lifecycle Governance"为核心定位的论文
- 那么 ADL Lite 有机会成为**Agent Governance 品类中"Capability/Tool Lifecycle"子品类的定义者**

> **品类卡位的黄金法则**：不是做第一个进入品类的人，而是做**第一个定义子品类边界**的人。ADL Lite 不需要与 AgentSafe（行为治理）或 KYA（权限治理）竞争，而是定义一个它们都不覆盖的**新子品类**：**Agent Capability Lifecycle Governance with Cryptographically Verifiable Provenance**。

---

> **报告附录：引用文献清单**
>
> 本报告中引用的关键文献（2024-2026）：
> - KYA: "A Framework-Agnostic Trust Layer..." (arXiv:2605.25376, 2026) [已验证]
> - AgentGuardian: "Learning Access Control Policies to Govern AI Agent Behavior" (2026) [未验证]
> - AgentSafe: Khan et al. (arXiv:2512.03180, 2025) [已验证]
> - MI9: Wang et al. (2025) [未验证]
> - ABC: "Formal Specification and Runtime Enforcement..." (2026) [未验证]
> - AgentSpec: Wang et al. (2026) [未验证]
> - Colosseum: "Auditing Collusion in Cooperative Multi-Agent Systems" (2026) [未验证]
> - "From Agent Traces to Trust": Wang et al. (arXiv:2606.04990, 2026) [已验证]
> - "Can We Trust Open Agentic Systems?" (2026) [未验证]
> - "The Provenance Paradox in Multi-Agent LLM Routing" (2026) [未验证]
> - "Towards Secure Systems of Interacting AI Agents" (2025) [未验证]
> - MCP Safety Audit: Radosevich & Halloran (2025) [未验证]
> - OWASP MCP Top 10 (2025) [已验证]
> - "A Survey on Long-Term Memory Security in LLM Agents" (2026) [未验证]
> - Letta Context Repositories (2026) [未验证]
> - Graph-Native Cognitive Memory (2026) [未验证]
> - Dataiku Govern (2026)
> - miniOrange ALM (2026)
> - LTM Security Survey (2026) [未验证]
