# 技术教学文档 — 后端 P0-P1 紧急修复

## 开发思路

### 需求分析过程
基于 5 路并行代码搜索代理 + 关键文件交叉验证生成的《代码质量与性能检查报告》，识别出 41 个问题。其中 P0 致命 5 个、P1 严重 12 个，需立即修复。后端涉及 12 个问题，分为 4 个批次按依赖关系执行。

### 技术选型考虑

#### 锁机制选择
| 场景 | 方案 | 理由 |
|------|------|------|
| 用户注册 TOCTOU | DB UNIQUE 约束 | 最简单可靠，DB 层兜底，应用层捕获 DataIntegrityViolationException 转友好提示 |
| 分析结果并发更新 | @Version 乐观锁 | completeAnalysis 是短事务，冲突概率低，乐观锁无阻塞 |
| 会话状态转换 | @Lock(PESSIMISTIC_WRITE) | 状态转换涉及校验+更新原子性，悲观锁确保读到的数据不会被其他人改 |

#### 幂等性方案选择
选择 Redis SETNX 而非唯一约束/状态机：
- 分析接口的幂等 key 需要基于业务参数动态计算（userId + paperIds + topic）
- Redis SETNX 支持自动过期（5分钟窗口），无需手动清理
- 支持结果缓存，重复请求可直接返回已完成结果

#### 缓存时序修复
选择 `TransactionSynchronization.afterCommit()` 而非 `@CacheEvict`：
- `@CacheEvict` 默认在方法返回后（事务提交前）执行，存在窗口期
- `afterCommit` 回调确保只在事务成功提交后删缓存，避免回滚后缓存已删导致脏读
- 参考项目中 SessionService/FavoriteService 已有的正确实现

### 遇到的问题及解决方案

#### 问题1：@CacheEvict 与 @Transactional 的执行顺序
Spring AOP 代理链中，`@CacheEvict` 的拦截器在 `@Transactional` 拦截器之内，导致 evict 在 commit 之前执行。
**解决方案**：移除 `@CacheEvict`，改用 `CacheEvictionHelper.evictKeysAfterCommit()` 在 `afterCommit` 回调中执行删除。

#### 问题2：syncProfileToRedis 手动 Key 与 Spring Cache Key 不匹配
手动写入 `user:profile:json:{userId}`，`@CacheEvict(value="userProfileJson")` 删除的是 `userProfileJson::{userId}`。
**解决方案**：syncProfileToRedis 失败时主动 `redisTemplate.delete(key)` 删除手动 Key；同时用 `evictKeysAfterCommit` 精确删除 Spring Cache Key。

## 实现步骤

1. **批次1 依赖升级**：修改 pom.xml 版本号，`mvn clean compile` 验证编译
2. **批次2 DDL+锁**：
   - 修改 01_create_tables.sql 添加约束和 version 列
   - 新建迁移脚本 04/05
   - AnalysisResult 添加 @Version
   - SessionRepository 添加 @Lock 方法
   - AnalysisTransactionService/UserService 添加异常捕获
3. **批次3 N+1+幂等**：
   - PaperService 新增 validatePapersExist
   - AnalysisService 替换循环为批量调用
   - 新建 IdempotencyUtil
   - AnalysisController 3个端点添加幂等检查
4. **批次4 缓存一致性**：
   - syncProfileToRedis catch 块添加 delete(key)
   - CacheEvictionHelper 新增 evictKeysAfterCommit
   - UserService 移除 @CacheEvict，改用 evictKeysAfterCommit

## 解决了什么问题

### 核心问题
1. **5个安全漏洞**：Spring Boot CVE（路径遍历/OOM/授权绕过）+ Apache POI CVE（ZIP DoS/OOM）
2. **并发竞态**：用户注册重复用户名、会话状态被并发覆盖、分析结果更新丢失
3. **N+1 查询**：generateReport 最多 20 次 DB 往返 → 1 次批量查询
4. **幂等性缺失**：重复提交导致重复 AI 调用（30s/次）和重复资源创建
5. **缓存不一致**：画像数据最长滞留 1 小时，事务提交前删缓存导致脏读

### 解决方案对比
| 问题 | 方案A（未采用） | 方案B（已采用） | 优势 |
|------|----------------|----------------|------|
| 并发注册 | synchronized 代码块 | DB UNIQUE 约束 | 跨 JVM 生效，无需分布式锁 |
| 分析结果并发 | 悲观锁 SELECT FOR UPDATE | @Version 乐观锁 | 无阻塞，高并发性能好 |
| 幂等性 | 唯一约束 | Redis SETNX | 支持动态 key 和结果缓存 |
| 缓存时序 | @CacheEvict(beforeInvocation=true) | afterCommit 回调 | 只在成功提交后删，回滚不删 |

## 变更内容

### 新增文件
- `db/04_add_unique_constraints.sql` — users 表唯一约束迁移
- `db/05_add_version_column.sql` — analysis_results 表 version 列迁移
- `util/IdempotencyUtil.java` — Redis SETNX 幂等性工具

### 修改文件
- `pom.xml` — Spring Boot 3.2.12, Apache POI 5.2.5
- `db/01_create_tables.sql` — users UNIQUE 约束 + analysis_results version 列
- `entity/AnalysisResult.java` — @Version 字段
- `service/AnalysisTransactionService.java` — 乐观锁冲突捕获
- `repository/SessionRepository.java` — findBySessionIdForUpdate 悲观锁
- `service/SessionService.java` — 4个写方法使用悲观锁
- `service/UserService.java` — 唯一约束捕获 + @CacheEvict 移除 + syncProfileToRedis 修复
- `cache/CacheEvictionHelper.java` — evictKeysAfterCommit 方法
- `service/PaperService.java` — validatePapersExist 批量校验
- `service/AnalysisService.java` — N+1 修复
- `controller/AnalysisController.java` — 幂等性检查

### 配置变更
- pom.xml 依赖版本升级（无 application.yml 变更）

## 关键技术点

### @Version 乐观锁工作原理
JPA 在 UPDATE 时自动检查 version 字段：
```sql
UPDATE analysis_results SET status=?, result=?, version=version+1 
WHERE id=? AND version=?
```
如果 version 不匹配（已被其他事务修改），抛出 `ObjectOptimisticLockingFailureException`。

### Redis SETNX 幂等性
```java
// 原子操作：key 不存在则设置并返回 true，已存在返回 false
Boolean acquired = redisTemplate.opsForValue()
        .setIfAbsent("idempotency:" + key, "1", Duration.ofMinutes(5));
```
SETNX 保证原子性，TTL 防止永久锁定。

### TransactionSynchronization.afterCommit
```java
TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
    @Override
    public void afterCommit() {
        // 仅在事务成功提交后执行
        redisTemplate.delete(key);
    }
});
```
如果事务回滚，`afterCommit` 不会被调用，缓存保持不变（仍为旧值，与回滚后的 DB 一致）。

## 经验总结

### 开发过程中的收获
1. **@CacheEvict 时序陷阱**：Spring 的 @CacheEvict 默认在方法返回后、事务提交前执行，这对 Cache-Aside 模式是有害的。正确做法是使用 `afterCommit` 回调。
2. **手动 Redis Key 与 Spring Cache Key 的隔离**：两套 Key 体系需要分别失效，不能假设 @CacheEvict 能清理手动写入的 Key。
3. **N+1 修复的分层考虑**：在 PaperService 中暴露批量校验方法而非直接在 AnalysisService 中注入 PaperRepository，保持 Controller→Service→Repository 分层。

### 踩过的坑及如何避免
1. **CacheEvictionHelper 的 pattern vs 精确 Key**：`evictByPatternAfterCommit` 用 SCAN+pattern 匹配，适合 Spring Cache 的 `cacheName::key` 格式；但手动写入的 `user:profile:json:{userId}` 不符合此格式，需新增 `evictKeysAfterCommit` 精确删除方法。
2. **findBySessionIdForUpdate 只用于写操作**：读操作（getSessionDetail、validateSessionAccess）不需要悲观锁，否则会不必要地阻塞并发读。

### 最佳实践建议
1. 所有写操作方法统一使用 `evictByPatternAfterCommit` 或 `evictKeysAfterCommit`，不使用 `@CacheEvict`
2. 实体类的关键写操作场景考虑添加 `@Version` 乐观锁
3. 昂贵操作（AI 调用、文件导出）的接口必须实现幂等性
