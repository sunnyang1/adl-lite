# ADL Lite 产品缺陷清单与修复方案

**日期**：2026-07-21
**来源**：全库只读扫描（代码证据）+ 测试/构建实测
**结论先行**：核心算法与形式化资产健康（Coq 0 Admitted、无裸 `except:`、无密钥硬编码）；缺陷集中在 **打包/依赖、安全默认值、持久化一致性、文档漂移** 四个工程维度，全部可定点修复。

---

## P0 — 阻断级（不修则产品不可用/不可信）

### P0-1 裸安装后 `import adl_lite` 必崩
- **证据**：`shacl_validation.py:18-20`（pyshacl）、`prov_export.py:24-25`（rdflib）、`embeddings.py:12` / `vector_index.py:20`（numpy）均为顶层硬导入，且被 `__init__.py:57,103,110` 急切导入；但这些依赖只在 dev/gov extras 或根本未声明（numpy 无任何 extra）。
- **影响**：`pip install adl-lite` 的零基础用户第一步就失败——这是产品的"第一公里"缺陷。
- **修复**：`__init__.py` 改为惰性导入（`__getattr__` 按需加载）；shacl/prov/embeddings/vector_index 相关符号延迟到首次使用时 import，并在 ImportError 中给出 `pip install adl-lite[embeddings]` 类指引。预计改动 4–5 个文件。

### P0-2 test_mcp_server 收集失败，CI 必红
- **证据**：`tests/test_mcp_server.py`（39 个测试）在 `.[dev]` 环境下 `ModuleNotFoundError: No module named 'mcp'`；dev extras 不含 mcp；`ci.yml:34-35` 正是 `.[dev]` + `pytest tests/`。
- **修复**：双保险——dev extras 加 `mcp>=1.0`；同时 `tests/test_mcp_server.py` 顶部加 `pytest.importorskip("mcp")`，保证干净环境优雅跳过。

### P0-3 安全默认链：任何默认部署 = 全员 admin
- **证据**：JWT 密钥硬编码 `"change-me"`（`api_auth.py:101`、`config.py:78`、`api.py:288`）；`AUTH_ENABLED` 默认 false（`config.py:77`）；auth 关闭时 `require_auth` 返回 `role="admin"`（`api_auth.py:160-161`）；CORS 默认 `*` 全开（`api.py:359-363`）；`tokenUrl` 指向不存在的端点（`api_auth.py:93`）。
- **修复**：① 无默认密钥——`AUTH_ENABLED=true` 且未配 `JWT_SECRET` 时启动直接报错；② auth 关闭时 anonymous 角色降为 `reader`，admin 端点要求显式密钥；③ CORS 默认收紧为 localhost；④ 补 `/auth/token` 签发端点或移除 tokenUrl。

### P0-4 scope ACL 在生产路径零 enforcement
- **证据**：`validate_scope_access`（`validator.py:283-295`）仅被 tests 引用；`api.py` 只把 scope 当存储字段，private 文档经 API 取出无任何检查。AGENTS.md 宣称的 scope 校验未落地。
- **修复**：在 API/MCP 读路径统一接入 scope 检查（按调用者 tenant/role 过滤），补集成测试覆盖 `private/`、`user/`、`shared/` 前缀。

---

## P1 — 数据完整性级

### P1-1 NetworkX 图重启遮蔽历史数据
- **证据**：`memory.py:223-226` 默认进程内 NetworkX，`__init__` 不从 SQLite relations 表重建；重启后图为空→走 SQL 正常，但一旦本会话新增一条边，图"部分为真"，`get_related`（:476-477）优先走图，**历史关系全部隐身**。且两后端遍历方向不一致（:493 有向 successors vs :519-523 SQL 双向）。
- **修复**：① init 时从 relations 表重建图（或默认改为 SQLGraphAdapter，图仅作缓存并标记 dirty）；② 统一 BFS 方向语义为双向；③ 用 `graph_backends.py` 已有抽象收口。注意：`graph_backends.py` 目前零测试，修复时必须补测试。

### P1-2 计量/配额默认落 `:memory:`，重启即丢
- **证据**：`metering.py:32` `_DEFAULT_METERING_DB = ":memory:"`；`config.py:81` 默认 None。日配额跨重启可被绕过——Phase 2 刚提交的计量能力在默认配置下不可靠。
- **修复**：默认落盘到用户数据目录（如 `~/.adl_lite/metering.db`），或启动时显式告警；配额判定与计量写库同事务。

### P1-3 静默吞异常导致数据丢失不可见
- **证据**：`memory.py:874-879` `close()` 中 vector_index 落盘失败静默；`memory.py:795-796` delete 漂移静默；FDE 层另有约 7 处 except 空 pass。
- **修复**：统一改为 `logging.warning` + 上抛或记录失败状态；借机把 logging 推广到 consensus/api/cli 等主要模块（目前 38 个模块零 logging，`get_logger` 导出却无人使用）。

### P1-4 运行时状态文件被 git 跟踪
- **证据**：`state.json`、`adl_consensus.json` 已 commit；`ANCHOR.md` 每次跑测试被重写（本轮整理已亲见）。
- **修复**：从版本库移除并加入 .gitignore；测试中的 anchor/状态输出改写到临时目录。

---

## P2 — 一致性/打磨级

| # | 缺陷 | 证据 | 修复 |
|---|------|------|------|
| P2-1 | 版本三处漂移：pyproject `0.6.0-alpha` vs CHANGELOG 无 0.6.0 条目 vs `api.py:351` 硬编码 `0.5.0-alpha`（被 `tests/test_api.py:40` 锁死） | 实测 | 版本号单一来源（`adl_lite/__version__.py`），api/测试/徽章全部引用；补 CHANGELOG 0.6.0 条目 |
| P2-2 | 文档数字全面失真：README 徽章 1358 测试（实测 1493+1error）、AGENTS.md 另有 944/796 两个版本；"28 experiments (E1–E30)"（实际 32，新增 E5a/E17/E34/E35）；AGENTS.md 称 pygit2 未声明（已声明） | 实测 | 重新计数统一；徽章改为 CI 自动生成 |
| P2-3 | `adl-lite validate --strict-template` 按文档调用直接报错——flag 定义在根 parser（`cli.py:734-737`） | 实测复现 | 下沉到 validate 子 parser |
| P2-4 | 旗舰示例 `examples/capital_reflux_trap.md` 自身通不过 strict-template（缺 observation/reasoning/conclusion） | 实测 | 修示例文件 |
| P2-5 | `pip install adl-lite[did-ethr]` 指引错误（实际 extra 名 `did`）；did:ethr 两模块口径相反（`did_resolver` 实现了残缺版，`trust_model` 显式拒绝） | `did_resolver.py:297,497,510`；`trust_model.py:295-299` | 改文案；统一声明"Phase-1 不支持"，did_resolver 中 ethr 路径同步标注 |
| P2-6 | `export_ontology(format="rdfxml")` 直接 NotImplementedError；`fde/pipeline_engine.py:177` export 是 stub；B4 validator-diversity 自认 "effectively a no-op" | 三处 | rdfxml 补实现或明确文档标注；FDE export 补实现；B4 在 PROOFS/文档中如实标注 Phase-1 限制 |
| P2-7 | 测试盲区：`jsonld_export.py`、`graph_backends.py` 零测试；`config.py` 零覆盖；`export_owl()` 公开 API 零直接测试 | grep 实证 | 每个模块补最小契约测试（输入→输出不变量） |
| P2-8 | E19 三个 runner 测试依赖真实环境（装没装 pygit2 结果不同） | 本轮实测 | 改 monkeypatch 模拟依赖缺失 |
| P2-9 | PROOFS.md 称 Crypto.v "5 条 Axioms"，实际 3 条；specs/ 混入 .bin TTrace 二进制 | 实测 | 改数字；移除二进制 |
| P2-10 | `mcp_server.py:16` 引用不存在的 `adl-lite mcp` 子命令 | grep 零命中 | 补子命令或改文档 |

---

## 建议修复顺序（按"缺陷消除率/工作量"比排序）

**第一批（1–2 天，纯工程快赢）**：P0-1 惰性导入、P0-2 mcp extra+importorskip、P2-1 版本单一来源、P2-2 文档数字、P2-3 CLI flag、P2-4 示例、P2-5 文案、P2-8 monkeypatch、P1-4 git 卫生。
**第二批（2–4 天）**：P0-3 安全默认链、P0-4 scope ACL 接入、P1-2 计量落盘、P1-3 静默异常+logging 推广。
**第三批（1 周+，涉及语义决策）**：P1-1 图后端一致性（需定 BFS 方向语义）、P2-6 rdfxml/FDE export/B4 如实标注、P2-7 测试补盲。

> 本清单所有条目均有代码证据（文件:行号），可直接转成 GitHub Issues。
