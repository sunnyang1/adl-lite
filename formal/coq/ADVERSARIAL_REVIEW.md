# ADL Lite Coq 形式化 — 对抗性审查报告（第一性原理）

**审查范围**: `formal/coq/theories/` 全部 6 个文件  
**审查方法**: 第一性原理 + 对抗性构造（试图找反例）  
**Coq 版本**: 8.18.0  
**审查日期**: 2026-04-26

---

## 1. 执行摘要

| 严重程度 | 数量 | 类别 |
|----------|------|------|
| 🔴 阻断性 | 1 | 未完成引理 `fold_left_status_max_eq_validated_implies_in`（T6 依赖） |
| 🟡 高 | 4 | 公理化消减（Axioms 4-12 = `True`）、event_id 碰撞、actor 验证过弱、confidence 无界 |
| 🟢 中 | 3 | 证明风格脆弱性、缺失不变式、scale 不一致 |
| ⚪ 低 | 2 | 文档/命名、CRDT 前提可证性 |

**结论**: 核心 Status 格和 Event 映射是可靠的；T1/T2/T3/T4/T5/T7 的机器证明成立；**T6 依赖一个 `Admitted` 引理**；CRDT 代数性质在额外前提 `branch_compat` 下成立。主要风险在于 **9 个安全/密码学公理被消减为 `True`**，使形式化在安全属性上存在根本性缺口。

---

## 2. 逐层审查

### 2.1 Status 格（Status.v）

#### 2.1.1 格的完备性 ✅

`status_rank` 定义了全序：
```coq
PROVISIONAL(0) < FORKED(1) < VALIDATED(2) < DEPRECATED(3) < ARCHIVED(4)
```

`status_lub` 对 `nil` 返回 `PROVISIONAL`（rank 0），这是正确的——空链的最小上界是最小元。

**对抗性测试**: 是否存在两个 status 没有 LUB？不存在，因为全序的任意子集都有 LUB（最大值）。`status_max` 使用 `Nat.leb` 实现，覆盖所有 5×5=25 种组合。

**验证**: `status_max_comm`, `status_max_upper_bound`, `status_max_least` 均机器证明通过。格的性质（自反、传递、上界、最小上界）完整。

#### 2.1.2 `fold_left_status_max_eq_validated_implies_in` — 🔴 阻断性缺口

```coq
Lemma fold_left_status_max_eq_validated_implies_in : forall (ss : list status) (acc : status),
  status_rank acc <= 2 ->
  fold_left status_max ss acc = VALIDATED ->
  In VALIDATED ss / acc = VALIDATED.
Admitted.
```

**为什么重要**: T6（`status_confidence_consistency`）直接依赖此引理。如果该引理不成立，则 T6 无法保证 "VALIDATED status 蕴含存在 VALIDATE 事件"。

**第一性原理分析**:
- 前提 `status_rank acc <= 2` 限制 `acc` ∈ {PROVISIONAL, FORKED, VALIDATED}
- 如果 `acc = VALIDATED`，结论直接成立（`acc = VALIDATED`）
- 如果 `acc = PROVISIONAL` 或 `FORKED`，需要证明 `fold_left status_max ss acc = VALIDATED` 蕴含 `VALIDATED ∈ ss`
- 关键观察：`status_max` 的单调性——如果 `acc` 的 rank ≤ 2，且 `ss` 中所有元素的 rank ≤ 2，则 `fold_left` 结果 rank ≤ 2。所以要得到 `VALIDATED`（rank 2），必须 `ss` 中有 `VALIDATED` 或 `acc = VALIDATED`。
- 但 `status_rank` 是 `nat`，`status_max` 选择较大 rank。如果 `ss` 中有 `DEPRECATED`（rank 3），`fold_left` 结果可能是 `DEPRECATED` 而非 `VALIDATED`。但前提 `fold_left = VALIDATED` 已经排除了这种情况。

**对抗性构造尝试**:
1. `acc = PROVISIONAL`, `ss = [DEPRECATED]` → `fold_left = DEPRECATED ≠ VALIDATED` ❌
2. `acc = FORKED`, `ss = [PROVISIONAL, FORKED]` → `fold_left = FORKED ≠ VALIDATED` ❌
3. `acc = PROVISIONAL`, `ss = [VALIDATED]` → `fold_left = VALIDATED`, `VALIDATED ∈ ss` ✓
4. `acc = FORKED`, `ss = [VALIDATED]` → `fold_left = VALIDATED`, `VALIDATED ∈ ss` ✓

看起来引理是成立的。但**机器证明未完成**，在投稿前必须补上。

**建议补证策略**:
```coq
Proof.
  induction ss as [| s ss' IH]; simpl; intros acc Hrank Heq.
  - right. apply Heq.  (* ss = nil, fold_left = acc = VALIDATED *)
  - destruct (status_rank s <=? status_rank acc) eqn:Hle.
    + (* s 的 rank <= acc, status_max 选 acc *)
      apply IH in Heq; [ | apply Hrank | ].
      * destruct Heq; [ left; right; apply H | right; apply H ].
      * admit. (* 需要证明 status_rank (status_max acc s) <= 2 *)
    + (* s 的 rank > acc, status_max 选 s *)
      (* 如果 s = VALIDATED, 结论成立；否则对 ss' 用 IH *)
      admit.
Admitted.
```

实际上，补证需要归纳法，但 `status_rank` 的 nat 比较可以通过 `destruct s` 简化。

#### 2.1.3 `status_lub_append` 的 soundness ✅

```coq
Lemma status_lub_append : forall (ss : list status) (s : status),
  status_lub (ss ++ [s]) = status_max (status_lub ss) s.
```

**对抗性审查**: `status_lub` 对 `nil` 返回 `PROVISIONAL`。
- `ss = nil`: `status_lub [s] = s`, `status_max PROVISIONAL s = s` ✓
- `ss = [s0]`: `status_lub [s0, s] = status_max s0 s`, `status_max (status_lub [s0]) s = status_max s0 s` ✓
- `ss = [s0, s1]`: `status_lub [s0, s1, s] = fold_left status_max [s1, s] s0 = status_max (status_max s0 s1) s`, `status_max (status_lub [s0, s1]) s = status_max (status_max s0 s1) s` ✓

通过 `fold_left_status_max_app` 的分配律，证明是正确的。

---

### 2.2 Event 模型（Event.v）

#### 2.2.1 `StatusOf` 映射的正确性

```coq
Definition StatusOf (et : adl_event_type) : status :=
  match et with
  | REGISTER   => PROVISIONAL
  | VALIDATE   => VALIDATED
  | DEPRECATE  => DEPRECATED
  | FORK       => FORKED
  | ARCHIVE    => ARCHIVED
  | RELATE     => PROVISIONAL
  | EVIDENCE   => PROVISIONAL
  | SEAL       => PROVISIONAL
  | ANNOUNCE   => PROVISIONAL
  | SNAPSHOT   => PROVISIONAL
  end.
```

**对抗性审查**: 只有 `VALIDATE` 产生 `VALIDATED`。这与论文 §4.2 "Status is derived from EventChain" 一致。`SNAPSHOT` 映射到 `PROVISIONAL` 而非 `VALIDATED`——这是正确的，因为 `SNAPSHOT` 是 front matter 的重建事件，不提升 status。

**引理 `StatusOf_eq_VALIDATED`**:
```coq
Lemma StatusOf_eq_VALIDATED : forall (et : adl_event_type),
  StatusOf et = VALIDATED <-> et = VALIDATE.
```

证明通过 `destruct et; simpl; try discriminate` 完成。覆盖了所有 10 种事件类型。✅

#### 2.2.2 Record `event` 的对抗性风险

```coq
Record event : Set := mkEvent {
  event_id    : nat;
  actor       : string;
  event_type  : adl_event_type;
  confidence  : nat;
  prev        : option nat
}.
```

🟡 **高: `event_id` 是 `nat` 而非 cryptographic hash**

- 在真实系统中，`event_id` 是 SHA-256 hash，碰撞概率可忽略
- 在 Coq 中，`event_id` 是 `nat`，攻击者可以**精确构造**两个不同事件但相同 `event_id`
- `distinct_ids` 要求 `event_id` 唯一，但**不保证事件内容唯一**
- 攻击者可以替换一个事件的内容但保持 `event_id` 不变，从而破坏 `axiom_prev_linkage` 而不破坏 `distinct_ids`

**建议**: 在形式化中增加 `event_id = hash(event_content)` 的约束，或者将 `event_id` 类型改为 `string`（表示 hash）并增加碰撞抵抗假设。

🟡 **高: `actor` 验证太弱**

```coq
Definition axiom_valid_event (e : event) : Prop :=
  actor e <> EmptyString.
```

- 攻击者设 `actor = " "`（空格）或 `"x"` 就通过验证
- 在真实系统中，actor 是 DID（`did:key:z6Mk...`），需要 DID 格式验证和签名验证
- `axiom_signature_verification` 在 Chain.v 中被定义为 `True`

🟡 **高: `confidence` 无上界约束**

- `confidence` 是 `nat`，没有 `[0, 1]` 或 `[0, 100]` 的 clamp 约束
- `axiom_confidence_clamped` 在 Chain.v 中被定义为 `True`
- 攻击者可以设 `confidence = 2^64`，破坏 `gamma_agg` 的 scale 假设（`MAX_SCALED = 100`）
- 虽然 `gamma_agg` 用 `min MAX_SCALED` 限制，但 `derived_confidence` 不受限制

---

### 2.3 Confidence 推导（Confidence.v）

#### 2.3.1 `derived_confidence_events` 的 G-Counter 语义 ✅

```coq
Definition derived_confidence_events (es : list event) : nat :=
  max_confidence
    (filter (fun e =>
      match event_type e with
      | VALIDATE => true
      | SNAPSHOT => true
      | _        => false
      end) es).
```

**对抗性审查**:
- `filter` 只保留 `VALIDATE` 和 `SNAPSHOT`，符合论文 G-Counter (max) 语义
- `max_confidence` 是 `Nat.max` 的 fold，是单调的
- `confidence_monotonicity_default` 证明：`append VALIDATE` 不降低 confidence ✅

#### 2.3.2 `confidence_boundedness` 的 soundness ✅

```coq
Theorem confidence_boundedness : forall (es : list event) (e : event),
  In e es -> confidence e <= max_confidence es.
```

证明通过列表归纳，`Nat.le_max_l` 和 `Nat.le_max_r` 完成。✅

#### 2.3.3 `gamma_agg` 的对抗性审查

```coq
Definition gamma_agg (es : list event) : nat :=
  let ves := validate_events es in
  let actors := unique_actors (actors_of ves) in
  let n := List.length actors in
  if n =? 0 then 0
  else
    let c_base := Nat.max BASE_FLOOR (mean_actor_max actors ves) in
    let bonus := BONUS_INC * (n - 1) in
    Nat.min MAX_SCALED (c_base + bonus).
```

**第一性原理分析**:
- `BASE_FLOOR = 50`（0.5 scaled）
- `BONUS_INC = 5`（0.05 scaled）
- `MAX_SCALED = 100`（1.0 scaled）
- `c_base` 是 per-actor max confidence 的均值，但 **floor division**（`sum / n`）
- `bonus` 是 `5 * (n-1)`，当 `n = 11` 时，`bonus = 50`，`c_base >= 50`，所以 `c_base + bonus >= 100 = MAX_SCALED`
- `n = 12` 时，`bonus = 55`，即使 `c_base = 50`（最小），`c_base + bonus = 105 > 100`，`min` 截断到 100

**对抗性构造**:
- 攻击者创建 1 个 actor，confidence = 0 → `c_base = max(50, 0) = 50`, `bonus = 0` → `gamma_agg = 50` ✓
- 攻击者创建 11 个 actor，每个 confidence = 0 → `c_base = 50`, `bonus = 50` → `gamma_agg = 100` ✓
- 攻击者创建 12 个 actor，每个 confidence = 0 → `c_base = 50`, `bonus = 55` → `min 100 105 = 100` ✓
- 攻击者创建 100 个 actor → `bonus = 495`, `c_base = 50` → `min 100 545 = 100` ✓

**结论**: `gamma_agg` 的 boundedness 是可靠的，因为 `min MAX_SCALED` 始终截断。但 `mean_actor_max` 的 floor division 引入了信息损失——`mean` 可能低估真实均值。这是论文中已知的设计选择。

🟢 **中: `gamma_agg` 与 `derived_confidence` 的 scale 不一致**

- `gamma_agg` 返回 `[0, 100]` 的 scaled 值
- `derived_confidence` 返回 `nat`（未 scaled）
- 在论文中，`gamma_agg` 是 "bonus formula"，而 `derived_confidence` 是 "G-Counter max"
- 两个概念在代码中未统一 scale，但这是设计意图（`gamma_agg` 用于聚合， `derived_confidence` 用于默认）

---

### 2.4 Chain 良好形成性（Chain.v）

#### 2.4.1 `well_formed` 的 13 个合取子项

```coq
Definition well_formed (es : chain) : Prop :=
  (forall e, In e es -> axiom_valid_event e)
  /\ distinct_ids es
  /\ axiom_increasing_ids es
  /\ axiom_prev_linkage es
  /\ axiom_scope_acl es           (* True *)
  /\ axiom_precondition_eval es     (* True *)
  /\ axiom_signature_verification es (* True *)
  /\ axiom_shacl_constraints es     (* True *)
  /\ axiom_status_transition es     (* True *)
  /\ axiom_confidence_clamped es    (* True *)
  /\ axiom_lifecycle_monotonic es   (* True *)
  /\ axiom_validator_collusion es   (* True *)
  /\ axiom_synthetic_tagging es.     (* True *)
```

🟡 **高: 9 个安全公理被消减为 `True`**

这是形式化中**最严重的系统性缺口**。在论文中，这些公理对应：
- `axiom_scope_acl`: 范围 ACL（scope prefix rules）
- `axiom_precondition_eval`: 前置条件评估（Comparator enum，无 `eval()`）
- `axiom_signature_verification`: 签名验证（Ed25519 / secp256k1）
- `axiom_shacl_constraints`: SHACL 约束验证
- `axiom_status_transition`: 状态转换合法性
- `axiom_confidence_clamped`: confidence 截断到 [0, 1]
- `axiom_lifecycle_monotonic`: 生命周期单调性
- `axiom_validator_collusion`: 合谋抵抗（N_min 验证器）
- `axiom_synthetic_tagging`: 合成事件标记

**对抗性影响**:
- 攻击者可以提交 `confidence = 1000` 的事件，不破坏 `well_formed`（因为 `axiom_confidence_clamped = True`）
- 攻击者可以伪造 `actor = "attacker"` 的签名，不破坏 `well_formed`（因为 `axiom_signature_verification = True`）
- 攻击者可以执行非法状态转换（如 `VALIDATED -> PROVISIONAL`），不破坏 `well_formed`（因为 `axiom_status_transition = True`）

**建议**: 在论文的 "Formalization Limitations" 章节中明确声明这些公理被消减为 `True`，并说明未来工作将逐条形式化。

#### 2.4.2 `valid_append` 的 soundness

```coq
Definition valid_append (es : chain) (e : event) : Prop :=
  match es with
  | nil =>
      prev e = None /\ axiom_valid_event e
  | _ :: _ =>
      event_id (last es e) < event_id e /\    (* 严格递增 *)
      prev e = Some (event_id (last es e)) /\   (* prev 链接 *)
      axiom_valid_event e                       (* 结构有效 *)
  end.
```

✅ **正确**: `valid_append` 捕捉了 append-only 链的核心约束：
1. ID 严格递增（防回滚）
2. prev 链接到上一个事件 ID（防篡改）
3. actor 非空（基本验证）

**对抗性测试**:
- 攻击者试图 append 一个 `event_id` 更小的事件 → `valid_append` 拒绝（`event_id (last es e) < event_id e` 不成立）✓
- 攻击者试图修改中间事件 → 无法做到，因为 `valid_append` 只扩展链，不修改已有事件 ✓
- 攻击者试图 fork 一个无效链 → `fork_determinism` 的前提 `well_formed parent` 和 `valid_append parent fork_event` 阻止 ✓

#### 2.4.3 `well_formedness_preservation` 的完整性

```coq
Theorem well_formedness_preservation : forall (es : chain) (e : event),
  well_formed es -> valid_append es e -> well_formed (es ++ [e]).
```

**对抗性审查**:
- 证明对 `all_events_valid_append`, `distinct_ids_append`, `increasing_ids_append`, `prev_linkage_append` 分别调用
- 后 9 个公理用 `all: auto.` 解决（因为它们都是 `True`）
- 如果未来将这些公理替换为实际定义，所有使用 `all: auto.` 的证明需要重写

🟢 **中: 证明风格脆弱性**

`all: auto.` 在公理为 `True` 时有效，但在公理复杂化后会失效。建议在 `repeat split` 后显式处理每个子项，或至少保留注释说明哪些子项被 `auto` 覆盖。

---

### 2.5 不变式（Invariants.v）

#### 2.5.1 T1: `derived_status_is_lub` ✅

```coq
Theorem derived_status_is_lub : forall (es : chain),
  well_formed es ->
  (forall s, In s (map StatusOf (map event_type es)) -> status_leq s (derived_status es))
  /\ (forall b, (forall s, In s (map StatusOf (map event_type es)) -> status_leq s b) ->
       status_leq (derived_status es) b).
```

- 第一子项：每个事件的 status 都 ≤ derived_status（上界性质）
- 第二子项：derived_status 是最小上界（最小性）
- 证明直接调用 `status_lub_upper_bound` 和 `status_lub_least` ✅

**对抗性审查**: 如果 `StatusOf` 的映射不完整（如新增事件类型未映射），则 `status_lub` 可能返回错误值。但 `StatusOf` 覆盖了所有 `adl_event_type` 构造子， exhaustive match 保证完整性。

#### 2.5.2 T2: `fork_determinism` ✅

当前 T2 已证明 6 个性质：

| 性质 | 证明状态 | 依赖 |
|------|----------|------|
| `well_formed (parent ++ [fork_event])` | ✅ | `well_formedness_preservation` |
| `well_formed ([child_register])` | ✅ | `well_formedness_preservation` + `well_formed []` |
| `derived_status = max(original, FORKED)` | ✅ | `derived_status_append_fork` |
| `derived_status child = PROVISIONAL` | ✅ | `unfold derived_status; simpl` |
| `derived_confidence parent unchanged` | ✅ | `fork_preserves_confidence` |
| `derived_confidence child = 0` | ✅ | `child_register_confidence_zero` |

**对抗性审查**: T2 要求 `valid_append nil child_register`。如果攻击者试图创建一个 `child_register` 的 `prev` 不是 `None`，`valid_append` 会拒绝。这是正确的，因为 child chain 的 REGISTER 事件必须是链的第一个事件。

#### 2.5.3 T3: `status_monotonic` ✅（在 Status.v 中）

```coq
Theorem status_monotonic : forall (prefix suffix : list status),
  status_leq (status_lub prefix) (status_lub (prefix ++ suffix)).
```

**对抗性审查**: `status_monotonic` 证明了添加后缀不会降低 status。这是正确的，因为 `status_lub` 是 max 操作，append 只会增加或保持元素。如果攻击者试图 append 一个 "降级" 事件（如 `DEPRECATED` 到 `PROVISIONAL` 链），status 会**提升**到 `DEPRECATED` 而非降低。这与 "status never regresses" 的语义一致——**regress 是指不能从 VALIDATED 回到 PROVISIONAL，但提升到 DEPRECATED 是允许的**。

#### 2.5.4 T4: `confidence_boundedness` ✅

```coq
Theorem confidence_boundedness_chain : forall (es : chain) (e : event),
  In e es -> confidence e <= max_confidence es.
```

**对抗性审查**: 如果 `confidence` 未 clamped（`axiom_confidence_clamped = True`），`max_confidence` 可以任意大。但 boundedness 定理本身仍然成立——它说的是 "任何事件的 confidence ≤ 链的最大 confidence"，这是 `Nat.max` 的 trivial 性质。

#### 2.5.5 T5-γ_agg: `gamma_agg_boundedness_chain` ✅

```coq
Theorem gamma_agg_boundedness_chain : forall (es : chain),
  gamma_agg es <= MAX_SCALED.
```

**对抗性审查**: `gamma_agg` 的 `n = 0` 分支返回 0，否则 `min MAX_SCALED (...)`。`Nat.le_min_l` 保证结果 ≤ `MAX_SCALED`。✅

#### 2.5.6 T6: `status_confidence_consistency` ⚠️ 依赖 Admitted 引理

```coq
Theorem status_confidence_consistency : forall (es : chain),
  well_formed es ->
  derived_status es = VALIDATED ->
  exists e, In e es /\ event_type e = VALIDATE.
```

**证明结构分析**:
1. `destruct es`：空链不可能 `derived_status = VALIDATED`（`status_lub [] = PROVISIONAL`）
2. `remember (StatusOf (event_type e)) as s0`
3. `destruct s0` 覆盖 5 种 status：
   - `PROVISIONAL` / `FORKED`: 调用 `fold_left_status_max_eq_validated_implies_in` → `Admitted` ⚠️
   - `VALIDATED`: 第一个事件就是 `VALIDATE`，直接构造存在性证明 ✅
   - `DEPRECATED` / `ARCHIVED`: 用 `fold_left_status_max_acc_leq` 导出矛盾 ✅

**对抗性审查**: 如果 `Admitted` 引理不成立，攻击者可以构造一个 chain：
- 第一个事件是 `REGISTER`（`PROVISIONAL`）
- 后续事件都是 `RELATE`/`EVIDENCE`/`SEAL`/`ANNOUNCE`/`SNAPSHOT`（都是 `PROVISIONAL`）
- 但 `derived_status = VALIDATED`（通过某种方式）

这在 `StatusOf` 的语义下是不可能的（只有 `VALIDATE` 产生 `VALIDATED`），但需要通过 `fold_left_status_max` 的归纳证明来确认。`Admitted` 缺口意味着这个证明在机器层面不完整。

#### 2.5.7 T7: `well_formedness_preservation` ✅

已在 Chain.v 中证明，见 2.4.3。

---

### 2.6 CRDT 合并（CRDT.v）

#### 2.6.1 `event_content` 忽略 `prev` ✅

```coq
Definition event_content (e : event) : nat * string * adl_event_type * nat :=
  (event_id e, actor e, event_type e, confidence e).
```

**对抗性审查**: `prev` 字段被排除在 `event_content` 之外。这是正确的，因为 `reanchor` 操作会重写 `prev` 以建立新的链式链接。如果 `prev` 被包含在 content 中，reanchor 后的事件会与原始事件不同，破坏 CRDT 的幂等性。

#### 2.6.2 `branch_compat` 的前提必要性

```coq
Definition branch_compat (b1 b2 : branch) : Prop :=
  forall e1 e2, In e1 b1 -> In e2 b2 -> event_id e1 = event_id e2 -> e1 = e2.
```

**对抗性审查**: `branch_compat` 要求：如果两个分支共享一个 `event_id`，则事件必须相同。这不是 `well_formed` 的推论——`well_formed` 只保证单分支内 `distinct_ids`，不保证跨分支唯一性。

**攻击场景**: 两个独立 agent 创建了两个不同内容但相同 `event_id` 的事件（因为 `event_id` 是 `nat` 而非 hash）。`branch_compat` 假设不成立，但 `merge_branch` 仍会成功，因为 `merge_branch` 基于 `event_id` 去重和排序。结果可能是：合并后的链包含一个 "错误" 事件（因为去重只保留一个，但两个事件内容不同）。

⚪ **低: 需要论证 `branch_compat` 的可证性**

在真实系统中，`event_id` 是 hash，碰撞概率可忽略。在形式化中，如果 `event_id` 改为 hash 类型，`branch_compat` 可以从 `well_formed` 的 hash 碰撞抵抗假设导出。当前形式化中，`branch_compat` 是额外的用户假设，不是 `well_formed` 的推论。

#### 2.6.3 `merge_branch` 的 well-formedness preservation ✅

```coq
Theorem merge_preserves_well_formed : forall b1 b2 : branch,
  well_formed b1 -> well_formed b2 -> well_formed (merge_branch b1 b2).
```

证明调用 `all_events_valid_merge`, `distinct_ids_merge`, `increasing_ids_merge`, `reanchor_linkage`。但后 9 个公理仍用 `all: auto.` 解决。✅（在当前简化假设下）

#### 2.6.4 CRDT 代数性质 ✅

| 性质 | 证明 | 前提 |
|------|------|------|
| `merge_commutative` | ✅ | `branch_compat` |
| `merge_associative` | ✅ | `branches_compat3` |
| `merge_idempotent` | ✅ | `well_formed b` |

**对抗性审查**: `merge_idempotent` 的证明基于 `sort_dedup_content_eq_idem`，它证明 `merge_branch b b` 和 `merge_branch b nil` 都产生 `normalized_ids` 后的排序去重列表。因为 `b ++ b` 的 `event_content` 集合与 `b ++ nil` 相同（去重后），所以结果相等。这是正确的，因为 `merge_branch` 的核心操作是 `sort_by_id` + `dedup_by_id`，与 `b` 的重复无关。

---

## 3. 证明工程风险

### 3.1 `all: auto.` 的脆弱性

在 `well_formedness_preservation` 和 `merge_preserves_well_formed` 中，后 9 个公理子项用 `all: auto.` 解决。这是因为它们当前都是 `True`。一旦替换为实际定义，所有相关证明会失效。

**建议**: 在 `repeat split` 后显式注释哪些子项被 `auto` 覆盖，或者为每个公理子项写独立的 lemma，然后组合。

### 3.2 `Admitted` 引理的传播

`fold_left_status_max_eq_validated_implies_in` 被 `T6` 直接依赖。如果该引理不成立，整个 T6 失效。`Admitted` 在 Coq 中相当于 "假设此引理成立"，在机器证明中是最强的逻辑缺口。

**建议**: 在投稿前必须完成此引理的证明。预计工作量：1-2 小时的 Coq 证明（通过 `destruct` 和 `induction` 结合 `status_rank` 的比较）。

### 3.3 `event_id` 的 nat 类型

`event_id` 使用 `nat` 而非 `string` 或 `bytes` 类型，这在形式化中是常见的简化，但在对抗性审查中需要明确：
- 攻击者可以暴力猜测 `event_id`
- `event_id` 碰撞可以被精确构造
- 没有 hash 的单向性保证

**建议**: 在论文中声明 "形式化中 `event_id` 为 `nat`，实际系统使用 SHA-256，碰撞概率可忽略"。

---

## 4. 审查结论

### 4.1 已可靠证明的定理

| 定理 | 状态 | 说明 |
|------|------|------|
| T1: Status LUB | ✅ | `status_lub` 的完整格性质 |
| T2: Fork Determinism | ✅ | 6 个性质全部机器证明 |
| T3: Status Monotonicity | ✅ | `prefix ++ suffix` 不降低 status |
| T4: Confidence Boundedness | ✅ | G-Counter max 的 trivial 上界 |
| T5: γ_agg Boundedness | ✅ | `min MAX_SCALED` 保证 |
| T7: Well-formedness Preservation | ✅ | `valid_append` 保持所有结构约束 |
| T9: CRDT Merge | ✅ | 交换、结合、幂等 + well-formedness |

### 4.2 需要完成的缺口

| 缺口 | 严重程度 | 建议行动 |
|------|----------|----------|
| `fold_left_status_max_eq_validated_implies_in` | 🔴 | 必须在投稿前完成机器证明 |
| 9 个公理消减为 `True` | 🟡 | 在论文 "Limitations" 中声明；未来工作逐条形式化 |
| `event_id` 碰撞假设 | 🟡 | 在论文中声明形式化使用 `nat` 简化；实际系统使用 SHA-256 |
| `actor` / `confidence` 验证 | 🟡 | 在论文中声明形式化简化；实际系统使用 DID 验证和 [0,1] clamp |
| `branch_compat` 可证性 | ⚪ | 在论文中声明需要 `event_id` 作为 hash 的额外假设 |
| `all: auto.` 脆弱性 | 🟢 | 重构为显式子项处理，或至少保留注释 |

### 4.3 第一性原理总结

ADL Lite 的 Coq 形式化**核心代数结构**（Status 格、Event 映射、G-Counter confidence、CRDT 合并）是可靠的。机器证明覆盖了论文中声明的 T1/T2/T3/T4/T5/T7/T9。

**唯一阻断性缺口**是 T6 依赖的 `Admitted` 引理。该引理在数学上是成立的（可通过 `status_rank` 的归纳证明），但尚未完成机器证明。

**系统性风险**在于 9 个安全公理被消减为 `True`。这并不意味着形式化 "错误"——而是 "不完整"。在论文中明确声明这些公理被简化，可以将其归类为 "known limitation" 而非 "bug"。

---

## 附录：Admitted 引理的补证策略

```coq
Lemma fold_left_status_max_eq_validated_implies_in : forall (ss : list status) (acc : status),
  status_rank acc <= 2 ->
  fold_left status_max ss acc = VALIDATED ->
  In VALIDATED ss / acc = VALIDATED.
Proof.
  (* 策略：对 ss 归纳，对 acc 和 s 做 destruct 覆盖所有 status 组合 *)
  induction ss as [| s ss' IH]; simpl; intros acc Hrank Heq.
  - (* ss = nil: fold_left = acc = VALIDATED *)
    right. apply Heq.
  - (* ss = s :: ss' *)
    destruct acc; destruct s;
      try (simpl in Heq; simpl in Hrank; try lia; try (left; left; reflexivity));
      try (apply IH in Heq; try lia;
           destruct Heq; [ left; right; apply H | right; apply H ]).
    (* 需要处理 status_max 的选择逻辑 *)
Admitted.
```

实际上，更简洁的策略是：
1. `destruct acc` 覆盖 5 种 status
2. 对 `acc = VALIDATED`，直接 `right; reflexivity`
3. 对 `acc = PROVISIONAL/FORKED`，对 `ss` 归纳
4. 在每一步 `destruct s`，利用 `status_max` 的单调性：如果 `acc` 的 rank ≤ 2 且 `status_max acc s` 的 rank = 2（VALIDATED），则要么 `s = VALIDATED`，要么 `acc = VALIDATED`
5. 如果 `s = VALIDATED`，`In VALIDATED (s :: ss')` 成立
6. 如果 `s ≠ VALIDATED` 且 `status_rank s < 2`，则 `status_max acc s = acc`，需要对 `ss'` 用 IH

这个证明大约 20-30 行 Coq 代码，预计 1 小时完成。
