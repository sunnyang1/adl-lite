# ADL Lite — Event-First Operational Ontology

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ESWC + ISWC 2027 Target](https://img.shields.io/badge/Target-ESWC%20%2B%20ISWC%202027-blue.svg)](https://eswc-conferences.org/)
[![Experiments: 6/6 PASS](https://img.shields.io/badge/experiments-6%2F6%20PASS-brightgreen.svg)]()
[![IBM AML: 495K chains 100% integrity](https://img.shields.io/badge/IBM%20AML-495K%20chains%20100%25%20OK-blue.svg)]()

> **"世界是事件的总和，而非事物的总和" — Wittgenstein, Tractatus Logico-Philosophicus §1.1**

ADL Lite 是 **事件优先 (event-first)** 的 Markdown-native 操作 ontology。每个概念是一个 **追加式、密码学哈希化的 EventChain**。Status/confidence/validators 从不存储为可变字段——全部从事件链计算。

参考 Palantir Foundry Data Engine 的 Ontology 层 (Object Type / Property Type / Link Type / Action Type)，但以 Markdown-native、Git-backed、pip-installable 的形式实现。

## 架构

```
Markdown 概念文件 (L1/L2/L3/L4)
        ↓
ADLParser → ADLDocument + EventChain
        ↓
OntologyManager ← adl_core_ontology.yaml (classes / predicates / actions)
        ↓
ActionExecutor (precondition validation + side effects)
        ↓
ConsensusEngine (append-only transition chain)
        ↓
ADLMemory (Hot skeleton / Warm SQLite+NetworkX / Cold archive)
```

### 四层文档模型

| Layer | 语法 | 角色 | 事件类型 |
|-------|------|------|----------|
| L1 | YAML front matter | 身份元数据 (派生快照) | SNAPSHOT |
| L2 | Markdown body | 人/LLM 叙事 | — |
| L3 | `adl:relation/evidence/seal` | 语义断言 | RELATE, EVIDENCE, SEAL |
| L4 | `adl:action` | 类型化动作 + 前置条件 | REGISTER, VALIDATE, ... |

### 事件优先设计

```python
from adl_lite import Event, EventChain, EventType

chain = EventChain(concept_id="claim-2026-0042")

chain.append(Event(concept_id="claim-2026-0042",
                   event_type=EventType.SUBMIT,
                   actor="claimant",
                   payload={"amount": 420}))

chain.append(Event(concept_id="claim-2026-0042",
                   event_type=EventType.VALIDATE,
                   actor="approver_05",
                   payload={"confidence": 0.85}))

# status 是链计算的，不是存储的
assert chain.status == DiscoveryStatus.VALIDATED
assert chain.confidence == 0.85
assert chain.validators == ["approver_05"]
assert chain.verify_integrity()  # SHA-256 哈希验证
```

## 实验结果 (6/6 PASS)

| # | 实验 | 关键指标 |
|---|------|---------|
| E1 | 事件链完整性 | 50 条有效链 100% pass; 10 条损坏链 100% 检出 |
| E2 | 状态推导准确性 | 2,204 个事件组合 100% 正确推导 |
| E3 | 快照往返一致性 | 38 个概念文件 100% status 匹配 |
| E4 | 前置条件精度 | P=1.0, R=1.0, F1=1.0 (13 个测试用例) |
| E5 | 5-agent 可审计性 | 5/5 链完整性通过 |
| E6 | **IBM AML 真数据管道** | **495,671 条链, 508 万事件, 100% 完整性** |

详见: [`docs/paper/EVENT_FIRST_DRAFT.md`](docs/paper/EVENT_FIRST_DRAFT.md)

## 快速开始

```bash
git clone https://github.com/sunnyang1/adl-lite.git
cd adl-lite
pip install -e ".[dev]"

# 跑所有实验
python -m experiments.runner all

# 列出实验
python -m experiments.runner list

# 跑单个
python -m experiments.runner E2
```

### CLI

```bash
# 验证
adl-lite validate examples/*.md
adl-lite validate --strict examples/*.md

# 解析
adl-lite parse examples/capital_reflux_trap.md

# 共识
adl-lite consensus register examples/capital_reflux_trap.md
adl-lite consensus transition disc-capital-trap --to validated --actor agent_1

# Ontology 查询
adl-lite ontology query --json
```

### Python API

```python
from adl_lite import parse_file, Event, EventChain, EventType
from adl_lite.action_executor import ActionExecutor
from adl_lite.ontology import OntologyManager

# 事件链
doc = parse_file("examples/capital_reflux_trap.md")
chain = doc.event_chain
print(chain.status)           # 从链计算
print(chain.history())         # 完整审计日志

# Action 执行
mgr = OntologyManager()
executor = ActionExecutor(mgr)
errors = executor.validate_action(doc, action_block)

# 数据导入 (IBM AML)
from adl_lite.data_importer import DataImporter
chains = DataImporter().import_csv("HI-Small_Trans.csv",
    event_type=EventType.REGISTER, concept_id_field="Account")
```

## 项目结构

```
adl-lite/
├── adl_lite/
│   ├── models.py            # Event, EventChain, ADLActionBlock, PreconditionRule
│   ├── parser.py            # L1/L2/L3/L4 解析器
│   ├── validator.py         # SSA 验证 + scope ACL
│   ├── consensus.py         # 共识链 + 分叉
│   ├── action_executor.py   # Action 执行 + 前置条件校验
│   ├── data_importer.py     # CSV/JSON → Event 导入
│   ├── ontology.py          # OntologyManager (predicates/actions/transitions)
│   ├── memory.py            # Hot/Warm/Cold 索引
│   ├── tools.py             # Agent 工具集
│   ├── lark/                # 飞书 bridge
│   └── adl_core_ontology.yaml  # v0.2: classes + predicates + actions
├── experiments/
│   ├── base.py              # BaseExperiment + ExperimentResult
│   ├── registry.py          # @register("E1") 装饰器
│   ├── runner.py            # python -m experiments.runner all
│   ├── e1_chain_integrity.py    # 事件链完整性
│   ├── e2_status_derivation.py  # 状态推导准确性
│   ├── e3_snapshot_roundtrip.py # 快照往返
│   ├── e4_precondition.py       # 前置条件
│   ├── e5_agent_audit.py        # 5-agent 审计
│   └── e6_aml_pipeline.py       # IBM AML 全管道
├── docs/
│   ├── paper/EVENT_FIRST_DRAFT.md  # 新论文
│   └── experiments/
├── examples/                # 概念文件示例
├── tests/                   # pytest (111 tests)
└── data/aml/                # AML 概念 + 查询
```

## 核心概念

| 术语 | 定义 |
|------|------|
| **EventChain** | 追加式、密码学哈希化的事件序列。概念即链。 |
| **Event** | 原子事件：event_type, actor, payload, hash, previous_event_id |
| **Event-first** | Status/confidence/validators 从链计算，不存可变字段 |
| **Action Type** | L4 块：声明式动作 + Comparator 前置条件 (无 eval()) |
| **Digital Twin** | 概念的事件链 = 概念的完整数字孪生 (参考 Palantir FDE) |

## 共识状态

| 🟡 provisional | 🟢 validated | 🔴 deprecated | 🔵 forked | ⚪ archived |

## 许可

MIT License — 详见 [LICENSE](LICENSE)
