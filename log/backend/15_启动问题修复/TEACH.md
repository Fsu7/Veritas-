# 技术教学文档

## 开发思路

### 需求分析
项目本地启动后，通过 `curl /health` 发现两个异常：
1. `aiService: DOWN` — 但 `curl http://localhost:8000/health` 直接访问 AI 服务返回正常
2. `test_user` / `password123` 登录失败 — seed data 注释明确声称密码为 `password123`

初步判断为跨服务 JSON 解析错误 + seed data 数据损坏。

### 技术选型考虑
- 用 `bcrypt.checkpw()` 验证哈希 → 确认 seed data 哈希确实错误
- 用 `curl` + `python3 -m json.tool` 逐层查看 AI 服务实际返回结构
- 用 `lsof` + `ps` 验证三服务进程状态

### 遇到的问题及解决方案
| 问题 | 原因 | 解决 |
|------|------|------|
| `isHealthy()` 始终 false | `map.get("status")` 读的是根级，status 在 `data.status` | 先 `map.get("data")` 再 `dataMap.get("status")` |
| 旧哈希不匹配 | 手工编写的哈希并非由 `password123` 生成 | `bcrypt.hashpw()` 重新生成并 `checkpw()` 验证 |

## 实现步骤
1. 用 `curl + python3 -m json.tool` 获取 AI `/health` 完整 JSON，确认 status 在 `data.status` 层级
2. 用 `bcrypt.checkpw(b'password123', old_hash)` 验证旧哈希失败
3. 修改 `PythonAIClient.isHealthy()`：`map.get("status")` → `data = map.get("data"); dataMap.get("status")`
4. 修改 `03_insert_seed_data.sql`：替换注释和 INSERT 中的哈希值
5. `kill` 旧后端进程 + 重新 `mvn spring-boot:run` 启动
6. `curl /health` 验证 `aiService: UP` + 登录验证

## 变更内容

### 修改文件
| 文件 | 变更 |
|------|------|
| `backend/.../PythonAIClient.java` L221-232 | `isHealthy()` 解 `data` 嵌套层，移除冗余 `contains` 回退 |
| `backend/.../03_insert_seed_data.sql` L8 | 更新注释：旧哈希 → 新哈希 |
| `backend/.../03_insert_seed_data.sql` L21 | 更新 INSERT：旧哈希 → 新哈希 |

### 配置变更
无配置变更。

## 关键技术点

### Python↔Java 统一响应契约
```
Python ok(data=X)  →  {"code":200, "message":"success", "data": X, "timestamp":...}
Java  ApiResponse<T>  →  {"code":200, "message":"success", "data": T, "timestamp":...}
```
**关键规则**：Java 端解析 Python 返回时必须先取 `data` 字段，再从中取具体业务数据。

### BCrypt 哈希验证
```python
import bcrypt
# 生成
hash = bcrypt.hashpw(b'password123', bcrypt.gensalt(rounds=10))
# 验证
assert bcrypt.checkpw(b'password123', hash)
```
`$2a$` / `$2b$` 前缀差异（bcrypt 版本）不影响 `checkpw()` 兼容性。

## 经验总结
1. **跨服务调试黄金法则**：先直接调 Python（绕过 Java 代理），确认数据源正确 → 再查 Java 解析层
2. **统一响应格式是双刃剑**：`data` 嵌套带来了一层间接性，所有手动 JSON 解析（不经过 Spring 反序列化）都要注意这层
3. **seed data 应可回归**：每次 `mysql < seed.sql` 后应能直接登录，不要假设手动 fix
4. **`contains` 回退不靠谱**：字符串匹配 `"status":"UP"` 可能命中其他字段，应严格 JSON 路径解析
