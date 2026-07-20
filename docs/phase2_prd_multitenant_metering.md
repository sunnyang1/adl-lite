# 整合 PRD：多租户能力注册表隔离 + 按量计量（阶段二 · 第一片）

> 类型：简单 PRD（默认风格，中文）｜范围：仅「多租户隔离 + 按量计量 + 计量数据模型」第一可编码切片

## 1. 项目信息

- **Language**: 中文
- **Programming Language**: Python 3.10+（继承 ADL Lite 现有栈：FastAPI 提供 REST、SQLite 默认存储；Neo4j 经 `[neo4j]` extra 可选）
- **Project Name**: `multitenant_metering_registry`
- **原始需求复述**: 商业计划书阶段二（6–18 月）目标为「上线托管能力注册表 SaaS（按量计量）」。本次仅推进第一可编码切片：多租户隔离 + 按量计量（API 调用计数 + 注册实体计数）+ 计量数据模型。计费集成（Stripe/Lago）、SOC2、签客户、定价策略、MCP 增强均不在本次范围。本期只做「计量（metering）」数据层与查询/导出，不做「计费（billing）」收款/发票。

## 2. 产品定义

### Product Goals

1. **多租户隔离** —— 不同租户的能力注册表 / EventChain 数据彼此隔离，租户 A 不能读 / 写租户 B。
2. **按量计量** —— 记录每租户的 API 调用次数与注册实体数，支持查询与导出，为后续计费层提供事实数据源。
3. **零行为回归** —— 开发者带租户上下文调用既有 API 时，单租户行为与现有完全一致（向后兼容 `auth_enabled=False` 模式）。

### User Stories

**模块 A：多租户隔离**
- As a **SaaS 运营方**，我希望不同租户的数据在存储层被物理 / 逻辑隔离，以便我能向客户承诺数据不串租户。
- As a **租户管理员**，我希望我的注册表查询 / 写入只作用于本租户，以便我不会误读或覆盖其他租户的数据。
- As a **开发者**，我希望在请求中带上租户上下文后，既有 `/api/v1/consensus/*` 端点行为不变，以便我无需改写调用逻辑。

**模块 B：按量计量**
- As a **SaaS 运营方**，我希望能按租户查看 API 调用量与注册实体数，以便我能评估用量并为后续计费建模。
- As a **租户管理员**，我希望能查看本租户当前周期的用量与配额水位，以便我能管理自身消耗。
- As a **开发者**，我希望每次经认证的 API 调用被自动计量（无需我手动埋点），以便计量对我透明。

## 3. 技术规范

### Requirements Pool

| 优先级 | 编号 | 需求 |
|--------|------|------|
| P0 | R1 | **租户模型**：引入 `tenant_id`（字符串，建议 UUID 或域名 slug），作为所有隔离与计量的主键。 |
| P0 | R2 | **租户上下文注入**：从 JWT claim `tenant_id` 或 API Key→租户映射解析 `tenant_id`；扩展 `api_auth.UserInfo` 增加 `tenant_id` 字段；新增 `require_tenant` 依赖（包裹 `require_auth`），在 `auth_enabled=True` 时强制解析并返回 `TenantContext`（无租户上下文即 403）。 |
| P0 | R3 | **数据层租户隔离**：EventChain / 注册表查询按 `tenant_id` 过滤。默认 SQLite —— `WarmIndex` 表 `documents` / `events` 增加 `tenant_id` 列并建索引（`ADLMemory` 已有 `tenant_id` 与 `prefilter(tenant_id=)` 可复用）；可选 Neo4j 后端按 `tenant_id` 节点属性 / 标签隔离。 |
| P0 | R4 | **引擎租户化**：`api.py` 现有模块级单例 `_engine` 改为按 `tenant_id` 索引的引擎注册表；新增 `_get_engine(tenant_id)` 惰性创建并缓存，每租户独立 state 文件 / DB。 |
| P0 | R5 | **`UsageMeter` 数据模型**：`api_calls` + `registered_entities` 计数，按（tenant_id, 周期）聚合；默认持久化到 SQLite 表 `usage_meter`。 |
| P0 | R6 | **计量记录**：中间件 / 依赖在每次经认证的 API 调用将当前租户 `api_calls += 1`；在 `POST /api/v1/consensus/register` 成功创建实体时 `registered_entities += 1`。 |
| P0 | R7 | **用量查询端点**：`GET /api/v1/tenants/{tenant_id}/usage` 返回当前周期计数 `{api_calls, registered_entities, period_start, period_end}`；授权规则——仅同租户或 admin / 运营方可读。 |
| P1 | R8 | 按端点细分计数（register / list / transition 等分别计数）。 |
| P1 | R9 | 用法导出：CSV / JSON 导出（按租户 + 周期）。 |
| P1 | R10 | 周期语义：支持日 / 月周期与重置（滚动或自然月），`period_start` / `period_end` 明确。 |
| P1 | R11 | 计量持久化到 Neo4j（可选后端）的一致实现。 |
| P2 | R12 | 配额强制：超量拒绝（429）或告警。 |
| P2 | R13 | 用量 Webhook（供后续计费层订阅）。 |
| P2 | R14 | 实时用量流（供 dashboard，本期不实现 UI）。 |

### UI Design Draft

本期为**后端 / 数据层切片，无前端页面交付**。仅提供：
- REST 端点（既有 consensus 端点经租户化改造 + 新增 usage 端点）。
- OpenAPI 中对 `tenant_id` 来源（JWT claim / API Key 映射）的说明文档。
- （P2）dashboard 实时流预留接口，本期不实现前端。

## 4. 接口 / API 设计稿

### 4.1 现有 `api.py` 端点如何注入 / 要求 tenant

**现状对齐（`adl_lite/api.py` + `adl_lite/api_auth.py`）**：
- `create_app(auth_enabled=False, jwt_secret, api_keys, rate_limit, cors_origins)`；所有端点经 `user: UserInfo = Depends(require_auth)` 获取身份（`identity`, `role`），**无租户概念**；`_engine` 为全局单例，不区分租户。
- `require_auth` 支持 JWT（`Authorization: Bearer`）或 `X-API-Key`；`create_access_token(data, ...)` 的 `data` 已支持任意 payload（含 `sub` / `role`），加 `tenant_id` 无需改签名。

**改造方案（不破坏既有签名，向后兼容）**：
- 扩展 `api_auth.UserInfo`：`tenant_id: str | None = None`。
- JWT：`require_auth` 解码后 `UserInfo(identity=sub, role=role, tenant_id=payload.get("tenant_id"))`。
- API Key：新增 `api_key_tenants: dict[str, str]` 配置，由 `create_app(api_key_tenants=...)` → `configure_auth(...)` 注入；API Key 命中时查表得 `tenant_id`。
- 新增依赖 `require_tenant(user: UserInfo = Depends(require_auth)) -> TenantContext`：当 `auth_enabled=True` 且 `user.tenant_id is None` 时抛 `403`。
- 各 consensus 端点签名由 `Depends(require_auth)` 改为 `Depends(require_tenant)`，改用 `_get_engine(tenant.id)` 取本租户引擎，所有存储 / 查询经 `tenant.id` 过滤。
- 向后兼容：`auth_enabled=False` 时 `require_tenant` 返回默认租户（如 `"default"`），行为与当前单租户一致。

### 4.2 新增用量查询端点

```
GET /api/v1/tenants/{tenant_id}/usage?period=monthly   # period: daily | monthly
Authorization: Bearer <jwt>   # 需同租户或 role=admin（运营方）
```

响应 `200`：
```json
{
  "tenant_id": "acme",
  "api_calls": 1280,
  "registered_entities": 42,
  "period_start": "2025-07-01T00:00:00Z",
  "period_end":   "2025-08-01T00:00:00Z"
}
```

授权：路径 `tenant_id` 必须等于 `TenantContext.id`，或调用者 `role=admin`；否则 `403`。

### 4.3 数据结构（`UsageMeter` / `MeteringRecord`）

```python
# 聚合计量记录（按租户 + 周期），对应 SQLite 表 usage_meter
class MeteringRecord(BaseModel):
    tenant_id: str
    api_calls: int
    registered_entities: int
    period_start: str   # ISO 8601
    period_end:   str   # ISO 8601
    updated_at:   str   # ISO 8601, 最近一次更新时间

# 计量器（运行时聚合 + 持久化）
class UsageMeter:
    tenant_id: str
    period: Literal["daily", "monthly"]
    # increment_api_call()       -> api_calls += 1
    # increment_entity()         -> registered_entities += 1
    # snapshot() -> MeteringRecord
    # reset(period_start, period_end) -> 跨周期清零
```

（P1 可选）`UsageEvent` 明细表：`tenant_id, endpoint, ts`，支撑按端点细分（R8）与导出（R9）。

### 4.4 租户上下文注入方式草案

- **JWT 方案（首选）**：token payload 含 `{"sub": "<user>", "role": "user|admin", "tenant_id": "<tid>"}`；`create_access_token` 已支持任意 `data`，无需改签名。
- **API Key 方案（后备）**：`configure_auth(api_key_tenants={key: tenant_id})`；`verify_api_key` 增强为返回 `(identity, tenant_id)` 或新增 `resolve_tenant(key)`。适用于服务端到服务端、无 JWT 场景。
- **拒绝规则**：两者均无租户信息且 `auth_enabled=True` 时，`require_tenant` 返回 `403`。

## 5. Open Questions（待确认）

1. **`tenant_id` 来源优先级**：JWT claim 优先、API Key 映射优先，还是两者皆可并存（冲突时谁胜出）？
2. **「注册实体」计数定义**：一个 registered capability（`register` 事件）= 1 实体？还是按 EventChain 中 `REGISTER` / `SNAPSHOT` 事件数累计（含 fork）？
3. **计量持久化后端**：默认独立 SQLite 表 `usage_meter`，还是并入 Phase1 的 Neo4j（tenant 节点属性）？
4. **周期与重置语义**：按自然月（每月 1 日重置）还是滚动 30 天窗口？
5. **是否本期即做配额强制**（P2 R12）？还是本期仅计量、配额延后到计费层？

---

*复用资产（阶段一已交付，不要重写）*：`graph_backends.py`（含 Neo4j 适配器）、`trust_model.py`（`ConsensusConfig` / `TrustValidator`）、`api_auth.py`（JWT / API Key / 限流）、`memory.py`（`ADLMemory` 已带 `tenant_id` 与 `prefilter(tenant_id=)`）。
