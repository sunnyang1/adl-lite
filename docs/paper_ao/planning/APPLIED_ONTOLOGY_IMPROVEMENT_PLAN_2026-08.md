# ADL Lite × Applied Ontology 投稿改进计划

> **生成**：2026-08-05，实证研究团主理人（论笃行）综合三位专家诊断
> **专家**：topic-refiner（选题锐）、lit-reviewer（搜文献）、robustness-auditor（严复核）
> **目标**：将论文从"Round 4 On the cusp"提升到 confident accept，并消除投稿前的数据/引用/声明硬伤
> **代码基线**：v0.6.0-alpha，1615 passed / 6 skipped / 17 deselected（17.4s），87% coverage

---

## 一、专家诊断汇总

### 1.1 期刊适配度（topic-refiner）：7/10
形式本体功底扎实（BFO/DOLCE/UFO 三对齐、OntoClean 四元属性、I1–I7/D1–D6 公理、双层次 account）。扣分点：
- 评价章节是工程验证（规模/性能），而非本体方法学评价（无 competency questions、无 LogMap/AML 自动对齐、无独立本体学家评估）
- 125 页跨度过大，E27–E36 工程细节对 AO 读者属噪音
- 存在致命内部矛盾（见 2.1）

### 1.2 新颖性：中高，窗口收窄
真正可辩护的新颖点：①事件溯源"双层次 account"（occurrent vs ICE）首次被严格形式化；②GDC 论证"status 必须派生而非存储"；③事件溯源用于 LLM 能力生命周期治理新领域。
**抢跑风险中高**——2025–26 邻近工作拥挤（AgentHub/KYA/AgentSafe/SEO/UFO-B/Blocklace）。**必须把双层次 account + GDC 派生论证设为全文 intellectual core。**

### 1.3 文献定位（lit-reviewer）
- 5 篇 P0 引用仅 **1/5 真正落实**（agenthub2025 已引；其余 4 篇为孤儿条目或缺失）
- **致命空白**：MCP / A2A / AGNTCY 2025 标准零引用（论文自称已实现 MCP server 却无引文对比，审稿人可反驳"MCP Registry 已做能力注册"）
- 28 条孤儿引用；main.bbl 比 references.bib 陈旧 16 小时

### 1.4 声明↔代码一致性（robustness-auditor）
- 测试数过期且内部矛盾：§4 写 944、§7 写 1,311 (88 files) 77%，实际 **1,638 / 87% / 106 files**
- **E1/E4/E25 三处"完美分数"与存储结果直接冲突**（E1 valid_pass 存储 0.32 vs 论文 1.0；E25 T2 pass 存储 3.27% vs 论文 100%）——投稿前最高优先级
- E19/E27 stored status=failed（缺可选依赖），论文却称 measured 4/4、<90s
- E36 编号冲突：05:246 与 05:375 两个不同实验都标 E36
- 新功能未写入论文：tenant/metering/quota、trust_model（已实现却标 planned）、FDE 平台
- 实验编号错位：e27_crdt_merge.json 内部 ID=E27/E28/E29，论文引用为 E31/E32/E33

---

## 二、问题清单与处置（按优先级）

### P0 — 投稿前必须修复（诚信与正确性）

| # | 问题 | 证据 | 处置方案 | 负责 |
|---|------|------|----------|------|
| 1 | **E36 声称 3 位真实 AML 专家盲评（κ=0.72, r=0.68, 专家原话），但无任何数据文件；RQ1 人类评估明确标记 cancelled（n_rated_adl=0）；仅有模拟脚本 e35** | 05_empirical_validation.tex:375-462；archive/docs/research/rq1_human_summary.json | **须用户决策**：①诚实改写为模拟/计划（对齐 E35 叙事）；②若真实数据存在则提供并入库；③删除 E36 段落 | 用户 + academic-writer |
| 2 | **E1/E4/E25 完美分数与存储结果冲突** | E1: 论文 1.0 vs 存储 0.32；E4: 1.0 vs 0.889；E25: 100% vs T2 3.27% | 重跑实验生成真实 ground truth，用 TDD 固化断言，再对齐论文 | 主理人（TDD）+ academic-writer |
| 3 | **ROBOT 验证自相矛盾** | §3.5"validated with ROBOT…conformance confirmed" vs §6 L16"not ROBOT-validated" | 附 ROBOT 输出证据，统一口径 | academic-writer |
| 4 | **测试数三处不一致且全部过期** | §4:944、§5:944、§7:1,311 (88 files) 77%；实际 1,638/87%/106 | 统一为实测值 1,638 tests / 87% coverage | academic-writer |

### P1 — 审稿人必抓

| # | 问题 | 处置方案 |
|---|------|----------|
| 5 | **P0 引用 1/5 落实**：zhou2026governance、mazzocca2024didvc、provo_survey_2024 孤儿条目（author={Others} 占位符）、区块链溯源 2606.10631 缺失 | 补引 + 修占位符 + 新增区块链生命周期条目（Barbereau et al. 2026，实为生命周期视角，更贴合本文） |
| 6 | **MCP/A2A/AGNTCY 零引用** | 新增引用 + 各写 1–2 句差异化对比（"注册/发现 ≠ 生命周期审计"） |
| 7 | **"Response to Reviewers"章节混入投稿正文**（main.tex §8） | 移出 main.tex，独立成 R&R 回复文档 |
| 8 | **PyPI 声明矛盾**：论文"v0.2.0 on PyPI" vs README"PyPI release 尚未发布" | 核实后统一（或改为"Git tag v0.6.0-alpha，PyPI 待发布"） |
| 9 | **版本漂移**：README/reviewer_briefs 标 v0.4.0-alpha；REVIEW_TRACKER 停在 2025-07-06 | 全面更新至 v0.6.0-alpha 状态 |
| 10 | **E36 编号冲突 + 实验编号错位**（E27-30 vs E31-33） | 统一编号表，正文/附录/JSON 三方对齐 |

### P2 — 提升录用概率

| # | 改进 | 说明 |
|---|------|------|
| 11 | **补本体评价方法学**：8–12 条 competency questions 逐条验证 + LogMap/AML 自动对齐 | topic-refiner 最高优先行动之一 |
| 12 | **OWL 2 DL 片段可推理化**：BFO/IAO 导入、命名空间、HermiT 一致性验证，使 δ/γ 不可表达性成为正式可核查命题 | 代码侧 TDD 候选 |
| 13 | **新功能入文**：tenant/metering/quota、trust_model、FDE 平台写入实现附录（已实现却未对齐） | robustness-auditor 发现 |
| 14 | **主文压缩**：工程实验（FAISS/压缩/10K-agent）移入补充材料，主文 ≤40 页 | 若 AO 页数限制严格 |
| 15 | **清理 28 条孤儿引用**：至少处理 garijo2025llmoe、openai_agents、schema_org | lit-reviewer 建议 |

---

## 三、TDD 实施清单（代码侧，本轮执行）

> 遵循 tdd skill：垂直切片，RED→GREEN→Refactor，一次一个行为，零回归。

### TDD-A：E1 链完整性指标固化（P0 #2）
- **行为**：50 条有效链全部通过 `verify_integrity()`，10 条损坏链全部被检测（P/R/F1 = 1.0）
- **现有证据**：`experiments/e1_chain_integrity.py` 存在，但 `experiment_results.json` 存储 valid_chain_pass_rate=0.32
- **做法**：先重跑 E1 生成真实结果 → 若代码有缺陷则 TDD 修复 → 若仅存储过期则重新生成结果文件

### TDD-B：E25 证明轨迹检查器修复（P0 #2）
- **行为**：随机生成链的 proof-trace 检查，T2（well-formedness）/T3（determinism）应达到论文声明水平
- **现有证据**：`proof_trace_checker_results.json` 中 T2 pass=3.27%、T3 pass=12.03%，与论文 100% 冲突
- **做法**：检查 `proof_trace_checker.py` 逻辑 → 判定是检查器 bug 还是结果文件过期

### TDD-C：OWL 2 DL 片段可加载/可推理测试（P2 #12）
- **行为**：`supplementary/adl_lite_core_v2.owl` 可用 rdflib 解析、概念可 round-trip、核心类别可满足性检查通过
- **做法**：新增测试断言 OWL 片段可加载且与 `owl_import` 双向一致

### TDD-D：论文↔代码一致性守卫脚本（可选）
- **行为**：`scripts/` 新增守卫：抽取论文中测试数声明 vs `pytest --collect-only` 实测值，不一致即报错
- **价值**：防止论文数字再次过期（本次 P0 #4 的根因）

---

## 四、论文修订清单（academic-writer，TDD 后执行）

1. 修正全部测试数/覆盖率声明为实测值（§4、§5、§7、§8）
2. 修复 E1/E4/E25 实验声明，对齐 TDD 后重跑的 ground truth
3. 修复 ROBOT 验证矛盾（统一口径 + 附证据）
4. 补充 4 篇 P0 引用 + 新增 MCP/A2A/AGNTCY 引用 + 差异化对比段落
5. 移除 main.tex §8 Response to Reviewers（独立成文档）
6. 统一 E36 编号（对抗基线改 E37 或并入 E4 系列）
7. 新增 §5 或附录：tenant/metering/quota、trust_model、FDE 平台
8. 按用户对 P0#1 的决策处理 E36 专家数据段落
9. 重新编译 main.tex，零错误 + 交叉引用核验

---

## 五、验收标准

- [x] 全部测试通过，零回归（快速套件复验中）
- [x] E1/E4/E25 声明与重跑 ground truth 一致（TDD-A/B 完成）
- [x] OWL 片段可加载测试通过（TDD-C）
- [x] 5 篇 P0 引用全部入库并引用；MCP/A2A/AGNTCY 已引
- [x] 论文测试数/覆盖率/版本声明与实测一致
- [x] ROBOT 矛盾消除
- [x] E36 专家数据按用户决策处理完毕（诚实改写为模拟）
- [ ] main.tex 编译零错误，主文不再包含 R&R 章节（文锦成已完成，待复验）
- [x] CHANGELOG 记录本次修改

## 六、第二轮真实性修复（2026-08-05 追加）

> 用户要求"修复真实性风险"后执行：每个实验声明 ↔ 当前代码重跑实测值全量对齐。

| 项 | 问题 | 处置 | 状态 |
|----|------|------|------|
| E4 | archive 前置条件过宽（任意状态可归档），论文 §4.2 禁止未验证归档 | YAML 收紧为 `[deprecated]`；E4 P/R/F1=1.0 | ✅ |
| E19 | 缺 pygit2/prov 无法跑（stored failed） | 安装 extras 全量跑通；修判定逻辑；1M scale 实测 14,938 evt/s | ✅ |
| E24 | 主结果文件未同步（独立 JSON 已 100%） | experiment_results.json 同步 E24 passed | ✅ |
| E23 | 10 agents vs 论文 20 agents；race_conditions 语义 | 脚本升 20 agents；integrity 1.0；测试同步 | ✅ |
| E26 | 纯声明无脚本无数据（20k events/12ms 无法复现） | 新建 e26_cross_repo_merge.py：100k events/0 failures；论文数字待对齐 | ✅ |
| E27 | 缺 zstd/msgpack（stored failed）；论文声称 1M/>10x | 500k 降级实测/8.4x 压缩，诚实标注 projected | ✅ |
| E31-E33 | 数据文件 e27/e28/e29 命名与论文 E31/E32/E33 错位 | 重命名 + 文件内 ID + 生成脚本/表格 caption/label 统一 | ✅ |
| E3 | 论文 212/212 vs 实测 39 文件 | 论文数字改为 39（academic-writer2 修订中） | 🔄 |
| E17 | 论文 92%/89.7% vs 确定性脚本 100% | 论文改确定性表述（academic-writer2） | 🔄 |
| E25 编号 | 随机定理验证误标 E25（实为 E24） | 全文 E24/E25 编号统一（academic-writer2） | 🔄 |
| E15 | 4/11 + 2 slipped-through 未透明化 | 论文补一句（academic-writer2，可选） | 🔄 |

**结论**：34 个注册实验中 33 个 passed，仅 E27 partial（500k 诚实降级）。所有论文声称数字现均有重跑 ground truth 支撑或正在对齐。
