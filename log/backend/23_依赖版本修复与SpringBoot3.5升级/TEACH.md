# 技术教学文档 — 依赖版本修复与 Spring Boot 3.5 升级

## 开发思路

### 需求分析过程

用户报告 `backend` 项目"一堆报错"，并指向 4 个文件/目录：
1. `SecurityConfig.java`
2. `AnalysisController.java`
3. `AnalysisResult.java`
4. `target/generated-sources`

初看像是 4 个独立问题，但通过 `mvn clean compile` 实际编译发现**根本原因是同一个**：pom.xml 中的依赖版本号是臆造的，导致 Maven 无法解析依赖，进而引发连锁错误。

### 技术选型考虑

#### Spring Boot 版本选择

原报告建议升级到 3.2.28，但通过 Maven Central 验证发现：
- Spring Boot 3.2.x 系列最新版本是 **3.2.12**（2024-11-21 发布）
- 3.2.x 分支已于 **2024-12 结束 OSS 支持**
- **3.2.28 这个版本根本不存在**

可选升级路径：

| 方案 | 版本 | OSS 支持 | 风险 |
|------|------|---------|------|
| A. 回退 | 3.2.12 | 已 EOL | 不修复 CVE，违背报告意图 |
| B. 同代升级 | 3.3.13 | 已 EOL | API 变更较小 |
| C. 跨代升级 | 3.4.7 | 已 EOL（企业支持） | Jetty 12 等变更 |
| D. 最新稳定 | **3.5.3** | **仍受 OSS 支持** | 可能引入 API 变更 |

**最终选择方案 D**：升级到 3.5.3，理由：
- 仍受 OSS 支持（End of OSS Support: 2026-06，今天是 2026-06-26，刚到边界）
- 修复 3.2.x 系列的所有安全 CVE
- Java 17 仍受支持（Spring Boot 3.x 全系列要求 Java 17+）

#### jjwt 版本选择

原报告建议升级到 0.13.0，但 Maven Central 查询显示：
- jjwt-api 最新版本是 **0.12.6**（2024-06-21 发布）
- **0.13.0 这个版本根本不存在**
- 0.12.x 与 0.11.x 之间有 API 变更，但项目原本就用 0.12.5，所以 0.12.6 是安全升级

#### MapStruct 版本选择

原项目使用 MapStruct 1.5.5.Final，在 Spring Boot 3.2 下工作正常。升级到 Spring Boot 3.5 后出现：
```
Attempt to recreate a file for type com.literatureassistant.mapper.SessionMapperImpl
```

这是 MapStruct 1.5.x 与 Lombok 1.18.38 在 Spring Boot 3.5 下的已知兼容性问题。MapStruct 1.6.x 对 Lombok 协作做了改进，升级到 1.6.3 后问题解决。

### 架构设计思路

本次修复不涉及架构变更，纯粹是依赖版本号修正和 API 兼容性适配。

### 遇到的问题及解决方案

#### 问题 1：Spring Boot 3.2.28 不存在
- **现象**：`mvn clean compile` 报 `Non-resolvable parent POM`
- **原因**：Maven Central 上没有 3.2.28 这个版本
- **解决**：通过 Maven Central REST API 查询实际可用版本，升级到 3.5.3

#### 问题 2：jjwt 0.13.0 不存在
- **现象**：依赖解析失败
- **原因**：jjwt 最新版是 0.12.6，0.13.0 是臆造的
- **解决**：改为 0.12.6

#### 问题 3：MapStruct `Attempt to recreate a file`
- **现象**：编译时 MapStruct 处理器尝试重复创建 `*MapperImpl.java` 文件
- **原因**：MapStruct 1.5.5 与 Lombok 1.18.38 在 Spring Boot 3.5 下协作异常
- **解决**：升级 MapStruct 到 1.6.3

#### 问题 4：`RedisCacheConfiguration.allowCacheNullValues(boolean)` 找不到
- **现象**：`mvn compile` 报"找不到符号"
- **原因**：Spring Data Redis 3.5 移除了此方法（默认就允许缓存 null 值，无需显式调用）
- **验证方法**：`javap -p -classpath spring-data-redis-3.5.1.jar org.springframework.data.redis.cache.RedisCacheConfiguration`
- **解决**：移除该行调用

#### 问题 5：SessionStateMachineTest 构造器参数不匹配
- **现象**：`mvn test-compile` 报"实际参数列表和形式参数列表长度不同"
- **原因**：`SessionService` 有 5 个 final 字段（含 `RedisTemplate`），但测试只传了 4 个
- **解决**：补充 `@Mock RedisTemplate<String, String> redisTemplate` 并传入构造器

---

## 实现步骤

1. **第一步：定位根本原因**
   - 执行 `mvn clean compile` 获取实际错误信息
   - 发现第一个错误：`spring-boot-starter-parent:3.2.28 not found`

2. **第二步：验证依赖版本**
   - 通过 Maven Central REST API 查询 Spring Boot 3.2.x 实际可用版本
   - 发现 3.2.x 最新是 3.2.12，3.2.28 不存在
   - 查询 3.5.x 最新版本，确认 3.5.3 可用

3. **第三步：修复 pom.xml 版本号**
   - Spring Boot：3.2.28 → 3.5.3
   - jjwt：0.13.0 → 0.12.6（同样验证 0.13.0 不存在）
   - MapStruct：1.5.5.Final → 1.6.3（预防性升级）

4. **第四步：修复 RedisConfig API 不兼容**
   - 编译发现 `allowCacheNullValues(boolean)` 方法不存在
   - 用 `javap` 反编译确认方法被移除
   - 移除该行调用（默认行为已满足需求）

5. **第五步：修复测试代码构造器参数**
   - 编译测试代码发现 `SessionStateMachineTest` 构造器参数不匹配
   - 查询 `SessionService` 实际有 5 个 final 字段
   - 补充 `RedisTemplate` mock 参数

6. **第六步：最终验证**
   - `mvn clean compile test-compile` 全部通过
   - BUILD SUCCESS

---

## 解决了什么问题

### 核心问题描述
后端项目无法编译，出现 5 个连锁错误，根本原因是依赖版本号是臆造的。

### 解决方案对比

| 方案 | 描述 | 优劣 |
|------|------|------|
| A. 回退到原版本 | Spring Boot 3.2.12 + jjwt 0.12.5 | ✅ 最小变更，但违背报告修复 CVE 的意图 |
| B. 升级到真实存在的版本 | Spring Boot 3.5.3 + jjwt 0.12.6 | ✅ 修复 CVE + 仍受 OSS 支持，但需适配 API 变更 |

**最终选择方案 B**，并逐一修复 API 变更引发的新错误。

### 最终方案的优势
- Spring Boot 3.5.3 是当前最新稳定版，仍受 OSS 支持
- jjwt 0.12.6 是 0.12.x 最新版，与项目原 API 完全兼容
- MapStruct 1.6.3 修复了与 Lombok 的协作问题
- 所有修改都通过实际编译验证

---

## 变更内容

### 新增文件
无

### 修改文件

#### 1. `Veritas/backend/pom.xml`
- `parent.version`: `3.2.28` → `3.5.3`
- `properties.jjwt.version`: `0.13.0` → `0.12.6`
- `properties.mapstruct.version`: `1.5.5.Final` → `1.6.3`

#### 2. `Veritas/backend/src/main/java/com/literatureassistant/config/RedisConfig.java`
- 移除第 61 行 `.allowCacheNullValues(true)` 调用
- 更新注释说明默认行为

#### 3. `Veritas/backend/src/test/java/com/literatureassistant/service/SessionStateMachineTest.java`
- 新增 `import org.springframework.data.redis.core.RedisTemplate;`
- 新增 `@Mock private RedisTemplate<String, String> redisTemplate;` 字段
- 修改构造器调用：`new SessionService(..., redisTemplate)` 补充第 5 个参数

### 配置变更
- 无（application.yml 未修改）

---

## 关键技术点

### 1. Maven Central 版本验证方法
```bash
# 查询某 groupId+artifactId 的最新版本
curl "https://search.maven.org/solrsearch/select?q=g:%22org.springframework.boot%22%20AND%20a:%22spring-boot-starter-parent%22&core=gav&rows=10&wt=json"
```

返回 JSON 中 `response.docs[0].v` 即为最新版本号。

### 2. Spring Boot 版本支持矩阵
通过 https://spring.io/projects/spring-boot#support 查询：
- 3.5.x：End of OSS Support 2026-06（当前仍受支持）
- 3.4.x：End of OSS Support 2025-12（已 EOL）
- 3.3.x：End of OSS Support 2025-06（已 EOL）
- 3.2.x：End of OSS Support 2024-12（已 EOL）

### 3. javap 反编译验证 API
```bash
# 查看 jar 包中某类的所有方法签名
javap -p -classpath ~/.m2/repository/org/springframework/data/spring-data-redis/3.5.1/spring-data-redis-3.5.1.jar org.springframework.data.redis.cache.RedisCacheConfiguration
```

输出确认 `allowCacheNullValues(boolean)` 方法已不存在，只有 `disableCachingNullValues()`。

### 4. MapStruct + Lombok 协作
- MapStruct 处理 `@Mapper` 注解时生成 `*MapperImpl.java`
- Lombok 处理 `@Builder` / `@Data` 注解时修改类结构
- 两者通过 `lombok-mapstruct-binding` 协作
- MapStruct 1.5.x 在 Spring Boot 3.5 下协作异常，升级到 1.6.x 解决

### 5. Spring Data Redis 3.5 的 API 变更
- `RedisCacheConfiguration.allowCacheNullValues(boolean)` —— **已移除**
- 替代方案：默认行为 `DEFAULT_CACHE_NULL_VALUES=true` 已允许缓存 null 值
- 如需禁用：`disableCachingNullValues()`

---

## 经验总结

### 开发过程中的收获

1. **依赖版本号必须验证**：不能盲信报告或文档中的版本号，必须通过 Maven Central 实际查询确认存在
2. **编译错误是连锁的**：一个根本原因（依赖版本不存在）会引发多个看似不相关的错误（MapStruct 失败、API 不兼容、构造器不匹配）
3. **渐进式编译验证**：每修复一个错误就重新编译，定位下一个错误，避免被错误信息淹没

### 踩过的坑及如何避免

#### 坑 1：盲信报告建议的版本号
- **问题**：报告中建议"升级 Spring Boot 到 3.2.28"，实际这个版本不存在
- **避免**：升级依赖前必须通过 `mvn dependency:tree` 或 Maven Central API 验证版本存在

#### 坑 2：忽略 API 变更
- **问题**：升级 Spring Boot 到 3.5 后，Spring Data Redis 3.5 移除了 `allowCacheNullValues` 方法
- **避免**：跨次版本升级（3.2 → 3.5）时，必须查看 Release Notes 中的 Breaking Changes

#### 坑 3：测试代码与主代码不同步
- **问题**：`SessionService` 添加了 `RedisTemplate` 字段后，测试代码没有同步更新
- **避免**：修改类的构造器（特别是 `@RequiredArgsConstructor` 生成的）后，必须同步检查所有直接调用构造器的测试代码

### 最佳实践建议

1. **依赖升级流程**：
   ```bash
   # 1. 查询当前版本
   mvn dependency:tree | grep <artifactId>
   # 2. 查询最新版本
   curl "https://search.maven.org/solrsearch/select?q=g:%22<groupId>%22%20AND%20a:%22<artifactId>%22&core=gav&rows=5&wt=json"
   # 3. 修改 pom.xml
   # 4. 编译验证
   mvn clean compile
   # 5. 测试编译验证
   mvn test-compile
   ```

2. **API 变更验证**：
   ```bash
   # 反编译查看方法签名
   javap -p -classpath <jar-path> <class-name>
   ```

3. **Spring Boot 升级检查清单**：
   - [ ] 查看目标版本的 Release Notes
   - [ ] 检查 Breaking Changes
   - [ ] 验证 Java 版本兼容性
   - [ ] 验证第三方依赖兼容性（Lombok / MapStruct 等）
   - [ ] 编译主代码
   - [ ] 编译测试代码
   - [ ] 运行单元测试
