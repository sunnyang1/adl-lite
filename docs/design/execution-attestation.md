# 执行证明层（Execution Attestation Layer, EAL）设计草案 v0.1

> 状态：**Phase 1 已实现**（v0.7.0-alpha，2026-07-23）——ExecutionLog、EXECUTE/ATTEST/EXEC_ANCHOR
> 事件类型、公理 13–15、`adl:execution` 块、本体同步、CLI `adl-lite execute`、注册钩子（D5）均已落地；
> Phase 2（ATTEST 重放 harness、证据加权置信度、refute→DEPRECATE 提案、校准接线）未开始。
> 起源：商业计划书对抗性审查发现的最深产品缺口——"链上记录 ≠ 事实"（预言机问题）。

## 1. 问题陈述（第一性原理）

ADL Lite 的公理是"概念 = EventChain，状态从链派生"。这把**治理**做到了事实化：
REGISTER/VALIDATE/DEPRECATE 都是密码学锚定的事件，篡改可检测、历史可审计。

但有一个环节从未被事实化：**执行**。

- 一个 `VALIDATE` 事件声称"我运行过这个能力，它有效"——但协议没有任何东西证明验证者真的运行过任何东西。
- 一个能力声称"p95 延迟 < 200ms"——但注册者没有任何义务展示执行证据。
- 结果：注册表可能漂移成**纸面能力生态**——治理精良的元数据，描述着无人验证过的东西。

现有机制的真实保证边界（诚实盘点）：

| 机制 | 保证了什么 | 没保证什么 |
|------|-----------|-----------|
| 哈希链 + 12 公理 | 记录不被篡改 | 记录的内容为真 |
| N_min 抗串谋 | 撒谎成本 ≥ N 个身份 | 任何单个声明有证据 |
| γ_agg / γ_cal 校准 | 统计上抑制低准确率验证者 | 自举所需的地面真值从哪来 |

第一性原理重构：**我们无法在 Lite 尺度让执行本身去信任化（那是 zk/TEE 的领域），
但我们可以让每一句关于执行的声称变成可证伪、可归因、有代价的声称。**
诚实的声称和撒谎的声称在今天的协议里成本相同——这才是真正的缺口。
EAL 的目标不是"证明执行发生"，而是**让撒谎变贵、让懒惰可见、让校准有地面真值**。

## 2. 设计目标与非目标

**目标**

1. 执行证据成为一等公民：有 schema、有生命周期、有校验规则。
2. 证据分级：从签名回执到重放确认，保证级别显式标注、可比较。
3. 与 CRDT 语义兼容：不破坏 status LUB / confidence G-Counter 的单调性（T9 不动）。
4. 复用现有密码学基建：LD-Proof（`sign_event`）、Merkle 锚定、DID——零新原语。
5. 给校准提供地面真值：ATTEST 裁决 → 验证者准确率 → γ_cal 自举。

**非目标**

- 不做信任最小化计算（zk-proof / TEE 只留 schema 插口，Phase 3+）。
- 不做代币/经济层——激励全部走声誉与准入（§8）。
- 不强制所有能力接入——存量豁免，新注册能力按 scope 政策要求（§11 D5）。

## 3. 保证级别谱（Assurance Spectrum）

| 级别 | 名称 | 证据形式 | 证明的东西 | 没证明的 |
|------|------|---------|-----------|---------|
| L0 | 自我声明（现状） | 无 | — | 一切 |
| L1 | **签名执行回执** | input/output 承诺 + 环境指纹 + LD-Proof | 某个身份在某一时刻对一次执行做出了**可归因、不可抵赖**的声称 | 声称属实 |
| L2 | **重放/性质确认** | 独立验证者重跑并比对承诺，或验证声明性质 | 至少有第二个独立方能复现该输入→输出映射 | 生产环境每次执行都如此 |
| L3 | 可验证计算 | TEE quote / zk-proof | 执行本身（在硬件/密码学假设下） | —（Phase 3+ 插口） |

关键洞察：ADL Lite 的生态位是**注册表与生命周期**，不是可验证计算平台。
EAL 把 L1–L2 证据变成一等公民，并为 L3 留好插口——这就够了。
L1 的价值常被低估：签名回执把"无声的失败"变成"可追责的记录"，是声誉博弈的地基。

## 4. 核心架构决策：证据放在哪

| 方案 | 结构 | 优点 | 缺点 |
|------|------|------|------|
| A. 全部上主链 | EXECUTE/ATTEST 都追加到能力 EventChain | 单一审计轨迹，基建全复用 | **链膨胀**：热门能力执行 10³–10⁵ 次/月，治理信号被淹没；E13/E21/E27 已量化长链成本 |
| B. 完全独立 | ExecutionLog 与主链只在注册时关联 | 主链零负担 | 证据与治理脱钩，ATTEST 无法喂给校准/共识 |
| **C. 混合（推荐）** | 原始 EXECUTE 回执 → 每能力独立 `ExecutionLog`（append-only，hash-chained，走 cold_storage 分层）；主链只承载两类事件：**EXEC_ANCHOR**（定期锚定日志 Merkle root + 计数）和 **ATTEST**（对执行的裁决——这是治理相关信号） | 主链保持 O(治理) 规模（每月 +1 锚）；证据可独立分层/压缩/归档；ATTEST 在主链上可直接参与派生 | 引入第二种链类型；跨链引用需要解析约定（§6 已有先例） |

膨胀定量：某能力月增 10⁴ 次执行，方案 A 主链年增 12 万事件（E21 量级，verify/memory 成本显著）；
方案 C 主链年增 12 个锚 + O(验证者数) 个 ATTEST，ExecutionLog 走 zstd+msgpack 冷存储（`cold_storage.py` 现成）。

```mermaid
flowchart LR
    subgraph 主链 EventChain（治理）
        R[REGISTER] --> V[VALIDATE]
        V --> AN[EXEC_ANCHOR<br/>月度 Merkle 锚]
        V --> AT[ATTEST confirm/refute]
    end
    subgraph ExecutionLog（证据，每能力一条，可冷存储）
        E1[EXECUTE 回执] --> E2[EXECUTE 回执] --> E3[...]
    end
    AN -. merkle root .-> E3
    AT -. subject_execution .-> E1
    AT --> CAL[CALIBRATE /<br/>update_from_feedback<br/>验证者准确率]
```

## 5. 数据模型

### 5.1 新事件类型（`models.py:108` EventType 新增分组）

```python
# Execution attestation events (EAL)
EXECUTE = "execute"          # 执行回执（ExecutionLog）
ATTEST = "attest"            # 对执行的裁决（主链，治理相关）
EXEC_ANCHOR = "exec_anchor"  # 执行日志 Merkle 锚（主链）
# Phase 3: CHALLENGE = "challenge"  # 挑战-响应
```

Axiom 12（`models.py:634`）只检查"event_type 是已知枚举成员"→ 新增成员对全部存量链后向兼容。
status LUB 与 confidence G-Counter 均不消费新类型（`models.py:407/447`）→ **派生逻辑零改动**。

### 5.2 EXECUTE 回执（写入 ExecutionLog）

```yaml
event_type: execute
actor: "did:key:z6Mk..."            # 执行者 DID
payload:
  execution_id: "exec-01J8..."      # ULID，全局唯一
  capability: "disc-gradient-explosion"
  occurred_at: "2026-07-23T12:00:00Z"
  input_commitment: "sha256:9f2c..."
  output_commitment: "sha256:41ab..."
  env: {runtime: "python3.12", adl_lite: "0.6.0", platform: "darwin-arm64"}
  duration_ms: 183
  assurance: "self-report"           # L1；L2 由 ATTEST 赋予
  artifacts_ref: null                # 可选：日志 bundle URI / 独立 Merkle root
proof: { ... }                       # LD-Proof，复用 sign_event（Axiom 14 强制）
```

### 5.3 ATTEST 裁决（写入主链）

```yaml
event_type: attest
actor: "did:key:z7Qb..."            # 验证者 DID（≠ 执行者，见 §8 抗串谋）
payload:
  subject_execution: "exec-01J8..."       # 指向 ExecutionLog 条目
  subject_log_root: "sha256:..."          # 裁决时所见的日志锚（防事后换日志）
  method: "replay"          # replay | property-check | manual | tee-quote | zk-proof
  verdict: "confirm"        # confirm | refute | inconclusive
  replay:                          # method=replay 时必填（Axiom 15）
    input_commitment: "sha256:9f2c..."
    output_commitment: "sha256:41ab..."
    match: true
    tolerance: "exact"      # exact | property | statistical
  evidence_ref: null        # verdict=refute 时必填
proof: { ... }
```

### 5.4 EXEC_ANCHOR（主链，定期）

```yaml
event_type: exec_anchor
actor: "did:key:..."                # 执行者或注册表服务
payload:
  log_merkle_root: "sha256:..."     # compute_chain_merkle_root 直接复用
  window: {from: "2026-07-01", to: "2026-07-31"}
  execution_count: 1024
  executor_set: ["did:key:..."]
```

### 5.5 能力侧执行规格（新 L3 块 `adl:execution`）——让重放成为可能

没有规格，验证者无从下手，ATTEST 就是空话。这是本层**最容易被忽略但最关键**的一块：

```yaml
```adl:execution
invocation:
  type: cli                        # cli | http | python
  command: "python -m mycap.score --input {input_file}"
  timeout_ms: 5000
determinism: deterministic         # deterministic | stochastic | side-effecting
properties:                        # property-check 的断言集（Comparator 闭集，无 eval）
  - "output.confidence in [0, 1]"
  - "p95_latency_ms < 200"
test_vectors:                      # 重放基准
  - input_commitment: "sha256:..."
    expected_output_commitment: "sha256:..."
```
```

- `determinism` 决定重放语义：deterministic → exact 比对；stochastic → statistical
  （分布一致性，如多次采样的矩检验）；side-effecting → 仅 property-check + 人工。
- strict-template 政策：新注册能力**必填**（§11 D5），存量豁免。

### 5.6 防抄袭：commit–reveal 挑战（Phase 3 机制，schema 先行）

确定性能力的执行者可缓存旧答案应付重放；验证者也可能照抄执行者的 output hash。
解法：挑战者先提交 `seed_commitment = H(seed)`，执行者提交 `H(output)` 后，挑战者揭示 seed。
双方都被锁定时序，抄袭与预计算同时被阻断。`CHALLENGE` 事件 schema 在 Phase 1 预留、Phase 3 实现。

## 6. 派生与校验规则变更

### 6.1 新公理（沿用 `_check_wfN_*` 模式，加入 `verify_report()`）

- **Axiom 13（证据 schema）**：EXECUTE 必含 `execution_id` + input/output commitment；
  ATTEST 必含 `subject_execution` + `verdict` + `method`；EXEC_ANCHOR 必含 `log_merkle_root`。
- **Axiom 14（证明在场）**：EXECUTE / ATTEST 必须携带可验证的 `proof`（LD-Proof）。
  证据若不可归责，则毫无价值。新类型无存量链，可直接硬约束。
- **Axiom 15（裁决自洽）**：`method=replay ∧ verdict=confirm` ⇒ `replay.match=true` 且承诺一致；
  `verdict=refute` ⇒ 必含 `evidence_ref` 或不匹配细节。

### 6.2 跨链引用解析（沿用注入式 lookup 先例）

`RelationValidator.filter_valid_relations`（relation_validator.py:86）已确立模式：
**链保持自包含，引用在验证层用注入的 lookup 解析**，未知目标默认 PROVISIONAL 而非报错。
EAL 沿用：`ADLValidator` / 新 `AttestationValidator` 接受
`execution_lookup: dict[str, ExecutionReceipt]`；
ATTEST 指向缺失的 `subject_execution` → 派生视图标记 `pending`，**不构成完整性失败**。
理由：证据日志可能尚未同步（edge 场景，`sync_manager.py`），注册表必须容错。

### 6.3 本体 YAML 同步（adl_core_ontology.yaml）

- classes 增加：`execution`、`attestation`
- actions 增加：`execute` / `attest`（`triggers_transition: null`，不改变状态机）
- predicates 增加：`attests`、`executed-by`、`anchored-by`
- 新政策参数：`attestation.min_distinct_scopes`（默认 2）、`attestation.evidence_factor_unbacked`（α，默认 0.5）、`attestation.refute_threshold`（r，默认 2）
- 状态转换表**不变**

## 7. 与置信度/校准的集成（Phase 2）

### 7.1 证据加权置信度（可选启用，默认关）

```
effective_confidence(C) = max over VALIDATE v of ( v.confidence × factor(v) )
factor(v) = 1.0  若 v 被 ≥ k 个来自不同 scope 的 confirm ATTEST 支持
          = α    否则（α 默认 0.5，本体可调）
```

单调性论证：ATTEST 只增不删，factor 只升不降，max 保持单调 → CRDT G-Counter 语义不被破坏。
代价：confidence 派生变为**跨链函数**（依赖 ATTEST 状态）——这是 Phase 1 默认关闭它的原因。

### 7.2 反驳语义：推状态，不扣分数（保住 T9 的关键设计）

`refute` **绝不直接降低 confidence**（那会破坏单调性并开放 griefing：恶意反驳拉低对手）。
改为：≥ r 个不同 scope 的 refute（附 evidence_ref）→ 自动发起 `DEPRECATE` **提案**，
走现有状态机与 N_min 流程裁决。负证据推动状态沿格**前移**（validated → deprecated），
与 LUB 语义同向，而不是逆着置信度向下拽。

### 7.3 校准自举闭环（本层对现有系统最大的反哺）

```
ATTEST verdict ──被后续独立重放推翻/支持──► MARGINCalibrator.update_from_feedback()
        │                                          │
        ▼                                          ▼
  验证者/执行者准确率档案 ◄──── γ_cal 加权 ◄──── calibrated_confidence()
```

今天 γ_cal 的准确率无地面真值来源（自举问题）；ATTEST 的 confirm/refute 及其后续命运
恰好提供了标签。`apply_calibration_event`（calibration.py:138）管道现成，只需接数据源。
对推翻的裁决施加**非对称重罚**（EWMA 加速下调），使串谋 attestor 的长期收益为负。

## 8. 激励结构（无代币）

注册表不是区块链，激励 = **声誉 × 权重 × 准入**：

| 参与者 | 诚实行为的收益 | 撒谎的代价 |
|--------|--------------|-----------|
| 执行者 | 被证实的能力在 `adl-lite related`/memory 查询中排序更高；高声誉 → 更少强制验证轮次（快速通道） | 签名回执 = 可证伪声明；被推翻后 accuracy 非对称下调，连带其全部历史声称被折价 |
| 验证者 | 准确裁决积累 γ_cal 权重 → 自己的 VALIDATE 更"值钱"；高声誉 → 更广 scope 准入 | 被推翻的 ATTEST 永久损害准确率；同 scope 互证不计入 min_distinct_scopes |
| 挑战者 | 成功揭露懒惰执行者 → 准确率奖励 | 无效挑战消耗自身响应配额 |

抗串谋强化：`min_distinct_validators`（consensus.py:313，现有）扩展为
`min_distinct_scopes`（证据层）——同一组织 scope 内的互证在计数时折价为 1。

## 9. 威胁模型与诚实的能力边界

| 威胁 | L1 缓解 | L2 缓解 | 残余风险（必须对论文/用户诚实声明） |
|------|--------|--------|------|
| 懒惰执行者（自报未执行） | 签名回执使其可归责 | 挑战 + 重放 | **L1 无法检测**；L2 依赖挑战覆盖率 |
| 串谋 attestor（互证） | — | distinct-scope 要求 + 推翻重罚 | 多身份女巫攻击需 DID 层外的身份锚，超出 Lite 范围 |
| 重放抄袭（抄 output hash） | — | commit–reveal（§5.6） | 确定性能力可缓存旧答案 → 挑战种子必须新鲜且不可预测 |
| refute 刷屏（恶意差评） | 必须附 evidence_ref | 误判损害自身 accuracy | 治理仲裁有成本，需要速率限制 |
| 选择性披露（只记成功） | — | 挑战响应率公开可见 | **两次挑战之间的静默失败不可见**——L1/L2 的根本局限，只有 L3 能闭合 |

一句话：EAL 把"无成本的声称"变成"有代价的声称"，把"不可见的懒惰"变成"可观测的信号"——
它不声称解决预言机问题，它声称把预言机问题**约束到可管理的范围**。

## 10. 分阶段路线图

| 阶段 | 版本 | 内容 | 验收 |
|------|------|------|------|
| **Phase 1** | v0.7.0 | ExecutionLog 链类型 + EXECUTE/EXEC_ANCHOR + `adl:execution` spec + 公理 13–15 + CLI（`adl-lite execute record/anchor/log`）；**置信度/状态零改动（纯可观察性）** | 单测 + E31 |
| **Phase 2** | v0.8.0 | ATTEST + 重放 harness + 证据加权置信度（默认关）+ refute→DEPRECATE 提案 + 校准自举接线 | 单测 + E32 |
| **Phase 3** | v0.9.0 | CHALLENGE commit–reveal + 响应率指标 + TEE/zk schema 插口 | 单测 + E33 |

新实验（28 个已注册实验之外）：

- **E31 懒惰验证者可检测性**：有/无 EAL 下，注入不执行的假验证者，测量检测率与单次检测成本。
  直接回应"oracle problem"审稿攻击点——建议纳入 AO 论文评估节。
- **E32 证据加权 vs 裸 G-Counter**：对抗性验证场景下，两种置信度派生的长期准确率对比。
- **E33（Phase 3）**：挑战–响应博弈仿真：理性懒惰执行者在不同挑战频率下的期望收益拐点。

## 11. 待决策点（请拍板）

| # | 问题 | 选项 | 建议 |
|---|------|------|------|
| D1 | 证据存放架构 | A 主链 / B 独立 / C 混合 | **C**：主链 O(治理)，日志走冷存储 |
| D2 | Phase 1 是否纯可观察性（不动 confidence/status） | 是 / 否 | **是**：先立证据，再动派生，保护 T9 证明 |
| D3 | 反驳语义 | 扣 confidence / 推 status 前移 | **推 status**：保单调性、防 griefing |
| D4 | 是否纳入 AO 论文（E31/E32 作为对 oracle-problem 批评的回应） | 纳入 / 纯工程 | **纳入**：这是审稿人最可能攻击的点，值得用实验回应 |
| D5 | `adl:execution` spec 是否成为新注册能力的 strict-template 必填 | 必填 / 可选 | **必填（新注册）+ 存量豁免**：没有 spec 的 ATTEST 是空话 |

## 12. 明确排除（本次不做）

- zk-proof / TEE 的实际集成（仅 schema 插口）
- 代币、质押、罚没等经济机制
- 对存量链的任何迁移（纯新增，后向兼容）
- 跨组织锚定联邦（B4）——另一独立 backlog 项，可在 EAL 落地后复用 EXEC_ANCHOR 机制
