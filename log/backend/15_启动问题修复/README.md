# 启动发现问题修复

## 功能描述
- **解决了什么问题**：项目启动后 `HealthController.health()` 报告 `aiService: DOWN`（实际 AI 服务正常）；seed data 中 `test_user` 的 BCrypt 哈希错误导致无法登录
- **实现了什么功能**：修复 2 个 bug，恢复 health 端点和 seed data 的正确性
- **业务价值**：运维可观测性恢复正常；新数据库初始化后可立即使用 seed 账号登录

## 实现逻辑

### Bug-1: `PythonAIClient.isHealthy()` 未解析嵌套 `data` 层

**根因**：AI 服务 `/health` 返回统一响应格式 `{code, message, data: {status: "UP"}, timestamp}`，但 `isHealthy()` 直读 `map.get("status")`（取到 null），导致始终返回 false。

**修复**：先解 `data` 层，再读 `dataMap.get("status")`。

**修改文件**：
- [PythonAIClient.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/client/PythonAIClient.java#L221-L232) — `isHealthy()` JSON 解析段

### Bug-2: Seed Data BCrypt 哈希错误

**根因**：`03_insert_seed_data.sql` 中声称 `password123` 的 BCrypt 哈希是 `$2a$10$N9qo8uLO...`，但 `bcrypt.checkpw()` 验证不通过，说明该哈希为手写/复制错误。

**修复**：用 `bcrypt.hashpw(b'password123', gensalt(rounds=10))` 重新生成并验证。

**修改文件**：
- [03_insert_seed_data.sql](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/resources/db/03_insert_seed_data.sql#L8) — 更新注释中的哈希
- [03_insert_seed_data.sql](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/resources/db/03_insert_seed_data.sql#L21) — 更新 INSERT 中的哈希值

## 接口变更

无接口变更。仅修复内部逻辑，响应格式不变。

## 测试结果
- 后端 `/health` 返回 `aiService: UP, mysql: UP, redis: UP, status: UP`：✅ 通过
- `test_user` / `password123` 登录：✅ 通过（code=200，token 有效）
- 持 token 调 `/api/papers` 论文列表：✅ 通过（返回 27 篇）
- 三服务仍正常运行（8000/8080/5173）：✅ 通过

## 相关文件
- `backend/src/main/java/com/literatureassistant/client/PythonAIClient.java`
- `backend/src/main/resources/db/03_insert_seed_data.sql`
