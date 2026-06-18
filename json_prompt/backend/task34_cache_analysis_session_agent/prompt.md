# Task 34: 分析结果缓存 + 会话状态缓存 + Agent状态缓存完善

> **课题编号**：XH-202630
> **版本**：v0.5
> **里程碑**：JM5 缓存优化与功能完善（Week 9 Day 3）
> **功能编号**：F2.6.3, F2.6.4, F2.6.5, F2.3.1, F2.3.2, F2.4.1, F2.4.4
> **创建日期**：2026-06-17

---

## 1. Context

### 1.1 项目
XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究

### 1.2 当前版本
v0.5 / JM5：缓存优化与功能完善（Week 9 Day 3）

### 1.3 需求描述
完善分析结果缓存、会话状态缓存、Agent状态缓存：
- AnalysisService 写方法补 @CacheEvict（analyzePaper/comparePapers/generateReport）
- 统一 AnalysisService 的 Spring Cache 与 AgentClientService 手动 Redis
- SessionService 为 createSession/listSessions 添加缓存
- AgentClientService Agent状态Hash缓存完善（与SSE同步验证）
- 缓存一致性保障 Cache-Aside 写后删策略验证

### 1.4 参考文档
- `docs/backend/Java后端模块系统架构文档.md` — 第6/7/8/9章
- `docs/backend/Java后端模块项目里程碑文档.md` — 第7章 JM5 Day 3
- `AGENTS.md` — 关键规则第6条 Cache-Aside

---

## 2. Current Architecture

### 2.1 涉及层级
- java_backend
- data_layer（Redis）

### 2.2 相关模块
| 模块路径 | 职责 |
|---------|------|
| `com.literatureassistant.service.AnalysisService` | 分析服务，已实现@Cacheable(analysisResult)，写方法未加@CacheEvict |
| `com.literatureassistant.service.SessionService` | 会话管理，已实现@Cacheable/@CacheEvict，createSession/listSessions未缓存 |
| `com.literatureassistant.service.AgentClientService` | AI服务调用，手动RedisTemplate操作，与Spring Cache分离 |
| `com.literatureassistant.config.RedisConfig` | 已配置analysisResult(30min)/sessionState(2h) |

### 2.3 已有实现
| 文件 | 描述 | 复用方式 |
|------|------|---------|
| `service/AnalysisService.java` | getAnalysisResult(@Cacheable)；写方法未加@CacheEvict | 扩展 |
| `service/SessionService.java` | getSessionDetail(@Cacheable)+updateStatus等(@CacheEvict)；createSession/listSessions未缓存 | 扩展 |
| `service/AgentClientService.java` | 手动RedisTemplate：agent:state Hash + analysis:result String | 扩展 |
| `config/RedisConfig.java` | 已配置analysisResult/sessionState缓存空间 | 直接复用 |

---

## 3. Relevant Modules

### 3.1 AnalysisService
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/service/AnalysisService.java`
- **职责**：分析服务业务，论文分析/对比/综述编排
- **关键接口**：
  - `@Cacheable(value="analysisResult", key="#analysisId") AnalysisResponse getAnalysisResult(...)`
  - `AnalysisTaskResponse analyzePaper(...)` — 未加@CacheEvict
  - `AnalysisTaskResponse comparePapers(...)` — 未加@CacheEvict
  - `AnalysisTaskResponse generateReport(...)` — 未加@CacheEvict

### 3.2 SessionService
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/service/SessionService.java`
- **职责**：会话管理业务，状态机驱动生命周期
- **关键接口**：
  - `SessionResponse createSession(...)` — 未加缓存
  - `PageResponse<SessionResponse> listSessions(...)` — 未加缓存
  - `@Cacheable(value="sessionState") SessionDetailResponse getSessionDetail(...)`

### 3.3 AgentClientService
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/service/AgentClientService.java`
- **职责**：AI服务调用编排，降级处理，Agent状态Redis管理
- **关键接口**：
  - `void updateAgentState(...)` — 写入 agent:state:{analysisId} Hash, TTL=5min
  - `private void cacheAnalysisResult(...)` — 写入 analysis:result:{analysisId} String, TTL=30min
  - `private AnalysisResultDTO handleFallback(...)` — 降级读取缓存

---

## 4. Files To Modify

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 修改 | `service/AnalysisService.java` | 写方法补@CacheEvict(analysisResult)；统一两套Key命名注释 |
| 修改 | `service/SessionService.java` | createSession加@CacheEvict(sessionList)；listSessions加@Cacheable(sessionList) |
| 修改 | `service/AgentClientService.java` | Agent状态Hash完善；注释说明手动Redis与Spring Cache分工 |
| 修改 | `config/RedisConfig.java` | 新增 sessionList 缓存空间（TTL=10min） |
| 新增 | `test/.../AnalysisCacheTest.java` | 分析结果缓存测试 |
| 新增 | `test/.../SessionCacheTest.java` | 会话缓存测试 |

---

## 5. Implementation Requirements

### 5.1 功能要求

| ID | 描述 | 优先级 | 验收条件 |
|----|------|--------|---------|
| FR-001 | AnalysisService 写方法补 @CacheEvict(analysisResult) | P0 | 分析完成后缓存被删除 |
| FR-002 | 统一 analysisResult 与 analysis:result 两套Key命名（注释说明） | P1 | 两套Key策略清晰说明 |
| FR-003 | SessionService 为 listSessions 添加 @Cacheable(sessionList)，TTL=10min | P1 | 第二次调用直接返回缓存 |
| FR-004 | SessionService 为 createSession 添加 @CacheEvict(sessionList, allEntries=true) | P1 | 创建会话后列表缓存被清空 |
| FR-005 | AgentClientService Agent状态Hash与SSE同步验证 | P1 | Hash与SSE一致 |
| FR-006 | RedisConfig 新增 sessionList 缓存空间（TTL=10min） | P1 | RedisConfig包含sessionList |
| FR-007 | Cache-Aside 写后删策略验证 | P0 | 策略验证通过 |

### 5.2 跨系统一致性
- **字段命名**：Java camelCase ↔ Python/JSON snake_case
- **关键字段映射**：analysisId↔analysis_id, sessionId↔session_id, userId↔user_id, agentName↔agent_name, durationMs↔duration_ms
- **数据流转**：分析结果 → MySQL + Redis(analysis:result)；Agent状态 → Redis(agent:state Hash) + SSE推送

### 5.3 降级要求
- **Agent降级**：单Agent超时30s跳过；多Agent失败降级为Retriever+Generator；review重试1次

### 5.4 安全要求
- **数据隔离**：缓存Key包含userId/sessionId/analysisId
- **敏感信息**：缓存中不得存储敏感信息

---

## 6. Constraints

### 6.1 缓存策略
- **模式**：Cache-Aside，写MySQL后删Redis缓存
- **TTL分层**：
  - analysisResult: 30min (27min~33min with ±10% jitter)
  - analysis:result: 30min (手动RedisTemplate)
  - sessionState: 2h (108min~132min with ±10% jitter)
  - sessionList: 10min (9min~11min with ±10% jitter)
  - agent:state: 5min (Hash, 手动RedisTemplate)
- **穿透防护**：空值缓存TTL=60s
- **雪崩防护**：TTL ±10%随机偏移
- **大小限制**：单个缓存值不超过1MB

### 6.2 其他约束
- 命名：Java PascalCase/camelCase, 数据库snake_case, JSON snake_case
- 分层：Controller → Service → Repository → Client
- 错误处理：BusinessException + GlobalExceptionHandler
- 日志：SLF4J + Logback，禁止循环日志、敏感信息
- 数据库：utf8mb4 + InnoDB，禁止SELECT *
- 安全：JWT + BCrypt + 数据隔离

---

## 7. Forbidden Actions

| ID | 禁止行为 | 原因 | 严重程度 |
|----|---------|------|---------|
| FA-001 | 输出伪代码或TODO注释 | 必须输出完整可执行代码 | critical |
| FA-002 | 修改需求范围外的模块 | 本任务仅涉及AnalysisService/SessionService/AgentClientService/RedisConfig | high |
| FA-003 | 破坏三层分离架构 | 架构约束ADR-001 | critical |
| FA-004 | 破坏分层调用规范 | 分层架构约束 | critical |
| FA-005 | Entity直接返回给前端 | 数据隔离与接口稳定性 | high |
| FA-006 | 硬编码敏感配置 | 安全约束 | critical |
| FA-007 | 违反跨系统字段命名约定 | 跨系统一致性约束 | high |
| FA-008 | 在循环中打印INFO及以上级别日志 | 性能约束 | medium |
| FA-009 | 使用SQL拼接 | SQL注入防护 | critical |
| FA-010 | 忽略降级场景 | 可用性约束ADR-003 | high |

---

## 8. Test Requirements

### 8.1 单元测试

| 测试名称 | 描述 | 覆盖场景 |
|---------|------|---------|
| `AnalysisCacheTest.getAnalysisResult_cacheHit_returnsCached` | 验证analysisResult缓存命中 | normal_flow |
| `AnalysisCacheTest.analyzePaper_evictsCache` | 验证analyzePaper完成后失效缓存 | normal_flow |
| `AnalysisCacheTest.handleFallback_readsCache` | 验证降级时读取缓存 | degradation |
| `SessionCacheTest.listSessions_cacheHit_returnsCached` | 验证sessionList缓存命中 | normal_flow |
| `SessionCacheTest.createSession_evictsListCache` | 验证createSession后列表缓存清空 | normal_flow |
| `SessionCacheTest.updateStatus_evictsStateCache` | 验证updateStatus后sessionState缓存删除 | normal_flow |
| `AgentClientServiceTest.updateAgentState_syncsWithSse` | 验证Agent状态Hash与SSE一致 | normal_flow |

### 8.2 验证命令
```bash
cd Veritas/backend && mvn test -Dtest=AnalysisCacheTest
cd Veritas/backend && mvn test -Dtest=SessionCacheTest
cd Veritas/backend && mvn compile
```

---

## 9. Acceptance Criteria

- [ ] AC-001: AnalysisService写方法补@CacheEvict(analysisResult)
- [ ] AC-002: analysisResult与analysis:result两套Key命名在注释中说明
- [ ] AC-003: SessionService为listSessions添加@Cacheable(sessionList)，TTL=10min
- [ ] AC-004: SessionService为createSession添加@CacheEvict(sessionList, allEntries=true)
- [ ] AC-005: AgentClientService Agent状态Hash与SSE同步验证通过
- [ ] AC-006: RedisConfig新增sessionList缓存空间，TTL=10min
- [ ] AC-007: Cache-Aside写后删策略验证通过
- [ ] AC-008: 缓存Key包含userId/sessionId/analysisId，确保数据隔离
- [ ] AC-009: mvn test 全部通过
