# Phase B — 论文级实验升级计划

> **目标：** 把 Phase 1 的 pilot 指标升级为可写进论文、可复现、可辩护的实验。  
> **原则：** scripted 数字是 smoke test；Phase B 数字才进 RESULTS 正文。

---

## 与 Phase 1 (pilot) 的区别

| 维度 | Pilot | Phase B |
|------|-------|---------|
| RQ1 baseline | 向 plain 文本**注入**代词 | **配对** fair plain（同 L2，去掉 L3） |
| RQ1 指标 | 代词率 | Rubric：代词 + 实体锚点 + validator |
| RQ3 检索 | token overlap | **TF-IDF** + 关系图 boost |
| 5-Agent | 纯脚本 | 可选 **LLM discoverer**（OpenAI） |
| 数据集 | 生成 stub | 逐步替换为**真实 AML 概念**（见 DATASET_GUIDE） |

---

## 快速开始

```bash
cd adl-lite
pip install -e ".[dev,experiments]"

# Phase B 全套（无 API key）
python -m experiments.run_phase_b

# 小米 MiMo Token Plan（tp- 密钥，中国集群默认）
export MIMO_API_KEY=tp-...
export MIMO_API_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
export MIMO_MODEL=mimo-v2.5-pro
python -m experiments.run_sim --llm

# 或 OpenAI
export OPENAI_API_KEY=sk-...
python -m experiments.run_sim --llm
```

输出：`docs/experiments/summary_phase_b.json`

---

## 四条研究问题 — Phase B 操作手册

### RQ1 — 歧义降低

**脚本：** `experiments/rq1_ambiguity.py --mode phase_b`  
**方法：** 对每条 ADL 文档生成 fair plain 配对，用 `experiments/rubric.py` 比较 composite ambiguity score。

**你要做的：**
1. 把 `examples/` 和 `data/aml/concepts/` 写成**无模糊代词**、实体名显式出现
2. 跑 Phase B，记录 `ambiguity_reduction_pct`
3. （进阶）抽 20 条 LLM 生成发现，**人工 1–5 分** referent clarity，写入 `data/eval/human_rq1.json`

### RQ2 — 共识轮数

**脚本：** `experiments/rq2_consensus.py`  
**Phase B 升级：** 用 `run_sim --llm` 或多次 scripted run，统计到 `validated` 的 transition 数；与「无 chain 的 plain wiki」对比。

**你要做的：**
1. 设计 3 个 discovery 任务（同一现象，2 个 agent 各写一版）
2. 记录 ADL 显式 transition vs plain 的「口头达成一致」轮数（人工或日志）

### RQ3 — 检索 Recall@10

**脚本：** `experiments/rq3_retrieval.py --mode phase_b`  
**方法：** TF-IDF + L3 relation boost vs 无 relation 的 TF-IDF。

**你要做的：**
1. 在 `data/aml/queries.json` 增加 **expert 标注** relevant ids（可多标签）
2. 若 TF-IDF 仍打平，加 `sentence-transformers` 作为 Phase B+（可选依赖）
3. 目标：ADL delta > 0 且 n=15 查询可复现

### RQ4 — 作用域零泄露

**脚本：** `experiments/rq4_leakage.py`  
**现状：** ADL ACL 已可报告 leaks=0。论文中强调 baseline「无 ACL」的 `baseline_leaks_uncontrolled`。

**你要做的：** 保持 0；若加新 scope 规则，补 `tests/test_scope_access.py`

---

## LLM 5-Agent 工作流

| 角色 | Phase B 实现 |
|------|----------------|
| Discoverer | `experiments/llm_harness.py` — OpenAI 生成 ADL MD |
| Reviewer | `ADLValidator` + `ConsensusEngine.transition` |
| Skeptic / Merger / Librarian | 仍用 `harness.py` scripted 或下一轮 LLM 扩展 |

**日志：** `experiments/logs/llm_run.jsonl`（gitignored）  
**产物：** `experiments/outputs/llm_discovery_*.md`

---

## 数据集升级（AML 20 概念）

见 [`docs/DATASET_GUIDE.md`](../DATASET_GUIDE.md)。

优先级：
1. 把 `aml-attention-trap` 扩写为与 `capital_reflux_trap.md` 同级深度
2. 每周替换 3–5 个 stub 为业务真实案例
3. 每条概念至少 1 个 `adl:relation` 指向公域或私域 URI

---

## 论文里程碑建议

| 周 | 产出 |
|----|------|
| 1 | Phase B 跑通 + `summary_phase_b.json` 进 repo |
| 2 | 3 条人工标注 RQ1 + 查询集修订 |
| 3 | 1 次完整 LLM 5-agent 实验 + 日志 |
| 4 | `docs/paper/OUTLINE.md` Method/Evaluation 填入真实数字 |
| 5–8 | 扩 corpus、显著性检验（可选 scipy）、内部审阅 |

---

## 命令对照

```bash
pytest experiments/test_phase_b.py -v   # Phase B 单测
python -m experiments.run_all --phase pilot   # 旧 pilot
python -m experiments.run_all --phase b       # Phase B
```
