# Task 39：缓存命中率测试 + 一致性验证（Week10 D3-4）

> **课题编号**：XH-202630
> **版本**：v0.5
> **里程碑**：JM5 缓存优化与功能完善（Week 10 Day 3-4）
> **功能编号**：F2.6.1, F2.6.2, F2.6.3, F2.6.4, F2.6.5, F2.6.6
> **创建日期**：2026-06-17

---

## 1. Context（项目上下文）

### 项目
XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究

### 当前版本
v0.5 / JM5：缓存优化与功能完善（Week 10 Day 3-4）

### 需求描述
缓存命中率测试 + 一致性验证：
- 缓存命中率测试（UserService/PaperService/SessionService/AnalysisService，命中率>50%）
- Cache-Aside 写后删策略验证（写操作后缓存立即失效，读操作回填）
- 双重失效验证（userProfile+userProfileJson+userInfo 同步失效）
- 缓存穿透防护验证（空值缓存 TTL=60s）
- 缓存雪崩防护验证（TTL ±10% 随机偏移）
- Agent状态Hash与SSE同步验证
- 缓存Key命名规范验证（RedisKeyUtil 统一生成）

### 参考文档
- `docs/backend/Java后端模块系统架构文档.md` — 第9章 缓存管理
- `docs/backend/Java后端模块项目里程碑文档.md` — 第7章 JM5 Week 10 Day 3-4
- `AGENTS.md` — 关键规则第6条 Cache-Aside 写后删

---

## 2. Current Architecture（当前架构）

### 涉及层级
- java_backend
- data_layer

### 相关模块
| 模块 | 路径 | 职责 |
|------|------|------|
| UserService | `com.literatureassistant.service` | task32 已添加 @Cacheable/@CacheEvict + syncProfileToRedis |
| PaperService | `com.literatureassistant.service` | task33 已添加 @Cacheable(paperDetail/paperSearch)，task35 扩展参数 |
| SessionService | `com.literatureassistant.service` | task34 已为 createSession/listSessions 加缓存 |
| AnalysisService | `com.literatureassistant.service` | task34 已为写方法补 @CacheEvict |
| AgentClientService | `com.literatureassistant.service` | 手动RedisTemplate：agent:state Hash + analysis:result String |
| RedisConfig | `com.literatureassistant.config` | 7个缓存空间，TTL_JITTER_RATIO=0.1 |
| RedisKeyUtil | `com.literatureassistant.util` | 11个key方法，统一命名规范 |

### 已有实现
- `RedisConfig.java` — cacheManager 配置7个缓存空间，applyJitter 方法实现±10%随机偏移
- `RedisKeyUtil.java` — 11个静态key方法，统一命名规范 {域}:{操作}:{标识符}
- `UserService.java` — @Cacheable(userInfo/userProfile) + @CacheEvict(userProfile+userProfileJson+userInfo)
- `PaperService.java` — @Cacheable(paperDetail/paperSearch) + listPapers缓存
- `SessionService.java` — @Cacheable(sessionState/sessionList) + @CacheEvict
- `AnalysisService.java` — @Cacheable(analysisResult) + 写方法 @CacheEvict
- `AgentClientService.java` — 手动RedisTemplate，agent:state Hash(TTL=5min)

---

## 3. Relevant Modules（关键模块）

### CacheHitRateTest（新建）
- **路径**：`Veritas/backend/src/test/java/com/literatureassistant/cache/CacheHitRateTest.java`
- **职责**：缓存命中率测试：验证4个Service缓存命中率 > 50%
- **关键接口**：
  - `testUserServiceCacheHitRate()` — 验证 UserService 命中率
  - `testPaperServiceCacheHitRate()` — 验证 PaperService 命中率
  - `testSessionServiceCacheHitRate()` — 验证 SessionService 命中率
  - `testAnalysisServiceCacheHitRate()` — 验证 AnalysisService 命中率

### CacheConsistencyTest（新建）
- **路径**：`Veritas/backend/src/test/java/com/literatureassistant/cache/CacheConsistencyTest.java`
- **职责**：缓存一致性验证：Cache-Aside写后删 + 双重失效 + 读回填 + Agent状态Hash与SSE同步
- **关键接口**：
  - `testCacheAsideWriteAfterDelete()` — 验证写后删策略
  - `testDoubleInvalidationUserProfile()` — 验证双重失效
  - `testReadRefillCache()` — 验证读回填
  - `testAgentStateHashSseSync()` — 验证Agent状态Hash与SSE同步

### CachePenetrationAvalancheTest（新建）
- **路径**：`Veritas/backend/src/test/java/com/literatureassistant/cache/CachePenetrationAvalancheTest.java`
- **职责**：缓存穿透与雪崩防护验证
- **关键接口**：
  - `testPenetrationProtectionEmptyCache()` — 验证空值缓存 TTL=60s
  - `testAvalancheProtectionTtlJitter()` — 验证 TTL ±10% 随机偏移
  - `testCacheKeyNamingConvention()` — 验证Key命名规范

---

## 4. Files To Modify（变更文件）

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `cache/CacheHitRateTest.java` | 缓存命中率测试（4个Service） |
| 新增 | `cache/CacheConsistencyTest.java` | 缓存一致性测试（写后删+双重失效+读回填+Agent同步） |
| 新增 | `cache/CachePenetrationAvalancheTest.java` | 穿透与雪崩防护测试（空值缓存+TTL偏移+Key规范） |

---

## 5. Implementation Requirements（实现要求）

### 功能要求

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | testUserServiceCacheHitRate：10次相同查询，9次命中，命中率90%>50% | UserService 命中率 > 50% |
| FR-002 | P0 | testPaperServiceCacheHitRate：getPaperDetail + searchPapers 命中率 > 50% | PaperService 命中率 > 50% |
| FR-003 | P0 | testSessionServiceCacheHitRate：getSessionDetail 命中率 > 50% | SessionService 命中率 > 50% |
| FR-004 | P0 | testAnalysisServiceCacheHitRate：getAnalysisResult 命中率 > 50% | AnalysisService 命中率 > 50% |
| FR-005 | P0 | testCacheAsideWriteAfterDelete：写操作后缓存失效，读操作回填 | 写后删策略生效 |
| FR-006 | P0 | testDoubleInvalidationUserProfile：三个缓存 key 同步失效 | 双重失效验证通过 |
| FR-007 | P0 | testReadRefillCache：缓存miss后从DB读取并写入缓存 | 读回填正确 |
| FR-008 | P1 | testAgentStateHashSseSync：Agent状态Hash与SSE同步，TTL=5min | Agent状态同步 |
| FR-009 | P0 | testPenetrationProtectionEmptyCache：空值缓存 TTL=60s | 空值缓存生效 |
| FR-010 | P0 | testAvalancheProtectionTtlJitter：TTL 在 baseSeconds±10% 范围内 | TTL偏移正确 |
| FR-011 | P1 | testCacheKeyNamingConvention：RedisKeyUtil 11个方法返回key符合规范 | Key命名规范 |
| FR-012 | P0 | 测试使用 @SpringBootTest + @Autowired，@AfterEach 清理测试key | 测试隔离正确 |

### 跨系统一致性
- **字段命名**：Java camelCase ↔ Python/JSON snake_case
  - userId ↔ user_id
  - paperId ↔ paper_id
  - analysisId ↔ analysis_id
  - sessionId ↔ session_id
- **数据流转**：测试 → Service(@Cacheable/@CacheEvict) → RedisTemplate → Redis

### 安全要求
- **数据隔离**：测试数据使用测试专用ID，测试后清理缓存

---

## 6. Constraints（约束）

### 命名规范
- Java: 类名PascalCase, 方法/变量camelCase, 常量UPPER_SNAKE_CASE, 文件PascalCase.java
- JSON: 字段名snake_case

### 分层规范
- Controller → Service → Repository → Client，禁止跨层

### 错误处理
- BusinessException + GlobalExceptionHandler

### 缓存策略
- Cache-Aside：写MySQL后删Redis缓存
- TTL分层：userProfile/userInfo(1h) / paperDetail(30min) / paperSearch(10min) / analysisResult(30min) / sessionState(2h) / agentState(5min) / favoriteList(10min)
- 缓存穿透防护：空值缓存 TTL=60s
- 缓存雪崩防护：TTL ±10% 随机偏移
- 单个缓存值不超过1MB

### 日志规范
- SLF4J + Logback
- 禁止循环内 INFO+ 日志

### 安全规范
- 测试数据使用测试专用ID，测试后清理

---

## 7. Forbidden Actions（禁止行为）

| ID | 禁止行为 | 原因 | 严重程度 |
|----|---------|------|---------|
| FA-001 | 输出伪代码或TODO注释 | 必须输出完整可执行代码 | critical |
| FA-002 | 修改需求范围外的模块 | 避免引入无关变更 | high |
| FA-003 | 破坏三层分离架构 | 架构约束ADR-001 | critical |
| FA-004 | 破坏分层调用规范 | 分层架构约束 | critical |
| FA-005 | Entity直接返回给前端 | 数据隔离与接口稳定性 | high |
| FA-006 | 硬编码敏感配置 | 安全约束 | critical |
| FA-007 | 违反跨系统字段命名约定 | 跨系统一致性约束 | high |
| FA-008 | 在循环中打印INFO及以上级别日志 | 性能约束 | medium |
| FA-009 | 使用SQL拼接 | SQL注入防护 | critical |
| FA-010 | 忽略降级场景 | 可用性约束ADR-003 | high |

---

## 8. Test Requirements（测试要求）

### 单元测试
| 测试名 | 描述 | 覆盖场景 |
|--------|------|---------|
| testUserServiceCacheHitRate | 验证 UserService 命中率 > 50% | normal_flow |
| testPaperServiceCacheHitRate | 验证 PaperService 命中率 > 50% | normal_flow |
| testSessionServiceCacheHitRate | 验证 SessionService 命中率 > 50% | normal_flow |
| testAnalysisServiceCacheHitRate | 验证 AnalysisService 命中率 > 50% | normal_flow |
| testCacheAsideWriteAfterDelete | 验证写后删策略 | normal_flow |
| testDoubleInvalidationUserProfile | 验证双重失效 | normal_flow |
| testReadRefillCache | 验证读回填 | normal_flow |
| testAgentStateHashSseSync | 验证Agent状态Hash与SSE同步 | normal_flow |
| testPenetrationProtectionEmptyCache | 验证空值缓存 TTL=60s | normal_flow, boundary_condition |
| testAvalancheProtectionTtlJitter | 验证 TTL ±10% 偏移 | normal_flow, boundary_condition |
| testCacheKeyNamingConvention | 验证Key命名规范 | normal_flow |

### 验证命令
```bash
cd Veritas/backend && mvn test -Dtest=CacheHitRateTest
cd Veritas/backend && mvn test -Dtest=CacheConsistencyTest
cd Veritas/backend && mvn test -Dtest=CachePenetrationAvalancheTest
```

---

## 9. Acceptance Criteria（验收标准）

| ID | 验收标准 | 验证方式 |
|----|---------|---------|
| AC-001 | UserService 缓存命中率 > 50% | automated_test |
| AC-002 | PaperService 缓存命中率 > 50% | automated_test |
| AC-003 | SessionService 缓存命中率 > 50% | automated_test |
| AC-004 | AnalysisService 缓存命中率 > 50% | automated_test |
| AC-005 | 写操作后缓存立即失效（Cache-Aside 写后删） | automated_test |
| AC-006 | 双重失效：userProfile + userProfileJson + userInfo 同步失效 | automated_test |
| AC-007 | 读操作回填缓存 | automated_test |
| AC-008 | 空值缓存 TTL=60s 生效 | automated_test |
| AC-009 | TTL 随机偏移在 ±10% 范围内 | automated_test |
| AC-010 | Agent状态Hash与SSE同步 | automated_test |
| AC-011 | 缓存Key命名符合 RedisKeyUtil 规范 | automated_test |
| AC-012 | mvn test 全量通过 | automated_test |
