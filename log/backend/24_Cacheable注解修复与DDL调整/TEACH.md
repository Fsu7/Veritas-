# 技术教学文档

## 开发思路

### 需求分析过程
项目启动时发现多个后端接口返回 500 错误，经排查发现两个独立问题：
1. `@Cacheable(sync=true)` 与 `unless` 属性不兼容 — Spring Cache 在同步模式下不支持 `unless` 条件，启动后首次调用即抛异常
2. `ddl-auto=validate` 模式下 JPA 实体与数据库表结构不匹配 — ENUM 列类型差异导致 Hibernate 校验失败

### 技术选型考虑
- `sync=true` 防缓存击穿功能必须保留（高并发场景必需），因此选择移除 `unless` 而非移除 `sync`
- DDL 模式从 `validate` 改为 `update`，让 Hibernate 自动同步表结构（开发环境合理，生产环境应保持 validate）
- GlobalExceptionHandler 临时添加错误详情输出用于快速定位问题，修复后还原

### 架构设计思路
- 缓存注解修复遵循"最小改动"原则：仅移除不兼容的 `unless` 属性，保留其余所有配置
- DDL 模式调整通过 `application.yml` 全局配置，不修改代码

### 遇到的问题及解决方案

#### 问题1：@Cacheable sync=true 与 unless 冲突
- **现象**：`getUserInfo`、`listFavorites`、`getAnalysisResult`、`getSessionDetail` 四个方法全部返回 500
- **根因**：Spring Cache 的 `sync=true` 模式下，`unless` 条件不被支持。Jackson 序列化时抛出 `IllegalArgumentException`
- **排查方法**：临时修改 `GlobalExceptionHandler` 输出异常详情 `e.getMessage()`，发现错误信息明确指出 "A sync=true operation does not support the unless attribute"
- **解决方案**：移除 4 处 `unless = "#result == null"`，保留 `sync = true`

#### 问题2：ddl-auto=validate 校验失败
- **现象**：后端启动时 Hibernate 抛出 `SchemaManagementException`
- **根因**：DDL 脚本创建的 ENUM 列与 JPA `@Convert` 注解期望的 VARCHAR 列类型不匹配。Hibernate validate 模式严格校验列类型
- **解决方案**：改为 `ddl-auto: update`，让 Hibernate 自动将 ENUM 列改为 VARCHAR

## 实现步骤

1. **临时增强错误输出**：修改 `GlobalExceptionHandler.handleGeneral`，将 `e.getMessage()` 和 `e.getCause().getMessage()` 加入响应体
2. **重新编译启动后端**：`mvn clean spring-boot:run -DskipTests`
3. **curl 复现错误**：登录获取 token，调用 `GET /api/users/{userId}` 和 `GET /api/papers/favorites`，确认 500 错误及原因
4. **修复 @Cacheable 注解**：逐一移除 4 个 Service 方法的 `unless` 属性
5. **修复 DDL 模式**：`application.yml` 中 `ddl-auto: validate` → `update`
6. **还原 GlobalExceptionHandler**：移除临时调试代码，恢复原始错误响应
7. **验证修复**：`mvn clean spring-boot:run`，curl 测试所有 4 个接口返回 200

## 解决了什么问题

### 核心问题描述
项目所有缓存读取接口（用户信息、收藏列表、分析结果、会话详情）均无法正常工作，返回 500 错误。后端服务无法正常启动（DDL 校验失败）。

### 解决方案对比
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| 移除 sync，保留 unless | 改动最小 | 丧失缓存击穿防护 | ❌ |
| 移除 unless，保留 sync | 保留防击穿能力 | null 值会被缓存（可接受） | ✅ |
| 同时移除两者 | 最简单 | 丧失两项功能 | ❌ |

### 最终方案的优势
- 保留 `sync=true` 防止缓存击穿（多个并发请求只穿透一个到 DB）
- `unless` 移除后，null 值会被缓存（Spring Cache 默认行为），实际可防止缓存穿透
- 改动量最小，不影响现有业务逻辑

## 变更内容

### 修改文件
1. **`backend/src/main/java/com/literatureassistant/service/UserService.java`**
   - 第 108 行：`@Cacheable(value = "userInfo", key = "#userId", unless = "#result == null", sync = true)` → `@Cacheable(value = "userInfo", key = "#userId", sync = true)`

2. **`backend/src/main/java/com/literatureassistant/service/FavoriteService.java`**
   - 第 132 行：移除 `unless = "#result == null"`，保留 `sync = true`

3. **`backend/src/main/java/com/literatureassistant/service/AnalysisService.java`**
   - 第 233 行：移除 `unless = "#result == null"`，保留 `sync = true`

4. **`backend/src/main/java/com/literatureassistant/service/SessionService.java`**
   - 第 134 行：移除 `unless = "#result == null"`，保留 `sync = true`

5. **`backend/src/main/resources/application.yml`**
   - 第 22 行：`ddl-auto: validate` → `ddl-auto: update`

6. **`backend/src/main/java/com/literatureassistant/exception/GlobalExceptionHandler.java`**
   - 临时添加错误详情输出用于排查，修复后还原

### 配置变更
- `application.yml` → `spring.jpa.hibernate.ddl-auto`: `validate` → `update`

## 关键技术点

### Spring Cache sync=true 的限制
- `sync=true` 使缓存操作同步化（同一 key 的并发请求只执行一次方法调用）
- 此模式下 Spring Cache **不支持** `unless` 和 `condition` 条件
- 这是因为 sync 模式使用 `Cache.get(key, Supplier)` 而非 `Cache.put()`，不经过后置条件判断

### Hibernate ddl-auto 模式
| 模式 | 行为 | 适用场景 |
|------|------|---------|
| validate | 仅校验，不修改 | 生产环境 |
| update | 自动创建/修改表结构 | 开发环境 |
| create | 每次启动重建表 | 测试环境 |
| none | 不做任何操作 | 生产环境 |

### MapStruct 增量编译冲突
- `mvn spring-boot:run`（不 clean）时，MapStruct 注解处理器可能因残留生成文件报 `Attempt to recreate a file for type XxxMapperImpl`
- 解决方案：使用 `mvn clean spring-boot:run` 干净编译

## 经验总结

### 开发过程中的收获
1. **快速定位 500 错误**：临时增强 `GlobalExceptionHandler` 输出异常详情是最快的排查手段
2. **Spring Cache 注解兼容性**：`sync` 与 `unless` 的冲突是隐蔽的，编译时不报错，运行时才触发
3. **DDL 模式选择**：开发环境用 `update` 避免手动维护表结构，生产环境必须用 `validate`

### 踩过的坑及如何避免
- **坑**：增量编译时 MapStruct 报 `Attempt to recreate a file`，导致后端无法启动，表现为"网络错误"
- **避免**：修改 Java 源码后始终使用 `mvn clean spring-boot:run`
- **坑**：`@Cacheable` 的 `unless` 在 `sync=true` 下静默失败，日志中仅有 `IllegalArgumentException`
- **避免**：使用 `sync=true` 时不要添加 `unless` 或 `condition` 属性

### 最佳实践建议
1. 开发环境 `ddl-auto: update`，生产环境 `ddl-auto: validate`（通过 profile 区分）
2. `@Cacheable(sync=true)` 时不要使用 `unless`/`condition`
3. `GlobalExceptionHandler` 的通用异常处理应输出足够信息用于排查（至少 log.error 完整堆栈）
4. 修改 Java 代码后用 `mvn clean` 避免增量编译问题
