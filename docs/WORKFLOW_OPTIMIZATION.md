# 工作流评估：可循环优化项

## 当前状态快照

| 维度 | 数量 | 说明 |
|------|------|------|
| 论文主文件 | 29 | 7 sections + 9 appendix + 13 supplementary |
| 实验脚本 | 30+ | e1–e25, e6b, e12, e17, e19, e20b, e21, e23, e25 等 |
| LaTeX 标签 | ~200+ | 分布在 29 个 .tex 文件中 |
| 交叉引用 | ~400+ | \ref, \cref, \label, \cite |
| 表格 | ~35 | 含实验数据表、对比表、性质表 |
| 公式 | ~50+ | 含 6 个核心公式 (eq:status-order 等) |
| 总页数 | 81 | 0 编译错误, 0 未定义引用 |

---

## 可循环优化的 7 个工作项

### 1. 🟢 实验结果 → LaTeX 表格（已实现但未全面使用）

**当前状态**：每次新增实验（E27, E28, E29），手动从 JSON 数据复制到 LaTeX `tabular` 环境，手工格式化。

**问题**：
- E27 数据在 `docs/experiments/e27_crdt_merge.json`，但 §5.6 表格是**手打**的
- E28 数据在 `docs/experiments/e28_expert_validation.json`，但 §5.7 表格是**手打**的
- E29 数据在 `docs/experiments/e29_merkle_comparison.json`，但 §5.8 表格是**手打**的

**循环优化方案**：

```python
# experiments/generate_tables.py — 未实现

def json_to_latex_table(json_path, table_id, caption):
    """Auto-generate LaTeX table from experiment JSON."""
    data = load(json_path)
    rows = format_rows(data)  # auto-detect numeric columns
    return latex_table_template(rows, table_id, caption)

# 在 Makefile 中：
# make tables  →  重新生成所有实验表格
```

**收益**：新增实验只需 `python generate_tables.py`，无需手动复制数字。评审人要求修改数据时，改 JSON 重跑即可。

**优先级**：🔴 高 — 每次实验修改都要手动更新 3-5 个表格

---

### 2. 🟢 交叉引用一致性检查（未实现）

**当前状态**：依赖 `latexmk` 编译报错发现 undefined references。但**断裂引用不会报错**（如指向已删除的 subsection）。

**问题场景**：
- §4.5 从 `subsec:formal-semantics` 重命名为 `subsec:compact-formal-spec` 时，需要手动搜索 8 个文件中的引用
- 删除 §6.5 的 `tab:baseline-comparison` 表格时，需要检查是否有其他 section 引用它

**循环优化方案**：

```python
# scripts/check_refs.py — 未实现

def check_all_refs():
    labels = collect_all_labels("docs/paper_ao/**/*.tex")
    refs = collect_all_refs("docs/paper_ao/**/*.tex")
    # 检测：
    # 1. 有 \ref 无 \label (undefined reference)
    # 2. 有 \label 无 \ref (dead label, 可删除)
    # 3. 指向已删除文件的 \ref (file renamed)
    # 4. 同一 label 在多个文件定义
```

**收益**：重命名 section 时自动检测所有引用，避免人工遗漏。上次 §4.5 重命名后，发现 8 处引用需更新。

**优先级**：🟡 中 — 每次结构性重构都会触发，但频率不高

---

### 3. 🟡 重复内容检测（部分实现，未系统化）

**当前状态**：靠人工通读发现重复（如 §1.3 和 §6.2/§7.1 的贡献描述逐句重复）。

**已做的工作**：压缩了 7 处重复（-4 页），但**依赖人工记忆**，没有系统化工具。

**循环优化方案**：

```python
# scripts/check_redundancy.py — 未实现

def find_similar_paragraphs(threshold=0.7):
    """Find paragraphs with >70% cosine similarity across sections."""
    paragraphs = extract_all_paragraphs("docs/paper_ao/**/*.tex")
    for p1, p2 in combinations(paragraphs, 2):
        if similarity(p1.text, p2.text) > threshold:
            report(p1.file, p1.line, p2.file, p2.line, similarity)
```

**检测规则**：
- 排除引用/定义重复（自然允许）
- 检测叙述性段落重复（如 "The contributions are..." 在 §1.3, §6.2, §7.1 中重复）
- 检测表格描述重复（如 `tab:baseline-comparison` 的描述在 §2.1 和 §6.5 中重复）

**收益**：在每次"通读精简"前自动扫描，减少人工阅读量。81 页论文人工通读需要 2-3 小时，工具扫描只需 30 秒。

**优先级**：🟡 中 — 每次 Major Revision 前运行一次

---

### 4. 🟡 公式/定理编号一致性（未实现）

**当前状态**：9 个定理（T1–T9），分布在 §4.5 和 Appendix E。公式编号（eq:status-order 等）是手打的。

**问题**：
- T1–T7 在 §4.5.5 摘要表中，T8 在 §4.5.5 但证明在 Appendix E.5，T9 在 §4.5.5 但证明在 Appendix E.9
- 公式引用 `eq:delta-def` 在 §4.5.1 定义，在 §5.5 和 Appendix E 中被引用
- 如果新增定理 T10，需要手动更新所有"Theorem 1–9"的表述

**循环优化方案**：

```python
# scripts/check_theorems.py — 未实现

def check_theorem_consistency():
    """Ensure all theorems are: defined, cited, and proved in consistent locations."""
    theorems = extract_all_theorems("docs/paper_ao/**/*.tex")
    for thm in theorems:
        assert thm.has_label(), f"{thm} has no label"
        assert thm.has_proof(), f"{thm} has no proof section"
        assert count_refs(thm.label) > 0, f"{thm} never cited"
```

**收益**：新增定理时自动检测是否漏了证明、引用或摘要表更新。

**优先级**：🟡 中 — 仅在形式化节扩展时触发

---

### 5. 🔴 评审意见 → 修改计划 → 执行 → 验证（半自动化，可优化）

**当前状态**：每次评审意见 → 人工分析 → 写 plan.md → 手动修改 → 编译 → 提交

**问题**：
- 没有统一的"评审意见解析器"，每次都要人工理解评审人的 10+ 个问题
- 修改计划（plan.md）和实际修改之间的追踪靠人工记忆
- 没有自动验证"是否每个问题都回应了"

**循环优化方案**：

```markdown
# .reviewer_tracking/REVIEWER_5.md — 模板化

## Q1: Formal proofs missing
- [ ] §4.5.5: Expand theorem summary table
- [ ] Appendix E: Add detailed proofs (5-8 sentences each)
- [ ] Appendix E.5: Add precondition grammar
- Evidence: tab:theorems-summary, appendix_e.tex
- Status: DONE
- Commit: a5944cd

## Q2: Clock skew handling
- [ ] §4.6: New subsection on distributed ordering
- Evidence: §4.6.1, eq:total-order
- Status: DONE
- Commit: a5944cd
```

**自动化脚本**：

```python
# scripts/check_reviewer_response.py — 未实现

def verify_all_questions_addressed(reviewer_file):
    """Check that every reviewer question has a corresponding modification."""
    questions = parse_reviewer_file(reviewer_file)
    for q in questions:
        assert q.has_evidence(), f"Q{q.id}: no evidence section cited"
        assert q.has_commit(), f"Q{q.id}: no git commit linked"
```

**收益**：评审人第二轮问"为什么没解决 Q3"时，可以出示追踪文件证明已修改。避免遗漏。

**优先级**：🔴 高 — 每次 Major Revision 的核心痛点

---

### 6. 🟡 LaTeX 编译流水线（部分自动化，可增强）

**当前状态**：`latexmk -pdf` 可以自动编译，但：
- 不检查**表格溢出**（评审人第一次说"有表格超出文档"）
- 不检查**页面数**（目标 40-50，实际 81）
- 不检查**引用完整性**（只检查 undefined，不检查 dead）

**循环优化方案**：

```makefile
# Makefile additions

check: compile
	python scripts/check_table_overflow.py   # 检测宽表格
	python scripts/check_page_count.py       # 报告页数
	python scripts/check_dead_refs.py        # 检测断裂引用
	python scripts/check_orphan_figures.py   # 检测未引用图表

table_overflow:  # 检查是否有 tabular 超过 \textwidth
	grep -n "begin{tabular" docs/paper_ao/sections/*.tex | \
	while read line; do python scripts/check_table_width.py "$line"; done
```

**收益**：在提交前自动捕获格式问题，而不是等评审人发现。

**优先级**：🟡 中 — 编译已经自动化，但检查项不够

---

### 7. 🟢 实验流水线（已实现 runner.py，但未与论文集成）

**当前状态**：`python -m experiments.runner all` 可以运行所有实验，但：
- 实验结果不**自动**写入论文
- 每次实验修改后需要手动重新运行、提取数据、更新表格
- 实验编号不连续（E5, E6, E6b, E7...E25，缺少 E18, E22, E24, E26）

**循环优化方案**：

```python
# experiments/runner.py 扩展

class ExperimentPipeline:
    def run_all(self):
        for exp in self.registered_experiments:
            result = exp.run()
            self.save_json(result)
            self.generate_latex_table(result)  # 自动更新论文表格
            self.update_reviewer_response(exp.id, result)  # 更新追踪文件
    
    def verify_consistency(self):
        """Ensure experiment IDs match between code, paper, and JSON."""
        code_ids = extract_ids_from("experiments/e*.py")
        paper_ids = extract_ids_from("docs/paper_ao/sections/05_empirical_validation.tex")
        json_ids = extract_ids_from("docs/experiments/*.json")
        assert code_ids == paper_ids == json_ids, "ID mismatch"
```

**收益**：实验修改后一键更新论文所有相关内容（表格、引用、追踪文件）。

**优先级**：🔴 高 — 每次新增实验都要手动改 3-5 个文件

---

## 总结：优先实施顺序

| 优先级 | 优化项 | 当前痛点 | 预估收益 |
|--------|--------|----------|----------|
| **🔴 P0** | 1. 实验结果→LaTeX 表格 | 每次新增实验手动复制 3-5 个表格 | 减少 90% 表格维护时间 |
| **🔴 P0** | 5. 评审意见追踪 | 人工记忆 10+ 问题，易遗漏 | 零遗漏，可追溯 |
| **🔴 P0** | 7. 实验流水线集成 | 实验/论文/JSON 不同步 | 一键更新所有相关内容 |
| **🟡 P1** | 2. 交叉引用检查 | 重命名 section 时手动搜 8 个文件 | 自动检测断裂引用 |
| **🟡 P1** | 3. 重复内容检测 | 人工通读 81 页找重复 | 30 秒扫描 vs 2 小时 |
| **🟡 P1** | 4. 公式/定理一致性 | 新增定理时手动更新摘要表 | 自动验证完整性 |
| **🟡 P1** | 6. 编译检查增强 | 表格溢出靠评审人发现 | 提交前自动捕获 |

---

## 建议立即实施的 3 个脚本

### 脚本 A: `scripts/experiment_to_latex.py`（P0，1 小时实现）

读取 `docs/experiments/e*.json` → 生成 `docs/paper_ao/tables_auto/` 下的 `.tex` 文件 → 在论文中 `\input{tables_auto/e27}`。

### 脚本 B: `scripts/reviewer_tracker.py`（P0，30 分钟实现）

解析 `docs/REVIEWER_RESPONSE_*.md` → 检查每个问题是否有 `Evidence:` 和 `Commit:` → 生成追踪报告。

### 脚本 C: `scripts/check_redundancy.py`（P1，1 小时实现）

提取所有段落 → 计算相似度 → 报告 >70% 的段落对。

---

*评估时间: 2025-06-22*  
*论文状态: 81 页, 0 编译错误, 0 未定义引用*  
*Git: `1ec0bdd` on `sunnyang1/adl-lite`*
