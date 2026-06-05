# 启动发现问题修复计划

**审阅者**: 资深 Java 后端架构审阅工程师 (java-review skill)
**审阅日期**: 2026-06-05
**审阅范围**: `PythonAIClient.isHealthy()` + `03_insert_seed_data.sql`

---

## 审阅摘要

| 级别 | 数量 |
|------|------|
| 🔴 严重 (Block) | 0 |
| 🟠 重要 (Strong Suggestion) | 2 |
| 🟡 建议 (Suggestion) | 1 |
| 🟢 提示 (Nit) | 0 |

**总体评价**: 2 个已知 bug 需修复，1 个潜在风险建议验证。代码质量整体良好，无安全问题。

---

## 当前状态分析

### 项目架构

```
Vue3 (5173) → Java Spring Boot (8080) → Python FastAPI (8000)
                                    ↕
                              MySQL9 + Redis
```

### 统一响应格式（关键上下文）

Python 端 `ok()` 返回 4 字段扁平结构：
```json
{"code": 200, "message": "success", "data": { ... }, "timestamp": 1700000000}
```

Java 端 `ApiResponse<T>` 同样 4 字段，`data` 承载业务数据。
Java 端 Jackson 配置 `property-naming-strategy: SNAKE_CASE`，自动转换 camelCase ↔ snake_case。

### 已确认的两个 Bug

| # | 问题 | 影响 | 根因 |
|---|------|------|------|
| 1 | `PythonAIClient.isHealthy()` 始终返回 `false` | `/health` 端点报告 `aiService: DOWN`，但实际 AI 正常 | 读取 `map.get("status")` 而非 `data.status` |
| 2 | `03_insert_seed_data.sql` BCrypt 哈希不匹配 `password123` | 新建库执行 seed data 后 `test_user` 无法登录 | 手写哈希与注释声明不一致 |

---

## 问题 1: `PythonAIClient.isHealthy()` 未解析嵌套 `data` 层

### 审阅分析

**文件**: [PythonAIClient.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/client/PythonAIClient.java#L211-L235)

**违反原则**: 代码审阅 — 边界处 JSON 解析应与契约一致（[code-review.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/.trae/skills/java-review/code-review.md) "统一响应格式"）

**调用链**:
```
HealthController.checkAIService()
  → AgentClientService.isHealthy()          [L194-196]
    → PythonAIClient.isHealthy()            [L211-235]
      → GET http://ai-service:8000/health
        → main.py health_check()            [L69-80]  返回 ok(data={...})
          → JSONResponse(content={code, message, data, timestamp})
```

**AI 服务实际返回结构**（已实测）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "llm": "loaded",
    "embedding": "loaded_api",
    "chroma": "connected",
    "prompts": "loaded",
    "searchService": "ready",
    "reranker": "ready",
    "status": "UP"          ← status 在 data 内部！
  },
  "timestamp": 1780635729886
}
```

**当前代码** (`isHealthy()` L221-225)：
```java
Map<?, ?> map = objectMapper.readValue(body, Map.class);
Object status = map.get("status");      // null! status 在 data 层级
return "UP".equals(status);             // 永远为 false
```

**回退逻辑** (L228-229) 也错误：
```java
return body.contains("\"status\":\"UP\"");  // 匹配到 data.status，但路径逻辑矛盾
```
因为 `map.get("status")` 的意图是读根级，而 `contains` 回退却匹配到了嵌套层。实际运行时回退逻辑会命中，但这是偶然——当 body 中别的 key 也包含 "status":"UP" 子串时可能误判。

**影响**: 
- `HealthController.health()` 的 `overallStatus` 错误地显示 `DOWN`
- Docker Compose `healthcheck` 依赖此端点 → 容器会被误判为不健康
- 不影响业务流（前端/API 不依赖此状态来做路由决策），但运维可观测性受损

### 修复方案

将 `isHealthy()` 的 JSON 解析改为先读 `data` 再读 `status`：

```java
// 修复前
Map<?, ?> map = objectMapper.readValue(body, Map.class);
Object status = map.get("status");
return "UP".equals(status);

// 修复后
Map<?, ?> map = objectMapper.readValue(body, Map.class);
Object data = map.get("data");
if (data instanceof Map<?, ?> dataMap) {
    Object status = dataMap.get("status");
    return "UP".equals(status);
}
return false;
```

同时修改 parse 失败的回退逻辑，移除冗余 `contains` 检查（正确解析路径已覆盖）。

### 修改文件

| 文件 | 行号 | 操作 |
|------|------|------|
| [PythonAIClient.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/client/PythonAIClient.java) | L221-229 | 替换 JSON 解析段 |

改动量：~8 行。

---

## 问题 2: Seed Data BCrypt 哈希错误

### 审阅分析

**文件**: [03_insert_seed_data.sql](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/resources/db/03_insert_seed_data.sql#L7-L8)

**违反原则**: 安全审阅 — 密码必须正确加密存储（[review-checklist.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/.trae/skills/java-review/review-checklist.md) "密码安全"）

SQL 第 8 行注释声称：
```sql
-- BCrypt('password123', strength=10) = $2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy
```

但第 21 行实际存储的哈希无法用 `bcrypt.checkpw(b'password123', hash)` 验证通过（已测试）。说明该哈希是手写/复制错误产物，并非真正由 `password123` 生成。

### 修复方案

用 Python `bcrypt` 库重新生成 `password123` 的正确 BCrypt 哈希，替换 SQL 中的旧值 + 更新注释。

新哈希（已生成并验证）：
```sql
-- BCrypt('password123', strength=10) = $2b$10$ESdOqDvXtRaQmMu/nqox9uMI4lwki47zMD753.vYC3j8eOlmeBaZy
```

### 修改文件

| 文件 | 行号 | 操作 |
|------|------|------|
| [03_insert_seed_data.sql](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/resources/db/03_insert_seed_data.sql) | L8, L21 | 更新哈希注释 + 替换哈希值 |

改动量：2 行。

---

## 潜在风险（本次不修改，建议后续排查）

### U-001: `PythonAIClient.search()` 可能未解析 `data` 层

**文件**: [PythonAIClient.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/client/PythonAIClient.java#L184-L197)

`search()` 方法在 L193 直接读 `response.get("results")`，但 AI 服务返回的是 `ok(data={results:[...]})` 即 `{code, message, data: {results: [...]}, timestamp}`。如果此方法被调用，会始终返回空列表。

**当前保护**: 当前 `PaperService.searchPapers()` 走的是 MySQL 关键字搜索（不经过 `PythonAIClient`），因此该路径未被触发。但如果未来启用 AI 语义搜索作为 `PaperService` 的补充，此 bug 会暴露。

**建议**: 后续启用 AI 语义搜索前修复此方法（同样需解 `data` 层 + 读取 `data.results`）。

---

## 验证步骤

### 修复 1 验证（`isHealthy`）

```bash
# 1. 确认 AI 服务正常运行
curl -s http://localhost:8000/health | python3 -c "import sys,json; d=json.load(sys.stdin); \
  print(f'AI status in data: {d[\"data\"][\"status\"]}')"

# 2. 重启后端（mvn spring-boot:run 正在运行，需先 kill 再启动）
# 3. 验证后端 /health 返回 aiService: UP
curl -s http://localhost:8080/health | python3 -m json.tool
# 预期: {"code":200,...,"data":{"aiService":"UP","mysql":"UP","redis":"UP","status":"UP"},...}
```

### 修复 2 验证（seed data）

```bash
# 用新哈希验证登录
curl -s -X POST http://localhost:8080/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test_user","password":"password123"}' | python3 -c \
  "import sys,json; d=json.load(sys.stdin); assert d['code']==200, 'Login failed'; print('OK: Login works')"
```

---

## 审阅维度总结

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构一致性 | ⭐⭐⭐⭐ | Java→Python 契约嵌套解析不统一，修复后可恢复 |
| 代码质量 | ⭐⭐⭐⭐ | `isHealthy()` 未深度解析嵌套 data，属契约解析疏忽 |
| 安全 | ⭐⭐⭐⭐ | 种子数据 BCrypt 哈希有误，修复后合规 |
| 可观测性 | ⭐⭐→⭐⭐⭐⭐ | 修复 `isHealthy` 后 health 端点恢复准确 |

---

## 优先修复建议

1. **[P0]** 修复 `PythonAIClient.isHealthy()` JSON 嵌套解析 (~8 行)
2. **[P1]** 修复 `03_insert_seed_data.sql` BCrypt 哈希 (~2 行)
3. **[P2]** 排查 `PythonAIClient.search()` 的 `data.results` 解析问题（后续任务）
