# 02 — 故障响应 Runbook 模板

> 版本：v1.0 | 每个 Runbook 必须每季度测试一次

---

## 使用说明

本模板用于为每个关键服务编写标准化的故障响应手册。将 `[占位符]` 替换为实际信息。

**核心原则：**
- 凌晨 3 点被叫醒也能照着执行
- 止血优先，根因分析可以等
- 每步操作必须有验证方法
- 每季度至少进行一次演练

---

## Runbook 模板

```markdown
# Runbook: [服务名称] — [故障场景]

## 快速参考
- **服务名称**：[服务名，附代码仓库链接]
- **负责团队**：[团队名，Slack/企微群]
- **值班安排**：[PagerDuty/Opsgenie 排班链接]
- **监控大盘**：[Grafana/Datadog 链接]
- **日志查询**：[日志平台链接]
- **最近演练**：[YYYY-MM-DD]

---

## 告警识别

### 会触发哪些告警
| 告警名称 | 告警来源 | 触发条件 | 紧急程度 |
|---------|---------|---------|---------|
| [告警1] | [监控工具] | [触发条件] | [P1/P2/P3] |

### 常见症状
- **用户侧**：[用户会看到什么 — 报错页面/白屏/超时/数据不一致]
- **指标侧**：[错误率飙升/延迟飙升/QPS 骤降/CPU 打满/内存泄漏]
- **日志侧**：[关键错误日志关键词]

### 误报检查（5 分钟内确认）
1. [ ] 检查是否有正在进行的部署或配置变更
2. [ ] 检查是否有计划的维护窗口
3. [ ] 检查是否只有单个可用区/机房受影响
4. [ ] 检查依赖服务状态页是否正常
5. [ ] 检查监控系统本身是否正常

---

## 诊断步骤

> 按顺序执行，每步不超过 15 分钟。15 分钟无结论就进入下一步或升级。

### 步骤 1：检查服务健康状态
```bash
# Kubernetes
kubectl get pods -n <namespace> | grep <service>
kubectl describe pod <pod-name> -n <namespace>

# 检查最近重启
kubectl get pods -n <namespace> -l app=<service> --sort-by=.status.startTime
```

### 步骤 2：检查最近变更
```bash
# 查看部署历史
kubectl rollout history deployment/<service> -n production

# 查看最近配置变更
git log --since="2 hours ago" -- <config-path>

# 查看最近的 feature flag 变更
# [根据实际 flag 系统补充命令]
```

### 步骤 3：检查依赖服务
| 依赖服务 | 健康检查方式 | 状态页链接 |
|---------|------------|-----------|
| [数据库] | `[健康检查命令]` | [链接] |
| [缓存] | `[健康检查命令]` | [链接] |
| [消息队列] | `[健康检查命令]` | [链接] |
| [第三方API] | `[健康检查命令]` | [链接] |

### 步骤 4：检查资源使用
```bash
# CPU / 内存
kubectl top pods -n <namespace> -l app=<service>

# 磁盘（如适用）
kubectl exec -it <pod> -n <namespace> -- df -h
```

### 步骤 5：检查日志
```bash
# 关键错误搜索
kubectl logs -n <namespace> -l app=<service> --tail=200 | grep -i "error\|fatal\|panic\|OOM"

# 特定时间段
kubectl logs -n <namespace> <pod> --since=30m
```

---

## 修复方案

### 方案 A：回滚部署（首选 — 如果是部署导致）
```bash
# 1. 确认上一个可用版本
kubectl rollout history deployment/<service> -n production

# 2. 回滚到上一版本
kubectl rollout undo deployment/<service> -n production

# 3. 验证回滚状态
kubectl rollout status deployment/<service> -n production

# 4. 监控恢复
watch kubectl get pods -n production -l app=<service>
```

### 方案 B：重启服务（状态异常时）
```bash
# 滚动重启 — 保持可用性
kubectl rollout restart deployment/<service> -n production

# 验证
kubectl rollout status deployment/<service> -n production
```

### 方案 C：扩容（容量不足时）
```bash
# 临时扩容
kubectl scale deployment/<service> -n production --replicas=<target>

# 如果 HPA 未启用，立即启用
kubectl autoscale deployment/<service> -n production \
  --min=3 --max=20 --cpu-percent=70
```

### 方案 D：降级/功能开关（无法快速修复时）
```bash
# 关闭非核心功能
# [根据实际 feature flag 系统补充]

# 或通过配置中心降级
# [根据实际配置中心补充]
```

### 方案 E：切流/故障转移（单可用区故障时）
```bash
# 将流量切到健康可用区
# [根据实际流量管理方案补充 — Istio/Nginx/CLB]
```

---

## 恢复验证

故障修复后，必须逐项确认：

- [ ] 错误率回到基线水平：[大盘链接]
- [ ] P99 延迟在 SLO 范围内：[大盘链接]
- [ ] 10 分钟内无新增告警
- [ ] 核心用户流程手动验证通过
- [ ] （如果涉及）数据一致性检查通过
- [ ] 扩容的实例是否需要缩回（24 小时后确认）

---

## 常见故障场景速查

| 场景 | 首选方案 | 预计恢复时间 |
|------|---------|------------|
| 部署引入 bug | 方案 A — 回滚 | 5-10 分钟 |
| 流量突增 | 方案 C — 扩容 | 3-5 分钟 |
| 内存泄漏/OOM | 方案 B — 重启 | 2-5 分钟 |
| 依赖服务不可用 | 方案 D — 降级 | 视情况 |
| 单可用区故障 | 方案 E — 切流 | 5-10 分钟 |
| 数据库慢查询 | 限流 + kill 慢查询 | 10-30 分钟 |
| 配置错误 | 回滚配置 | 5-10 分钟 |

---

## 相关链接

- 架构文档：[链接]
- 服务依赖图：[链接]
- 上次复盘报告：[链接]
- 团队 On-Call 排班：[链接]
```

---

## 编写 Runbook 的检查清单

写好 Runbook 后，用以下清单自检：

- [ ] **可执行性**：凌晨被叫醒的工程师能否按步骤执行？
- [ ] **命令可直接复制**：所有命令都是可直接粘贴执行的完整命令
- [ ] **有验证步骤**：每步操作后都有验证方法
- [ ] **有回滚方案**：每个变更操作都有对应的回滚步骤
- [ ] **时间预估**：每个方案有预估执行时间
- [ ] **无单点知识**：不依赖某个人的记忆或经验
- [ ] **最近演练过**：最近 90 天内经过实际演练

---

## 演练记录

| 日期 | 演练场景 | 参与者 | 恢复时间 | 发现的问题 | 改进措施 |
|------|---------|--------|---------|-----------|---------|
| | | | | | |
