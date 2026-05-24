# XH-202630 科研文献智能助手 — Java后端模块项目里程碑文档

> **课题编号**：XH-202630
> **课题名称**：领域知识个性化生成与多智能体协同决策系统研究
> **发榜单位**：上海云之脑智能科技有限公司（科大讯飞全资子公司）
> **文档版本**：v1.0
> **创建日期**：2026年5月24日
> **文档状态**：初稿

---

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0 | 2026-05-24 | 项目组 | 初始版本 |

---

## 目录

- [1 文档概述](#1-文档概述)
- [2 Java后端里程碑总览](#2-java后端里程碑总览)
- [3 JM1：项目骨架与数据层就绪](#3-jm1项目骨架与数据层就绪)
- [4 JM2：基础API可用](#4-jm2基础api可用)
- [5 JM3：AI服务调用打通](#5-jm3ai服务调用打通)
- [6 JM4：分析服务与SSE推送完成](#6-jm4分析服务与sse推送完成)
- [7 JM5：缓存优化与功能完善](#7-jm5缓存优化与功能完善)
- [8 JM6：性能优化与交付就绪](#8-jm6性能优化与交付就绪)
- [9 里程碑依赖关系](#9-里程碑依赖关系)
- [10 关键路径与风险](#10-关键路径与风险)
- [11 Java后端验收标准汇总](#11-java后端验收标准汇总)
- [12 里程碑检查清单](#12-里程碑检查清单)

---

## 1 文档概述

### 1.1 编写目的

本文档从Java后端模块视角，将项目整体里程碑细化为Java后端专属的6个子里程碑（JM1-JM6），明确每个里程碑的交付物、任务分解、验收标准和风险应对，为Java后端开发提供精确的进度跟踪和交付指引。

### 1.2 Java后端6大模块

| 模块编号 | 模块名称 | 核心职责 | 优先级 |
|---------|---------|---------|--------|
| F2.1 | 用户管理模块 | 用户注册/登录、画像CRUD、JWT鉴权 | P0 |
| F2.2 | 论文管理模块 | 论文元数据查询、搜索、收藏 | P0 |
| F2.3 | 会话管理模块 | 分析会话生命周期管理 | P0 |
| F2.4 | 分析服务模块 | 论文分析/对比/综述的任务编排 | P0 |
| F2.5 | AI服务调用模块 | Java-Python通信、请求转换、降级机制 | P0 |
| F2.6 | 缓存管理模块 | Redis缓存策略、一致性保障 | P1 |

### 1.3 与项目整体里程碑的映射

```mermaid
graph LR
    subgraph 项目里程碑
        M1["M1 基础设施就绪<br/>Week 1-2"]
        M2["M2 单Agent可用<br/>Week 3-4"]
        M3["M3 前后端联调<br/>Week 5-6"]
        M4["M4 多Agent协同<br/>Week 7-8"]
        M5["M5 功能完整<br/>Week 9-10"]
        M6["M6 交付就绪<br/>Week 11-14"]
    end

    subgraph Java后端里程碑
        JM1["JM1 骨架+数据层<br/>Week 1-2"]
        JM2["JM2 基础API<br/>Week 5"]
        JM3["JM3 AI调用打通<br/>Week 5-6"]
        JM4["JM4 分析+SSE<br/>Week 7-8"]
        JM5["JM5 缓存+完善<br/>Week 9-10"]
        JM6["JM6 优化+交付<br/>Week 11-14"]
    end

    M1 -.-> JM1
    M3 -.-> JM2
    M3 -.-> JM3
    M4 -.-> JM4
    M5 -.-> JM5
    M6 -.-> JM6

    style JM1 fill:#e3f2fd,stroke:#1565c0
    style JM2 fill:#e8f5e9,stroke:#2e7d32
    style JM3 fill:#fff3e0,stroke:#ef6c00
    style JM4 fill:#fce4ec,stroke:#c62828
    style JM5 fill:#f3e5f5,stroke:#6a1b9a
    style JM6 fill:#e0f7fa,stroke:#00695c
```

> **说明**：Java后端在M2（Week 3-4）阶段无专属任务，该阶段主要开发Python AI服务。Java后端开发集中在M1、M3-M6。

---

## 2 Java后端里程碑总览

| 里程碑 | 时间窗口 | 对应项目里程碑 | 核心交付 | 状态 |
|--------|---------|-------------|---------|------|
| **JM1：项目骨架与数据层就绪** | Week 1-2（5/23 - 6/5） | M1 | Spring Boot骨架+MySQL/Redis连接+JPA实体 | ⬜ |
| **JM2：基础API可用** | Week 5（6/20 - 6/26） | M3 | 用户管理+论文管理+会话管理API | ⬜ |
| **JM3：AI服务调用打通** | Week 5-6（6/20 - 7/3） | M3 | PythonAIClient+请求转换+响应解析 | ⬜ |
| **JM4：分析服务与SSE推送完成** | Week 7-8（7/4 - 7/17） | M4 | 分析服务编排+对比/综述API+SSE推送 | ⬜ |
| **JM5：缓存优化与功能完善** | Week 9-10（7/18 - 7/31） | M5 | 缓存策略+筛选排序+报告导出 | ⬜ |
| **JM6：性能优化与交付就绪** | Week 11-14（8/1 - 9/30） | M6 | 异步调用+性能调优+测试+部署文档 | ⬜ |

```
进度条：

JM1 ████░░░░░░░░░░░░░░░░░░░░░░░░░░  Week 1-2
JM2 ████████████████░░░░░░░░░░░░░░░  Week 1-5
JM3 ████████████████████░░░░░░░░░░░  Week 1-6
JM4 ████████████████████████░░░░░░░  Week 1-8
JM5 ████████████████████████████░░░  Week 1-10
JM6 ████████████████████████████████  Week 1-14
```

---

## 3 JM1：项目骨架与数据层就绪

### 3.1 基本信息

| 项目 | 内容 |
|------|------|
| **目标** | Spring Boot项目可启动，MySQL/Redis连接正常，JPA实体和Repository就绪 |
| **时间** | Week 1-2（5月23日 - 6月5日） |
| **前置条件** | JDK 17 + Maven + Docker Desktop已安装 |
| **涉及模块** | 全局基础设施（为F2.1-F2.6提供基础） |

### 3.2 交付物清单

| 序号 | 交付物 | 验收标准 | 状态 |
|------|--------|---------|------|
| 1 | Spring Boot项目骨架 | `mvn spring-boot:run` 启动成功，`/health` 返回200 | ⬜ |
| 2 | Maven依赖配置 | pom.xml包含所有必需依赖（WebFlux/JPA/Redis/JWT/Lombok/MapStruct） | ⬜ |
| 3 | application.yml配置 | MySQL/Redis/AI服务/JWT配置项完整，支持环境变量注入 | ⬜ |
| 4 | 6个JPA Entity类 | User/UserProfile/Paper/Session/AnalysisResult/PaperFavorite | ⬜ |
| 5 | 6个Repository接口 | JpaRepository + 自定义查询方法定义 | ⬜ |
| 6 | RedisConfig配置类 | CacheManager + RedisTemplate + TTL分层配置 | ⬜ |
| 7 | WebClientConfig配置类 | 连接池 + 超时30s + 重试1次 | ⬜ |
| 8 | SecurityConfig配置类 | JWT过滤器链 + 白名单路径 | ⬜ |
| 9 | 统一响应与异常体系 | ApiResponse + BusinessException + GlobalExceptionHandler | ⬜ |
| 10 | 枚举类定义 | EducationLevel/KnowledgeLevel/PreferredStyle/SessionStatus/AnalysisType/AnalysisStatus | ⬜ |
| 11 | Docker Compose Java后端配置 | Dockerfile + docker-compose.yml backend服务定义 | ⬜ |

### 3.3 详细任务分解

#### Week 1 Day 5-7：项目初始化✅

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 5 | Spring Boot项目创建 + Maven依赖 | pom.xml + 启动类 |
| Day 6 | application.yml + application-dev.yml + application-prod.yml | 配置文件 |
| Day 7 | Dockerfile + docker-compose.yml backend服务 | 部署配置 |

#### Week 2 Day 1-3：数据层搭建

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 1 | 6个Entity类 + 枚举类 | entity/*.java + enums/*.java |
| Day 2 | 6个Repository接口 + 自定义查询 | repository/*.java |
| Day 3 | RedisConfig + WebClientConfig + SecurityConfig | config/*.java |

#### Week 2 Day 4-7：基础框架搭建

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 4 | ApiResponse + PageResponse + 统一响应 | dto/common/*.java |
| Day 5 | BusinessException体系 + GlobalExceptionHandler | exception/*.java |
| Day 6 | JwtUtil + RedisKeyUtil + DateTimeUtil | util/*.java |
| Day 7 | HealthController + 集成测试验证 | controller/HealthController.java |

### 3.4 验收检查点

```
□ Spring Boot启动: mvn spring-boot:run 无报错
□ 健康检查: curl http://localhost:8080/health 返回200
□ MySQL连接: HikariCP连接池初始化成功
□ Redis连接: RedisTemplate SET/GET 测试通过
□ JPA实体: 启动时自动创建6张表（ddl-auto=update）
□ Redis缓存: CacheManager配置6个缓存空间，TTL正确
□ 异常处理: 访问不存在的路径返回统一错误格式
□ Docker: docker build 构建镜像成功
□ 环境变量: ${MYSQL_PASSWORD}、${JWT_SECRET}等正确注入
□ 日志: 控制台输出包含requestId的日志
```

### 3.5 风险与应对

| 风险 | 应对 |
|------|------|
| Spring Boot 3.2与JDK 17兼容性问题 | 使用Spring Initializr生成标准项目 |
| MySQL 9与Hibernate方言不兼容 | 使用MySQL8Dialect或自定义方言 |
| Redis连接超时 | 检查Docker网络配置，确认端口映射 |

---

## 4 JM2：基础API可用

### 4.1 基本信息

| 项目 | 内容 |
|------|------|
| **目标** | 用户管理、论文管理、会话管理三大基础模块API可用 |
| **时间** | Week 5 Day 1-4（6月20日 - 6月23日） |
| **前置条件** | JM1完成 |
| **涉及模块** | F2.1 用户管理、F2.2 论文管理、F2.3 会话管理 |

### 4.2 交付物清单

| 序号 | 交付物 | 验收标准 | 状态 |
|------|--------|---------|------|
| 1 | UserController + UserService | 注册/登录/查询/画像CRUD API可用 | ⬜ |
| 2 | JwtAuthFilter | Token验证+黑名单检查+身份注入 | ⬜ |
| 3 | RegisterRequest/LoginRequest/ProfileUpdateRequest | @Valid参数校验生效 | ⬜ |
| 4 | UserResponse/LoginResponse/ProfileResponse | DTO正确映射Entity | ⬜ |
| 5 | UserMapper | MapStruct Entity↔DTO转换正确 | ⬜ |
| 6 | PaperController + PaperService | 分页查询/详情/搜索API可用 | ⬜ |
| 7 | PaperRepository自定义查询 | 全文索引检索+条件过滤+排序 | ⬜ |
| 8 | PaperSearchRequest/PaperResponse/PaperDetailResponse | 请求响应DTO完整 | ⬜ |
| 9 | PaperMapper | MapStruct映射正确 | ⬜ |
| 10 | SessionController + SessionService | 创建/列表/详情/删除API可用 | ⬜ |
| 11 | Session状态机 | active→completed/expired 转换正确 | ⬜ |
| 12 | SessionCreateRequest/SessionResponse | DTO完整 | ⬜ |

### 4.3 详细任务分解

#### Week 5 Day 1-2：用户管理模块（F2.1）

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 1 上午 | UserController + RegisterRequest/LoginRequest | controller + dto |
| Day 1 下午 | UserService（注册/登录/BCrypt/JWT） | service |
| Day 2 上午 | JwtAuthFilter + JwtUtil完善 | filter + util |
| Day 2 下午 | 画像CRUD + ProfileUpdateRequest/ProfileResponse | controller + dto |

#### Week 5 Day 3：论文管理模块（F2.2）

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 3 上午 | PaperController + PaperService（列表/详情） | controller + service |
| Day 3 下午 | 论文搜索（全文索引+条件过滤+排序） | repository自定义查询 |

#### Week 5 Day 4：会话管理模块（F2.3）

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 4 上午 | SessionController + SessionService | controller + service |
| Day 4 下午 | 会话状态机 + DTO映射 | service + mapper |

### 4.4 验收检查点

```
□ 用户注册: POST /api/users/register 返回201
□ 用户登录: POST /api/users/login 返回JWT Token
□ JWT鉴权: 未登录请求返回401
□ Token黑名单: 退出登录后Token不可用
□ 画像创建: POST /api/users/{userId}/profile 保存成功
□ 画像查询: GET /api/users/{userId}/profile 返回画像
□ 画像更新: PUT /api/users/{userId}/profile 更新成功
□ 论文列表: GET /api/papers?page=1&size=10 分页正确
□ 论文详情: GET /api/papers/{paperId} 返回完整信息
□ 论文搜索: GET /api/papers/search?q=Multi-Agent 返回结果
□ 会话创建: POST /api/sessions 返回sessionId
□ 会话列表: GET /api/sessions 返回用户会话
□ 会话删除: DELETE /api/sessions/{sessionId} 删除成功
□ 参数校验: 空用户名注册返回400错误
□ 数据隔离: 用户A无法访问用户B的会话
```

### 4.5 关键演示场景

```
1. curl -X POST /api/users/register -d '{"username":"test","email":"test@test.com","password":"12345678"}'
   → 返回201 + userId

2. curl -X POST /api/users/login -d '{"username":"test","password":"12345678"}'
   → 返回200 + JWT Token

3. curl -H "Authorization: Bearer <token>" GET /api/papers/search?q=Agent
   → 返回论文列表

4. curl -H "Authorization: Bearer <token>" POST /api/sessions -d '{"topic":"Multi-Agent"}'
   → 返回sessionId
```

---

## 5 JM3：AI服务调用打通

### 5.1 基本信息

| 项目 | 内容 |
|------|------|
| **目标** | Java后端成功调用Python AI服务，完成请求转换和响应解析 |
| **时间** | Week 5 Day 5 - Week 6 Day 2（6月24日 - 7月1日） |
| **前置条件** | JM2完成 + Python AI服务可用（M2完成） |
| **涉及模块** | F2.5 AI服务调用、F2.4 分析服务（基础） |

### 5.2 交付物清单

| 序号 | 交付物 | 验收标准 | 状态 |
|------|--------|---------|------|
| 1 | PythonAIClient | WebClient封装，连接池+超时30s+重试1次 | ⬜ |
| 2 | AgentRequest DTO | Java→Python请求格式转换正确 | ⬜ |
| 3 | AnalysisResultDTO | Python→Java响应解析正确 | ⬜ |
| 4 | AgentClientService | 调用编排+降级处理 | ⬜ |
| 5 | AnalysisController（基础） | 论文分析请求+结果查询API | ⬜ |
| 6 | AnalysisService（基础） | 分析任务创建+状态管理 | ⬜ |
| 7 | AgentStateResponse DTO | Agent状态数据结构定义 | ⬜ |
| 8 | 健康检查集成 | /health 包含AI服务状态检查 | ⬜ |

### 5.3 详细任务分解

#### Week 5 Day 5-7：AI服务调用模块（F2.5）

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 5 | PythonAIClient（同步调用+超时+重试） | client/PythonAIClient.java |
| Day 6 | AgentRequest + AnalysisResultDTO + AgentStateResponse | dto |
| Day 7 | AgentClientService（调用编排+降级处理） | service/AgentClientService.java |

#### Week 6 Day 1-2：分析服务模块基础（F2.4）

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 1 | AnalysisController + AnalysisService（论文分析） | controller + service |
| Day 2 | 分析结果查询 + 状态查询 | AnalysisService扩展 |

### 5.4 验收检查点

```
□ PythonAIClient: 调用 POST /api/agent/analyze 成功
□ 请求转换: Java DTO正确转为Python JSON格式（snake_case）
□ 响应解析: Python返回的JSON正确解析为Java DTO
□ 超时处理: Python服务超时30s后触发重试
□ 降级处理: Python不可用时返回降级提示
□ 论文分析: POST /api/analysis/paper 返回analysisId
□ 分析结果: GET /api/analysis/{analysisId} 返回结果
□ 分析状态: GET /api/analysis/{analysisId}/status 返回进度
□ 健康检查: /health 包含aiService状态（UP/DOWN）
□ 错误处理: Python返回错误时Java不崩溃，返回502
```

### 5.5 关键演示场景

```
1. Java调用Python论文分析：
   POST /api/analysis/paper {"paperId":"arxiv_2024_001","userId":"usr_001"}
   → Java构建AgentRequest → 调用Python → 返回analysisId

2. 查询分析结果：
   GET /api/analysis/{analysisId}
   → 返回5维度分析结果JSON

3. AI服务降级测试：
   停止Python服务 → 调用分析API → 返回降级提示
```

### 5.6 风险与应对

| 风险 | 应对 |
|------|------|
| Java-Python通信序列化问题 | 统一JSON格式（snake_case），使用@JsonProperty注解 |
| Python服务响应格式变更 | 定义严格的DTO契约，增加字段兼容性处理 |
| WebClient连接池耗尽 | 配置合理连接池参数（maxConnections=50） |

---

## 6 JM4：分析服务与SSE推送完成

### 6.1 基本信息

| 项目 | 内容 |
|------|------|
| **目标** | 完整的分析服务编排（论文分析/对比/综述）+ SSE实时推送Agent状态 |
| **时间** | Week 7-8（7月4日 - 7月17日） |
| **前置条件** | JM3完成 + Python 6-Agent工作流可用（M4进行中） |
| **涉及模块** | F2.4 分析服务（完整）、F2.5 AI服务调用（SSE扩展） |

### 6.2 交付物清单

| 序号 | 交付物 | 验收标准 | 状态 |
|------|--------|---------|------|
| 1 | 对比分析API | POST /api/analysis/compare 支持2-5篇论文对比 | ⬜ |
| 2 | 综述生成API | POST /api/analysis/report 生成个性化综述 | ⬜ |
| 3 | SSE推送端点 | GET /api/analysis/{analysisId}/agent-stream 实时推送 | ⬜ |
| 4 | PythonAIClient SSE接收 | Flux<ServerSentEvent> 接收Python SSE流 | ⬜ |
| 5 | Agent状态Redis缓存 | agent:state:{analysisId} 实时更新 | ⬜ |
| 6 | AnalysisService完整编排 | 获取画像→获取论文→创建会话→调用AI→保存结果 | ⬜ |
| 7 | CompareRequest/ReportRequest | 请求DTO含论文ID列表+用户画像 | ⬜ |
| 8 | 降级机制完善 | AI服务不可用时返回缓存结果或降级提示 | ⬜ |

### 6.3 详细任务分解

#### Week 7 Day 1-4：分析服务扩展

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 1-2 | AnalysisService完整编排（画像→论文→会话→AI→结果） | AnalysisService重构 |
| Day 3 | 对比分析API + CompareRequest | AnalysisController扩展 |
| Day 4 | 综述生成API + ReportRequest | AnalysisController扩展 |

#### Week 7 Day 5 - Week 8 Day 3：SSE推送

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 5-6 | PythonAIClient SSE接收（Flux<ServerSentEvent>） | PythonAIClient扩展 |
| Day 7-8 | Agent状态Redis缓存 + AgentController SSE转发 | AgentController + Redis操作 |
| Day 9-10 | SSE端点 + 前端联调 | AgentController完善 |

#### Week 8 Day 4-7：降级与完善

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 4-5 | 降级机制完善（缓存回退+降级标记） | AgentClientService扩展 |
| Day 6-7 | 集成测试 + Bug修复 | 测试代码 |

### 6.4 验收检查点

```
□ 对比分析: POST /api/analysis/compare 返回对比结果
□ 综述生成: POST /api/analysis/report 返回analysisId
□ SSE推送: Agent执行过程中前端实时收到状态更新
□ SSE事件格式: event:agent_state_update + data:JSON
□ Agent状态缓存: Redis中agent:state:{id} 正确更新
□ 分析编排: 画像→论文→会话→AI调用→结果保存 完整流程
□ 降级: Python不可用时返回缓存或降级提示，不崩溃
□ 个性化: 请求中包含用户画像信息，Python正确接收
□ 引用标注: 综述结果中包含citations数组
□ 超时处理: SSE流120s超时后正常关闭
```

### 6.5 关键演示场景

```
1. 综述生成完整流程：
   POST /api/analysis/report {"topic":"Multi-Agent协同决策","paperIds":[...],"userId":"usr_001"}
   → Java获取画像 → 创建会话 → 调用Python → SSE推送状态 → 保存结果

2. SSE实时推送：
   GET /api/analysis/{analysisId}/agent-stream
   → 接收: event:agent_state_update data:{"agentName":"retriever","status":"running"}
   → 接收: event:agent_state_update data:{"agentName":"retriever","status":"completed"}
   → 接收: event:analysis_completed data:{"analysisId":"anl_001","status":"completed"}

3. 降级测试：
   停止Python → 调用综述生成 → 返回降级响应
```

### 6.6 风险与应对

| 风险 | 应对 |
|------|------|
| SSE流中断 | 前端useSSE自动重连（3s间隔，最多5次） |
| Agent状态Redis缓存与SSE不同步 | SSE事件同时写入Redis，查询API从Redis读取 |
| WebClient SSE接收内存泄漏 | Flux订阅使用Disposable管理，超时自动取消 |
| 多用户同时请求SSE | 连接池配置合理，限制单用户并发分析数 |

---

## 7 JM5：缓存优化与功能完善

### 7.1 基本信息

| 项目 | 内容 |
|------|------|
| **目标** | 缓存策略完善+筛选排序+报告导出+收藏功能 |
| **时间** | Week 9-10（7月18日 - 7月31日） |
| **前置条件** | JM4完成 |
| **涉及模块** | F2.6 缓存管理、F2.2 论文管理（扩展）、F2.4 分析服务（导出） |

### 7.2 交付物清单

| 序号 | 交付物 | 验收标准 | 状态 |
|------|--------|---------|------|
| 1 | 用户画像缓存 | @Cacheable + @CacheEvict，TTL 1h，命中率>50% | ⬜ |
| 2 | 论文检索缓存 | 搜索结果缓存，TTL 10min，相同查询命中缓存 | ⬜ |
| 3 | 分析结果缓存 | 分析结果缓存，TTL 30min | ⬜ |
| 4 | 会话状态缓存 | 会话状态缓存，TTL 2h | ⬜ |
| 5 | Agent状态缓存完善 | Hash结构，5min TTL，与SSE同步 | ⬜ |
| 6 | 论文筛选排序 | 年份/会议/引用数筛选 + 相关度/时间/引用排序 | ⬜ |
| 7 | 论文收藏API | POST/DELETE /api/papers/{paperId}/favorite | ⬜ |
| 8 | 收藏列表API | GET /api/papers/favorites 分页查询 | ⬜ |
| 9 | PDF导出服务 | PdfExporter生成格式正确的PDF | ⬜ |
| 10 | Word导出服务 | WordExporter生成格式正确的Word文档 | ⬜ |
| 11 | 缓存一致性保障 | Cache-Aside写后删+双重失效（画像更新） | ⬜ |

### 7.3 详细任务分解

#### Week 9 Day 1-3：缓存优化（F2.6）

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 1 | 用户画像缓存 + 用户信息缓存 | UserService添加@Cacheable/@CacheEvict |
| Day 2 | 论文检索缓存 + 论文详情缓存 | PaperService添加缓存注解 |
| Day 3 | 分析结果缓存 + 会话状态缓存 + Agent状态缓存 | AnalysisService/SessionService缓存 |

#### Week 9 Day 4-5：论文管理扩展

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 4 | 筛选排序（年份/会议/引用数/相关度） | PaperRepository扩展 + PaperService |
| Day 5 | 论文收藏/取消收藏 + 收藏列表 | PaperController + PaperService扩展 |

#### Week 9 Day 6 - Week 10 Day 2：报告导出

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 6-7 | PDF导出（iText/Apache PDFBox） | PdfExporter.java |
| Day 8-9 | Word导出（Apache POI） | WordExporter.java |

#### Week 10 Day 3-7：缓存测试与完善

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 3-4 | 缓存命中率测试 + 一致性验证 | 测试代码 |
| Day 5-7 | Bug修复 + 代码优化 | 修复记录 |

### 7.4 验收检查点

```
□ 画像缓存: 更新画像后缓存立即失效
□ 检索缓存: 相同查询第二次直接返回缓存
□ 分析缓存: 已完成分析结果可缓存命中
□ 缓存命中率: >50%
□ 筛选: 年份范围/会议/引用数筛选正确
□ 排序: 相关度/时间/引用排序正确
□ 收藏: 收藏/取消收藏操作正确
□ 收藏列表: 分页查询用户收藏论文
□ PDF导出: 格式正确，引用保留
□ Word导出: 格式正确，可编辑
□ Cache-Aside: 写操作后缓存失效，读操作回填
□ 双重失效: 画像更新时userProfile+userProfileJson同时失效
```

---

## 8 JM6：性能优化与交付就绪

### 8.1 基本信息

| 项目 | 内容 |
|------|------|
| **目标** | 异步调用优化+性能达标+测试通过+部署文档完整 |
| **时间** | Week 11-14（8月1日 - 9月30日） |
| **前置条件** | JM5完成 |
| **涉及模块** | F2.5 AI服务调用（异步优化）、全局性能优化 |

### 8.2 交付物清单

| 序号 | 交付物 | 验收标准 | 状态 |
|------|--------|---------|------|
| 1 | AsyncAgentClient | WebFlux异步调用AI服务，非阻塞 | ⬜ |
| 2 | 流式输出支持 | LLM首字节响应<2秒 | ⬜ |
| 3 | 连接池优化 | HikariCP(max=20) + Redis Lettuce连接池调优 | ⬜ |
| 4 | N+1查询修复 | JPA JOIN FETCH避免N+1问题 | ⬜ |
| 5 | 论文批量导入API | POST /api/papers/import 批量导入+去重 | ⬜ |
| 6 | 用户信息更新API | PUT /api/users/{userId} 更新用户基本信息 | ⬜ |
| 7 | 会话详情API | GET /api/sessions/{sessionId} 含关联分析结果 | ⬜ |
| 8 | 会话状态更新API | PUT /api/sessions/{sessionId}/status | ⬜ |
| 9 | P0功能测试 | 所有P0 API接口测试通过 | ⬜ |
| 10 | 性能测试报告 | API响应时间+并发测试数据 | ⬜ |
| 11 | 部署文档 | Docker部署步骤+环境变量说明 | ⬜ |

### 8.3 详细任务分解

#### Week 11：性能优化

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 1-3 | AsyncAgentClient + 流式输出 | AsyncAgentClient.java |
| Day 4-5 | 连接池优化 + N+1查询修复 | 配置调优 + Repository优化 |
| Day 6-7 | 论文批量导入 + P1 API补充 | PaperController扩展 |

#### Week 12：测试修复

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 1-3 | P0功能测试（所有API接口） | 测试报告 |
| Day 4-5 | 性能测试（响应时间+并发50用户） | 性能报告 |
| Day 6-7 | Bug修复 | 修复记录 |

#### Week 13-14：文档与交付

| 天数 | 任务 | 产出 |
|------|------|------|
| Week 13 Day 1-3 | 部署文档 + 环境变量说明 | 部署文档 |
| Week 13 Day 4-7 | 协助技术报告（后端架构部分） | 技术报告章节 |
| Week 14 | 最终测试 + 演示准备 | 测试确认 |

### 8.4 验收检查点

```
□ 异步调用: WebFlux非阻塞调用AI服务
□ 流式首字节: <2秒
□ API平均响应: 非AI调用≤500ms
□ 论文检索: ≤3秒
□ JWT鉴权: ≤10ms
□ 并发: ≥50用户
□ 缓存命中率: >50%
□ 数据库连接池: 利用率<80%
□ P0功能: 100%通过
□ P1功能: >80%通过
□ Docker: docker-compose up 一键部署
□ 部署文档: 完整可操作
```

---

## 9 里程碑依赖关系

### 9.1 依赖图

```mermaid
graph TD
    JM1["JM1 骨架+数据层<br/>Week 1-2"]
    JM2["JM2 基础API<br/>Week 5"]
    JM3["JM3 AI调用打通<br/>Week 5-6"]
    JM4["JM4 分析+SSE<br/>Week 7-8"]
    JM5["JM5 缓存+完善<br/>Week 9-10"]
    JM6["JM6 优化+交付<br/>Week 11-14"]

    JM1 --> JM2
    JM2 --> JM3
    JM3 --> JM4
    JM4 --> JM5
    JM5 --> JM6

    style JM1 fill:#e3f2fd,stroke:#1565c0
    style JM2 fill:#e8f5e9,stroke:#2e7d32
    style JM3 fill:#fff3e0,stroke:#ef6c00
    style JM4 fill:#fce4ec,stroke:#c62828
    style JM5 fill:#f3e5f5,stroke:#6a1b9a
    style JM6 fill:#e0f7fa,stroke:#00695c
```

### 9.2 外部依赖

```mermaid
graph LR
    subgraph Java后端
        JM1 --> JM2 --> JM3 --> JM4 --> JM5 --> JM6
    end

    subgraph 外部依赖
        M1["M1 MySQL/Redis就绪"]
        M2["M2 Python AI服务可用"]
        M4["M4 Python 6-Agent工作流"]
    end

    M1 -.->|JM1需要| JM1
    M2 -.->|JM3需要| JM3
    M4 -.->|JM4需要| JM4
```

### 9.3 关键路径

```
关键路径：JM1 → JM2 → JM3 → JM4 → JM5 → JM6

最关键里程碑：JM4（分析服务与SSE推送完成）
原因：
1. SSE推送是跨三层（Python→Java→前端）的核心链路
2. 分析服务编排涉及最多模块协作（F2.1+F2.2+F2.3+F2.4+F2.5）
3. 依赖Python 6-Agent工作流完成，存在外部依赖风险

缓冲策略：
├── JM1-JM3: 严格按计划执行
├── JM4: 允许延迟3天（与Python开发并行）
├── JM5: 允许延迟1周（P1功能可降级为P2）
└── JM6: 预留4周时间，充裕
```

---

## 10 关键路径与风险

### 10.1 Java后端专属风险

| 里程碑 | 关键风险 | 概率 | 影响 | 应对措施 |
|--------|---------|------|------|---------|
| JM1 | Spring Boot 3.2 + MySQL 9兼容性 | 中 | JM2延迟 | 提前测试，使用Docker MySQL 8 |
| JM1 | JPA Entity与数据库表不匹配 | 低 | 启动失败 | 使用ddl-auto=update自动同步 |
| JM2 | JWT鉴权过滤器配置错误 | 中 | 接口无法访问 | 参考Spring Security官方文档 |
| JM2 | MapStruct映射编译错误 | 低 | DTO转换失败 | 提前测试简单映射场景 |
| JM3 | Java-Python通信序列化不一致 | 高 | 请求/响应解析失败 | 严格定义API契约，使用@JsonProperty |
| JM3 | WebClient超时配置不合理 | 中 | 请求超时或阻塞 | 超时30s+重试1次+降级 |
| JM4 | SSE流内存泄漏 | 中 | 服务器内存耗尽 | Disposable管理+超时自动取消 |
| JM4 | Agent状态Redis与SSE不同步 | 中 | 前端显示不一致 | SSE事件同时写Redis |
| JM5 | 缓存一致性漏洞 | 中 | 数据不一致 | Cache-Aside严格+双重失效 |
| JM5 | PDF/Word导出格式问题 | 低 | 导出文件不可用 | 使用成熟库（iText/POI） |
| JM6 | 并发性能不达标 | 中 | 验收不通过 | 连接池调优+异步调用+缓存 |

### 10.2 风险缓解时间表

| 时间 | 必须完成的风险应对 |
|------|------------------|
| **JM1前** | 确认JDK 17 + Maven + Docker环境可用 |
| **JM2前** | 完成JWT鉴权POC验证 |
| **JM3前** | 与Python端确认API契约（请求/响应格式） |
| **JM4前** | 完成WebClient SSE接收POC |
| **JM5前** | 缓存命中率基线测试 |
| **JM6前** | 性能基线测试，确认优化方向 |

---

## 11 Java后端验收标准汇总

### 11.1 API接口验收

| 模块 | API | 方法 | 优先级 | 验收标准 |
|------|-----|------|--------|---------|
| F2.1 | /api/users/register | POST | P0 | 返回201 + userId |
| F2.1 | /api/users/login | POST | P0 | 返回200 + JWT Token |
| F2.1 | /api/users/{userId} | GET | P0 | 返回用户信息 |
| F2.1 | /api/users/{userId}/profile | GET/POST/PUT | P0 | 画像CRUD正确 |
| F2.1 | /api/users/logout | POST | P1 | Token加入黑名单 |
| F2.2 | /api/papers | GET | P0 | 分页查询正确 |
| F2.2 | /api/papers/{paperId} | GET | P0 | 返回论文详情 |
| F2.2 | /api/papers/search | GET | P0 | 搜索+筛选+排序正确 |
| F2.2 | /api/papers/{paperId}/favorite | POST/DELETE | P2 | 收藏操作正确 |
| F2.2 | /api/papers/favorites | GET | P2 | 收藏列表分页 |
| F2.2 | /api/papers/import | POST | P2 | 批量导入+去重 |
| F2.3 | /api/sessions | POST | P0 | 创建会话 |
| F2.3 | /api/sessions | GET | P0 | 用户会话列表 |
| F2.3 | /api/sessions/{sessionId} | GET | P1 | 会话详情+关联结果 |
| F2.3 | /api/sessions/{sessionId}/status | PUT | P1 | 状态更新 |
| F2.3 | /api/sessions/{sessionId} | DELETE | P1 | 删除会话 |
| F2.4 | /api/analysis/paper | POST | P0 | 返回analysisId |
| F2.4 | /api/analysis/compare | POST | P1 | 返回对比结果 |
| F2.4 | /api/analysis/report | POST | P0 | 返回analysisId |
| F2.4 | /api/analysis/{analysisId} | GET | P0 | 返回分析结果 |
| F2.4 | /api/analysis/{analysisId}/status | GET | P0 | 返回分析状态 |
| F2.4 | /api/analysis/{analysisId}/agent-stream | GET(SSE) | P1 | SSE实时推送 |

### 11.2 性能验收

| 验收项 | 目标值 | 验收方法 |
|--------|--------|---------|
| API平均响应（非AI调用） | ≤500ms | 自动计时 |
| 论文检索响应 | ≤3秒 | 自动计时 |
| JWT鉴权耗时 | ≤10ms | 自动计时 |
| 缓存命中率 | >50% | 监控统计 |
| 数据库连接池利用率 | <80% | HikariCP监控 |
| 并发用户支持 | ≥50 | 压力测试 |

### 11.3 里程碑级验收

| 里程碑 | 核心验收标准 | 不通过条件 |
|--------|-------------|-----------|
| JM1 | Spring Boot可启动，6张表自动创建，Redis连接正常 | 项目无法启动 |
| JM2 | 用户/论文/会话三大模块API可用 | 核心API返回500 |
| JM3 | Java成功调用Python AI服务并解析响应 | 通信链路不通 |
| JM4 | 分析服务完整编排+SSE推送正常 | SSE无法推送或分析流程断裂 |
| JM5 | 缓存命中率>50%+导出功能可用 | 缓存未生效 |
| JM6 | 性能达标+P0功能100%通过 | 性能或功能不达标 |

---

## 12 里程碑检查清单

### JM1检查清单

```
□ Spring Boot项目可启动（mvn spring-boot:run）
□ /health接口返回200
□ MySQL连接正常（HikariCP初始化成功）
□ Redis连接正常（SET/GET测试通过）
□ 6个Entity类编译通过
□ 6个Repository接口编译通过
□ RedisConfig配置6个缓存空间
□ WebClientConfig配置超时30s+重试1次
□ SecurityConfig JWT过滤器链配置
□ ApiResponse统一响应格式
□ BusinessException异常体系
□ GlobalExceptionHandler全局异常处理
□ 6个枚举类定义完整
□ JwtUtil/RedisKeyUtil/DateTimeUtil工具类
□ Dockerfile构建成功
□ application.yml + application-dev.yml + application-prod.yml
```

### JM2检查清单

```
□ 用户注册API可用
□ 用户登录API可用（返回JWT Token）
□ JWT鉴权正常（未登录返回401）
□ Token黑名单正常（退出后Token不可用）
□ 画像创建/查询/更新API可用
□ 论文分页查询API可用
□ 论文详情查询API可用
□ 论文搜索API可用（全文索引+条件过滤）
□ 会话创建/列表/详情/删除API可用
□ 会话状态机转换正确
□ 参数校验生效（@Valid）
□ 数据隔离正确（用户只能访问自己的数据）
□ MapStruct映射正确
□ 统一响应格式正确
```

### JM3检查清单

```
□ PythonAIClient同步调用成功
□ 请求转换正确（Java camelCase → Python snake_case）
□ 响应解析正确（Python JSON → Java DTO）
□ 超时处理正常（30s超时+重试1次）
□ 降级处理正常（Python不可用时返回降级提示）
□ 论文分析API可用
□ 分析结果查询API可用
□ 分析状态查询API可用
□ AgentRequest DTO格式正确
□ AnalysisResultDTO解析正确
□ AgentStateResponse定义完整
□ /health包含AI服务状态
```

### JM4检查清单

```
□ 对比分析API可用（2-5篇论文）
□ 综述生成API可用
□ SSE推送端点可用
□ PythonAIClient SSE接收正常
□ Agent状态Redis缓存正确
□ 分析服务完整编排（画像→论文→会话→AI→结果）
□ 降级机制完善（缓存回退+降级标记）
□ 个性化信息正确传递给Python
□ 综述结果包含citations数组
□ SSE流120s超时正常关闭
□ 前端SSE接收正常
```

### JM5检查清单

```
□ 用户画像缓存命中
□ 论文检索缓存命中
□ 分析结果缓存命中
□ 会话状态缓存命中
□ 缓存命中率>50%
□ 画像更新后缓存立即失效
□ 双重失效（userProfile+userProfileJson）
□ 论文筛选（年份/会议/引用数）正确
□ 论文排序（相关度/时间/引用）正确
□ 论文收藏/取消收藏正确
□ 收藏列表分页查询正确
□ PDF导出格式正确
□ Word导出格式正确
□ Cache-Aside写后删策略正确
```

### JM6检查清单

```
□ AsyncAgentClient异步调用正常
□ 流式首字节<2秒
□ API平均响应≤500ms
□ 论文检索≤3秒
□ JWT鉴权≤10ms
□ 并发≥50用户
□ 缓存命中率>50%
□ HikariCP连接池利用率<80%
□ N+1查询已修复
□ 论文批量导入可用
□ 用户信息更新API可用
□ 会话详情API含关联分析结果
□ 会话状态更新API可用
□ P0功能100%通过
□ P1功能>80%通过
□ Docker一键部署成功
□ 部署文档完整
```

---

## 附录A：Java后端API开发顺序

```mermaid
graph TD
    subgraph JM1-基础框架
        HEALTH["GET /health"]
        CONFIG["配置类"]
        ENTITY["Entity + Repository"]
        EXCEPTION["异常体系"]
    end

    subgraph JM2-基础API
        REGISTER["POST /api/users/register"]
        LOGIN["POST /api/users/login"]
        USER_INFO["GET /api/users/{userId}"]
        PROFILE["GET/POST/PUT /api/users/{userId}/profile"]
        LOGOUT["POST /api/users/logout"]
        PAPERS["GET /api/papers"]
        PAPER_DETAIL["GET /api/papers/{paperId}"]
        PAPER_SEARCH["GET /api/papers/search"]
        SESSION_CREATE["POST /api/sessions"]
        SESSION_LIST["GET /api/sessions"]
    end

    subgraph JM3-AI调用
        AI_CLIENT["PythonAIClient"]
        AGENT_REQ["AgentRequest DTO"]
        ANALYSIS_PAPER["POST /api/analysis/paper"]
        ANALYSIS_RESULT["GET /api/analysis/{id}"]
        ANALYSIS_STATUS["GET /api/analysis/{id}/status"]
    end

    subgraph JM4-分析+SSE
        ANALYSIS_COMPARE["POST /api/analysis/compare"]
        ANALYSIS_REPORT["POST /api/analysis/report"]
        SSE_STREAM["GET /api/analysis/{id}/agent-stream"]
    end

    subgraph JM5-缓存+完善
        CACHE["缓存注解"]
        FAVORITE["POST/DELETE /api/papers/{id}/favorite"]
        FAVORITES["GET /api/papers/favorites"]
        EXPORT["PDF/Word导出"]
    end

    subgraph JM6-优化
        ASYNC["AsyncAgentClient"]
        IMPORT["POST /api/papers/import"]
        SESSION_DETAIL["GET /api/sessions/{id}"]
        SESSION_STATUS["PUT /api/sessions/{id}/status"]
    end

    HEALTH --> REGISTER
    CONFIG --> PAPERS
    ENTITY --> SESSION_CREATE
    EXCEPTION --> AI_CLIENT

    REGISTER --> LOGIN
    LOGIN --> PROFILE
    PAPERS --> PAPER_SEARCH

    AI_CLIENT --> ANALYSIS_PAPER
    ANALYSIS_PAPER --> ANALYSIS_RESULT

    ANALYSIS_RESULT --> ANALYSIS_COMPARE
    ANALYSIS_COMPARE --> ANALYSIS_REPORT
    ANALYSIS_REPORT --> SSE_STREAM

    SSE_STREAM --> CACHE
    PAPER_SEARCH --> FAVORITE
    ANALYSIS_RESULT --> EXPORT

    CACHE --> ASYNC
    PAPERS --> IMPORT
    SESSION_LIST --> SESSION_DETAIL
```

---

## 附录B：Java后端核心类文件清单

| 里程碑 | 新增文件 | 累计文件数 |
|--------|---------|-----------|
| JM1 | LiteratureAssistantApplication + 4config + 6entity + 6repository + 6enum + 3util + 3exception + 3dto/common + HealthController | ~33 |
| JM2 | 3controller + 3service + 3mapper + ~12dto(request/response) | ~54 |
| JM3 | PythonAIClient + AgentClientService + ~5dto + AnalysisController + AnalysisService | ~62 |
| JM4 | AgentController + AnalysisService扩展 + PythonAIClient扩展 + ~3dto | ~68 |
| JM5 | PdfExporter + WordExporter + PaperService扩展 + PaperController扩展 | ~73 |
| JM6 | AsyncAgentClient + 测试类 | ~80+ |

---

> **文档维护**：每个里程碑完成时更新状态（⬜→✅），记录实际完成日期
> **进度跟踪**：每周更新里程碑进度，如有延迟立即评估影响
> **变更控制**：里程碑交付物调整需评估对前端和AI服务的影响
