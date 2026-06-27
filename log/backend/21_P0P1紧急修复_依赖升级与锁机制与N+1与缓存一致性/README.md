# P0-P1 紧急修复 — 后端（依赖升级与锁机制与N+1与缓存一致性）

## 功能描述

### 解决了什么问题
基于《代码质量与性能检查报告》中标记为 P0（致命）和 P1（严重）的 19 个问题，本次修复覆盖后端 12 个问题：
- P0 安全漏洞：Spring Boot 3.2.5 的 3 个 CVE、Apache POI 5.2.3 的 2 个 CVE
- P1 并发竞态：全项目无锁机制导致用户注册 TOCTOU 竞态、会话状态转换 read-modify-write 竞态、分析结果并发更新丢失
- P1 N+1 查询：`AnalysisService.comparePapers`（2-5次）和 `generateReport`（最多20次）循环内逐条查询论文
- P1 幂等性缺失：三个分析接口无防重机制，重复提交导致重复创建资源和重复 AI 调用
- P1 缓存一致性：`UserService` 手动 Redis Key 与 `@CacheEvict` Key 不匹配；`@CacheEvict` 在事务提交前执行导致缓存与 DB 不一致

### 实现了什么功能
1. 依赖升级：Spring Boot 3.2.5→3.2.12，Apache POI 5.2.3→5.2.5
2. 数据库约束：users 表添加 username/email UNIQUE 约束，analysis_results 表添加 version 乐观锁列
3. 锁机制：AnalysisResult `@Version` 乐观锁 + SessionService `@Lock(PESSIMISTIC_WRITE)` 悲观锁 + UserService 唯一约束冲突捕获
4. N+1 消除：PaperService 新增 `validatePapersExist` 批量校验方法
5. 幂等性：新建 `IdempotencyUtil` 工具类，基于 Redis SETNX 实现 5 分钟去重窗口
6. 缓存一致性：`syncProfileToRedis` 失败时删除旧 Key；`CacheEvictionHelper.evictKeysAfterCommit` 替代 `@CacheEvict` 确保事务提交后失效

### 业务价值
- 消除 5 个安全漏洞（CVE），防止路径遍历、OOM DoS、授权绕过攻击
- 消除并发竞态导致的重复用户注册、状态覆盖、更新丢失
- 消除 N+1 查询将最坏 20 次 DB 往返降为 1 次
- 防止重复 AI 调用（每次 30s + 计算资源浪费）
- 修复缓存不一致导致用户读到过期画像数据（最长滞留 1 小时）

## 实现逻辑

### 修改的核心文件列表

| 文件 | 修改内容 |
|------|---------|
| `backend/pom.xml` | Spring Boot 3.2.5→3.2.12, Apache POI 5.2.3→5.2.5 |
| `backend/src/main/resources/db/01_create_tables.sql` | users 表 UNIQUE 约束, analysis_results 表 version 列 |
| `backend/src/main/resources/db/04_add_unique_constraints.sql` | 新建迁移脚本 |
| `backend/src/main/resources/db/05_add_version_column.sql` | 新建迁移脚本 |
| `entity/AnalysisResult.java` | 添加 @Version 乐观锁字段 |
| `service/AnalysisTransactionService.java` | completeAnalysis 捕获 ObjectOptimisticLockingFailureException |
| `repository/SessionRepository.java` | 新增 findBySessionIdForUpdate 悲观锁查询 |
| `service/SessionService.java` | 4个写方法改用 findBySessionIdForUpdate |
| `service/UserService.java` | register 捕获唯一约束冲突; 移除 @CacheEvict 改用 evictKeysAfterCommit; syncProfileToRedis 失败删 Key |
| `cache/CacheEvictionHelper.java` | 新增 evictKeysAfterCommit 方法 |
| `service/PaperService.java` | 新增 validatePapersExist 批量校验方法 |
| `service/AnalysisService.java` | comparePapers/generateReport 改用批量校验 |
| `util/IdempotencyUtil.java` | 新建幂等性工具类 |
| `controller/AnalysisController.java` | 3个端点添加 Idempotency-Key 幂等检查 |

### 使用的设计模式
- **乐观锁模式**：`@Version` 字段 + JPA 自动版本检查
- **悲观锁模式**：`@Lock(PESSIMISTIC_WRITE)` + `SELECT ... FOR UPDATE`
- **幂等性模式**：Redis SETNX 分布式锁 + 结果缓存
- **Cache-Aside 模式修正**：`TransactionSynchronization.afterCommit()` 回调确保事务提交后删缓存

## 接口变更

### Request — 幂等性 Header（新增可选）
```http
POST /api/analysis/paper
Idempotency-Key: client-generated-uuid
Content-Type: application/json

{
  "paperId": "paper_001",
  "topic": "深度学习综述"
}
```

### Response — 重复请求（新增 409 响应）
```json
{
  "code": 409,
  "message": "相同的分析请求正在处理中，请稍后重试",
  "data": null,
  "timestamp": "2026-06-25T12:00:00",
  "errorCode": "IDEMPOTENT_IN_PROGRESS"
}
```

### Response — 乐观锁冲突（新增 409 响应）
```json
{
  "code": 409,
  "message": "分析结果正在被并发更新，请重试",
  "data": null,
  "timestamp": "2026-06-25T12:00:00",
  "errorCode": "CONFLICT"
}
```

## 测试结果
- Java 编译 (`mvn clean compile`)：✅ 通过 (exit code 0)
- 依赖版本验证：Spring Boot 3.2.12 ✅, Apache POI 5.2.5 ✅
- 是否通过：是

## 相关文件
- 计划文件：`.trae/documents/P0-P1紧急问题修复计划.md`
- 修复清单：`Veritas/修复清单-1-紧急(P0-P1).md`（19个问题已标记 [已修复]）
- 检查报告：`Veritas/代码质量与性能检查报告.md`
