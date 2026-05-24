# 架构决策记录 (Architecture Decision Records)

> **项目**: XH-202630 科研文献智能助手  
> **副标题**: 领域知识个性化生成与多智能体协同决策系统研究  
> **创建日期**: 2026-05-23  
> **维护者**: 项目开发团队  
> **文档版本**: 1.0

---

## 目录

- [ADR-001: 三层分离架构](#adr-001-三层分离架构vue3--spring-boot--fastapi)
- [ADR-002: 多智能体协同编排](#adr-002-多智能体协同编排langgraph-stategraph)
- [ADR-003: LLM 三级降级策略](#adr-003-llm-三级降级策略)
- [ADR-004: 三数据库存储架构](#adr-004-三数据库存储架构mysql--redis--chromadb)
- [ADR-005: 混合 RAG 检索与 RRF 融合](#adr-005-混合-rag-检索与-rrf-融合)
- [ADR-006: 个性化引擎与用户画像驱动 Prompt](#adr-006-个性化引擎与用户画像驱动-prompt)
- [ADR-007: Cache-Aside 缓存模式与 TTL 分层](#adr-007-cache-aside-缓存模式与-ttl-分层)
- [ADR-008: JWT 认证与 Redis 黑名单](#adr-008-jwt-认证与-redis-黑名单)
- [ADR-009: SSE 实时 Agent 状态推送](#adr-009-sse-实时-agent-状态推送)
- [ADR-010: Docker Compose 部署架构](#adr-010-docker-compose-部署架构)
- [ADR-011: 知识图谱增强 RAG（Neo4j）](#adr-011-知识图谱增强-ragneo4j)

---

## ADR-001: 三层分离架构（Vue3 + Spring Boot + FastAPI）

### 状态

✅ 已采纳

### 上下文

科研文献智能助手需要同时满足：Web 前端交互、业务数据管理、AI 推理服务三类截然不同的需求。前端需要响应式 UI 与丰富可视化；后端需要事务安全、权限控制、数据持久化；AI 服务需要 Python 生态的 ML/NLP 库与灵活的 Prompt 工程。

### 决策

采用**三层分离架构**：

| 层级 | 技术栈 | 职责 |
|------|--------|------|
| 前端层 | Vue3 + TypeScript + Vite + Element Plus | 用户交互、可视化、状态管理 |
| 业务层 | Java Spring Boot 3.2+ | 用户认证、论文管理、会话管理、缓存、AI 服务代理 |
| AI 服务层 | Python FastAPI + LangGraph | 多 Agent 编排、RAG 检索、LLM 调用、个性化生成 |

**关键接口边界**：
- 前端 → Java：RESTful API（JSON）+ SSE 事件流
- Java → Python：WebClient HTTP 调用（30s 超时，1 次重试）+ SSE 转发

### 理由

1. **关注点分离**：Java 处理事务与权限，Python 处理 AI 推理，Vue3 处理展示，各层独立演进
2. **生态优势**：Python 拥有 LangChain/LangGraph/Transformers 等成熟 AI 生态；Java 拥有 Spring 生态的企业级能力
3. **独立部署与扩展**：AI 服务可独立扩缩容，不影响业务层稳定性
4. **AI Coding 友好**：三层技术栈边界清晰，便于 AI 辅助编码时分上下文工作
5. **成本控制**：符合单人开发者 + AI Coding 的 14 周开发约束

### 后果

**正面**：
- 各层可独立开发、测试、部署
- AI 服务故障不影响用户认证和论文管理等基础功能
- Python 生态直接可用，无需 Java 调用 Python 的桥接方案

**负面**：
- 三套技术栈增加维护复杂度
- Java ↔ Python 间存在序列化/反序列化开销和网络延迟
- 跨系统字段命名需统一约定（Java camelCase ↔ Python/JSON snake_case）
- 需要维护两套 API 规范（Java REST + Python REST）

### 关联文档

- `信息架构文档(IA).md` — 信息流与接口边界
- `开发规范文档.md` — 三套技术栈编码规范
- `Java后端模块系统架构文档.md` — PythonAIClient 设计

---

## ADR-002: 多智能体协同编排（LangGraph StateGraph）

### 状态

✅ 已采纳

### 上下文

科研文献分析是一个多步骤、多角色的复杂任务，涉及文献检索、深度分析、对比研究、报告生成和质量审核。单一 Prompt 难以同时兼顾各环节的专业性和准确性，需要多个专业 Agent 协同工作。

### 决策

采用 **LangGraph StateGraph** 编排 6 个专业 Agent：

```
Coordinator → Retriever → Analyzer → [Comparer] → Generator → Reviewer
     ↑                                                        |
     └──────────── (质量不达标时回退重试) ─────────────────────┘
```

| Agent | 职责 | 超时 |
|-------|------|------|
| Coordinator | 任务分解与调度 | 30s |
| Retriever | 语义+关键词混合检索 | 30s |
| Analyzer | 深度文献分析 | 30s |
| Comparer | 多文献对比（条件执行） | 30s |
| Generator | 报告生成 | 30s |
| Reviewer | 质量审核与反馈 | 30s |

**工作流总超时**: 120s，单个 Agent 超时 30s

**条件路由**：当 `comparison_count >= 2` 时激活 Comparer Agent，否则跳过。

**状态管理**：LangGraph StateGraph 维护全局 `AgentState`，包含 query、papers、analysis、comparison、report、review_feedback 等字段。

### 理由

1. **专业分工**：每个 Agent 专注于单一职责，Prompt 更精确，输出质量更高
2. **可观测性**：每个 Agent 的状态可独立追踪，前端通过 SSE 实时展示进度
3. **容错性**：单个 Agent 失败可重试，不影响已完成步骤
4. **LangGraph 优势**：原生支持条件路由、状态管理、超时控制，比自研编排更可靠
5. **可扩展**：未来可增加新 Agent（如翻译 Agent、可视化 Agent）而不影响现有流程

### 后果

**正面**：
- 分析流程透明、可调试
- 各 Agent 可独立优化 Prompt 和参数
- 前端可实时展示 Agent 执行状态（通过 SSE）

**负面**：
- 串行执行增加总体延迟（6 个 Agent 串行）
- LangGraph 状态图定义复杂，学习曲线较陡
- M4 里程碑（多智能体协同）是项目关键路径，风险最高
- Reviewer 不通过时的回退机制需仔细设计，避免无限循环

### 关联文档

- `AI服务模块系统架构文档.md` — Agent 基类与 StateGraph 设计
- `信息架构文档(IA).md` — Agent 工作流导航
- `前端模块系统架构文档.md` — AgentFlowChart 可视化

---

## ADR-003: LLM 三级降级策略

### 状态

✅ 已采纳

### 上下文

AI 服务的核心依赖大语言模型（LLM），但 LLM 服务存在多种不可控风险：软件方模型配额耗尽、外部 API 服务商故障、网络中断等。项目预算限制 ≤ ¥1,500，需要在保证可用性的同时控制成本。

### 决策

采用**三级降级策略**：

```
优先级 1: BuiltinLLMProvider（软件方提供的模型）
    ↓ 不可用时
优先级 2: APILLMProvider（外部 API，如 DeepSeek/OpenAI）
    ↓ 不可用时
优先级 3: LocalLLMProvider（本地 Qwen2 模型）
```

**降级触发条件**：
- 连续 3 次调用失败
- 响应超时（30s）
- HTTP 5xx 错误

**降级恢复**：每 5 分钟尝试恢复到更高级别 Provider。

### 理由

1. **高可用**：任一 Provider 故障不影响整体服务
2. **成本控制**：优先使用软件方免费额度，次选按量付费 API，本地模型兜底零成本
3. **数据隐私**：敏感文献数据可在本地模型处理，不外泄
4. **合规性**：满足科研数据不外流的潜在要求

### 后果

**正面**：
- 服务可用性从单一 Provider 的 ~99% 提升到 ~99.9%
- 用户无感知降级，体验一致
- 本地模型确保离线场景可用

**负面**：
- 本地 Qwen2 模型质量可能低于云端模型，影响生成质量
- 本地模型需要 GPU 资源（至少 4GB VRAM）
- 降级期间生成质量不一致
- 三个 Provider 的 Prompt 格式可能不同，需要适配层

### 关联文档

- `AI服务模块系统架构文档.md` — LLM Provider 架构设计
- `开发规范文档.md` — AI 服务配置规范

---

## ADR-004: 三数据库存储架构（MySQL + Redis + ChromaDB）

### 状态

✅ 已采纳

### 上下文

系统需要存储三类本质不同的数据：结构化业务数据（用户、论文、会话）、高速缓存数据（会话状态、检索结果）、高维向量数据（论文语义嵌入）。单一数据库无法同时满足这三类需求。

### 决策

采用**三数据库架构**：

| 数据库 | 版本 | 职责 | 数据特征 |
|--------|------|------|----------|
| MySQL | 8.0 | 用户、论文、会话、分析结果等业务数据 | 结构化、事务性、关系型 |
| Redis | 7.0 | 缓存、会话状态、Agent 状态、JWT 黑名单 | KV 型、低延迟、TTL 过期 |
| ChromaDB | 0.5+ | 论文语义向量存储与检索 | 768 维向量、余弦相似度、HNSW 索引 |

**数据一致性策略**：
- MySQL → ChromaDB：通过 `paper_id` 外键关联，论文入库时同步生成向量
- MySQL → Redis：Cache-Aside 模式，写 MySQL 后删除 Redis 缓存
- Redis 缓存未命中时回源 MySQL/ChromaDB

**MySQL 表设计**：6 张核心表 — `users`, `user_profiles`, `papers`, `sessions`, `analysis_results`, `paper_favorites`

**ChromaDB 配置**：`papers` collection，HNSW 参数 M=16, ef=200, 余弦相似度

### 理由

1. **各取所长**：MySQL 擅长关系查询与事务，Redis 擅长低延迟缓存，ChromaDB 擅长向量检索
2. **RAG 核心需求**：语义检索必须依赖向量数据库，传统全文检索无法满足语义相似度需求
3. **性能分层**：热点数据放 Redis（ms 级），业务数据放 MySQL（10ms 级），向量检索放 ChromaDB（100ms 级）
4. **成本效益**：ChromaDB 开源免费，嵌入式部署，无需额外向量数据库服务费用

### 后果

**正面**：
- 每种数据用最适合的存储引擎
- 语义检索质量远超纯关键词检索
- Redis 缓存显著降低 MySQL 和 ChromaDB 压力

**负面**：
- 三套数据库增加运维复杂度（备份、监控、升级）
- MySQL ↔ ChromaDB 数据同步需要额外逻辑
- ChromaDB 嵌入式部署不支持集群，单节点可用性受限
- 需要处理缓存与数据库间的一致性问题

### 关联文档

- `数据库设计文档.md` — 完整 DDL 与 Redis Key 设计
- `AI服务模块系统架构文档.md` — VectorStoreService 设计
- `Java后端模块系统架构文档.md` — 缓存管理模块

---

## ADR-005: 混合 RAG 检索与 RRF 融合

### 状态

✅ 已采纳

### 上下文

科研文献检索需要兼顾语义相似性和关键词精确匹配。纯语义检索可能遗漏专业术语精确匹配的文献；纯关键词检索无法理解同义词和语义关联。需要一种融合策略结合两者优势。

### 决策

采用**混合检索 + RRF（Reciprocal Rank Fusion）融合**：

```
用户查询
    ├── 语义检索：bge-large-zh-v1.5 编码 → ChromaDB 余弦相似度 → 排序 R_sem
    └── 关键词检索：MySQL FULLTEXT(ngram) → 排序 R_kw
    
RRF 融合: RRF_score(d) = Σ 1/(k + rank_i),  k=60
    
→ 融合排序 → Top-N 结果
```

**Embedding 模型**：BAAI/bge-large-zh-v1.5，768 维向量，中文优化

**ChromaDB 检索**：余弦相似度，HNSW 索引（M=16, ef=200）

**MySQL 全文检索**：`FULLTEXT INDEX (title, abstract) WITH PARSER ngram`，支持中文分词

**RRF 参数**：k=60（标准参数，平衡高排名与低排名文档的贡献）

### 理由

1. **互补性**：语义检索捕获概念关联（如"深度学习"↔"神经网络"），关键词检索确保术语精确匹配
2. **RRF 优势**：无需归一化分数，对排序而非绝对分数进行融合，更鲁棒
3. **中文优化**：bge-large-zh-v1.5 在中文语义相似度任务上表现优异；ngram parser 适合中文全文检索
4. **可调性**：RRF 的 k 参数可根据实际效果调整

### 后果

**正面**：
- 检索召回率显著高于单一检索方式
- RRF 融合计算简单，性能开销低
- 768 维向量在精度和存储间取得平衡

**负面**：
- 双路检索增加系统复杂度（需同时查询 ChromaDB 和 MySQL）
- Embedding 模型加载需要 ~2GB 内存
- 论文入库时需同时写入 MySQL 和生成向量存入 ChromaDB
- RRF 参数 k=60 是经验值，可能需要针对数据集调优

### 关联文档

- `AI服务模块系统架构文档.md` — SearchService 与 EmbeddingService 设计
- `数据库设计文档.md` — MySQL FULLTEXT 索引设计
- `信息架构文档(IA).md` — 检索流程信息流

---

## ADR-006: 个性化引擎与用户画像驱动 Prompt

### 状态

✅ 已采纳

### 上下文

不同用户对科研文献分析的需求差异显著：本科生需要通俗易懂的解读，研究生需要方法论深度，资深研究者需要创新点分析。统一的生成结果无法满足差异化需求，需要根据用户画像动态调整输出。

### 决策

采用**用户画像驱动 Prompt 构建引擎**：

```
UserProfile (difficulty_level, preferred_style, research_fields)
    ↓
PersonalizationService
    ├── DIFFICULTY_MAP: {basic, intermediate, advanced, expert}
    │     → 注入术语解释深度、方法论细节级别
    ├── STYLE_MAP: {academic, popular, concise, detailed}
    │     → 注入行文风格、结构偏好
    └── research_fields → 注入领域上下文关键词
    ↓
PromptTemplate + 变量替换 {{variable}}
    ↓
个性化 Prompt → LLM
```

**难度映射**：

| 级别 | 术语处理 | 方法论 | 示例 |
|------|----------|--------|------|
| basic | 全部解释 | 省略 | "简单来说，这篇论文研究的是..." |
| intermediate | 关键术语解释 | 简述 | "该研究采用了XX方法..." |
| advanced | 行业术语保留 | 详述 | "该方法的创新点在于..." |
| expert | 原始术语 | 深度剖析 | "与SOTA相比，该方法在XX指标上..." |

### 理由

1. **用户体验**：同一篇文献，不同水平用户获得不同深度的解读，真正实现"个性化"
2. **Prompt 工程可维护**：模板与变量分离，修改风格不影响逻辑
3. **可扩展**：新增难度级别或风格只需扩展 MAP，不需改代码
4. **符合项目定位**：项目核心目标之一就是"领域知识个性化生成"

### 后果

**正面**：
- 生成结果与用户水平匹配，减少信息过载或信息不足
- Prompt 模板化管理，便于迭代优化
- 用户画像数据可持久化，跨会话一致

**负面**：
- 用户画像数据依赖用户主动填写，冷启动问题
- 难度/风格映射是人工设计的规则，可能不够精细
- 个性化 Prompt 增加 Token 消耗（约增加 200-500 tokens/请求）
- 不同风格间的质量差异需要持续监控

### 关联文档

- `AI服务模块系统架构文档.md` — PersonalizationService 与 Prompt 模板管理
- `数据库设计文档.md` — user_profiles 表设计
- `信息架构文档(IA).md` — 用户画像信息类别

---

## ADR-007: Cache-Aside 缓存模式与 TTL 分层

### 状态

✅ 已采纳

### 上下文

AI 推理和向量检索延迟较高（100ms-30s），频繁调用会严重影响用户体验和系统吞吐量。同时，不同类型数据的时效性需求差异大：Agent 状态秒级变化，论文元数据很少变化，分析结果可缓存较长时间。

### 决策

采用 **Cache-Aside 模式** + **TTL 分层策略**：

**Cache-Aside 流程**：
```
读取: 查 Redis → 命中则返回 → 未命中则查 DB → 写入 Redis → 返回
写入: 写 DB → 删除 Redis 缓存（而非更新）
```

**8 个缓存空间与 TTL**：

| 缓存空间 | Key 模式 | TTL | 理由 |
|----------|----------|-----|------|
| 用户信息 | `user:info:{userId}` | 1h | 低频变更 |
| 论文详情 | `paper:detail:{paperId}` | 1h | 元数据极少变 |
| 论文列表 | `paper:list:{hash}` | 10min | 搜索结果短期有效 |
| 检索结果 | `search:result:{hash}` | 10min | RAG 检索成本高 |
| 会话状态 | `session:state:{sessionId}` | 2h | 会话期间保持 |
| Agent 状态 | `agent:state:{sessionId}` | 5min | 实时性要求高 |
| 分析结果 | `analysis:result:{resultId}` | 30min | 已完成结果可缓存 |
| AI 降级状态 | `ai:provider:status` | 5min | 降级状态需及时感知 |

### 理由

1. **Cache-Aside 简单可靠**：避免缓存与数据库双写一致性问题，删除而非更新防止脏数据
2. **TTL 分层精准**：实时性要求高的数据短 TTL，稳定数据长 TTL，平衡一致性与性能
3. **Redis 高性能**：ms 级响应，热点数据命中率 >80%
4. **Java 侧统一管理**：通过 Spring Cache + 自定义 CacheManager 统一管理所有缓存空间

### 后果

**正面**：
- 热点数据响应延迟从 100ms+ 降到 <5ms
- 减少 MySQL 和 ChromaDB 查询压力
- TTL 自动过期避免手动清理

**负面**：
- Cache-Aside 在高并发场景可能出现缓存击穿（需加锁或布隆过滤器）
- 删除缓存与写 DB 非原子操作，极端情况可能出现短暂不一致
- 8 个缓存空间增加配置和维护复杂度
- Redis 内存占用需要监控（预估 <1GB）

### 关联文档

- `Java后端模块系统架构文档.md` — 缓存管理模块设计
- `数据库设计文档.md` — Redis Key 命名规范
- `开发规范文档.md` — 缓存使用规范

---

## ADR-008: JWT 认证与 Redis 黑名单

### 状态

✅ 已采纳

### 上下文

系统需要用户认证与授权机制，但作为单体前端 + 单体后端架构，不需要 OAuth2 等复杂认证协议。同时，JWT 的无状态特性使得 Token 主动失效（如用户登出、密码修改）成为难点。

### 决策

采用 **JWT + Redis 黑名单** 方案：

**认证流程**：
```
登录: BCrypt 验证密码 → 生成 JWT (24h 有效期) → 返回 Bearer Token
请求: Authorization: Bearer <token> → 验证签名+过期 → 检查 Redis 黑名单 → 放行/拒绝
登出: 将 Token jti 写入 Redis 黑名单 (TTL = Token 剩余有效期)
```

**JWT 载荷**：
- `sub`: userId
- `username`: 用户名
- `iat` / `exp`: 签发/过期时间
- `jti`: Token 唯一 ID（用于黑名单）

**安全措施**：
- BCrypt 加密存储密码（强度 10）
- JWT 签名密钥通过配置注入，不硬编码
- Token 有效期 24 小时
- 黑名单 TTL 与 Token 剩余有效期一致，自动清理

### 理由

1. **无状态优势**：JWT 自包含用户信息，无需每次查库验证
2. **Redis 黑名单解决失效问题**：登出时写入黑名单，检查时 O(1) 查询
3. **简单高效**：相比 OAuth2 实现简单，满足当前需求
4. **自动清理**：黑名单 TTL 与 Token 过期时间对齐，Redis 自动清理

### 后果

**正面**：
- 认证流程简单，开发成本低
- Token 自包含减少数据库查询
- 黑名单机制确保登出即时生效

**负面**：
- 每次请求需查 Redis 黑名单（增加 ~1ms 延迟）
- JWT 无法撤销已发出但未登出的 Token（只能等自然过期）
- 密钥泄露则所有 Token 失效，需密钥轮换机制
- 不适合分布式 Session 场景（当前单实例足够）

### 关联文档

- `Java后端模块系统架构文档.md` — 用户管理模块与 JWT 设计
- `数据库设计文档.md` — Redis 黑名单 Key 设计
- `开发规范文档.md` — 安全规范

---

## ADR-009: SSE 实时 Agent 状态推送

### 状态

✅ 已采纳

### 上下文

多 Agent 工作流执行时间较长（10s-120s），用户需要实时了解当前哪个 Agent 正在工作、进度如何。传统 HTTP 请求-响应模式无法实现服务端主动推送，WebSocket 又过于重量级。

### 决策

采用 **SSE（Server-Sent Events）** 链路推送 Agent 状态：

```
Python AI Service → Java Backend → Frontend

Python (FastAPI): StreamingResponse(generator, media_type="text/event-stream")
    ↓ HTTP SSE
Java (Spring Boot): WebClient 接收 → SseEmitter 转发
    ↓ HTTP SSE
Frontend (Vue3): EventSource / useSSE composable 接收
```

**SSE 事件格式**：
```
event: agent_status
data: {"agent": "Analyzer", "status": "running", "progress": 0.6, "timestamp": "2026-05-23T10:30:00Z"}

event: agent_status
data: {"agent": "Analyzer", "status": "completed", "result_summary": "..."}
```

**前端处理**：
- `useSSE` composable 封装，自动重连（3s 间隔，最多 5 次）
- `agentStore` 更新状态，触发 `AgentFlowChart` 可视化
- ECharts Graph 展示 Agent 执行流程，颜色编码状态

### 理由

1. **SSE 轻量**：基于 HTTP，无需额外协议，浏览器原生支持
2. **单向推送足够**：Agent 状态是服务端→客户端的单向信息流，无需 WebSocket 的双向能力
3. **自动重连**：浏览器原生支持 SSE 断线重连，useSSE 进一步增强
4. **穿透代理**：SSE 基于 HTTP，Nginx 反向代理配置简单（需关闭 proxy_buffering）

### 后果

**正面**：
- 用户实时感知 Agent 执行进度，减少等待焦虑
- SSE 实现简单，前后端代码量少
- 与 REST API 共用同一 HTTP 连接基础设施

**负面**：
- SSE 仅支持服务端→客户端单向通信
- Nginx 需要特殊配置（`proxy_buffering off`）避免事件缓冲
- 长连接占用服务器资源（每个连接一个线程/协程）
- 浏览器 SSE 连接数限制（6 个/域名，HTTP/1.1）

### 关联文档

- `AI服务模块系统架构文档.md` — SSE 事件流设计
- `Java后端模块系统架构文档.md` — PythonAIClient SSE 转发
- `前端模块系统架构文档.md` — useSSE composable 与 AgentFlowChart
- `开发规范文档.md` — SSE 事件格式规范

---

## ADR-010: Docker Compose 部署架构

### 状态

✅ 已采纳

### 上下文

项目需要在单台服务器上部署完整系统（预算 ≤ ¥1,500），包含 5 个服务组件。手动部署耗时且易出错，需要自动化部署方案。同时，服务间存在启动依赖关系（如 MySQL 必须先于 Java 后端启动）。

### 决策

采用 **Docker Compose** 编排 5 个服务：

```yaml
services:
  mysql:      # MySQL 8.0 — 数据持久化
  redis:      # Redis 7.0 — 缓存
  ai-service: # Python FastAPI — AI 推理（依赖 mysql, redis）
  backend:    # Java Spring Boot — 业务服务（依赖 mysql, redis, ai-service）
  frontend:   # Nginx — 前端静态资源 + API 反向代理（依赖 backend）
```

**启动顺序**：`mysql → redis → ai-service → backend → frontend`

**关键配置**：
- MySQL: `utf8mb4` 字符集，`/docker-entrypoint-initdb.d/` 自动初始化
- Redis: 无密码（内网），`appendonly yes` 持久化
- AI Service: 挂载 `.env` 配置，健康检查 `/health`
- Backend: JVM 参数 `-Xmx512m`，健康检查 `/actuator/health`
- Frontend: Nginx SPA 路由 + API 代理 + SSE `proxy_buffering off`

**Dockerfile 策略**：
- 多阶段构建，减小镜像体积
- 非 root 用户运行（安全）
- 健康检查（HEALTHCHECK）

### 理由

1. **一键部署**：`docker compose up -d` 启动完整系统
2. **环境一致**：开发、测试、生产环境统一
3. **依赖管理**：`depends_on` + `healthcheck` 确保启动顺序
4. **资源控制**：`deploy.resources.limits` 限制各服务内存，适配低成本服务器
5. **单人运维友好**：无需 K8s 等复杂编排，Docker Compose 足够

### 后果

**正面**：
- 部署流程标准化，新人可快速搭建环境
- 容器隔离，服务故障不相互影响
- 镜像版本化，回滚简单

**负面**：
- Docker Compose 不支持自动扩缩容
- 单节点部署，无高可用保障
- AI Service 镜像较大（含 Embedding 模型 ~2GB）
- 服务器最低要求 4GB 内存（MySQL 1G + Redis 256M + AI 1.5G + Java 512M + Nginx 64M）
- 数据卷备份需额外脚本

### 关联文档

- `开发规范文档.md` — Docker 与部署规范
- `项目里程碑文档.md` — M1 基础设施搭建
- `数据库设计文档.md` — 数据初始化脚本

---

## ADR-011: 知识图谱增强 RAG（Neo4j）

### 状态

✅ 已采纳

### 上下文

纯向量检索（ChromaDB）和关键词检索（MySQL FULLTEXT）能覆盖大部分语义检索场景，但在以下场景存在不足：(1) 需要跨论文的实体关系推理（如"方法A基于方法B改进"）；(2) 需要发现论文间的隐含关联（如共同引用的关键文献）；(3) 需要结构化的知识导航（如按研究主题、方法类型浏览论文关系网络）。知识图谱可以补足向量检索在关系推理方面的短板。

### 决策

采用 **Neo4j 知识图谱** 作为向量检索的补充，构建论文-方法-实体关系网络：

**知识图谱 Schema**：
```
节点类型：
- Paper: 论文节点（paper_id, title, year, venue）
- Method: 方法节点（name, category）
- Concept: 概念节点（name, domain）
- Author: 作者节点（name, affiliation）

关系类型：
- USES: Paper → Method（论文使用某方法）
- IMPROVES: Method → Method（方法改进关系）
- RELATED_TO: Concept → Concept（概念关联）
- AUTHORED_BY: Paper → Author（作者关系）
- CITES: Paper → Paper（引用关系）
- BELONGS_TO: Method → Concept（方法归属领域）
```

**混合检索策略**：
```
用户查询
    ├── 语义检索：ChromaDB 向量相似度 → R_sem
    ├── 关键词检索：MySQL FULLTEXT → R_kw
    └── 图谱检索：Neo4j 关系遍历 + 实体匹配 → R_graph
    
RRF 融合: RRF_score(d) = Σ 1/(k + rank_i),  k=60
→ 三路融合排序 → Top-N 结果
```

**图谱构建方式**：论文入库时，通过 LLM 提取实体和关系，写入 Neo4j。非实时构建，批量离线处理。

### 理由

1. **关系推理**：图谱支持"方法A改进自方法B"等链式推理，纯向量检索无法实现
2. **结构化导航**：用户可按研究主题、方法网络浏览论文关系，提升可解释性
3. **创新点支撑**：知识图谱增强 RAG 是项目核心创新点之一，与纯 RAG 方案形成差异化
4. **检索互补**：向量检索擅长语义相似，图谱检索擅长关系推理，两者互补
5. **可视化增强**：Neo4j 数据可直接驱动前端知识图谱可视化，提升演示效果

### 后果

**正面**：
- 检索召回率提升（尤其对于关系型查询）
- 支持论文关系网络的可视化展示
- 符合项目创新点"知识图谱增强的RAG"的承诺
- 对比Agent可利用图谱发现论文间的矛盾和关联

**负面**：
- 增加一个数据库（Neo4j）的运维复杂度
- 图谱构建依赖 LLM 提取质量，初始构建成本较高
- 额外占用服务器资源（Neo4j ~256MB 内存）
- 图谱数据与 MySQL/ChromaDB 需要同步维护
- 初期数据量小（200篇论文），图谱效果可能不显著，需逐步积累

### 关联文档

- `数据库设计文档.md` — Neo4j Schema 设计
- `AI服务模块系统架构文档.md` — 知识图谱构建服务
- `前端模块系统架构文档.md` — 知识图谱可视化组件
- `01-项目策划案.md` — 创新点3: 知识图谱增强的RAG

---

## 决策关系图

```
ADR-001 三层分离架构
├── ADR-002 多智能体编排 (Python 层内)
├── ADR-003 LLM 降级 (Python 层内)
├── ADR-006 个性化引擎 (Python 层内)
├── ADR-009 SSE 推送 (跨三层)
└── ADR-004 三数据库架构
    ├── ADR-005 混合 RAG 检索 (MySQL + ChromaDB)
    ├── ADR-007 缓存策略 (MySQL + Redis)
    └── ADR-008 JWT 认证 (MySQL + Redis)

ADR-010 Docker 部署 (支撑所有决策)
│
ADR-011 知识图谱增强 RAG (AI 服务 + 数据层)
```

---

## 决策记录索引

| ADR 编号 | 标题 | 状态 | 日期 | 影响范围 |
|----------|------|------|------|----------|
| ADR-001 | 三层分离架构 | ✅ 已采纳 | 2026-05-23 | 全系统 |
| ADR-002 | 多智能体协同编排 | ✅ 已采纳 | 2026-05-23 | AI 服务 |
| ADR-003 | LLM 三级降级 | ✅ 已采纳 | 2026-05-23 | AI 服务 |
| ADR-004 | 三数据库存储架构 | ✅ 已采纳 | 2026-05-23 | 数据层 |
| ADR-005 | 混合 RAG 检索与 RRF | ✅ 已采纳 | 2026-05-23 | AI 服务 + 数据层 |
| ADR-006 | 个性化引擎 | ✅ 已采纳 | 2026-05-23 | AI 服务 |
| ADR-007 | Cache-Aside 缓存 | ✅ 已采纳 | 2026-05-23 | Java 后端 + 数据层 |
| ADR-008 | JWT 认证与黑名单 | ✅ 已采纳 | 2026-05-23 | Java 后端 + 数据层 |
| ADR-009 | SSE 实时推送 | ✅ 已采纳 | 2026-05-23 | 全系统 |
| ADR-010 | Docker Compose 部署 | ✅ 已采纳 | 2026-05-23 | 基础设施 |
| ADR-011 | 知识图谱增强 RAG | ✅ 已采纳 | 2026-05-23 | AI 服务 + 数据层 |

---

> **ADR 维护说明**：当架构决策发生变更时，应更新对应 ADR 的状态（提议/已采纳/已废弃/已替代），并记录变更原因和日期。新增架构决策应按序号递增添加。
