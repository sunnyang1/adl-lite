# ADL Lite 论文工作区（paper_ao）

> 目标期刊：Applied Ontology（备选 ESWC/ISWC 2027）
> 当前版本：v0.4.0-alpha（Month 3，代码-论文对齐完成）
> 论文长度：35 页（正文） + 21 页（补充材料）

---

## 根目录（核心文件）

| 文件 | 用途 | 说明 |
|------|------|------|
| `main.pdf` | 编译好的论文 | **最新完整版论文，直接看这份** |
| `main.tex` | 主 LaTeX 入口 | 调用 `sections/` 和 `supplementary.tex` |
| `references.bib` | 参考文献库 | BibTeX 源文件 |
| `supplementary.tex` | 补充材料入口 | 调用 `supplementary/` 下的各附录 |

### 论文章节源码（`sections/`）

按阅读顺序排列：

```
sections/
├── abstract.tex              ← 摘要
├── 01_introduction.tex       ← §1 引言（5页）
├── 02_related_work.tex       ← §2 相关工作（3页）
├── 03_ontological_analysis.tex ← §3 本体分析（7页）
├── 04_architecture.tex         ← §4 架构与形式语义（13页）
├── 05_empirical_validation.tex ← §5 实验验证（8页）
├── 06_discussion.tex           ← §6 讨论（4页）
├── 07_conclusion.tex           ← §7 结论与展望（1页）
├── agentsafe_integration.tex   ← AgentSafe 集成（可选章节）
├── appendix_a.tex ~ appendix_f.tex  ← 附录 A-F（正文后附录）
```

> 如需修改论文内容，直接编辑这些 `.tex` 文件，然后重新编译 `main.tex`。

---

## 子目录速查

### 📄 `build/` — 编译产物与构建日志（可忽略 / 可删除）

LaTeX 编译产生的中间文件和之前的压缩日志。不需要查看，如果磁盘紧张可以直接删除。

```
build/
├── *.aux, *.log, *.bbl, *.blg   ← LaTeX 编译中间产物
├── *.fdb_latexmk, *.fls, *.out  ← latexmk 辅助文件
├── pdflatex1/2/3.log           ← 多轮编译日志
├── bibtex.log                   ← 参考文献编译日志
├── compression_report.*          ← 论文压缩到 35 页时的记录
├── hyperref_fixes_log.md        ← 超链接修复记录
└── text_fixes_log.md            ← 文本压缩修复记录
```

### 🗂️ `planning/` — 各阶段计划文档

记录了论文从构思到投稿准备的全过程决策。按时间倒序看即可了解演进脉络。

**重点推荐：**
- `MODIFICATION_PLAN_AO.md` — 最新修改计划（Applied Ontology 投稿准备）
- `revision_plan.md` — 第四轮 peer review 修复方案（约 36KB，最详细）
- `IMPROVEMENT_PLAN.md` — 整体改进计划（大纲级）
- `COMPRESSION_PLAN.md` — 论文从 ~50 页压缩到 35 页的策略

其他文件：
- `plan.md`, `plan_v2.md` — 早期阶段计划
- `polish_plan.md` — 润色计划（即本次你发起的润色工作）
- `restructure_plan.md` — 结构调整方案
- `rewrite_plan.md` — 重写计划
- `strategic_directions.md` — 战略方向选择（AO vs ESWC/ISWC）
- `MODIFICATION_PLAN.md`, `MODIFICATION_PLAN_V2.md` — 中期修改计划

### 🔍 `research/` — 调研素材与搜索数据

写论文前的文献调研原始数据。

```
research/
├── agent_governance_research.md  ← Agent 治理领域调研笔记（25KB）
├── arxiv_search_1.csv            ← arXiv 搜索结果
├── scholar_search_1~4.csv        ← Google Scholar 批量搜索结果
└── (其他搜索数据)
```

> 这些是素材库，不是论文正文内容。如需补充引用或验证某篇论文，可在此查找。

### 📝 `review/` — 审稿报告与评审简报

所有审稿相关文件，包括内部 review 和外部 reviewer briefs。

```
review/
├── meta_review.md                ← 元评审汇总（3位评审员的交叉分析）
├── peer_review_report.md         ← 早期审稿报告
├── PEER_REVIEW_REPORT_v2.md      ← 第四轮审稿修复报告（17KB，当前基准）
└── reviewer_briefs/              ← 外部专家评审包（Month 3 准备）
    ├── README.md                 ← 评审包使用说明（含已知问题清单）
    ├── applied_ontology_reviewer.md    ← 本体学评审员检查清单
    ├── formal_semantics_reviewer.md      ← 形式语义评审员检查清单
    ├── systems_engineering_reviewer.md   ← 系统工程评审员检查清单
    └── review_report.md          ← 综合评审报告
```

**重点推荐：** `reviewer_briefs/README.md` — 里面有一份"已修复问题"和"已知未修复问题"清单，快速了解论文当前状态。

### 🛠️ `scripts/` — 辅助脚本

```
scripts/
├── check_compression.py   ← 检查论文各章节压缩效果（字数/页数）
└── check_long.py        ← 检查过长句子和段落
```

### 📑 `supplementary/` — 补充材料源码

论文补充材料的 LaTeX 源码，编译后生成 supplementary.pdf。

```
supplementary/
├── supplementary.tex           ← 补充材料入口
├── appendix_a_owl_dl.tex         ← 附录 A：OWL 2 DL 形式化片段
├── appendix_b_shacl.tex          ← 附录 B：SHACL 验证（未来工作）
├── appendix_c_adversarial.tex    ← 附录 C：对抗性测试套件
├── appendix_d_reproducibility.tex ← 附录 D：可复现性信息
├── appendix_e_proofs.tex          ← 附录 E：定理完整证明
├── appendix_f_comparison_tables.tex ← 附录 F：对比表格
├── appendix_g_bnf.tex             ← 附录 G：BNF 文法
├── appendix_h_complexity.tex      ← 附录 H：复杂度分析
├── appendix_i_tla.tex             ← 附录 I：TLA+ 规约
├── appendix_j_loss_analysis.tex   ← 附录 J：损失分析
├── appendix_k_threat_model.tex    ← 附录 K：威胁模型
├── appendix_l_e19_methodology.tex ← 附录 L：E19 实验方法
├── appendix_m_compression_log.tex ← 附录 M：压缩日志
└── (编译产物 *.aux, *.log, *.pdf 等)
```

> 补充材料共 21 页，涵盖证明、威胁模型、可复现性等支撑内容。

---

## 快速定位：不同场景下该看什么？

| 你想做什么 | 先看这些 |
|-----------|---------|
| **快速了解论文内容** | `main.pdf`（直接读完整论文） |
| **修改某章节文字** | `sections/XX_章节名.tex` |
| **补充参考文献** | `research/` 或 `references.bib` |
| **了解审稿意见和修复状态** | `review/PEER_REVIEW_REPORT_v2.md` + `review/reviewer_briefs/README.md` |
| **查看当前待办修改** | `planning/MODIFICATION_PLAN_AO.md` |
| **了解论文压缩/精简历史** | `planning/COMPRESSION_PLAN.md` |
| **重新编译论文** | 根目录运行 `latexmk main.tex`（或 `pdflatex main.tex` 3 轮） |
| **清理编译垃圾** | 删除 `build/` 目录 |

---

## 文件变动记录

本次整理（2025-06-21）将原先散落在根目录的 40+ 个文件归类为 5 个子目录：

- `build/` — 编译中间产物（11 个）+ 压缩日志（4 个）
- `planning/` — 各类计划文档（12 个）
- `research/` — 搜索数据和调研笔记（6 个）
- `review/` — 审稿报告 + reviewer_briefs（3 个文件 + 1 目录）
- `scripts/` — 辅助脚本（2 个）

根目录保留核心论文文件：`main.pdf`, `main.tex`, `references.bib`, `supplementary.tex` 以及 `sections/`, `supplementary/` 两个源码目录。

> 整理前备份：无（本次移动的文件均为可重新生成或纯文本文件，无需备份）。
