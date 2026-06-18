# 技术教学文档 — Java 后端 P0-P2 修复

## 开发思路

### 需求分析过程
本次修复源于《三层全栈综合技术评估报告》对 Java 后端的全面审查。评估识别出 9 项问题（P0×5、P1×2、P2×2），涵盖安全漏洞、配置风险、代码质量三个维度。

分析优先级：
1. **安全漏洞优先**：P0-1 Redis RCE 是最高危漏洞，可导致远程代码执行
2. **配置风险次之**：P0-2/3/4 涉及密码泄露和表结构意外变更
3. **功能缺陷**：P0-5 SSE 解析影响核心功能可靠性
4. **代码质量**：P1-1/2、P2-1/2 提升健壮性和可维护性

### 技术选型考虑

#### P0-1 Redis 反序列化方案对比
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| `BasicPolymorphicTypeValidator` 白名单 | 精确控制、官方推荐 | 需维护白名单 | ✅ |
| 关闭 `activateDefaultTyping` | 彻底安全 | 破坏现有序列化兼容性 | ❌ |
| 自定义 `TypeValidator` | 最灵活 | 维护成本高 | ❌ |

#### P0-5 SSE 解析方案对比
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| `bodyToFlux(ServerSentEvent.class)` | Spring 内置、可靠 | 需适配数据类型 | ✅ |
| `bodyToFlux(String.class)` + `bufferUntil` | 手动控制 | `text/event-stream` 下被 SSE Reader 拦截 | ❌（踩坑） |
| `bodyToFlux(byte[].class)` + 手动解析 | 完全控制 | 代码复杂、跨块处理困难 | ❌（原方案） |

#### P2-1 缓存失效方案对比
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| `CacheEvictionHelper` + SCAN | 精准、不阻塞 | 需手动调用 | ✅ |
| `@CacheEvict(allEntries=true)` | 简单 | 影响其他用户 | ❌（原方案） |
| `@CacheEvict(key=...)` | 精准 | 无法匹配多个分页 key | ❌ |

### 架构设计思路
- **安全优先**：所有安全相关修复（RCE、密码、ddl-auto）优先处理
- **最小侵入**：保持 Service 接口不变，缓存失效逻辑封装在 Helper 中
- **事务感知**：`evictByPatternAfterCommit` 在事务提交后清除缓存，遵循 Cache-Aside 写后删模式
- **测试同步**：每项修复同步更新对应测试，确保测试反映新行为

### 遇到的问题及解决方案

#### 问题1：`bodyToFlux(String.class)` 在 `text/event-stream` 下行为异常
- **现象**：P0-5 初版用 `bodyToFlux(String.class)` + `bufferUntil`，测试全部失败（events 为空）
- **原因**：当 Content-Type 为 `text/event-stream` 时，Spring WebClient 用 `ServerSentEventHttpMessageReader` 解析，`bodyToFlux(String.class)` 返回的是每个事件的 data 字符串，而非原始行
- **解决**：改用 `bodyToFlux(ServerSentEvent.class)`，直接利用 Spring 内置 SSE 解析器

#### 问题2：`ServerSentEvent.data()` 类型不确定
- **现象**：`convertServerSentEvent` 中 `sse.data()` 有时返回 String，有时返回 Map
- **原因**：`ServerSentEventHttpMessageReader` 在无泛型参数时，可能将 JSON data 自动解析为 Map
- **解决**：`convertServerSentEvent` 兼容两种情况（`instanceof Map` 判断）

#### 问题3：`SessionStateMachineTest` 构造函数签名变更
- **现象**：`SessionService` 新增 `CacheEvictionHelper` 字段后，`@RequiredArgsConstructor` 生成的构造函数签名变化
- **原因**：`SessionStateMachineTest` 用手动 `new SessionService(...)` 构造，参数不匹配
- **解决**：补传 `cacheEvictionHelper` mock 参数

#### 问题4：`LiteratureAssistantApplicationTests` 数据库连接失败
- **现象**：`@SpringBootTest` 上下文加载失败，`Access denied for user 'root'`
- **原因**：P0-3 将测试密码改为 `${MYSQL_TEST_PASSWORD:test_password}`，环境变量未设置时用默认值
- **解决**：运行测试时设置 `MYSQL_TEST_PASSWORD` 环境变量（非代码问题，是环境配置）

## 实现步骤

### 1. P0-1 Redis RCE 修复（RedisConfig.java）
1. 定位 `activateDefaultTyping` 调用
2. 将 `LaissezFaireSubTypeValidator.instance` 替换为 `BasicPolymorphicTypeValidator.builder()` 白名单
3. 白名单包含：`com.literatureassistant.`、`java.util.`、`java.time.`、`java.lang.`

### 2. P0-2/3/4 配置修复（application.yml）
1. MySQL 密码改为 `${MYSQL_PASSWORD:CHANGE_ME}`
2. `ddl-auto` 从 `update` 改为 `validate`
3. 测试密码改为 `${MYSQL_TEST_PASSWORD:test_password}`

### 3. P0-5 SSE 解析重构（PythonAIClient.java）
1. 初版：`bodyToFlux(String.class)` + `bufferUntil` + `parseSseEventFromLines`（失败）
2. 终版：`bodyToFlux(ServerSentEvent.class)` + `convertServerSentEvent`
3. 删除 `parseSseEventFromLines` 和 `splitSseEvents` 方法
4. `convertServerSentEvent` 兼容 data 为 Map 或 String 两种情况

### 4. P1-1 参数校验异常处理（GlobalExceptionHandler.java）
1. 新增 `@ExceptionHandler(ConstraintViolationException.class)` 方法
2. 收集所有 `ConstraintViolation` 的 `propertyPath` + `message`
3. 返回 400 + 分号分隔的错误信息

### 5. P1-2 Entity @Data 替换（4 个 Entity）
1. 移除 `@Data` 注解
2. 添加 `@Getter @Setter @EqualsAndHashCode(onlyExplicitlyIncluded = true)`
3. 在 `id` 字段添加 `@EqualsAndHashCode.Include`

### 6. P2-1 缓存精准失效（CacheEvictionHelper + Service）
1. 新建 `CacheEvictionHelper` 组件
2. 实现 `evictByPattern`：SCAN 扫描 + 分批 DEL
3. 实现 `evictByPatternAfterCommit`：事务提交后回调
4. `SessionService.createSession` 移除 `@CacheEvict(allEntries=true)`，改用 Helper
5. `FavoriteService.addFavorite/removeFavorite` 同上
6. 更新 6 个测试文件适配新逻辑

### 7. P2-2 SQL 日志降级（application.yml）
1. `org.hibernate.SQL` 从 `DEBUG` 改为 `WARN`
2. `org.hibernate.type.descriptor.sql.BasicBinder` 从 `TRACE` 改为 `WARN`

## 解决了什么问题

### 核心问题描述
1. **Redis RCE**：`LaissezFaireSubTypeValidator` 允许反序列化任意类型，攻击者可构造恶意 JSON 触发远程代码执行
2. **密码泄露**：明文密码在代码仓库中，任何有代码访问权限的人都能看到
3. **表结构风险**：`ddl-auto: update` 在生产环境可能意外修改表结构（如删除字段）
4. **SSE 丢失**：跨 TCP 块的 SSE 事件被错误分割，导致事件丢失
5. **缓存雪崩**：`allEntries=true` 清空整个缓存空间，所有用户缓存同时失效

### 解决方案对比
- Redis RCE：白名单 vs 关闭 DefaultTyping（白名单保持兼容性）
- SSE 解析：ServerSentEvent vs 手动解析（ServerSentEvent 更可靠）
- 缓存失效：SCAN 精准失效 vs allEntries（精准失效不影响其他用户）

### 最终方案的优势
- 安全性：白名单验证器消除 RCE 风险，同时保持序列化兼容性
- 可靠性：Spring 内置 SSE 解析器经过充分测试，比手动解析更可靠
- 隔离性：按用户前缀精准失效，用户间缓存互不影响
- 一致性：事务提交后清缓存，避免脏读回填

## 变更内容

### 新增文件
- `cache/CacheEvictionHelper.java`：缓存精准失效工具，SCAN + 事务提交后回调

### 修改文件
| 文件 | 变更点 |
|------|--------|
| `config/RedisConfig.java` | 反序列化白名单验证器 |
| `resources/application.yml` | 密码环境变量、ddl-auto、SQL 日志级别 |
| `test/resources/application-test.yml` | 测试密码环境变量 |
| `client/PythonAIClient.java` | SSE 解析改用 ServerSentEvent |
| `exception/GlobalExceptionHandler.java` | 新增 ConstraintViolationException 处理器 |
| `entity/Paper.java` | @Data → @Getter/@Setter/@EqualsAndHashCode |
| `entity/Session.java` | 同上 |
| `entity/AnalysisResult.java` | 同上 |
| `entity/PaperFavorite.java` | 同上 |
| `service/SessionService.java` | 移除 @CacheEvict，改用 CacheEvictionHelper |
| `service/FavoriteService.java` | 同上 |

### 配置变更
| 配置项 | 旧值 | 新值 |
|--------|------|------|
| `spring.datasource.password` | 明文 | `${MYSQL_PASSWORD:CHANGE_ME}` |
| `spring.jpa.hibernate.ddl-auto` | `update` | `validate` |
| `logging.level.org.hibernate.SQL` | `DEBUG` | `WARN` |
| 测试 `spring.datasource.password` | 明文 | `${MYSQL_TEST_PASSWORD:test_password}` |

## 关键技术点

### 1. BasicPolymorphicTypeValidator 白名单
```java
BasicPolymorphicTypeValidator.builder()
    .allowIfSubType("com.literatureassistant.")  // 业务实体
    .allowIfSubType("java.util.")                 // 集合类型
    .allowIfSubType("java.time.")                 // 时间类型
    .allowIfSubType("java.lang.")                 // 基础类型
    .build()
```
- `allowIfSubType` 匹配类名前缀，支持子类
- 仅允许白名单内的类型被反序列化，阻止恶意类注入

### 2. ServerSentEvent 解析
```java
.bodyToFlux(ServerSentEvent.class)
.map(this::convertServerSentEvent)

private AgentSseEvent convertServerSentEvent(ServerSentEvent<?> sse) {
    // sse.id() → Long
    // sse.event() → String (事件类型)
    // sse.data() → Object (可能是 Map 或 String)
}
```
- `ServerSentEventHttpMessageReader` 自动处理 SSE 协议（id/event/data 字段、跨块分片）
- 无需手动处理 `\n\n` 分隔和行解析

### 3. Cache-Aside 写后删模式
```java
public void evictByPatternAfterCommit(String pattern) {
    if (TransactionSynchronizationManager.isSynchronizationActive()) {
        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                evictByPattern(pattern);
            }
        });
    } else {
        evictByPattern(pattern);
    }
}
```
- **为什么不在方法内直接删**：事务未提交前删缓存，其他请求可能读到旧数据并回填缓存
- **为什么在 afterCommit 删**：事务已提交，DB 数据已更新，删缓存后下次读会从 DB 加载新数据
- **无事务上下文时**：直接删（如单元测试场景）

### 4. SCAN 分批删除
```java
redisTemplate.execute((RedisCallback<Void>) connection -> {
    List<byte[]> batch = new ArrayList<>(DELETE_BATCH_SIZE);
    try (Cursor<byte[]> cursor = connection.scan(options)) {
        while (cursor.hasNext()) {
            batch.add(cursor.next());
            if (batch.size() >= DELETE_BATCH_SIZE) {
                connection.del(batch.toArray(new byte[0][]));
                batch.clear();
            }
        }
    }
    if (!batch.isEmpty()) {
        connection.del(batch.toArray(new byte[0][]));
    }
    return null;
});
```
- **SCAN vs KEYS**：SCAN 是游标式扫描，不阻塞 Redis；KEYS 会阻塞
- **分批 DEL**：避免单次 DEL 大量 key 造成 Redis 阻塞
- **try-with-resources**：确保 Cursor 正确关闭

## 经验总结

### 开发过程中的收获
1. **Spring WebClient 的 Content-Type 敏感性**：`bodyToFlux(String.class)` 在不同 Content-Type 下行为不同，`text/event-stream` 会触发 `ServerSentEventHttpMessageReader`
2. **@RequiredArgsConstructor 与测试**：新增 final 字段会改变构造函数签名，手动构造的测试需同步更新
3. **Cache-Aside 写后删**：缓存清除时机很重要，事务提交前清缓存可能导致脏读回填
4. **SCAN vs KEYS**：生产环境严禁使用 KEYS，必须用 SCAN

### 踩过的坑及如何避免
1. **`bodyToFlux(String.class)` 在 SSE 下被拦截**：初版 P0-5 修复用 `String.class`，测试全部失败。原因是 `ServerSentEventHttpMessageReader` 拦截了 `text/event-stream` 的 String 解码。**避免方式**：SSE 流直接用 `ServerSentEvent.class`，不要用 `String.class`
2. **`ServerSentEvent.data()` 类型不确定**：有时是 String，有时是 Map。**避免方式**：用 `instanceof` 判断兼容两种情况
3. **构造函数签名变更导致测试编译失败**：新增 `CacheEvictionHelper` 字段后，`@RequiredArgsConstructor` 生成的构造函数变化。**避免方式**：修改 Service 构造函数后，全局搜索 `new XxxService(` 确保所有手动构造的测试同步更新
4. **环境变量未设置导致集成测试失败**：`LiteratureAssistantApplicationTests` 需要真实数据库连接。**避免方式**：CI 环境配置 `MYSQL_TEST_PASSWORD` 环境变量

### 最佳实践建议
1. **Redis 反序列化必须用白名单**：永远不要用 `LaissezFaireSubTypeValidator`
2. **密码必须环境变量化**：代码仓库中不应出现明文密码
3. **生产环境 ddl-auto 必须 validate**：避免意外表结构变更
4. **SSE 流用 ServerSentEvent**：不要手动解析 SSE 协议
5. **缓存失效要精准**：避免 `allEntries=true` 影响其他用户
6. **缓存清除要在事务提交后**：遵循 Cache-Aside 写后删模式
7. **Redis 扫描用 SCAN 不用 KEYS**：避免阻塞 Redis
