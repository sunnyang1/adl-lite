# AML 数据集升级指南

Phase B 需要把 `data/aml/concepts/` 从 **minimal stub** 升级为 **可发表的概念库**。

## 文件结构

```
data/aml/
├── manifest.json      # 概念列表（adl_id, path, scope）
├── queries.json       # 15+ 查询 + relevant adl_id 列表
└── concepts/
    └── aml-*.md       # 每条一个 ADL concept 或 discovery
```

## 单条概念 checklist

- [ ] L1：`adl_type`, `adl_id`, `status`, `confidence`, `scope`, `provisional_names`
- [ ] L2：Definition 段**不用** this/that/it/这个/那个
- [ ] L3：≥1 `adl:relation`，≥1 `adl:evidence`
- [ ] 至少一个 `adl://public/...` 或跨概念 `[[Wiki Link]]`
- [ ] `adl-lite validate data/aml/concepts/<file>.md` 通过

## 查询标注 (`queries.json`)

当前版本 **0.2**：20 条场景化查询，**12 条多标签**。

每条 query：

```json
{
  "id": "q01",
  "text": "customer splits cash deposits across branches staying below currency reporting threshold",
  "relevant": ["aml-smurfing", "aml-ctr-avoid"],
  "difficulty": "medium"
}
```

- `relevant` 由 **AML 领域专家** 标注，可多标签
- 使用场景语言，避免与 `adl_id` 字面重复
- `difficulty`: `medium` / `hard` — 便于分层汇报 Recall@k

**评估：** Phase B RQ3 使用 `tfidf_fair_plain`（plain 去掉 L3，ADL 索引含 relation 谓词/target）。

```bash
python -m experiments.rq3_retrieval --mode phase_b -k 5   # 更严格
python -m experiments.rq3_retrieval --mode phase_b -k 10
```

## 从 stub 升级示例

**Before（stub）：** 一句话 Definition  
**After：** 3 段 — 现象描述、监测特征、与公域概念同构关系（参考 `examples/capital_reflux_trap.md`）

## 验证

```bash
adl-lite validate data/aml/concepts/*.md
python -m experiments.rq3_retrieval --mode phase_b
python -m experiments.rq1_ambiguity --mode phase_b
```

## 目标规模（论文）

| 项 | Phase 1 | Phase B 目标 |
|----|---------|--------------|
| 概念数 | 20 stub | 20 **curated**（可扩 50） |
| 查询数 | 15 | 15–30 expert-labeled |
| 深度 | ~15 行/文件 | ~40–80 行/文件 |
