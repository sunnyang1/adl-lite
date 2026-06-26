# ADL Lite 论文润色与压缩计划

## 目标
- **润色**：按学术写作标准逐段审查语法、用词、语态、逻辑衔接、句式
- **压缩**：从 60 页 → 50 页（缩减约 17%，约 10 页）

## 当前页数分析

| 章节 | 行数 | 估计页数 | 压缩策略 | 目标页数 |
|------|------|----------|----------|----------|
| Abstract | 9 | 0.5 | 微调 | 0.5 |
| §1 Introduction | 59 | 2 | 精简背景，删除冗余 | 1.5 |
| §2 Related Work | 90 | 3 | 压缩对比表描述 | 2.5 |
| §3 Ontological Analysis | 178 | 5 | 精简公理表述 | 4.5 |
| §4 Architecture | 360 | 12 | **大幅精简**冗余解释、工作示例 | 9 |
| §5 Empirical | 196 | 6 | 压缩实验描述 | 5 |
| §6 Discussion | 108 | 3 | 精简限制描述 | 2.5 |
| §7 Conclusion | 30 | 1 | 微调 | 1 |
| Appendix A (PROV-O) | 34 | 1 | 移至补充材料 | 0 |
| Appendix B (SHACL) | 53 | 1.5 | 移至补充材料 | 0 |
| Appendix C (Adversarial) | 81 | 2.5 | 保留但精简 | 2 |
| Appendix D (Reproduce) | 57 | 1.5 | 保留 | 1.5 |
| Appendix E (Proofs) | 350 | 10 | **大幅压缩**冗余证明 | 5 |
| Appendix F (RDF-star) | 73 | 2 | 移至补充材料 | 0 |
| **总计** | **1700** | **~60** | | **~50** |

## 压缩策略（按优先级）

### P0: 将 4 个附录移至补充材料（-5.5 页）
- Appendix A (PROV-O Export) → 补充材料
- Appendix B (SHACL Shape) → 补充材料
- Appendix F (RDF-star) → 补充材料
- Appendix E 中 Theorem 4-7 的冗长证明 → 补充材料，正文保留 sketch

### P1: 压缩 §4 Architecture（-3 页）
- 精简 "Worked Example" 的 5 步详细描述（§4.2.2），保留核心但删减逐步注释
- 压缩 "Comparison with Formal Event Frameworks"（§4.5）
- 精简 Trust Model 中的重复描述
- 删减冗余的公式注释

### P2: 压缩 §5 Empirical（-1 页）
- 合并 E13-E16 的冗余描述
- 精简失败案例分析（保留核心但压缩 prose）
- 压缩案例研究描述

### P3: 微调其他章节（-0.5 页）
- §1 精简背景段落
- §6 压缩限制描述（L1-L12 可以更紧凑）

## 润色策略（按维度）

### 语法（Grammar）
- 检查主谓一致、时态、冠词、介词
- 修正 run-on sentences 和 comma splices
- 统一英式/美式标点

### 用词（Word Choice）
- 口语化 → 学术化（get→obtain, show→demonstrate, big→substantial）
- 删除冗余表达（in order to→to, due to the fact that→because）
- 精确化模糊表达（very good→12% improvement）

### 语态（Voice & Tense）
- 方法描述：主动语态 "We"
- 通用事实：现在时
- 实验结果：过去时
- 避免过度被动

### 逻辑衔接（Coherence）
- 段内信号词优化（However, Furthermore, Therefore）
- 段间过渡句
- 每段主题句检查

### 句式（Sentence Structure）
- 长短句搭配
- 避免 >40 词长句
- 分词短语、插入语多样化

## 执行计划

### Stage 1: 压缩（先压缩后润色，避免重复工作）
- 将 Appendix A/B/F 移至补充材料（main.tex 注释）
- 压缩 Appendix E（保留核心证明，删减冗余）
- 压缩 §4 工作示例
- 压缩 §5 实验描述

### Stage 2: 润色（逐章并行）
- 子代理 1: Abstract + §1 + §7
- 子代理 2: §2 + §3
- 子代理 3: §4 + §5
- 子代理 4: §6 + Appendices
- 主代理: 统一术语、时态、引用一致性

### Stage 3: 验证
- 编译 PDF
- 检查页数 ≤ 50
- 检查引用完整性
- 检查术语一致性

## 风险
- 压缩可能丢失关键信息 → 优先压缩冗余 prose，保留核心论证
- 润色可能改变技术含义 → 保留原意，仅改语言
- 附录移动可能破坏引用 → 检查所有 \ref 标签
