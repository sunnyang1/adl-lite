# RQ1 人工评分问卷 — 指称清晰度 (Referent Clarity)

> **状态：已取消（2026-05-24）** — 本稿投稿 ESWC/ISWC 使用 **LLM-as-judge / proxy** 作为 RQ1 主观维度证据，不运行本问卷。文件仅作审计/未来工作存档；正文可能与 `experiments/outputs/` 中最新 discovery 不一致。  
> 生成日期：2026-05-24  
> 对应模板：`data/eval/human_rq1_template.json`（15 条 active discovery）  
> 评分标准：`prompts/judge_referent_clarity.md`

---

## Part A — 评分说明

### 您在评什么？

请阅读每条 discovery 的 **L2 正文（Markdown  prose）**，评估：**核心概念、实体、账户、系统、模式等指称（referent）是否清晰可辨**。

- 关注 **谁/什么/哪个系统/哪个账户** 能在首次阅读时被识别，**不是** 语法或文风。
- **ADL 臂**：只评 Markdown 正文；**忽略** YAML 头（L1）与 ` ```adl:* ` 结构化块（L3）。
- **公平纯文本臂 (Fair Plain)**：同一 discovery 去掉 ADL 结构块后的 L2 措辞。
- **纯 LLM 非结构化臂 (Plain LLM)**：同一 AML 主题的 MiMo 非结构化笔记（3 个主题各 1 篇，batch 条目共用）。
- **请勿** 参考或抄写 LLM 代理分数（`rq1_llm_judge_summary.json`）。

### 1–5 分制（整数）

| 分数 | 含义 |
|------|------|
| **5** | 每个指称都有明确命名；没有让读者猜测「到底指哪个实体」的模糊名词短语。 |
| **4** | 几乎全部指称已锚定；至多一处轻微欠指定。 |
| **3** | 大体清晰；部分实体欠指定或名词短语有歧义。 |
| **2** | 频繁出现未解析的指称；读者需从上下文推断实体。 |
| **1** | 普遍歧义；指示代词、裸代词或模糊短语占主导。 |

### 填写方式

1. 每条 discovery 依次阅读 **臂 A → 臂 B → 臂 C**（建议打乱顺序盲评；本问卷按字母标注便于回填 JSON）。
2. 在 `[您的评分: ___]` 处填 **1–5 整数**。
3. 可选：在「备注」中标注需第三方裁决的歧义点（正式双评时，两评分差 ≥2 需 adjudication）。

---

## Part B — 逐条评分题（共 15 条）

### 题目 1 / 15

- **Discovery ID**：`disc-llm-peripheral-trap`
- **概念主题**：外围注意力陷阱 (Peripheral Attention Trap)
- **场景说明**：Peripheral Attention Trap — graph peripheral node concentration while value consolidates toward a hidden sink; align with aml-attention-trap monitoring signals
- **源文件**：`experiments/outputs/llm_discovery_peripheral-trap.md`

#### 臂 A — ADL L2（评分时忽略 YAML 与 ` ```adl:* ` 块）

```markdown
# Peripheral Attention Trap

## Discovery Statement

In transaction monitoring systems, suspicious activity frequently migrates to graph peripheral nodes—entities with low centrality scores that receive minimal investigative attention. The Peripheral Attention Trap describes a systematic evasion pattern where illicit fund flows deliberately route through low-priority nodes to exploit the concentration of monitoring resources on high-centrality hubs. Over time, sink convergence occurs as multiple peripheral paths terminate at a small set of dormant beneficiary accounts, creating a hidden aggregation layer invisible to hub-centric detection models.

## Intuition

Standard AML graph analytics prioritize nodes with high betweenness centrality, high degree, or strong community membership. Adversarial actors observe (or infer) the prioritization heuristics and deliberately construct transaction chains that traverse peripheral nodes—accounts with few connections, recent onboarding dates, or low historical alert volumes. The Peripheral Attention Trap emerges when the monitoring system's own attention allocation becomes a predictable attack surface. Sink convergence amplifies the trap: multiple peripheral chains, each individually below alert thresholds, funnel into a small set of beneficiary accounts that remain dormant until extraction.

## Related Concepts

- [[AML Attention Trap]] — parent pattern describing how monitoring focus creates exploitable blind spots
- [[Graph Peripheral Nodes]] — structural feature of transaction networks exploited by the trap
- [[Sink Convergence]] — aggregation mechanism where multiple peripheral paths terminate at shared beneficiaries
- [[Centrality Evasion]] — adversarial strategy of avoiding high-centrality positions in transaction graphs

```adl:relation
source: "Peripheral Attention Trap"
relation: isomorphic-to
target: "adl://public/concepts/aml-attention-trap"
mapping_type: topological
confidence: 0.88
```

```adl:relation
source: "Peripheral Attention Trap"
relation: compositional-with
target: "adl://public/concepts/graph-peripheral-nodes"
mapping_type: structural
confidence: 0.82
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/graph-peripheral-nodes-2026q1
description: "Clustering analysis of 2026-Q1 transaction graphs reveals 14 peripheral node clusters exhibiting anomalous sink convergence patterns. Peripheral nodes involved in confirmed SAR cases show 3.2x higher connectivity to shared beneficiary accounts compared to control group peripheral nodes."
confidence: 0.75
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: vecdb://ceiec-aml/sink-convergence-analysis
description: "Agent-based simulation of adversarial fund routing demonstrates that peripheral-path strategies reduce alert trigger rates by 67% compared to hub-routing strategies, while maintaining equivalent extraction efficiency. Sink convergence emerges naturally when multiple adversarial agents independently select peripheral routes."
confidence: 0.70
observed_at: "2026-05-23T00:00:00Z"
```
```

**以下 ADL 文档正文中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity`
- [您的评分: ___]

#### 臂 B — Fair Plain L2（去掉 ADL 结构块后的同一措辞）

```markdown
# Peripheral Attention Trap

## Discovery Statement

In transaction monitoring systems, suspicious activity frequently migrates to graph peripheral nodes—entities with low centrality scores that receive minimal investigative attention. The Peripheral Attention Trap describes a systematic evasion pattern where illicit fund flows deliberately route through low-priority nodes to exploit the concentration of monitoring resources on high-centrality hubs. Over time, sink convergence occurs as multiple peripheral paths terminate at a small set of dormant beneficiary accounts, creating a hidden aggregation layer invisible to hub-centric detection models.

## Intuition

Standard AML graph analytics prioritize nodes with high betweenness centrality, high degree, or strong community membership. Adversarial actors observe (or infer) the prioritization heuristics and deliberately construct transaction chains that traverse peripheral nodes—accounts with few connections, recent onboarding dates, or low historical alert volumes. The Peripheral Attention Trap emerges when the monitoring system's own attention allocation becomes a predictable attack surface. Sink convergence amplifies the trap: multiple peripheral chains, each individually below alert thresholds, funnel into a small set of beneficiary accounts that remain dormant until extraction.

## Related Concepts

- [[AML Attention Trap]] — parent pattern describing how monitoring focus creates exploitable blind spots
- [[Graph Peripheral Nodes]] — structural feature of transaction networks exploited by the trap
- [[Sink Convergence]] — aggregation mechanism where multiple peripheral paths terminate at shared beneficiaries
- [[Centrality Evasion]] — adversarial strategy of avoiding high-centrality positions in transaction graphs
```

**以下公平纯文本中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_fair_plain`
- [您的评分: ___]

#### 臂 C — Plain LLM 非结构化基线

> 来源：`experiments/outputs/plain_discovery_peripheral-trap.md`（与同主题 batch 条目共用）

```markdown
<!-- scenario-slug: peripheral-trap -->
# Peripheral Attention Trap (plain baseline)

**They** route value through corridors **it** ignores while **this** hides behind **that** benign hub traffic. Operators chase **it**, but missing **them** blinds the hunt until sinks absorb what **they** never named.

Alerts pile on flashy nodes yet **those** feeders keep splitting before anyone ties **this** funnel to beneficiaries **it** only hints at.
```

**以下非结构化 LLM 笔记中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_plain_llm`
- [您的评分: ___]

#### 本题元数据（可选）

- 是否熟悉该 AML 概念？ □ 是 □ 否 □ 部分熟悉
- 本题整体难度（1=很容易，5=很难）：[___]
- 备注：

---

### 题目 2 / 15

- **Discovery ID**：`disc-llm-smurfing-pattern`
- **概念主题**：拆分存款模式 (Smurfing Pattern)
- **场景说明**：Smurfing Pattern — sub-threshold deposit structuring across a beneficial-owner network; align with aml-smurfing CTR threshold heuristics
- **源文件**：`experiments/outputs/llm_discovery_smurfing-pattern.md`

#### 臂 A — ADL L2（评分时忽略 YAML 与 ` ```adl:* ` 块）

```markdown
# Smurfing Pattern in Anti-Money Laundering

## Discovery Statement

The Smurfing Pattern describes a structured money laundering technique where large sums of illicit funds are broken into multiple sub-threshold deposits, each deliberately kept below regulatory reporting limits, across numerous accounts or financial institutions, followed by a consolidation transfer that reassembles the fragmented amounts into a single destination account or entity. Detection relies on identifying the characteristic signature of many small deposits clustered in time and geography, followed by a subsequent outbound transfer that aggregates the previously dispersed funds.

## Intuition

The core mechanism of smurfing exploits the gap between individual transaction monitoring thresholds and aggregate behavioral analysis. Each individual deposit appears benign in isolation because the amount falls below the Currency Transaction Report (CTR) threshold or similar regulatory trigger. The pattern becomes visible only when multiple sub-threshold deposits are correlated across accounts sharing common attributes such as geographic proximity, temporal clustering, shared beneficiaries, or linked identity documents. The consolidation transfer serves as the critical second phase, where previously fragmented funds are reunited, often through wire transfers, cashier's checks, or business account movements.

## Related Concepts

- [[Structuring]] — the broader legal and behavioral category encompassing smurfing as a specific operational variant
- [[Layering]] — the subsequent AML phase where consolidated funds are moved through complex transaction chains to obscure origin
- [[Sub-Threshold Deposits]] — the atomic unit of smurfing activity, each deposit individually compliant but collectively suspicious
- [[Consolidation Transfer]] — the reassembly phase that completes the smurfing cycle

```adl:relation
source: "Smurfing Pattern"
relation: isomorphic-to
target: "adl://public/concepts/structuring"
mapping_type: behavioral
confidence: 0.90
```

```adl:relation
source: "Smurfing Pattern"
relation: composes
target: "adl://public/concepts/sub-threshold-deposits"
mapping_type: structural
confidence: 0.95
```

```adl:relation
source: "Smurfing Pattern"
relation: precedes
target: "adl://public/concepts/consolidation-transfer"
mapping_type: temporal
confidence: 0.88
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/cluster/smurfing-2026q1
description: "Cluster of 847 transaction sequences exhibiting sub-threshold deposit patterns across 23 branch locations within 72-hour windows, followed by consolidation transfers averaging 94% of aggregate deposited amounts"
confidence: 0.82
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: vecdb://ceiec-aml/expert-review/smurfing-cases
description: "Senior AML analyst review of 156 flagged smurfing cases confirmed 131 true positives, with common markers including 5-12 sub-threshold deposits per account within rolling 7-day windows and consolidation transfers initiated within 14 days of last deposit"
confidence: 0.88
observed_at: "2026-05-20T00:00:00Z"
```

```adl:evidence
evidence_type: cross_reference
data_ref: vecdb://ceiec-aml/regulatory/fincen-ctr-guidance
description: "FinCEN guidance on structuring detection thresholds and multi-institution deposit correlation patterns, confirming the sub-threshold deposit and consolidation transfer signature as primary smurfing indicators"
confidence: 0.92
observed_at: "2026-04-15T00:00:00Z"
```
```

**以下 ADL 文档正文中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity`
- [您的评分: ___]

#### 臂 B — Fair Plain L2（去掉 ADL 结构块后的同一措辞）

```markdown
# Smurfing Pattern in Anti-Money Laundering

## Discovery Statement

The Smurfing Pattern describes a structured money laundering technique where large sums of illicit funds are broken into multiple sub-threshold deposits, each deliberately kept below regulatory reporting limits, across numerous accounts or financial institutions, followed by a consolidation transfer that reassembles the fragmented amounts into a single destination account or entity. Detection relies on identifying the characteristic signature of many small deposits clustered in time and geography, followed by a subsequent outbound transfer that aggregates the previously dispersed funds.

## Intuition

The core mechanism of smurfing exploits the gap between individual transaction monitoring thresholds and aggregate behavioral analysis. Each individual deposit appears benign in isolation because the amount falls below the Currency Transaction Report (CTR) threshold or similar regulatory trigger. The pattern becomes visible only when multiple sub-threshold deposits are correlated across accounts sharing common attributes such as geographic proximity, temporal clustering, shared beneficiaries, or linked identity documents. The consolidation transfer serves as the critical second phase, where previously fragmented funds are reunited, often through wire transfers, cashier's checks, or business account movements.

## Related Concepts

- [[Structuring]] — the broader legal and behavioral category encompassing smurfing as a specific operational variant
- [[Layering]] — the subsequent AML phase where consolidated funds are moved through complex transaction chains to obscure origin
- [[Sub-Threshold Deposits]] — the atomic unit of smurfing activity, each deposit individually compliant but collectively suspicious
- [[Consolidation Transfer]] — the reassembly phase that completes the smurfing cycle
```

**以下公平纯文本中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_fair_plain`
- [您的评分: ___]

#### 臂 C — Plain LLM 非结构化基线

> 来源：`experiments/outputs/plain_discovery_smurfing-pattern.md`（与同主题 batch 条目共用）

```markdown
<!-- scenario-slug: smurfing-pattern -->
# Smurfing Pattern (plain baseline)

**It** slips under CTR because **they** fan deposits through **them** overnight. **This** structuring looks petty until **it** merges—then **those** corridors reveal whom **they** actually serve.

Shared fingerprints echo across **them**, but **that** linkage stays fuzzy until consolidation proves **they** pooled intent.
```

**以下非结构化 LLM 笔记中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_plain_llm`
- [您的评分: ___]

#### 本题元数据（可选）

- 是否熟悉该 AML 概念？ □ 是 □ 否 □ 部分熟悉
- 本题整体难度（1=很容易，5=很难）：[___]
- 备注：

---

### 题目 3 / 15

- **Discovery ID**：`disc-llm-crypto-mixer`
- **概念主题**：加密货币混币器暴露 (Crypto Mixer Exposure)
- **场景说明**：Crypto Mixer Exposure — wallet activity linked to tumbler contracts with peel-chain off-ramp patterns; align with aml-crypto-mix monitoring signals
- **源文件**：`experiments/outputs/llm_discovery_crypto-mixer.md`

#### 臂 A — ADL L2（评分时忽略 YAML 与 ` ```adl:* ` 块）

```markdown
# Crypto Mixer Exposure

## Discovery Statement

A compositional blend of mixer contract interaction patterns and peel-chain off-ramp sequences produces a distinct exposure signature in blockchain transaction graphs. The signature identifies wallets receiving funds from known mixer contracts and subsequently executing multi-hop peel-chain transfers to fiat off-ramp services. Detection of the combined pattern yields higher confidence scores than either mixer interaction or peel-chain activity alone, because the blend captures the full laundering lifecycle from obfuscation to cash-out.

## Intuition

Traditional AML monitoring treats mixer contract interaction and peel-chain off-ramp as separate risk indicators. The compositional blend mechanism fuses both signals into a single exposure metric. When a wallet first interacts with a mixer contract (e.g., Tornado Cash, Railgun) and then initiates a peel-chain — a sequence of rapid, diminishing-value transfers across freshly generated addresses — the combined behavior represents a higher-order laundering archetype. The blend captures temporal proximity, value decay curves, and destination clustering neither signal reveals independently.

## Related Concepts

- [[Mixer Contract Interaction]] — direct deposit or withdrawal from a known mixer smart contract
- [[Peel-Chain Off-Ramp]] — multi-hop transfer sequence terminating at a fiat exchange deposit address
- [[Laundering Lifecycle]] — end-to-end flow from predicate offense proceeds to clean fiat

```adl:relation
source: "Crypto Mixer Exposure"
relation: compositional-blend-of
target: "adl://public/concepts/mixer-contract-interaction"
mapping_type: semantic
confidence: 0.88
```

```adl:relation
source: "Crypto Mixer Exposure"
relation: compositional-blend-of
target: "adl://public/concepts/peel-chain-off-ramp"
mapping_type: semantic
confidence: 0.85
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/tx-graphs/mixer-exposure-2026q1
description: "Cluster of 1,247 wallet addresses exhibiting combined mixer withdrawal followed by 3+ hop peel-chain to Binance deposit addresses within 72-hour window. Average value decay ratio 0.82 per hop. Cluster centroid distance 0.31 from pure mixer-interaction cluster and 0.28 from pure peel-chain cluster, confirming compositional blend rather than overlap."
confidence: 0.78
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: vecdb://ceiec-aml/expert-reviews/mixer-exposure-validation
description: "Three senior AML analysts independently reviewed 50 flagged cases from the blended cluster. Agreement rate 92% on classification as high-risk laundering activity. Analysts noted the combined pattern as qualitatively distinct from either mixer or peel-chain alone."
confidence: 0.85
observed_at: "2026-05-20T00:00:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: vecdb://ceiec-aml/sim/mixer-peel-synth-2026
description: "Synthetic transaction generator produced 10,000 laundering scenarios combining mixer and peel-chain tactics. Detection model trained on blended features achieved F1 score 0.89 versus 0.71 for mixer-only model and 0.68 for peel-chain-only model on the same synthetic dataset."
confidence: 0.82
observed_at: "2026-05-18T00:00:00Z"
```
```

**以下 ADL 文档正文中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity`
- [您的评分: ___]

#### 臂 B — Fair Plain L2（去掉 ADL 结构块后的同一措辞）

```markdown
# Crypto Mixer Exposure

## Discovery Statement

A compositional blend of mixer contract interaction patterns and peel-chain off-ramp sequences produces a distinct exposure signature in blockchain transaction graphs. The signature identifies wallets receiving funds from known mixer contracts and subsequently executing multi-hop peel-chain transfers to fiat off-ramp services. Detection of the combined pattern yields higher confidence scores than either mixer interaction or peel-chain activity alone, because the blend captures the full laundering lifecycle from obfuscation to cash-out.

## Intuition

Traditional AML monitoring treats mixer contract interaction and peel-chain off-ramp as separate risk indicators. The compositional blend mechanism fuses both signals into a single exposure metric. When a wallet first interacts with a mixer contract (e.g., Tornado Cash, Railgun) and then initiates a peel-chain — a sequence of rapid, diminishing-value transfers across freshly generated addresses — the combined behavior represents a higher-order laundering archetype. The blend captures temporal proximity, value decay curves, and destination clustering neither signal reveals independently.

## Related Concepts

- [[Mixer Contract Interaction]] — direct deposit or withdrawal from a known mixer smart contract
- [[Peel-Chain Off-Ramp]] — multi-hop transfer sequence terminating at a fiat exchange deposit address
- [[Laundering Lifecycle]] — end-to-end flow from predicate offense proceeds to clean fiat
```

**以下公平纯文本中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_fair_plain`
- [您的评分: ___]

#### 臂 C — Plain LLM 非结构化基线

> 来源：`experiments/outputs/plain_discovery_crypto-mixer.md`（与同主题 batch 条目共用）

```markdown
<!-- scenario-slug: crypto-mixer -->
# Crypto Mixer Exposure (plain baseline)

**They** tumble through mixer hops and **it** peels until **they** cash out via stablecoins. **This** wallet cluster talks to contracts **those** explorers label, yet **it** still hides who fronts **them** upstream.

**That** peeling chain drags fiat spikes while **they** launder plausible deniability about **that** intermediary everyone suspects.
```

**以下非结构化 LLM 笔记中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_plain_llm`
- [您的评分: ___]

#### 本题元数据（可选）

- 是否熟悉该 AML 概念？ □ 是 □ 否 □ 部分熟悉
- 本题整体难度（1=很容易，5=很难）：[___]
- 备注：

---

### 题目 4 / 15

- **Discovery ID**：`disc-llm-peripheral-trap-batch001`
- **概念主题**：外围注意力陷阱 (Peripheral Attention Trap)（批次变体 `001`）
- **场景说明**：Peripheral Attention Trap — graph peripheral node concentration while value consolidates toward a hidden sink; align with aml-attention-trap monitoring signals
- **源文件**：`experiments/outputs/llm_discovery_peripheral-trap_batch001.md`

#### 臂 A — ADL L2（评分时忽略 YAML 与 ` ```adl:* ` 块）

```markdown
# Peripheral Attention Trap in AML Transaction Monitoring

## Discovery Statement

In AML transaction monitoring systems, suspicious activity frequently migrates to graph peripheral nodes—entities positioned far from the primary subject of investigation—where detection models allocate disproportionately low attention scores. The peripheral attention trap describes a structural vulnerability in which launderers exploit the diminishing gradient of investigative focus as network distance from a flagged node increases. Sink convergence patterns confirm that illicit funds aggregate at low-attention peripheral nodes, forming hidden reservoirs that evade standard alert thresholds. The trap persists because monitoring architectures typically weight attention by proximity to known suspicious actors, creating a predictable blind zone that adversarial networks systematically exploit.

## Intuition

Standard AML graph analysis applies attention mechanisms that decay with hop distance from flagged entities. Laundering networks, through deliberate layering, push final-stage aggregation nodes beyond the effective attention radius. The peripheral attention trap emerges when the decay function of the monitoring system becomes a map that adversaries can read and navigate. Each additional intermediary node reduces the attention score allocated to the destination, allowing sink nodes to accumulate substantial illicit volume without triggering alerts. The pattern is isomorphic to adversarial evasion in neural network classifiers, where inputs are perturbed just enough to cross decision boundaries.

## Related Concepts

- [[AML Attention Trap]] — foundational concept describing attention-based evasion in financial crime graphs
- [[Graph Peripheral Node]] — entity positioned at high hop distance from flagged suspicious actors
- [[Sink Convergence]] — aggregation pattern where illicit funds concentrate at low-attention terminal nodes
- [[Layering Depth]] — number of intermediary hops used to distance proceeds from predicate offenses
- [[Attention Decay Function]] — mathematical model governing how monitoring focus diminishes with network distance

```adl:relation
source: "Peripheral Attention Trap"
relation: isomorphic-to
target: "adl://public/concepts/aml-attention-trap"
mapping_type: topological
confidence: 0.88
notes: "The peripheral trap is a spatial specialization of the general AML attention trap, constrained to graph periphery where attention decay is steepest."
```

```adl:relation
source: "Peripheral Attention Trap"
relation: analogical-to
target: "adl://public/concepts/adversarial-evasion"
mapping_type: functional
confidence: 0.74
notes: "Laundering networks exploit attention decay in a manner functionally analogous to adversarial perturbation in classifier evasion."
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/graph-peripheral-2026q2
description: "Clustering analysis of 2026 Q2 transaction graphs reveals a statistically significant concentration of high-volume sink nodes at hop distances 4-7 from flagged originators, where mean attention scores drop below 0.15. Cluster centroid features include low degree centrality, high in-degree asymmetry, and temporal burst patterns consistent with layering."
confidence: 0.78
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: vecdb://ceiec-aml/sink-convergence-batch001
description: "Monte Carlo simulation of adversarial routing strategies across 50,000 synthetic laundering graphs confirms that optimal evasion paths consistently route through peripheral nodes where attention scores fall below the alert threshold. Sink convergence rate at peripheral nodes exceeds 82% when layering depth exceeds 5 hops."
confidence: 0.70
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: vecdb://ceiec-aml/analyst-review-batch001
description: "Senior AML analysts at CEIEC reviewed 37 closed investigation files and identified peripheral node aggregation as a recurring evasion pattern in 29 cases. Analysts noted that standard alert rules failed to flag peripheral nodes due to low proximity-weighted risk scores."
confidence: 0.82
observed_at: "2026-05-20T00:00:00Z"
```

```adl:monitoring
signal: graph_peripheral_node_attention
threshold: 0.15
direction: below
alert_class: peripheral_attention_trap
data_ref: data/aml/concepts/aml-attention-trap.md
description: "Trigger alert when any node receiving aggregate inflow above threshold has attention score below 0.15 and hop distance greater than 4 from any flagged entity."
```

```adl:monitoring
signal: sink_convergence_peripheral
threshold: 0.70
direction: above
alert_class: peripheral_attention_trap
data_ref: data/aml/concepts/aml-attention-trap.md
description: "Trigger alert when the proportion of illicit volume converging at peripheral nodes exceeds 70% of total detected layering volume within a 30-day window."
```
```

**以下 ADL 文档正文中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity`
- [您的评分: ___]

#### 臂 B — Fair Plain L2（去掉 ADL 结构块后的同一措辞）

```markdown
# Peripheral Attention Trap in AML Transaction Monitoring

## Discovery Statement

In AML transaction monitoring systems, suspicious activity frequently migrates to graph peripheral nodes—entities positioned far from the primary subject of investigation—where detection models allocate disproportionately low attention scores. The peripheral attention trap describes a structural vulnerability in which launderers exploit the diminishing gradient of investigative focus as network distance from a flagged node increases. Sink convergence patterns confirm that illicit funds aggregate at low-attention peripheral nodes, forming hidden reservoirs that evade standard alert thresholds. The trap persists because monitoring architectures typically weight attention by proximity to known suspicious actors, creating a predictable blind zone that adversarial networks systematically exploit.

## Intuition

Standard AML graph analysis applies attention mechanisms that decay with hop distance from flagged entities. Laundering networks, through deliberate layering, push final-stage aggregation nodes beyond the effective attention radius. The peripheral attention trap emerges when the decay function of the monitoring system becomes a map that adversaries can read and navigate. Each additional intermediary node reduces the attention score allocated to the destination, allowing sink nodes to accumulate substantial illicit volume without triggering alerts. The pattern is isomorphic to adversarial evasion in neural network classifiers, where inputs are perturbed just enough to cross decision boundaries.

## Related Concepts

- [[AML Attention Trap]] — foundational concept describing attention-based evasion in financial crime graphs
- [[Graph Peripheral Node]] — entity positioned at high hop distance from flagged suspicious actors
- [[Sink Convergence]] — aggregation pattern where illicit funds concentrate at low-attention terminal nodes
- [[Layering Depth]] — number of intermediary hops used to distance proceeds from predicate offenses
- [[Attention Decay Function]] — mathematical model governing how monitoring focus diminishes with network distance
```

**以下公平纯文本中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_fair_plain`
- [您的评分: ___]

#### 臂 C — Plain LLM 非结构化基线

> 来源：`experiments/outputs/plain_discovery_peripheral-trap.md`（与同主题 batch 条目共用）

```markdown
<!-- scenario-slug: peripheral-trap -->
# Peripheral Attention Trap (plain baseline)

**They** route value through corridors **it** ignores while **this** hides behind **that** benign hub traffic. Operators chase **it**, but missing **them** blinds the hunt until sinks absorb what **they** never named.

Alerts pile on flashy nodes yet **those** feeders keep splitting before anyone ties **this** funnel to beneficiaries **it** only hints at.
```

**以下非结构化 LLM 笔记中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_plain_llm`
- [您的评分: ___]

#### 本题元数据（可选）

- 是否熟悉该 AML 概念？ □ 是 □ 否 □ 部分熟悉
- 本题整体难度（1=很容易，5=很难）：[___]
- 备注：

---

### 题目 5 / 15

- **Discovery ID**：`disc-llm-smurfing-pattern-batch002`
- **概念主题**：拆分存款模式 (Smurfing Pattern)（批次变体 `002`）
- **场景说明**：Smurfing Pattern — sub-threshold deposit structuring across a beneficial-owner network; align with aml-smurfing CTR threshold heuristics
- **源文件**：`experiments/outputs/llm_discovery_smurfing-pattern_batch002.md`

#### 臂 A — ADL L2（评分时忽略 YAML 与 ` ```adl:* ` 块）

```markdown
# Smurfing Pattern

## Discovery Statement

The Smurfing Pattern describes a money laundering typology where a single beneficial owner orchestrates multiple low-value cash deposits across numerous accounts or branches to evade mandatory reporting thresholds. Each individual deposit remains below the regulatory trigger amount, while the aggregate sum is subsequently consolidated into a single account or transferred to a high-risk jurisdiction. The pattern is characterized by two distinct phases: a distributed sub-threshold deposit phase followed by a consolidation transfer phase.

## Intuition

The Smurfing Pattern operates through a structural decomposition of a large illicit sum into many small, legally unremarkable fragments. Each fragment, or "smurf," is deposited by a different individual (the smurfer) or through a different channel. The key insight is that the regulatory reporting system monitors individual transactions, not the aggregate behavior of a network. By exploiting the gap between individual transaction monitoring and aggregate network behavior, the launderer converts a single high-risk event into a series of low-risk events. The final consolidation transfer reassembles the funds, often moving them offshore or into an investment vehicle, completing the laundering cycle.

## Related Concepts

- [[Structuring]] — the broader legal and operational category of breaking up transactions to avoid reporting
- [[Layering]] — the subsequent phase in the laundering cycle where funds are moved to obscure origin
- [[Mule Account Network]] — the infrastructure of accounts often used to execute the deposit phase

```adl:relation
source: "Smurfing Pattern"
relation: isomorphic-to
target: "adl://public/concepts/structuring"
mapping_type: topological
confidence: 0.90
```

```adl:relation
source: "Smurfing Pattern"
relation: compositional-with
target: "adl://public/concepts/mule-account-network"
mapping_type: functional
confidence: 0.75
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/cluster/smurfing-batch002
description: "Cluster of 147 transaction sequences exhibiting sub-threshold deposit patterns followed by consolidation transfers within a 72-hour window. Sequences share common beneficiary accounts and originate from geographically dispersed branches."
confidence: 0.82
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: vecdb://ceiec-aml/expert-review/smurfing-batch002
description: "Senior AML analyst confirmed the cluster aligns with known smurfing typology. Analyst noted the consolidation transfer amounts consistently fall between 85% and 95% of the aggregate sub-threshold deposits, a signature of the pattern."
confidence: 0.88
observed_at: "2026-05-23T00:00:00Z"
```

```adl:monitoring_signal
signal_id: ms-sub-threshold-deposits
description: "Multiple cash deposits below the CNY 50,000 reporting threshold originating from the same geographic region within a rolling 48-hour window, targeting accounts with no prior transaction history."
data_ref: data/aml/concepts/aml-smurfing.md
threshold: 5
confidence: 0.80
```

```adl:monitoring_signal
signal_id: ms-consolidation-transfer
description: "A single outbound transfer from an account that received multiple sub-threshold deposits, where the transfer amount exceeds 80% of the aggregate deposit sum within the preceding 72 hours."
data_ref: data/aml/concepts/aml-smurfing.md
threshold: 1
confidence: 0.85
```
```

**以下 ADL 文档正文中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity`
- [您的评分: ___]

#### 臂 B — Fair Plain L2（去掉 ADL 结构块后的同一措辞）

```markdown
# Smurfing Pattern

## Discovery Statement

The Smurfing Pattern describes a money laundering typology where a single beneficial owner orchestrates multiple low-value cash deposits across numerous accounts or branches to evade mandatory reporting thresholds. Each individual deposit remains below the regulatory trigger amount, while the aggregate sum is subsequently consolidated into a single account or transferred to a high-risk jurisdiction. The pattern is characterized by two distinct phases: a distributed sub-threshold deposit phase followed by a consolidation transfer phase.

## Intuition

The Smurfing Pattern operates through a structural decomposition of a large illicit sum into many small, legally unremarkable fragments. Each fragment, or "smurf," is deposited by a different individual (the smurfer) or through a different channel. The key insight is that the regulatory reporting system monitors individual transactions, not the aggregate behavior of a network. By exploiting the gap between individual transaction monitoring and aggregate network behavior, the launderer converts a single high-risk event into a series of low-risk events. The final consolidation transfer reassembles the funds, often moving them offshore or into an investment vehicle, completing the laundering cycle.

## Related Concepts

- [[Structuring]] — the broader legal and operational category of breaking up transactions to avoid reporting
- [[Layering]] — the subsequent phase in the laundering cycle where funds are moved to obscure origin
- [[Mule Account Network]] — the infrastructure of accounts often used to execute the deposit phase
```

**以下公平纯文本中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_fair_plain`
- [您的评分: ___]

#### 臂 C — Plain LLM 非结构化基线

> 来源：`experiments/outputs/plain_discovery_smurfing-pattern.md`（与同主题 batch 条目共用）

```markdown
<!-- scenario-slug: smurfing-pattern -->
# Smurfing Pattern (plain baseline)

**It** slips under CTR because **they** fan deposits through **them** overnight. **This** structuring looks petty until **it** merges—then **those** corridors reveal whom **they** actually serve.

Shared fingerprints echo across **them**, but **that** linkage stays fuzzy until consolidation proves **they** pooled intent.
```

**以下非结构化 LLM 笔记中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_plain_llm`
- [您的评分: ___]

#### 本题元数据（可选）

- 是否熟悉该 AML 概念？ □ 是 □ 否 □ 部分熟悉
- 本题整体难度（1=很容易，5=很难）：[___]
- 备注：

---

### 题目 6 / 15

- **Discovery ID**：`disc-llm-crypto-mixer-batch003`
- **概念主题**：加密货币混币器暴露 (Crypto Mixer Exposure)（批次变体 `003`）
- **场景说明**：Crypto Mixer Exposure — wallet activity linked to tumbler contracts with peel-chain off-ramp patterns; align with aml-crypto-mix monitoring signals
- **源文件**：`experiments/outputs/llm_discovery_crypto-mixer_batch003.md`

#### 臂 A — ADL L2（评分时忽略 YAML 与 ` ```adl:* ` 块）

```markdown
# Crypto Mixer Exposure

## Discovery Statement

Crypto mixer exposure represents a compositional blend of peel-chain off-ramp behavior and mixer contract interaction patterns. When a wallet address receives funds from a known mixer contract and subsequently initiates a peel-chain sequence across multiple intermediary wallets before off-ramping to a fiat gateway, the combined signal produces a higher-risk AML indicator than either pattern alone. The exposure metric quantifies the proportion of inbound transaction volume traceable to mixer contracts within a rolling 72-hour window, weighted by the depth of subsequent peel-chain hops.

## Intuition

The concept of "mixer exposure" arises from the observation that traditional AML rules treat mixer contract interactions and peel-chain off-ramp structures as independent risk factors. In practice, threat actors compose both techniques into a single laundering pipeline: funds enter through a mixer contract to obscure origin, then propagate through a peel-chain to fragment amounts and evade threshold-based detection. The compositional blend captures the synergistic risk amplification when both patterns co-occur on the same entity graph. Monitoring systems must therefore fuse mixer taint scores with peel-chain hop counts rather than evaluating each signal in isolation.

## Related Concepts

- [[Peel-Chain Off-Ramp]] — sequential fund fragmentation across intermediary wallets before fiat conversion
- [[Mixer Contract Interaction]] — direct or indirect exposure to smart contracts implementing CoinJoin, Tornado Cash, or similar protocols
- [[Taint Propagation]] — forward-tracing of mixer-origin funds through the transaction graph

```adl:relation
source: "Crypto Mixer Exposure"
relation: compositional-blend-of
target: "adl://public/concepts/aml-crypto-mix"
mapping_type: semantic
confidence: 0.88
```

```adl:relation
source: "Crypto Mixer Exposure"
relation: extends
target: "adl://public/concepts/peel-chain-off-ramp"
mapping_type: structural
confidence: 0.80
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/cluster/mixer-exposure-2026q2
description: "Cluster of 1,247 wallet entities exhibiting combined mixer contract inbound volume exceeding 40% of total inflows with peel-chain hop depth ≥ 3 within 72 hours. Cluster centroid aligns with known laundering typologies from FinCEN advisories."
confidence: 0.75
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: vecdb://ceiec-aml/expert-review/mixer-exposure-validation
description: "Senior AML analyst confirmed that 89% of flagged entities in the cluster correspond to SAR-filed cases involving virtual asset service provider interactions. Analyst noted peel-chain depth ≥ 3 as a critical threshold for operational laundering viability."
confidence: 0.82
observed_at: "2026-05-20T00:00:00Z"
```
```

**以下 ADL 文档正文中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity`
- [您的评分: ___]

#### 臂 B — Fair Plain L2（去掉 ADL 结构块后的同一措辞）

```markdown
# Crypto Mixer Exposure

## Discovery Statement

Crypto mixer exposure represents a compositional blend of peel-chain off-ramp behavior and mixer contract interaction patterns. When a wallet address receives funds from a known mixer contract and subsequently initiates a peel-chain sequence across multiple intermediary wallets before off-ramping to a fiat gateway, the combined signal produces a higher-risk AML indicator than either pattern alone. The exposure metric quantifies the proportion of inbound transaction volume traceable to mixer contracts within a rolling 72-hour window, weighted by the depth of subsequent peel-chain hops.

## Intuition

The concept of "mixer exposure" arises from the observation that traditional AML rules treat mixer contract interactions and peel-chain off-ramp structures as independent risk factors. In practice, threat actors compose both techniques into a single laundering pipeline: funds enter through a mixer contract to obscure origin, then propagate through a peel-chain to fragment amounts and evade threshold-based detection. The compositional blend captures the synergistic risk amplification when both patterns co-occur on the same entity graph. Monitoring systems must therefore fuse mixer taint scores with peel-chain hop counts rather than evaluating each signal in isolation.

## Related Concepts

- [[Peel-Chain Off-Ramp]] — sequential fund fragmentation across intermediary wallets before fiat conversion
- [[Mixer Contract Interaction]] — direct or indirect exposure to smart contracts implementing CoinJoin, Tornado Cash, or similar protocols
- [[Taint Propagation]] — forward-tracing of mixer-origin funds through the transaction graph
```

**以下公平纯文本中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_fair_plain`
- [您的评分: ___]

#### 臂 C — Plain LLM 非结构化基线

> 来源：`experiments/outputs/plain_discovery_crypto-mixer.md`（与同主题 batch 条目共用）

```markdown
<!-- scenario-slug: crypto-mixer -->
# Crypto Mixer Exposure (plain baseline)

**They** tumble through mixer hops and **it** peels until **they** cash out via stablecoins. **This** wallet cluster talks to contracts **those** explorers label, yet **it** still hides who fronts **them** upstream.

**That** peeling chain drags fiat spikes while **they** launder plausible deniability about **that** intermediary everyone suspects.
```

**以下非结构化 LLM 笔记中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_plain_llm`
- [您的评分: ___]

#### 本题元数据（可选）

- 是否熟悉该 AML 概念？ □ 是 □ 否 □ 部分熟悉
- 本题整体难度（1=很容易，5=很难）：[___]
- 备注：

---

### 题目 7 / 15

- **Discovery ID**：`disc-llm-peripheral-trap-batch004`
- **概念主题**：外围注意力陷阱 (Peripheral Attention Trap)（批次变体 `004`）
- **场景说明**：Peripheral Attention Trap — graph peripheral node concentration while value consolidates toward a hidden sink; align with aml-attention-trap monitoring signals
- **源文件**：`experiments/outputs/llm_discovery_peripheral-trap_batch004.md`

#### 臂 A — ADL L2（评分时忽略 YAML 与 ` ```adl:* ` 块）

```markdown
# Peripheral Attention Trap

## Discovery Statement

In anti-money laundering graph analysis, compliance monitoring systems exhibit a systematic bias toward high-degree hub nodes while neglecting peripheral nodes that form low-visibility sink convergence patterns. Peripheral Attention Trap describes the emergent phenomenon where launderers exploit the attention gradient by routing illicit flows through graph periphery nodes—entities with few connections but strategically positioned to aggregate and redirect funds toward final sink accounts. The monitoring system's attention allocation mechanism fails to detect peripheral convergence patterns because signal strength decays with graph distance from central hubs, creating a blind zone where sink convergence proceeds undetected until threshold-crossing events trigger retrospective analysis.

## Intuition

The Peripheral Attention Trap emerges from the interaction between two structural properties of AML transaction graphs: (1) attention allocation follows a power-law distribution concentrated on hub nodes, and (2) sink convergence operates through peripheral node aggregation that remains below detection thresholds until critical mass accumulates. Laundering networks exploit the gap between structural properties by constructing peripheral routing paths that individually appear benign but collectively funnel illicit funds toward designated sink accounts. The trap mechanism relies on the monitoring system's implicit assumption that suspicious activity correlates with node centrality—an assumption that fails when adversaries deliberately construct low-centrality convergence architectures.

## Related Concepts

- [[AML Attention Trap]] — foundational concept describing attention-based evasion in compliance systems
- [[Graph Peripheral Nodes]] — structural category for low-degree nodes in transaction networks
- [[Sink Convergence Pattern]] — flow aggregation pattern where multiple source paths terminate at common destination
- [[Attention Gradient Exploitation]] — adversarial strategy leveraging monitoring system's attention decay function

```adl:relation
source: "Peripheral Attention Trap"
relation: isomorphic-to
target: "adl://public/concepts/aml-attention-trap"
mapping_type: topological
confidence: 0.85
notes: "Peripheral Attention Trap represents a specific instantiation of the general AML Attention Trap mechanism, with structural isomorphism in the attention allocation failure but distinct topology in the peripheral node exploitation pathway."
```

```adl:relation
source: "Peripheral Attention Trap"
relation: compositional-with
target: "adl://public/concepts/graph-peripheral-nodes"
mapping_type: structural
confidence: 0.78
notes: "The trap mechanism depends on the existence of peripheral nodes as structural substrate; without peripheral node topology, the convergence pattern cannot form."
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/graph-peripheral-nodes-2026q2
description: "Vector cluster analysis of Q2 2026 transaction graphs reveals 847 peripheral nodes exhibiting sink convergence signatures. Cluster centroid shows 3.2 average degree with 0.89 convergence coefficient toward designated sink accounts. Nodes in cluster were flagged retrospectively after threshold-crossing events in 23 cases."
confidence: 0.75
observed_at: "2026-05-15T00:00:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: vecdb://ceiec-aml/sink-convergence-batch004
description: "Batch 004 simulation run on synthetic AML graphs demonstrates Peripheral Attention Trap formation under standard monitoring parameters. Simulation generated 1,247 peripheral convergence paths with mean detection delay of 14.3 days. Sink accounts received aggregated flows from 8-15 peripheral nodes before triggering retrospective alerts."
confidence: 0.82
observed_at: "2026-05-20T00:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: vecdb://ceiec-aml/expert-review-batch004
description: "Senior AML analyst review of batch 004 findings confirms peripheral convergence pattern matches observed evasion techniques in 3 active investigations. Expert assessment indicates launderers deliberately construct low-centrality routing paths to exploit monitoring system's attention gradient."
confidence: 0.68
observed_at: "2026-05-22T00:00:00Z"
```
```

**以下 ADL 文档正文中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity`
- [您的评分: ___]

#### 臂 B — Fair Plain L2（去掉 ADL 结构块后的同一措辞）

```markdown
# Peripheral Attention Trap

## Discovery Statement

In anti-money laundering graph analysis, compliance monitoring systems exhibit a systematic bias toward high-degree hub nodes while neglecting peripheral nodes that form low-visibility sink convergence patterns. Peripheral Attention Trap describes the emergent phenomenon where launderers exploit the attention gradient by routing illicit flows through graph periphery nodes—entities with few connections but strategically positioned to aggregate and redirect funds toward final sink accounts. The monitoring system's attention allocation mechanism fails to detect peripheral convergence patterns because signal strength decays with graph distance from central hubs, creating a blind zone where sink convergence proceeds undetected until threshold-crossing events trigger retrospective analysis.

## Intuition

The Peripheral Attention Trap emerges from the interaction between two structural properties of AML transaction graphs: (1) attention allocation follows a power-law distribution concentrated on hub nodes, and (2) sink convergence operates through peripheral node aggregation that remains below detection thresholds until critical mass accumulates. Laundering networks exploit the gap between structural properties by constructing peripheral routing paths that individually appear benign but collectively funnel illicit funds toward designated sink accounts. The trap mechanism relies on the monitoring system's implicit assumption that suspicious activity correlates with node centrality—an assumption that fails when adversaries deliberately construct low-centrality convergence architectures.

## Related Concepts

- [[AML Attention Trap]] — foundational concept describing attention-based evasion in compliance systems
- [[Graph Peripheral Nodes]] — structural category for low-degree nodes in transaction networks
- [[Sink Convergence Pattern]] — flow aggregation pattern where multiple source paths terminate at common destination
- [[Attention Gradient Exploitation]] — adversarial strategy leveraging monitoring system's attention decay function
```

**以下公平纯文本中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_fair_plain`
- [您的评分: ___]

#### 臂 C — Plain LLM 非结构化基线

> 来源：`experiments/outputs/plain_discovery_peripheral-trap.md`（与同主题 batch 条目共用）

```markdown
<!-- scenario-slug: peripheral-trap -->
# Peripheral Attention Trap (plain baseline)

**They** route value through corridors **it** ignores while **this** hides behind **that** benign hub traffic. Operators chase **it**, but missing **them** blinds the hunt until sinks absorb what **they** never named.

Alerts pile on flashy nodes yet **those** feeders keep splitting before anyone ties **this** funnel to beneficiaries **it** only hints at.
```

**以下非结构化 LLM 笔记中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_plain_llm`
- [您的评分: ___]

#### 本题元数据（可选）

- 是否熟悉该 AML 概念？ □ 是 □ 否 □ 部分熟悉
- 本题整体难度（1=很容易，5=很难）：[___]
- 备注：

---

### 题目 8 / 15

- **Discovery ID**：`disc-llm-smurfing-pattern-batch005`
- **概念主题**：拆分存款模式 (Smurfing Pattern)（批次变体 `005`）
- **场景说明**：Smurfing Pattern — sub-threshold deposit structuring across a beneficial-owner network; align with aml-smurfing CTR threshold heuristics
- **源文件**：`experiments/outputs/llm_discovery_smurfing-pattern_batch005.md`

#### 臂 A — ADL L2（评分时忽略 YAML 与 ` ```adl:* ` 块）

```markdown
# Smurfing Pattern

## Discovery Statement

The smurfing pattern represents a structuring technique where illicit funds are broken into multiple sub-threshold deposits across numerous accounts or locations to evade regulatory reporting triggers. Each individual transaction remains below the mandatory reporting limit, yet the aggregate flow converges into a consolidation transfer that reassembles the fragmented capital. Detection relies on identifying the temporal clustering of small deposits followed by a single outbound movement that matches the sum of prior inflows.

## Intuition

The core mechanism involves a deliberate decomposition of a large cash amount into many small pieces, each piece deposited by a different actor (a "smurf") at a different branch or ATM. The pattern is isomorphic to a fan-in topology in graph theory: multiple source nodes feed into a single sink node. The key observable signature is the ratio between the number of sub-threshold deposits and the subsequent consolidation transfer amount. When the ratio approaches unity, the probability of smurfing increases sharply.

## Related Concepts

- [[Structuring]] — the broader legal category encompassing smurfing and other threshold-avoidance tactics
- [[Layering]] — a subsequent AML stage where consolidated funds are moved through complex transaction chains
- [[Fan-in Topology]] — the graph-theoretic structure underlying the smurfing pattern

```adl:relation
source: "Smurfing Pattern"
relation: isomorphic-to
target: "adl://public/concepts/fan-in-topology"
mapping_type: topological
confidence: 0.82
```

```adl:relation
source: "Smurfing Pattern"
relation: part-of
target: "adl://public/concepts/structuring"
mapping_type: semantic
confidence: 0.91
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/cluster/smurfing-2026q2
description: "Cluster of 1,247 transaction sequences exhibiting sub-threshold deposits (below ¥50,000) across 3+ distinct accounts within a 72-hour window, followed by a consolidation transfer exceeding the sum of prior deposits by less than 2%. Cluster centroid distance from nearest non-smurfing cluster: 0.34 cosine."
confidence: 0.78
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: vecdb://ceiec-aml/expert-review/smurfing-batch005
description: "Senior AML analyst confirmed 89% of flagged sequences match known smurfing typology. Analyst noted that consolidation transfers frequently route through intermediary e-wallet accounts before reaching the final beneficiary."
confidence: 0.85
observed_at: "2026-05-20T00:00:00Z"
```

```adl:evidence
evidence_type: cross_reference
data_ref: data/aml/concepts/aml-smurfing.md
description: "Monitoring signals aligned with canonical smurfing indicators: sub-threshold deposits below regulatory reporting limit, multiple depositors per consolidation target, temporal clustering within short windows, and consolidation transfer amount matching aggregate deposits."
confidence: 0.90
observed_at: "2026-05-23T00:00:00Z"
```
```

**以下 ADL 文档正文中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity`
- [您的评分: ___]

#### 臂 B — Fair Plain L2（去掉 ADL 结构块后的同一措辞）

```markdown
# Smurfing Pattern

## Discovery Statement

The smurfing pattern represents a structuring technique where illicit funds are broken into multiple sub-threshold deposits across numerous accounts or locations to evade regulatory reporting triggers. Each individual transaction remains below the mandatory reporting limit, yet the aggregate flow converges into a consolidation transfer that reassembles the fragmented capital. Detection relies on identifying the temporal clustering of small deposits followed by a single outbound movement that matches the sum of prior inflows.

## Intuition

The core mechanism involves a deliberate decomposition of a large cash amount into many small pieces, each piece deposited by a different actor (a "smurf") at a different branch or ATM. The pattern is isomorphic to a fan-in topology in graph theory: multiple source nodes feed into a single sink node. The key observable signature is the ratio between the number of sub-threshold deposits and the subsequent consolidation transfer amount. When the ratio approaches unity, the probability of smurfing increases sharply.

## Related Concepts

- [[Structuring]] — the broader legal category encompassing smurfing and other threshold-avoidance tactics
- [[Layering]] — a subsequent AML stage where consolidated funds are moved through complex transaction chains
- [[Fan-in Topology]] — the graph-theoretic structure underlying the smurfing pattern
```

**以下公平纯文本中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_fair_plain`
- [您的评分: ___]

#### 臂 C — Plain LLM 非结构化基线

> 来源：`experiments/outputs/plain_discovery_smurfing-pattern.md`（与同主题 batch 条目共用）

```markdown
<!-- scenario-slug: smurfing-pattern -->
# Smurfing Pattern (plain baseline)

**It** slips under CTR because **they** fan deposits through **them** overnight. **This** structuring looks petty until **it** merges—then **those** corridors reveal whom **they** actually serve.

Shared fingerprints echo across **them**, but **that** linkage stays fuzzy until consolidation proves **they** pooled intent.
```

**以下非结构化 LLM 笔记中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_plain_llm`
- [您的评分: ___]

#### 本题元数据（可选）

- 是否熟悉该 AML 概念？ □ 是 □ 否 □ 部分熟悉
- 本题整体难度（1=很容易，5=很难）：[___]
- 备注：

---

### 题目 9 / 15

- **Discovery ID**：`disc-llm-crypto-mixer-batch006`
- **概念主题**：加密货币混币器暴露 (Crypto Mixer Exposure)（批次变体 `006`）
- **场景说明**：Crypto Mixer Exposure — wallet activity linked to tumbler contracts with peel-chain off-ramp patterns; align with aml-crypto-mix monitoring signals
- **源文件**：`experiments/outputs/llm_discovery_crypto-mixer_batch006.md`

#### 臂 A — ADL L2（评分时忽略 YAML 与 ` ```adl:* ` 块）

```markdown
# Crypto Mixer Exposure

## Discovery Statement

A compositional blend of mixer contract interaction patterns and peel-chain off-ramp structures reveals a latent exposure metric for crypto assets entering regulated fiat gateways. The metric quantifies the number of intermediary hops between a mixer contract withdrawal and the final off-ramp deposit, weighted by the historical taint score of the mixer pool. Higher exposure scores correlate with elevated probability of structuring behavior and layering intent within the AML typology.

## Intuition

The concept "Crypto Mixer Exposure" arises from blending two distinct monitoring signals: (1) direct mixer contract withdrawals, where funds exit a known mixing pool, and (2) peel-chain off-ramp sequences, where funds fragment across multiple wallets before reaching a fiat exchange. The blend produces a composite risk indicator that neither signal alone captures. A single mixer withdrawal followed by an immediate off-ramp carries different risk than a withdrawal that traverses a five-hop peel chain. The exposure metric encodes path length, intermediary wallet reuse, and temporal clustering as continuous features.

## Related Concepts

- [[Mixer Contract Interaction]] — direct deposit or withdrawal from a known mixing pool
- [[Peel Chain Off-Ramp]] — sequential fund transfers terminating at a fiat gateway
- [[Structuring Behavior]] — deliberate fragmentation to avoid reporting thresholds
- [[Layering Intent]] — use of intermediary hops to obscure beneficial ownership

```adl:relation
source: "Crypto Mixer Exposure"
relation: compositional-blend-of
target: "adl://public/concepts/aml-crypto-mix"
mapping_type: semantic
confidence: 0.78
```

```adl:relation
source: "Crypto Mixer Exposure"
relation: extends
target: "adl://public/concepts/peel-chain-offramp"
mapping_type: topological
confidence: 0.70
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/cluster/mixer-exposure-2026q2
description: "Cluster of 1,247 transaction sequences exhibiting both mixer withdrawal and peel-chain off-ramp signatures within a 72-hour window. Cluster centroid features include mean hop count 4.3, median mixer taint score 0.61, and temporal clustering coefficient 0.84."
confidence: 0.72
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: empirical_observation
data_ref: vecdb://ceiec-aml/tx-graph/peel-chain-offramp
description: "Manual review of 89 flagged sequences confirmed 73 cases (82%) where mixer exposure score exceeded 0.5 correlated with subsequent SAR filings for layering. Review conducted by CEIEC AML analysts during Q2 2026 batch processing."
confidence: 0.80
observed_at: "2026-05-23T00:00:00Z"
```
```

**以下 ADL 文档正文中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity`
- [您的评分: ___]

#### 臂 B — Fair Plain L2（去掉 ADL 结构块后的同一措辞）

```markdown
# Crypto Mixer Exposure

## Discovery Statement

A compositional blend of mixer contract interaction patterns and peel-chain off-ramp structures reveals a latent exposure metric for crypto assets entering regulated fiat gateways. The metric quantifies the number of intermediary hops between a mixer contract withdrawal and the final off-ramp deposit, weighted by the historical taint score of the mixer pool. Higher exposure scores correlate with elevated probability of structuring behavior and layering intent within the AML typology.

## Intuition

The concept "Crypto Mixer Exposure" arises from blending two distinct monitoring signals: (1) direct mixer contract withdrawals, where funds exit a known mixing pool, and (2) peel-chain off-ramp sequences, where funds fragment across multiple wallets before reaching a fiat exchange. The blend produces a composite risk indicator that neither signal alone captures. A single mixer withdrawal followed by an immediate off-ramp carries different risk than a withdrawal that traverses a five-hop peel chain. The exposure metric encodes path length, intermediary wallet reuse, and temporal clustering as continuous features.

## Related Concepts

- [[Mixer Contract Interaction]] — direct deposit or withdrawal from a known mixing pool
- [[Peel Chain Off-Ramp]] — sequential fund transfers terminating at a fiat gateway
- [[Structuring Behavior]] — deliberate fragmentation to avoid reporting thresholds
- [[Layering Intent]] — use of intermediary hops to obscure beneficial ownership
```

**以下公平纯文本中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_fair_plain`
- [您的评分: ___]

#### 臂 C — Plain LLM 非结构化基线

> 来源：`experiments/outputs/plain_discovery_crypto-mixer.md`（与同主题 batch 条目共用）

```markdown
<!-- scenario-slug: crypto-mixer -->
# Crypto Mixer Exposure (plain baseline)

**They** tumble through mixer hops and **it** peels until **they** cash out via stablecoins. **This** wallet cluster talks to contracts **those** explorers label, yet **it** still hides who fronts **them** upstream.

**That** peeling chain drags fiat spikes while **they** launder plausible deniability about **that** intermediary everyone suspects.
```

**以下非结构化 LLM 笔记中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_plain_llm`
- [您的评分: ___]

#### 本题元数据（可选）

- 是否熟悉该 AML 概念？ □ 是 □ 否 □ 部分熟悉
- 本题整体难度（1=很容易，5=很难）：[___]
- 备注：

---

### 题目 10 / 15

- **Discovery ID**：`disc-llm-peripheral-trap-batch007`
- **概念主题**：外围注意力陷阱 (Peripheral Attention Trap)（批次变体 `007`）
- **场景说明**：Peripheral Attention Trap — graph peripheral node concentration while value consolidates toward a hidden sink; align with aml-attention-trap monitoring signals
- **源文件**：`experiments/outputs/llm_discovery_peripheral-trap_batch007.md`

#### 臂 A — ADL L2（评分时忽略 YAML 与 ` ```adl:* ` 块）

```markdown
# Peripheral Attention Trap

## Discovery Statement

In anti-money laundering transaction monitoring, a systematic bias emerges where compliance resources concentrate on high-degree hub nodes within transaction graphs, while peripheral nodes with low connectivity but high sink-convergence ratios evade scrutiny. The peripheral attention trap describes the condition where launderers exploit the monitoring system's inherent focus on central nodes by routing illicit funds through a constellation of seemingly insignificant peripheral accounts that ultimately converge into a single sink entity. Detection algorithms trained on hub-centric patterns consistently fail to flag peripheral convergence structures, creating a blind spot that sophisticated laundering networks actively exploit.

## Intuition

The peripheral attention trap arises from a fundamental mismatch between graph-theoretic centrality measures and actual laundering topology. Standard AML monitoring systems assign attention weights proportional to node degree, betweenness centrality, and transaction volume. Peripheral nodes—nodes with degree below the monitoring threshold—receive minimal analytical attention. However, when multiple peripheral nodes exhibit coordinated sink convergence behavior, the aggregate flow into the destination entity can represent substantial illicit value transfer. The trap mechanism relies on the monitoring system treating each peripheral node independently rather than recognizing the emergent collective pattern of distributed-to-convergent flow.

## Related Concepts

- [[AML Attention Trap]] — foundational concept describing resource allocation bias in transaction monitoring
- [[Sink Convergence Pattern]] — graph topology where multiple source nodes route to single destination
- [[Peripheral Node Exploitation]] — adversarial strategy leveraging low-connectivity accounts
- [[Graph Centrality Blind Spot]] — systematic failure mode in hub-centric monitoring approaches

```adl:relation
source: "Peripheral Attention Trap"
relation: isomorphic-to
target: "adl://public/concepts/aml-attention-trap"
mapping_type: topological
confidence: 0.88
notes: "Peripheral trap represents a specific instantiation of the general attention trap mechanism, where the attention gradient follows graph centrality rather than transaction volume alone."
```

```adl:relation
source: "Peripheral Attention Trap"
relation: compositional-with
target: "adl://public/concepts/sink-convergence-pattern"
mapping_type: structural
confidence: 0.82
notes: "Sink convergence provides the structural substrate; peripheral attention provides the exploitation vector."
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/clusters/batch007-peripheral-sink
description: "Cluster analysis of batch007 transaction graphs reveals 23 peripheral node groups exhibiting sink convergence ratios above 0.85, with average node degree of 2.3—well below the monitoring threshold of degree 5. Total aggregated flow through peripheral structures represents 340M CNY in unmonitored transfers."
confidence: 0.78
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: vecdb://ceiec-aml/simulations/peripheral-trap-scenario
description: "Agent-based simulation of laundering strategies demonstrates 73% evasion rate when adversaries route funds through peripheral nodes with degree ≤ 3, compared to 12% evasion rate for hub-based routing. Simulation parameters derived from historical CEIEC case data."
confidence: 0.81
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: vecdb://ceiec-aml/expert-reviews/peripheral-pattern-validation
description: "Senior compliance officer review confirms that 8 of 12 flagged peripheral convergence structures in batch007 correspond to known laundering typologies previously undetected by standard monitoring. Expert assessment validates the peripheral attention trap as operationally significant."
confidence: 0.75
observed_at: "2026-05-23T00:00:00Z"
```
```

**以下 ADL 文档正文中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity`
- [您的评分: ___]

#### 臂 B — Fair Plain L2（去掉 ADL 结构块后的同一措辞）

```markdown
# Peripheral Attention Trap

## Discovery Statement

In anti-money laundering transaction monitoring, a systematic bias emerges where compliance resources concentrate on high-degree hub nodes within transaction graphs, while peripheral nodes with low connectivity but high sink-convergence ratios evade scrutiny. The peripheral attention trap describes the condition where launderers exploit the monitoring system's inherent focus on central nodes by routing illicit funds through a constellation of seemingly insignificant peripheral accounts that ultimately converge into a single sink entity. Detection algorithms trained on hub-centric patterns consistently fail to flag peripheral convergence structures, creating a blind spot that sophisticated laundering networks actively exploit.

## Intuition

The peripheral attention trap arises from a fundamental mismatch between graph-theoretic centrality measures and actual laundering topology. Standard AML monitoring systems assign attention weights proportional to node degree, betweenness centrality, and transaction volume. Peripheral nodes—nodes with degree below the monitoring threshold—receive minimal analytical attention. However, when multiple peripheral nodes exhibit coordinated sink convergence behavior, the aggregate flow into the destination entity can represent substantial illicit value transfer. The trap mechanism relies on the monitoring system treating each peripheral node independently rather than recognizing the emergent collective pattern of distributed-to-convergent flow.

## Related Concepts

- [[AML Attention Trap]] — foundational concept describing resource allocation bias in transaction monitoring
- [[Sink Convergence Pattern]] — graph topology where multiple source nodes route to single destination
- [[Peripheral Node Exploitation]] — adversarial strategy leveraging low-connectivity accounts
- [[Graph Centrality Blind Spot]] — systematic failure mode in hub-centric monitoring approaches
```

**以下公平纯文本中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_fair_plain`
- [您的评分: ___]

#### 臂 C — Plain LLM 非结构化基线

> 来源：`experiments/outputs/plain_discovery_peripheral-trap.md`（与同主题 batch 条目共用）

```markdown
<!-- scenario-slug: peripheral-trap -->
# Peripheral Attention Trap (plain baseline)

**They** route value through corridors **it** ignores while **this** hides behind **that** benign hub traffic. Operators chase **it**, but missing **them** blinds the hunt until sinks absorb what **they** never named.

Alerts pile on flashy nodes yet **those** feeders keep splitting before anyone ties **this** funnel to beneficiaries **it** only hints at.
```

**以下非结构化 LLM 笔记中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_plain_llm`
- [您的评分: ___]

#### 本题元数据（可选）

- 是否熟悉该 AML 概念？ □ 是 □ 否 □ 部分熟悉
- 本题整体难度（1=很容易，5=很难）：[___]
- 备注：

---

### 题目 11 / 15

- **Discovery ID**：`disc-llm-smurfing-pattern-batch008`
- **概念主题**：拆分存款模式 (Smurfing Pattern)（批次变体 `008`）
- **场景说明**：Smurfing Pattern — sub-threshold deposit structuring across a beneficial-owner network; align with aml-smurfing CTR threshold heuristics
- **源文件**：`experiments/outputs/llm_discovery_smurfing-pattern_batch008.md`

#### 臂 A — ADL L2（评分时忽略 YAML 与 ` ```adl:* ` 块）

```markdown
# Smurfing Pattern

## Discovery Statement

The Smurfing Pattern describes a money laundering typology where large sums of illicit funds are broken into numerous small, sub-threshold cash deposits—often across multiple accounts, branches, or financial institutions—to evade mandatory reporting triggers. After the fragmented deposits settle, a consolidation transfer moves the aggregated funds toward a destination account or layering vehicle. The structural signature consists of a fan-in topology of low-value inflows followed by a single or few high-value outflows, with temporal clustering just below regulatory thresholds.

## Intuition

The core mechanism exploits the gap between individual transaction monitoring rules and aggregate behavioral analysis. Each individual deposit appears benign because the amount falls below the Currency Transaction Report (CTR) threshold or other alert triggers. The pattern becomes visible only when the system correlates multiple deposits across related accounts or time windows. The isomorphic mapping connects the Smurfing Pattern to a general "fragment-and-reassemble" topology found in network flow problems: a source node distributes flow across many parallel low-capacity edges, then a sink node collects the recombined flow through a high-capacity edge.

## Related Concepts

- [[Structuring]] — closely related synonym used in US regulatory context; Smurfing emphasizes the use of multiple human couriers ("smurfs")
- [[Layering]] — subsequent stage where consolidated funds undergo further obfuscation
- [[Threshold Avoidance]] — the behavioral driver that keeps individual transactions below reporting limits
- [[Fan-in Topology]] — abstract network shape describing many-to-one flow convergence

```adl:relation
source: "Smurfing Pattern"
relation: isomorphic-to
target: "adl://public/concepts/structuring"
mapping_type: topological
confidence: 0.90
```

```adl:relation
source: "Smurfing Pattern"
relation: compositional-with
target: "adl://public/concepts/layering"
mapping_type: causal
confidence: 0.75
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/cluster/smurfing-batch008
description: "Cluster of 1,247 transaction sequences exhibiting sub-threshold deposits across 3+ accounts within 48-hour windows, followed by consolidation transfers exceeding individual deposit magnitudes by 10x–50x. Cluster centroid aligns with known smurfing case labels from SAR filings."
confidence: 0.82
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: vecdb://ceiec-aml/expert-review/smurfing-batch008
description: "Senior AML analyst confirmed 78% of flagged sequences match manual smurfing adjudication. Analyst noted sub-threshold deposit clustering and consolidation transfer as primary diagnostic signals, consistent with data/aml/concepts/aml-smurfing.md monitoring specification."
confidence: 0.88
observed_at: "2026-05-23T00:00:00Z"
```

```adl:monitoring_signal
signal_name: sub_threshold_deposits
description: "Multiple cash deposits below CTR threshold within a rolling time window across related accounts."
source_ref: data/aml/concepts/aml-smurfing.md
```

```adl:monitoring_signal
signal_name: consolidation_transfer
description: "Outbound transfer or wire that aggregates value from multiple preceding sub-threshold deposits."
source_ref: data/aml/concepts/aml-smurfing.md
```
```

**以下 ADL 文档正文中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity`
- [您的评分: ___]

#### 臂 B — Fair Plain L2（去掉 ADL 结构块后的同一措辞）

```markdown
# Smurfing Pattern

## Discovery Statement

The Smurfing Pattern describes a money laundering typology where large sums of illicit funds are broken into numerous small, sub-threshold cash deposits—often across multiple accounts, branches, or financial institutions—to evade mandatory reporting triggers. After the fragmented deposits settle, a consolidation transfer moves the aggregated funds toward a destination account or layering vehicle. The structural signature consists of a fan-in topology of low-value inflows followed by a single or few high-value outflows, with temporal clustering just below regulatory thresholds.

## Intuition

The core mechanism exploits the gap between individual transaction monitoring rules and aggregate behavioral analysis. Each individual deposit appears benign because the amount falls below the Currency Transaction Report (CTR) threshold or other alert triggers. The pattern becomes visible only when the system correlates multiple deposits across related accounts or time windows. The isomorphic mapping connects the Smurfing Pattern to a general "fragment-and-reassemble" topology found in network flow problems: a source node distributes flow across many parallel low-capacity edges, then a sink node collects the recombined flow through a high-capacity edge.

## Related Concepts

- [[Structuring]] — closely related synonym used in US regulatory context; Smurfing emphasizes the use of multiple human couriers ("smurfs")
- [[Layering]] — subsequent stage where consolidated funds undergo further obfuscation
- [[Threshold Avoidance]] — the behavioral driver that keeps individual transactions below reporting limits
- [[Fan-in Topology]] — abstract network shape describing many-to-one flow convergence
```

**以下公平纯文本中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_fair_plain`
- [您的评分: ___]

#### 臂 C — Plain LLM 非结构化基线

> 来源：`experiments/outputs/plain_discovery_smurfing-pattern.md`（与同主题 batch 条目共用）

```markdown
<!-- scenario-slug: smurfing-pattern -->
# Smurfing Pattern (plain baseline)

**It** slips under CTR because **they** fan deposits through **them** overnight. **This** structuring looks petty until **it** merges—then **those** corridors reveal whom **they** actually serve.

Shared fingerprints echo across **them**, but **that** linkage stays fuzzy until consolidation proves **they** pooled intent.
```

**以下非结构化 LLM 笔记中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_plain_llm`
- [您的评分: ___]

#### 本题元数据（可选）

- 是否熟悉该 AML 概念？ □ 是 □ 否 □ 部分熟悉
- 本题整体难度（1=很容易，5=很难）：[___]
- 备注：

---

### 题目 12 / 15

- **Discovery ID**：`disc-llm-crypto-mixer-batch009`
- **概念主题**：加密货币混币器暴露 (Crypto Mixer Exposure)（批次变体 `009`）
- **场景说明**：Crypto Mixer Exposure — wallet activity linked to tumbler contracts with peel-chain off-ramp patterns; align with aml-crypto-mix monitoring signals
- **源文件**：`experiments/outputs/llm_discovery_crypto-mixer_batch009.md`

#### 臂 A — ADL L2（评分时忽略 YAML 与 ` ```adl:* ` 块）

```markdown
# Crypto Mixer Exposure

## Discovery Statement

A cluster of wallet addresses exhibits a recurring exposure pattern where funds pass through mixer contracts and subsequently re-enter regulated exchange deposit addresses via peel-chain off-ramp sequences. The pattern indicates a structured laundering pipeline where mixer output is fragmented across multiple intermediary wallets before final consolidation at KYC-gated off-ramp points. Monitoring signals derived from mixer contract interaction frequency, peel-chain depth, and time-to-exchange-deposit intervals provide a composite risk score that correlates strongly with confirmed suspicious activity reports (SARs) filed in the same observation window.

## Intuition

The discovery emerges from observing that mixer contract interactions alone are insufficient for AML alerting. When combined with peel-chain off-ramp behavior — where a single source wallet fans out to many destination wallets in rapid succession — the composite signal reveals a laundering topology. The key insight is that the temporal gap between mixer withdrawal and the first peel-chain hop serves as a discriminator: short gaps (under 30 minutes) correlate with automated laundering scripts, while longer gaps suggest manual intervention or staged operations. The concept aligns with the public AML concept `aml-crypto-mix` which documents mixer contracts and peel-chain off-ramp as canonical primitives.

## Related Concepts

- [[Mixer Contract]] — smart contract that pools and redistributes funds to obscure origin
- [[Peel Chain]] — sequential transfer pattern where each hop peels off a small amount to a destination wallet
- [[Off-Ramp]] — conversion point from crypto asset to fiat currency via a regulated exchange
- [[aml-crypto-mix]] — public concept documenting mixer and peel-chain primitives

```adl:relation
source: "Crypto Mixer Exposure"
relation: isomorphic-to
target: "adl://public/concepts/aml-crypto-mix"
mapping_type: topological
confidence: 0.88
```

```adl:relation
source: "Crypto Mixer Exposure"
relation: extends
target: "adl://public/concepts/peel-chain-detection"
mapping_type: behavioral
confidence: 0.75
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/cluster/mixer-exposure-2026q2
description: "Cluster of 1,247 wallet addresses showing mixer contract interaction followed by peel-chain off-ramp within 2-hour window. 83% of cluster members have associated SARs filed within 90 days of observation."
confidence: 0.80
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: empirical_observation
data_ref: vecdb://ceiec-aml/observation/mixer-peel-temporal-gap
description: "Temporal gap analysis between mixer withdrawal and first peel-chain hop. Short-gap cohort (under 30 minutes) shows 91% SAR correlation. Long-gap cohort (30 minutes to 6 hours) shows 67% SAR correlation."
confidence: 0.74
observed_at: "2026-05-20T00:00:00Z"
```

```adl:evidence
evidence_type: cross_reference
data_ref: vecdb://ceiec-aml/xref/exchange-deposit-consolidation
description: "Cross-reference with exchange deposit logs confirms that 78% of flagged peel-chain terminal wallets deposited to KYC-gated exchanges within 48 hours of mixer withdrawal."
confidence: 0.70
observed_at: "2026-05-22T00:00:00Z"
```
```

**以下 ADL 文档正文中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity`
- [您的评分: ___]

#### 臂 B — Fair Plain L2（去掉 ADL 结构块后的同一措辞）

```markdown
# Crypto Mixer Exposure

## Discovery Statement

A cluster of wallet addresses exhibits a recurring exposure pattern where funds pass through mixer contracts and subsequently re-enter regulated exchange deposit addresses via peel-chain off-ramp sequences. The pattern indicates a structured laundering pipeline where mixer output is fragmented across multiple intermediary wallets before final consolidation at KYC-gated off-ramp points. Monitoring signals derived from mixer contract interaction frequency, peel-chain depth, and time-to-exchange-deposit intervals provide a composite risk score that correlates strongly with confirmed suspicious activity reports (SARs) filed in the same observation window.

## Intuition

The discovery emerges from observing that mixer contract interactions alone are insufficient for AML alerting. When combined with peel-chain off-ramp behavior — where a single source wallet fans out to many destination wallets in rapid succession — the composite signal reveals a laundering topology. The key insight is that the temporal gap between mixer withdrawal and the first peel-chain hop serves as a discriminator: short gaps (under 30 minutes) correlate with automated laundering scripts, while longer gaps suggest manual intervention or staged operations. The concept aligns with the public AML concept `aml-crypto-mix` which documents mixer contracts and peel-chain off-ramp as canonical primitives.

## Related Concepts

- [[Mixer Contract]] — smart contract that pools and redistributes funds to obscure origin
- [[Peel Chain]] — sequential transfer pattern where each hop peels off a small amount to a destination wallet
- [[Off-Ramp]] — conversion point from crypto asset to fiat currency via a regulated exchange
- [[aml-crypto-mix]] — public concept documenting mixer and peel-chain primitives
```

**以下公平纯文本中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_fair_plain`
- [您的评分: ___]

#### 臂 C — Plain LLM 非结构化基线

> 来源：`experiments/outputs/plain_discovery_crypto-mixer.md`（与同主题 batch 条目共用）

```markdown
<!-- scenario-slug: crypto-mixer -->
# Crypto Mixer Exposure (plain baseline)

**They** tumble through mixer hops and **it** peels until **they** cash out via stablecoins. **This** wallet cluster talks to contracts **those** explorers label, yet **it** still hides who fronts **them** upstream.

**That** peeling chain drags fiat spikes while **they** launder plausible deniability about **that** intermediary everyone suspects.
```

**以下非结构化 LLM 笔记中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_plain_llm`
- [您的评分: ___]

#### 本题元数据（可选）

- 是否熟悉该 AML 概念？ □ 是 □ 否 □ 部分熟悉
- 本题整体难度（1=很容易，5=很难）：[___]
- 备注：

---

### 题目 13 / 15

- **Discovery ID**：`disc-llm-peripheral-trap-batch010`
- **概念主题**：外围注意力陷阱 (Peripheral Attention Trap)（批次变体 `010`）
- **场景说明**：Peripheral Attention Trap — graph peripheral node concentration while value consolidates toward a hidden sink; align with aml-attention-trap monitoring signals
- **源文件**：`experiments/outputs/llm_discovery_peripheral-trap_batch010.md`

#### 臂 A — ADL L2（评分时忽略 YAML 与 ` ```adl:* ` 块）

```markdown
# Peripheral Attention Trap

## Discovery Statement

In AML transaction monitoring, compliance analyst attention becomes disproportionately concentrated on a small set of high-centrality nodes within the transaction graph, while structurally significant peripheral nodes — nodes positioned at the graph boundary yet functionally acting as convergence sinks — receive systematically insufficient scrutiny. The resulting blind zone enables layering schemes to exploit low-attention periphery for final-stage fund consolidation, creating a measurable detection gap between graph-theoretic risk and human-investigated risk.

## Intuition

Standard alert ranking algorithms weight node importance by degree centrality and transaction velocity. Peripheral nodes, by definition, exhibit low degree centrality and therefore rank low in alert queues. However, a subset of peripheral nodes functions as terminal sink nodes where laundered funds converge after multi-hop layering. The "attention trap" emerges because the very metric designed to prioritize investigation — centrality — actively suppresses visibility of the most operationally critical nodes in the laundering topology. Analyst cognitive load compounds the effect: once high-centrality alerts consume available review bandwidth, peripheral sink convergence events persist unexamined across multiple monitoring cycles.

## Related Concepts

- [[AML Attention Trap]] — foundational concept describing attention misallocation in compliance monitoring
- [[Graph Sink Convergence]] — structural pattern where multiple paths terminate at a single low-centrality node
- [[Layering Periphery Exploitation]] — adversarial strategy leveraging peripheral node positioning

```adl:relation
source: "Peripheral Attention Trap"
relation: isomorphic-to
target: "adl://public/concepts/aml-attention-trap"
mapping_type: topological
confidence: 0.85
```

```adl:relation
source: "Peripheral Attention Trap"
relation: compositional-with
target: "adl://private/ceiec-aml/concepts/graph-sink-convergence"
mapping_type: structural
confidence: 0.78
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/graph-peripheral-sink-2026q1
description: "Clustering analysis of 2026-Q1 transaction graphs identified 347 peripheral nodes with sink-convergence signatures. Of the identified peripheral nodes, 89% received zero analyst attention within the standard 72-hour review window. Nodes exhibited mean degree centrality below 0.05 while aggregating total inbound flow exceeding 2.3M CNY across a median of 14 source paths."
confidence: 0.74
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: vecdb://ceiec-aml/attention-drift-signal-batch010
description: "Agent-based simulation of analyst attention allocation over 10,000 synthetic alert batches reproduced the peripheral blind zone. When centrality-weighted ranking was applied, peripheral sink nodes achieved a mean investigation delay of 11.4 days compared to 1.2 days for high-centrality nodes, despite equivalent or higher cumulative transaction volumes."
confidence: 0.70
observed_at: "2026-05-23T00:00:00Z"
```

```adl:monitoring
signals:
  - name: peripheral_sink_convergence_rate
    source: data/aml/concepts/aml-attention-trap.md
    description: "Rate at which peripheral nodes accumulate inbound paths exceeding threshold without triggering analyst review"
    threshold: "> 0.15 per monitoring cycle"
  - name: attention_drift_index
    source: data/aml/concepts/aml-attention-trap.md
    description: "Ratio of analyst time spent on high-centrality nodes versus peripheral sink nodes normalized by cumulative flow volume"
    threshold: "> 8.0 indicates trap activation"
```
```

**以下 ADL 文档正文中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity`
- [您的评分: ___]

#### 臂 B — Fair Plain L2（去掉 ADL 结构块后的同一措辞）

```markdown
# Peripheral Attention Trap

## Discovery Statement

In AML transaction monitoring, compliance analyst attention becomes disproportionately concentrated on a small set of high-centrality nodes within the transaction graph, while structurally significant peripheral nodes — nodes positioned at the graph boundary yet functionally acting as convergence sinks — receive systematically insufficient scrutiny. The resulting blind zone enables layering schemes to exploit low-attention periphery for final-stage fund consolidation, creating a measurable detection gap between graph-theoretic risk and human-investigated risk.

## Intuition

Standard alert ranking algorithms weight node importance by degree centrality and transaction velocity. Peripheral nodes, by definition, exhibit low degree centrality and therefore rank low in alert queues. However, a subset of peripheral nodes functions as terminal sink nodes where laundered funds converge after multi-hop layering. The "attention trap" emerges because the very metric designed to prioritize investigation — centrality — actively suppresses visibility of the most operationally critical nodes in the laundering topology. Analyst cognitive load compounds the effect: once high-centrality alerts consume available review bandwidth, peripheral sink convergence events persist unexamined across multiple monitoring cycles.

## Related Concepts

- [[AML Attention Trap]] — foundational concept describing attention misallocation in compliance monitoring
- [[Graph Sink Convergence]] — structural pattern where multiple paths terminate at a single low-centrality node
- [[Layering Periphery Exploitation]] — adversarial strategy leveraging peripheral node positioning
```

**以下公平纯文本中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_fair_plain`
- [您的评分: ___]

#### 臂 C — Plain LLM 非结构化基线

> 来源：`experiments/outputs/plain_discovery_peripheral-trap.md`（与同主题 batch 条目共用）

```markdown
<!-- scenario-slug: peripheral-trap -->
# Peripheral Attention Trap (plain baseline)

**They** route value through corridors **it** ignores while **this** hides behind **that** benign hub traffic. Operators chase **it**, but missing **them** blinds the hunt until sinks absorb what **they** never named.

Alerts pile on flashy nodes yet **those** feeders keep splitting before anyone ties **this** funnel to beneficiaries **it** only hints at.
```

**以下非结构化 LLM 笔记中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_plain_llm`
- [您的评分: ___]

#### 本题元数据（可选）

- 是否熟悉该 AML 概念？ □ 是 □ 否 □ 部分熟悉
- 本题整体难度（1=很容易，5=很难）：[___]
- 备注：

---

### 题目 14 / 15

- **Discovery ID**：`disc-llm-smurfing-pattern-batch011`
- **概念主题**：拆分存款模式 (Smurfing Pattern)（批次变体 `011`）
- **场景说明**：Smurfing Pattern — sub-threshold deposit structuring across a beneficial-owner network; align with aml-smurfing CTR threshold heuristics
- **源文件**：`experiments/outputs/llm_discovery_smurfing-pattern_batch011.md`

#### 臂 A — ADL L2（评分时忽略 YAML 与 ` ```adl:* ` 块）

```markdown
# Smurfing Pattern

## Discovery Statement

The Smurfing Pattern describes a money laundering typology where large sums of illicit funds are broken into numerous sub-threshold deposits, each deliberately kept below regulatory reporting limits, across multiple accounts or financial institutions. After the fragmented deposits settle, a consolidation transfer moves the aggregated funds to a destination account, completing the layering phase. Detection relies on identifying the temporal and relational clustering of small-value transactions followed by a unifying outbound transfer.

## Intuition

The core mechanism exploits regulatory blind spots created by fixed reporting thresholds. By distributing deposits across many "smurfs" (individual depositors or accounts), the launderer avoids triggering Currency Transaction Reports (CTRs) or Suspicious Activity Reports (SARs). The pattern becomes visible only when the network of sub-threshold deposits is analyzed holistically, revealing a funnel structure converging on a single beneficiary. Key signals include: (1) multiple deposits from different originators within a short time window, (2) each deposit amount falling just below the reporting threshold, and (3) a subsequent consolidation transfer that aggregates the fragmented funds.

## Related Concepts

- [[Structuring]] — the broader legal term for breaking transactions to evade reporting thresholds
- [[Layering]] — the AML phase where illicit funds are moved through multiple accounts to obscure origin
- [[Funnel Account]] — the destination account that receives consolidated smurf deposits
- [[Currency Transaction Report (CTR)]] — the regulatory filing that smurfing seeks to evade

```adl:relation
source: "Smurfing Pattern"
relation: isomorphic-to
target: "adl://public/concepts/structuring"
mapping_type: topological
confidence: 0.92
```

```adl:relation
source: "Smurfing Pattern"
relation: compositional-with
target: "adl://public/concepts/funnel-account"
mapping_type: functional
confidence: 0.85
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/cluster/smurfing-batch011
description: "Cluster of 1,247 transaction sequences exhibiting sub-threshold deposit patterns followed by consolidation transfers within 48-hour windows. Average deposit count per sequence: 8.3. Mean deposit amount: 94% of local reporting threshold."
confidence: 0.80
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: vecdb://ceiec-aml/expert-review/smurfing-2026q1
description: "AML compliance officer validation of 156 flagged smurfing cases. 89% confirmed as true positives. Expert notes highlight temporal clustering of deposits within 6-hour windows and geographic dispersion across 3+ branch locations as strong secondary indicators."
confidence: 0.88
observed_at: "2026-04-15T00:00:00Z"
```

```adl:evidence
evidence_type: cross_reference
data_ref: vecdb://ceiec-aml/regulatory/fincen-advisory-2025
description: "FinCEN Advisory FIN-2025-A003 references smurfing as a persistent typology. Documented cases show average of 12 sub-threshold deposits per laundering episode with consolidation transfers averaging 72 hours after initial deposit."
confidence: 0.75
observed_at: "2025-11-01T00:00:00Z"
```
```

**以下 ADL 文档正文中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity`
- [您的评分: ___]

#### 臂 B — Fair Plain L2（去掉 ADL 结构块后的同一措辞）

```markdown
# Smurfing Pattern

## Discovery Statement

The Smurfing Pattern describes a money laundering typology where large sums of illicit funds are broken into numerous sub-threshold deposits, each deliberately kept below regulatory reporting limits, across multiple accounts or financial institutions. After the fragmented deposits settle, a consolidation transfer moves the aggregated funds to a destination account, completing the layering phase. Detection relies on identifying the temporal and relational clustering of small-value transactions followed by a unifying outbound transfer.

## Intuition

The core mechanism exploits regulatory blind spots created by fixed reporting thresholds. By distributing deposits across many "smurfs" (individual depositors or accounts), the launderer avoids triggering Currency Transaction Reports (CTRs) or Suspicious Activity Reports (SARs). The pattern becomes visible only when the network of sub-threshold deposits is analyzed holistically, revealing a funnel structure converging on a single beneficiary. Key signals include: (1) multiple deposits from different originators within a short time window, (2) each deposit amount falling just below the reporting threshold, and (3) a subsequent consolidation transfer that aggregates the fragmented funds.

## Related Concepts

- [[Structuring]] — the broader legal term for breaking transactions to evade reporting thresholds
- [[Layering]] — the AML phase where illicit funds are moved through multiple accounts to obscure origin
- [[Funnel Account]] — the destination account that receives consolidated smurf deposits
- [[Currency Transaction Report (CTR)]] — the regulatory filing that smurfing seeks to evade
```

**以下公平纯文本中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_fair_plain`
- [您的评分: ___]

#### 臂 C — Plain LLM 非结构化基线

> 来源：`experiments/outputs/plain_discovery_smurfing-pattern.md`（与同主题 batch 条目共用）

```markdown
<!-- scenario-slug: smurfing-pattern -->
# Smurfing Pattern (plain baseline)

**It** slips under CTR because **they** fan deposits through **them** overnight. **This** structuring looks petty until **it** merges—then **those** corridors reveal whom **they** actually serve.

Shared fingerprints echo across **them**, but **that** linkage stays fuzzy until consolidation proves **they** pooled intent.
```

**以下非结构化 LLM 笔记中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_plain_llm`
- [您的评分: ___]

#### 本题元数据（可选）

- 是否熟悉该 AML 概念？ □ 是 □ 否 □ 部分熟悉
- 本题整体难度（1=很容易，5=很难）：[___]
- 备注：

---

### 题目 15 / 15

- **Discovery ID**：`disc-llm-crypto-mixer-batch012`
- **概念主题**：加密货币混币器暴露 (Crypto Mixer Exposure)（批次变体 `012`）
- **场景说明**：Crypto Mixer Exposure — wallet activity linked to tumbler contracts with peel-chain off-ramp patterns; align with aml-crypto-mix monitoring signals
- **源文件**：`experiments/outputs/llm_discovery_crypto-mixer_batch012.md`

#### 臂 A — ADL L2（评分时忽略 YAML 与 ` ```adl:* ` 块）

```markdown
# Crypto Mixer Exposure

## Discovery Statement

A compositional blend of mixer contract interaction patterns and peel-chain off-ramp heuristics yields a composite exposure score for wallet clusters. The score captures both direct mixer deposits and indirect second-hop peel-chain withdrawals, enabling detection of layered obfuscation strategies that neither heuristic alone would flag. High composite scores correlate with confirmed suspicious activity reports at a rate exceeding 0.72 in the CEIEC AML test cohort.

## Intuition

Traditional mixer detection relies on direct contract interaction flags. Peel-chain analysis separately tracks rapid multi-hop transfers to exchange deposit addresses. The compositional blend merges both signals: a wallet cluster receives funds from a known Tornado Cash-style contract, then initiates a peel-chain of four or more hops before an exchange off-ramp. The combined pattern—mixer ingress followed by structured peel-chain egress—forms a distinct obfuscation archetype. Weighting the mixer proximity score (0–1) against peel-chain hop count and velocity produces a unified exposure metric.

## Related Concepts

- [[AML Crypto Mix]] — mixer contract interaction patterns and peel-chain off-ramp heuristics
- [[Capital Reflux Trap]] — circular fund flow detection in traditional AML
- [[Peel Chain Detection]] — sequential small-value transfers to exchange deposit addresses

```adl:relation
source: "Crypto Mixer Exposure"
relation: compositional-blend-of
target: "adl://public/concepts/aml-crypto-mix"
mapping_type: semantic
confidence: 0.82
```

```adl:relation
source: "Crypto Mixer Exposure"
relation: analogous-to
target: "adl://public/concepts/capital_reflux_trap"
mapping_type: structural
confidence: 0.61
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/cluster/mixer-exposure-2026q2
description: "Cluster of 1,247 wallet groups exhibiting combined mixer-deposit and peel-chain-off-ramp signatures in Q2 2026 CEIEC transaction graph. Composite exposure scores above 0.70 align with 72% of confirmed SAR filings in the cohort."
confidence: 0.78
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: vecdb://ceiec-aml/expert-review/mixer-batch012
description: "Senior AML analyst review of 50 high-scoring wallet clusters confirmed 38 as true positives exhibiting layered mixer-plus-peel-chain obfuscation. Analysts noted the composite score reduced false positives from direct-mixer-only flags by approximately 40%."
confidence: 0.85
observed_at: "2026-05-20T00:00:00Z"
```
```

**以下 ADL 文档正文中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity`
- [您的评分: ___]

#### 臂 B — Fair Plain L2（去掉 ADL 结构块后的同一措辞）

```markdown
# Crypto Mixer Exposure

## Discovery Statement

A compositional blend of mixer contract interaction patterns and peel-chain off-ramp heuristics yields a composite exposure score for wallet clusters. The score captures both direct mixer deposits and indirect second-hop peel-chain withdrawals, enabling detection of layered obfuscation strategies that neither heuristic alone would flag. High composite scores correlate with confirmed suspicious activity reports at a rate exceeding 0.72 in the CEIEC AML test cohort.

## Intuition

Traditional mixer detection relies on direct contract interaction flags. Peel-chain analysis separately tracks rapid multi-hop transfers to exchange deposit addresses. The compositional blend merges both signals: a wallet cluster receives funds from a known Tornado Cash-style contract, then initiates a peel-chain of four or more hops before an exchange off-ramp. The combined pattern—mixer ingress followed by structured peel-chain egress—forms a distinct obfuscation archetype. Weighting the mixer proximity score (0–1) against peel-chain hop count and velocity produces a unified exposure metric.

## Related Concepts

- [[AML Crypto Mix]] — mixer contract interaction patterns and peel-chain off-ramp heuristics
- [[Capital Reflux Trap]] — circular fund flow detection in traditional AML
- [[Peel Chain Detection]] — sequential small-value transfers to exchange deposit addresses
```

**以下公平纯文本中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_fair_plain`
- [您的评分: ___]

#### 臂 C — Plain LLM 非结构化基线

> 来源：`experiments/outputs/plain_discovery_crypto-mixer.md`（与同主题 batch 条目共用）

```markdown
<!-- scenario-slug: crypto-mixer -->
# Crypto Mixer Exposure (plain baseline)

**They** tumble through mixer hops and **it** peels until **they** cash out via stablecoins. **This** wallet cluster talks to contracts **those** explorers label, yet **it** still hides who fronts **them** upstream.

**That** peeling chain drags fiat spikes while **they** launder plausible deniability about **that** intermediary everyone suspects.
```

**以下非结构化 LLM 笔记中，核心概念与实体的指称是否清晰？（1–5）**

- 字段名 `referent_clarity_plain_llm`
- [您的评分: ___]

#### 本题元数据（可选）

- 是否熟悉该 AML 概念？ □ 是 □ 否 □ 部分熟悉
- 本题整体难度（1=很容易，5=很难）：[___]
- 备注：

---

## Part C — 评分者元数据

请在完成全部 15 题后填写：

| 项目 | 您的回答 |
|------|----------|
| 评分者 ID（匿名，如 R01） | [___] |
| AML / 合规 / 金融科技相关背景（年） | [___] |
| 图分析 / 交易监控经验 | □ 无 □ 1–3 年 □ 3+ 年 |
| 是否已阅读 `prompts/judge_referent_clarity.md` 评分标准 | □ 是 □ 否 |
| 完成日期 | [___] |
| 整体套题难度感受（1–5） | [___] |
| 其他说明 | |

---

## 提交与回填

将分数写入 `data/eval/human_rq1_template.json`（或副本 `human_rq1_completed.json`）对应条目，例如：

```json
{
  "adl_id": "disc-llm-peripheral-trap",
  "referent_clarity": 4,
  "referent_clarity_fair_plain": 4,
  "referent_clarity_plain_llm": 2,
  "rater": "R01",
  "rating_completed_at": "2026-05-24T12:00:00Z"
}
```

分析命令：`python -m experiments.rq1_human_eval`

---

## 附录：Plain LLM 三篇全文（batch 共用）

### 外围注意力陷阱 (Peripheral Attention Trap)

```markdown
<!-- scenario-slug: peripheral-trap -->
# Peripheral Attention Trap (plain baseline)

**They** route value through corridors **it** ignores while **this** hides behind **that** benign hub traffic. Operators chase **it**, but missing **them** blinds the hunt until sinks absorb what **they** never named.

Alerts pile on flashy nodes yet **those** feeders keep splitting before anyone ties **this** funnel to beneficiaries **it** only hints at.
```

### 拆分存款模式 (Smurfing Pattern)

```markdown
<!-- scenario-slug: smurfing-pattern -->
# Smurfing Pattern (plain baseline)

**It** slips under CTR because **they** fan deposits through **them** overnight. **This** structuring looks petty until **it** merges—then **those** corridors reveal whom **they** actually serve.

Shared fingerprints echo across **them**, but **that** linkage stays fuzzy until consolidation proves **they** pooled intent.
```

### 加密货币混币器暴露 (Crypto Mixer Exposure)

```markdown
<!-- scenario-slug: crypto-mixer -->
# Crypto Mixer Exposure (plain baseline)

**They** tumble through mixer hops and **it** peels until **they** cash out via stablecoins. **This** wallet cluster talks to contracts **those** explorers label, yet **it** still hides who fronts **them** upstream.

**That** peeling chain drags fiat spikes while **they** launder plausible deniability about **that** intermediary everyone suspects.
```
