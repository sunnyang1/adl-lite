# PRD — F25: Neo4j 适配层

> Architecture §6.3 F25 — 原生图存储 + Cypher 查询替代 NetworkX (P2)

## 1. 项目信息

- **Language**: 中文
- **Project**: adl-lite (v0.6.0-alpha)
- **Team**: Software Development Team
- **仓库**: `/Users/michelleye/Documents/Allen's files/adl-lite`

### 原始需求

在现有 `WarmIndex` 基础上，新增可插拔的图数据库后端，支持用 **Neo4j**（原生图存储 + Cypher 查询）作为 NetworkX 的替代方案，用于关系图的存储和 BFS 遍历。Neo4j 为 optional dependency（通过 `[neo4j]` extras 安装），NetworkX 保持为默认后端，不破坏现有功能。

---

## 2. 产品定义

### Product Goals

1. **支持原生图数据库**：通过 Neo4j 驱动提供持久化图存储，避免 NetworkX 内存图在进程重启后丢失
2. **保持向后兼容**：现有 NetworkX 后端不受影响，Neo4j 以 optional extra 形式提供，未安装时优雅降级
3. **最小接口对齐**：Neo4jGraphAdapter 实现与 NetworkX graph 相同的接口（add_edge / BFS / contains），降低 WarmIndex 集成成本

### User Stories

1. **As a** 系统管理员, **I want** 将大规模关系图存储在 Neo4j 中, **so that** 图数据在服务重启后持久化保存，避免 NetworkX 内存重建开销
2. **As a** ADL 开发者, **I want** 通过 `pip install adl-lite[neo4j]` 一键启用 Neo4j 后端, **so that** 不引入不必要的依赖，保持核心包轻量
3. **As a** DevOps 工程师, **I want** 通过 CLI `adl-lite neo4j status` 检查 Neo4j 连接状态, **so that** 快速诊断图数据库连通性

---

## 3. 技术规范

### Requirements Pool

| 优先级 | 需求 | 说明 |
|--------|------|------|
| **P0** | `adl_lite/neo4j_adapter.py` — Neo4jGraphAdapter 类 | 实现 add_edge / bfs / __contains__ / node_count / close 接口 |
| **P0** | WarmIndex 可插拔图后端 | WarmIndex 支持构造时注入 graph_backend 参数；Neo4j 可用时替换 nx.DiGraph |
| **P0** | 单元测试（mock Neo4j 驱动） | 使用 unittest.mock 模拟 neo4j driver，不依赖真实 Neo4j 实例 |
| **P1** | `[neo4j]` extras 配置 | pyproject.toml 新增 `neo4j = ["neo4j>=5.0"]` optional-dependencies |
| **P1** | CLI `adl-lite neo4j` 子命令 | 支持 `status`、`rebuild` 子命令 |
| **P2** | 连接池 / 重试机制 | 短连接中断时自动重试（1次）；生产部署建议使用外部连接池 |

### 接口设计草案

**Neo4jGraphAdapter 核心接口**（对齐 NetworkX graph 使用方式）：

```python
class Neo4jGraphAdapter:
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j")
    def add_edge(self, source: str, target: str, relation: str, confidence: float = 1.0) -> None
    def bfs(self, start_node: str, max_depth: int) -> list[tuple[str, str, float]]
    def __contains__(self, node_id: str) -> bool
    def node_count(self) -> int
    def close(self) -> None
```

**WarmIndex 集成方式**（最小改动）：

```python
# memory.py
# 新增 __init__ 参数
class WarmIndex:
    def __init__(self, db_path: str = ":memory:",
                 graph_backend: Literal["networkx", "neo4j"] | Neo4jGraphAdapter | None = None):
        ...
        if graph_backend == "neo4j":
            from .neo4j_adapter import Neo4jGraphAdapter
            self.graph = Neo4jGraphAdapter(...)  # 需从环境变量读取 URI/auth
        elif isinstance(graph_backend, Neo4jGraphAdapter):
            self.graph = graph_backend
        elif HAS_NETWORKX:
            self.graph = nx.DiGraph()
        else:
            self.graph = None
```

### 验收标准

1. `Neo4jGraphAdapter` 可以独立实例化并完成 add_edge → bfs 的端到端流程（mock 环境下）
2. `WarmIndex(graph_backend="neo4j")` 在不安装 `neo4j` 库时抛出 `ImportError`，提示信息包含安装命令
3. 现有 `WarmIndex()` 默认行为不变（仍使用 NetworkX）
4. `get_related()` 在 Neo4j 后端下的 BFS 结果与 NetworkX 后端一致（相同数据）
5. `adl-lite neo4j status` 返回正确的连接状态（connected / disconnected / driver not installed）
6. 单元测试覆盖率达 90%+（neo4j_adapter.py）；测试不依赖任何外部 Neo4j 实例

### Open Questions

1. **Neo4j driver 版本**: 锁定 `neo4j>=5.0` 还是允许更宽的范围（如 `>=4.4`）？建议锁定 >=5.x，因为 4.x 已接近 EOL
2. **Connection URI 格式**: 从环境变量读取（`NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD`）还是通过 WarmIndex 构造参数传入？建议同时支持两种方式，环境变量为 fallback
3. **认证机制**: 是否支持 Neo4j Aura（bolt+routing://）和企业 SSO 场景？初始版本仅支持 basic auth（user/password），后续通过 P2 迭代支持
4. **`__contains__` 语义**: Neo4j 需要执行 Cypher 查询，对于单个节点判断性能是否可接受？对于高频调用场景是否需要引入本地缓存？
5. **CLI `rebuild` 行为**: 是从 SQLite relations 表重建到 Neo4j，还是需要额外的迁移逻辑？建议从 SQLite 全量重建，避免数据不一致
