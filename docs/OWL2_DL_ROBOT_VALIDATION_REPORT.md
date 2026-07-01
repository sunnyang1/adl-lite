# OWL 2 DL 扩展与 ROBOT 验证报告

## 1. 扩展内容概述

### 1.1 L3 关系谓词的对象属性声明

从 `adl_core_ontology.yaml` 中提取了全部 10 个 L3 关系谓词，在 OWL 2 DL 导出中声明为 `owl:ObjectProperty`：

| 谓词 (kebab-case) | OWL 属性名 (camelCase) | 特征 |
|------------------|----------------------|------|
| `isomorphic-to` | `isomorphicTo` | — |
| `specialisation-of` | `specialisationOf` | `TransitiveProperty` |
| `co-occurs-with` | `coOccursWith` | `SymmetricProperty` |
| `related-to` | `relatedTo` | — |
| `analogical-to` | `analogicalTo` | — |
| `analogical-transfer` | `analogicalTransfer` | — |
| `dual-of` | `dualOf` | `SymmetricProperty` |
| `fork-of` | `forkOf` | — |
| `mitigated-by` | `mitigatedBy` | — |
| `indexed-phrase` | `indexedPhrase` | — |

每个属性均声明了：
- `rdfs:domain` = `adl:Concept`
- `rdfs:range` = `adl:Concept`
- `rdfs:label` 与 `rdfs:comment`

### 1.2 核心类与属性声明

为通过 OWL 2 DL 配置文件验证，补充声明了：
- **7 个 OWL Classes**: `Concept`, `Event`, `discovery`, `concept`, `relation`, `evidence`, `formal_seal`
- **5 个 DatatypeProperties**: `hasConfidence`, `hasDomain`, `hasScope`, `hasActor`, `hasTimestamp`
- **3 个核心 ObjectProperties**: `hasStatus`, `belongsTo`, `validatedBy`

### 1.3 SWRL 完整性规则

嵌入了 2 条 SWRL 规则：

**Rule 1: ValidatedConfidenceRule**
- 前提：概念 `c` 的 `hasStatus` = `status/validated`，且 `hasConfidence` = `conf`
- 结论：`conf >= 0.5`

**Rule 2: NoSelfLoopRule**
- 前提：概念 `c1` 通过 `relatedTo` 与 `c2` 关联
- 结论：`c1 != c2`（禁止自环关系）

### 1.4 SPARQL 约束查询

生成了 3 个独立 SPARQL 约束文件（用于 `robot verify`）：

| 查询文件 | 目的 |
|---------|------|
| `confidence_range.sparql` | 检测 `confidence` 超出 `[0, 1]` 的概念 |
| `no_self_loop.sparql` | 检测 source == target 的自环 L3 关系 |
| `validated_min_confidence.sparql` | 检测 `validated` 状态但 `confidence < 0.5` 的概念 |

## 2. ROBOT 验证结果

### 2.1 语法验证

| 测试项 | 结果 | 说明 |
|--------|------|------|
| rdflib Turtle 解析 | ✅ 通过 | 179 triples 成功解析 |
| ROBOT convert (Turtle → OWL) | ✅ 通过 | 无语法错误 |
| ROBOT convert (RDF/XML → Turtle) | ✅ 通过 | 无语法错误 |

### 2.2 OWL 2 DL 配置文件验证

| 格式 | 结果 |
|------|------|
| Turtle (`adl_extended.ttl`) | ✅ **OWL 2 DL Profile 通过** |
| RDF/XML (`adl_extended.owl`) | ✅ **OWL 2 DL Profile 通过** |

> 初始版本存在 `Cannot pun between properties` 和 `Use of undeclared class` 错误，通过显式声明 `owl:Class`、`owl:ObjectProperty`、`owl:DatatypeProperty` 和 `swrl:varName` 的 `AnnotationProperty` 声明后修复。

### 2.3 一致性检验（Reasoning）

| 推理器 | 结果 | 说明 |
|--------|------|------|
| HermiT | ❌ 不支持 | SWRL built-in atoms (`swrlb:greaterThanOrEqual`, `swrlb:notEqual`) 不被 HermiT 支持（已知限制） |
| Structural | ✅ 通过 | 结构推理器成功完成，输出一致的本体 |

### 2.4 SPARQL 约束验证（ROBOT verify）

**正常本体（`capital_reflux_trap.md`）**

| 约束 | 结果 | 违规数 |
|------|------|--------|
| confidence_range | ✅ PASS | 0 |
| no_self_loop | ✅ PASS | 0 |
| validated_min_confidence | ✅ PASS | 0 |

**故意注入违规（`gradient_explosion.md` 的 confidence 被修改为 0.3）**

| 约束 | 结果 | 违规数 | 检测到的违规 |
|------|------|--------|-------------|
| validated_min_confidence | ❌ FAIL | 1 | `concept-gradient-explosion, 0.3` |

> SPARQL 约束验证能够正确识别并报告违反 `validated` 概念最小置信度约束的实例。

### 2.5 本体度量（ROBOT measure）

```
metric                          value
----                            -----
abox_axiom_count                35
axiom_count                     130
class_count                     7
dataproperty_count              5
individual_count                13
logical_axiom_count             74
obj_property_count              13
ontology_iri                    http://adl-lite.org/ontology/
owl2                            true
owl2_dl                         true
owl2_el                         false
owl2_ql                         false
owl2_rl                         false
signature_entity_count          44
tbox_axiom_count                36
```

## 3. 文件位置

- 扩展后的 OWL 导出模块：`adl_lite/owl_export.py`
- 生成的 Turtle 文件：`/tmp/adl_extended.ttl`
- 生成的 RDF/XML 文件：`/tmp/adl_extended.owl`
- SPARQL 约束文件：`/tmp/sparql_constraints/*.sparql`
- 验证报告文件：`/tmp/robot_metrics.tsv`

## 4. 已知限制与后续工作

1. **HermiT 不支持 SWRL built-in atoms**: 这是 HermiT 推理器的已知限制，非本体错误。SWRL 规则仍可在 Protégé 的 Drools 插件或外部规则引擎中执行。
2. **OWL 2 EL/QL/RL 配置**: 当前本体为 `owl2_dl=true`，但 `owl2_el=false` 等，因为 `TransitiveProperty` 和 `SymmetricProperty` 等特性超出了 EL/QL/RL 的表达能力。
3. **SHACL 约束**: 当前使用 SPARQL 约束进行验证；后续可补充 SHACL 形状文件以支持更丰富的数据验证场景。
