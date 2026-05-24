# ADL Lite — Agent Discovery Language

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ESWC + ISWC 2027 Target](https://img.shields.io/badge/Target-ESWC%20%2B%20ISWC%202027-blue.svg)](https://eswc-conferences.org/)

> **"给 Markdown 戴上语义眼镜——人类看到的是普通 Wiki 页面，Agent 看到的是类型化的概念包、关系图和共识状态。"**

ADL Lite 是一个用于**多智能体系统**的 Markdown-native 发现记录语言。它让多个 LLM-based Agent 能够：

- **结构化记录**新概念发现（Structured Semantic Anchoring）
- **达成跨 Agent 共识**（Concept Consensus Chain）
- **隔离私域/公域知识**（Namespace-scoped access control）
- **形式化验证**关键断言（Formal Seal with Lean4/Coq 引用）

## 定位与架构 (Positioning)

**Markdown-native operational ontology for multi-agent concept consensus** — a lightweight semantic layer on SQLite/NetworkX warm storage (schema + policy contract for agents, not a triple-store replacement). Ontology vs phenomenology: see [`docs/PRD.md`](docs/PRD.md) §2 Design philosophy.

```
Agents / CLI / MCP tools
        ↓
Ontology semantic layer     ← Phase 2+ (schema registry, predicate rules)
        ↓
ADLValidator + ConsensusEngine   ← v0.1 (~60–70% of ontology duties today)
        ↓
ADLMemory (Hot skeleton + Warm SQLite + NetworkX graph)
        ↓
Markdown files (L1 / L2 / L3)
```

| Capability | v0.1 (implemented) | Ontology track (planned) |
|------------|-------------------|--------------------------|
| L3 relation triples → warm `relations` table | ✅ | Predicate registry + strict validation (2a) |
| SSA + scope ACL + status machine | ✅ | Published in `adl_core_ontology.yaml` (2a–2b) |
| Cross-domain `isomorphic-to` in examples | ✅ | Governed property + `mapping_type` rules (2a) |
| `OntologyManager` + `adl-lite ontology` / agent introspection | — | 2b–2c |
| Turtle/OWL export (interop only, no reasoner) | — | Path B, Phase 3 |

Proposal: [`docs/proposals/ONTOLOGY_MIDDLE_LAYER.md`](docs/proposals/ONTOLOGY_MIDDLE_LAYER.md) · Product requirements: [`docs/PRD.md`](docs/PRD.md)

## 设计哲学

[维特根斯坦](https://en.wikipedia.org/wiki/Ludwig_Wittgenstein)：*"我的语言的界限意味着我的世界的界限。"*

LLM 的"世界"确实就是语言的界限。ADL Lite 通过**结构化语义锚定（SSA）**扩展这一界限——不是让 Agent 更好地说，而是让 Agent 更好地**相互理解**。

## 三层语法

```
L1  YAML Front Matter  ← 机器消费：身份、类型、状态、证据引用、作用域
L2  Markdown Body      ← 人类 + LLM：自然语言、[[Wiki Link]]、列表
L3  ```adl:* 代码块   ← Agent 消费：关系图、证据链、形式封印
```

### 完整示例

```markdown
---
adl_type: discovery
adl_id: disc-capital-trap
status: provisional
confidence: 0.84
novelty: 0.91
domain: financial_aml
mechanism: isomorphic_mapping
scope: private/ceiec-aml
provisional_names:
  zh: "资金注意力陷阱"
  en: "Capital Attention Trap"
---

# Capital Attention Trap

我们在 AML 交易网络中发现了一种异常模式...

```adl:relation
source: "Capital Attention Trap"
relation: isomorphic-to
target: "adl://public/concepts/gradient_explosion"
mapping_type: topological
confidence: 0.91
```
```

**人类看到的是**：一篇带 YAML 头的 Markdown Wiki 页面

**Agent 看到的是**：类型化的 `ADLDocument` 对象，包含关系图、证据链、共识状态

## 实施计划

Phase 1 任务分解见 [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md)，产品路线（含 Ontology 中间层）见 [`docs/PRD.md`](docs/PRD.md)，勾选清单见 [`docs/PHASE1_CHECKLIST.md`](docs/PHASE1_CHECKLIST.md)。**论文实验升级**见 [`docs/experiments/PHASE_B_PLAN.md`](docs/experiments/PHASE_B_PLAN.md)。实验复现指南见 [`docs/experiments/REPRODUCE.md`](docs/experiments/REPRODUCE.md)。设计起源见 [`ADL_Lite_对话全记录.md`](ADL_Lite_对话全记录.md)。

## 快速开始

### 安装

```bash
git clone https://github.com/sunnyang1/adl-lite.git
cd adl-lite
pip install -e ".[dev]"
```

### CLI

Normative syntax: [`docs/SPEC.md`](docs/SPEC.md).

```bash
# Parse summary (or JSON)
adl-lite parse examples/capital_reflux_trap.md
adl-lite parse examples/capital_reflux_trap.md -o json

# Validate (exit 1 on errors)
adl-lite validate examples/*.md

# Store and graph neighbors
adl-lite store examples/capital_reflux_trap.md --db my_adl.db
adl-lite related disc-capital-trap --db my_adl.db --depth 2

# Consensus chain (state in adl_consensus.json by default)
adl-lite consensus register examples/capital_reflux_trap.md
adl-lite consensus transition disc-capital-trap --to validated --actor agent_1 --reason "approved"
adl-lite consensus verify disc-capital-trap
```

### 解析文档（Python API）

```python
from adl_lite import parse_file

doc = parse_file("examples/capital_reflux_trap.md")

print(doc.front_matter.status_badge)        # 🟡
print(doc.concept_name)                      # Capital Attention Trap
print(f"Relations: {len(doc.relations)}")    # 2
print(f"Evidence:  {len(doc.evidence)}")     # 3

errors = doc.validate_semantics()
assert len(errors) == 0, f"Validation failed: {errors}"
```

### 存储与检索（Python API）

```python
from adl_lite import ADLMemory, parse_file

mem = ADLMemory(db_path="my_adl.db")
doc = parse_file("examples/capital_reflux_trap.md")
mem.store(doc)

skeleton = mem.hot.get("disc-capital-trap")
related = mem.find_related("disc-capital-trap", depth=2)
for concept, relation, conf in related:
    print(f"  {concept} via {relation} ({conf:.2f})")
```

### 共识管理（Python API）

```python
from adl_lite import ConsensusEngine, DiscoveryStatus

engine = ConsensusEngine()
engine.register(doc)
engine.transition(
    "disc-capital-trap",
    DiscoveryStatus.VALIDATED,
    actor="agent_reviewer_1",
    reason="Cross-agent agreement reached",
)
assert engine.verify_all()["disc-capital-trap"]
```

### Demo（一键端到端）

从发现文档到入库与关联查询，一条命令跑通 parse → validate → store → related：

```bash
# 默认：scripted 示例（capital_reflux_trap + 关联概念）
./scripts/demo_pipeline.sh

# 显式 scripted / 完整 5-agent 模拟
python scripts/demo_pipeline.py --scripted
python scripts/demo_pipeline.py --scripted --sim

# 可选 LLM 发现（无 API key 时优雅跳过）
python scripts/demo_pipeline.py --llm
```

Demo 会在临时 SQLite 库（或 `--db /path/to/demo.db`）中写入示例，并对 `disc-capital-trap` 执行关联查询，最后打印可读摘要。

### 运行测试

```bash
pytest tests/ -v
adl-lite validate examples/*.md
pytest tests/test_demo_pipeline.py -q
```

## 项目结构

```
adl-lite/
├── adl_lite/
│   ├── __init__.py       # 公开 API
│   ├── cli.py            # adl-lite 命令行
│   ├── parser.py         # L1/L2/L3 三层解析器
│   ├── models.py         # Pydantic 语义类型模型
│   ├── validator.py      # SSA 语义验证器
│   ├── consensus.py      # 概念共识链 + 分叉管理
│   └── memory.py         # 三层混合索引 (Hot/Warm/Cold)
├── docs/
│   ├── SPEC.md           # 规范（L1/L2/L3、作用域、状态机）
│   └── IMPLEMENTATION_PLAN.md
├── tests/
│   ├── test_parser.py
│   ├── test_cli.py
│   └── test_scope_access.py
├── examples/
│   ├── capital_reflux_trap.md
│   ├── gradient_explosion.md
│   └── attention_residual_discovery.md
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

## 核心概念

| 术语 | 定义 |
|------|------|
| **SSA** | Structured Semantic Anchoring — 用结构化约束"锁定"自然语言解释空间 |
| **Concept Bundle** | 记忆基本单元：身份 + 语义内容 + 关系图 + 证据链 + 共识状态 + 作用域 |
| **Consensus Chain** | 概念从 provisional → validated → deprecated 的链式共识过程（类区块链） |
| **Formal Seal** | 关键断言的 Lean4/Coq 验证引用，类似"数字印章" |
| **Fork Management** | 同一现象的竞争性解释：合并(>90%同构)/并行(不同领域)/剪枝(长期无引用) |
| **Skeleton** | 概念包的轻量摘要(<500B)，用于 Hot Storage 快速检索 |

## 共识状态徽章

| 徽章 | 状态 | 含义 |
|------|------|------|
| 🟡 | `provisional` | 待验证（默认） |
| 🟢 | `validated` | 已验证 |
| 🔴 | `deprecated` | 已废弃 |
| 🔵 | `forked` | 分叉中 |
| ⚪ | `archived` | 已归档 |

## 作用域隔离

```
adl://public/              ← 全网 Agent 可访问
adl://private/<org>/       ← 组织内隔离
adl://user/<id>/           ← 个人私域
adl://shared/<collab>/     ← 协作组共享
```

## 学术路线

**主投会议**: [ESWC 2027](https://eswc-conferences.org/) + [ISWC 2027](https://iswc2027.semanticweb.org/) — Semantic Web、ontology learning、agentic KG（LLMs4OL / In-Use / Resource 等 track 视 fit 选择）

**备选**: [AAMAS 2027](https://www.aamas-conference.org/) — 多智能体共识与协调链叙事

**研究问题**:

| RQ | 问题 | 假设（探索性） | Phase B pilot（见 [`docs/experiments/RESULTS.md`](docs/experiments/RESULTS.md)） |
|----|------|----------------|----------------------------------|
| RQ1 | SSA 能否降低多 Agent 协作语义歧义？ | 歧义率降低 40%+ | fair-plain LLM-judge **Δ=0**；vs unstructured plain-LLM **~+1.5**；**人工 RQ1 已取消** |
| RQ2 | SSA 能否加速概念共识达成？ | 共识轮数减少 50%+ | 脚本化 **8** transitions vs plain **0**（MiMo 批量不可直接对比） |
| RQ3 | 语义类型+关系图能否提升检索精度？ | Recall@10 +15% | 全量 hit **Δ +0.20**（`n=25`）；L3-only **`q21`–`q25` Δ +1.00** |
| RQ4 | URI 命名空间能否零泄露隔离？ | 泄露率=0%, Recall 损失<5% | **0** leaks；**99/99** probes denied（33 concepts × 3 requesters） |

**实施时间线**:

| 阶段 | 时间 | 产出 |
|------|------|------|
| Phase 1 | 5.23 - 6.30 | Parser + Hybrid Index + 5-Agent 框架 + AML 数据集 |
| Phase 2 | 7.1 - 8.15 | 4 组实验执行 + 统计检验；**Ontology 2a–2c**（见 PRD） |
| Phase 3 | 8.16 - 9.30 | ESWC/ISWC 论文写作 + 内部评审；**Turtle 导出**（Path B，Resource/In-Use 叙事） |
| Phase 4 | 2027 投稿窗 | 主投 ESWC 2027 + ISWC 2027；挂 arXiv |
| 可选冲刺 | 2026-05 前后 | ISWC 2026 Resource — 时间紧，可作 sprint 或顺延至 ISWC 2027 |

## 引用

```bibtex
@software{adl-lite,
  title = {{ADL Lite: Agent Discovery Language for Multi-Agent Concept Consensus}},
  author = {CEIEC AI Infrastructure},
  year = {2026},
  url = {https://github.com/sunnyang1/adl-lite}
}
```

## 许可

MIT License — 详见 [LICENSE](LICENSE)
