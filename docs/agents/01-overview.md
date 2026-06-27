# 01 — 项目概况与开发计划

> 加载时机：理解项目全貌、规划开发任务、准备答辩材料时加载。
> 关联文件：[02-tech-stack.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/agents/02-tech-stack.md) | [03-agent-system.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/agents/03-agent-system.md)

---

## 1 项目概况

| 项目 | 内容 |
|------|------|
| **课题编号** | XH-202630 |
| **课题名称** | 领域知识个性化生成与多智能体协同决策系统研究 |
| **子项目** | 科研文献助手 |
| **发榜单位** | 上海云之脑智能科技有限公司（科大讯飞全资子公司） |
| **开发周期** | 14周（2026年5月23日 - 9月30日） |
| **预算** | ≤ ¥1,500 |
| **团队** | 1名开发者（AI Coding辅助）+ 2名非开发者（数据/文档） |

### 1.1 核心功能

1. **智能文献检索** — 语义+关键词混合检索，RRF融合排序
2. **论文深度分析** — 5维度结构化提取（研究问题/核心方法/主要实验/核心结论/局限性）
3. **多论文对比** — 方法对比矩阵+矛盾自动发现
4. **个性化综述生成** — 用户画像驱动的Prompt个性化
5. **Agent协同可视化** — SSE实时推送6个Agent执行状态
6. **知识溯源** — 引用标注→原文跳转

### 1.2 四大创新点

1. 科研场景多Agent分工协同（6个专业Agent）
2. 用户画像驱动的个性化生成（4维度画像→Prompt适配）
3. 论文矛盾自动发现（对比Agent检测观点冲突）
4. Agent协同过程可视化（ECharts流程图+SSE实时推送）

---

## 2 里程碑与开发计划

| 里程碑 | 时间 | 核心交付 | 状态 |
|--------|------|---------|------|
| **M1 基础设施就绪** | Week 1-2 | 数据库+模型+3个项目骨架+Docker Compose | ✅ AM1✅ JM1✅ FM1✅ |
| **M2 单Agent可用** | Week 3-4 | RAG检索+检索/分析/生成3个Agent+LangGraph基础流程 | ✅ AM2✅ 代码就绪 |
| **M3 前后端联调** | Week 5-6 | 用户认证+论文管理+前端基础页面+全链路联调 | ✅ AM3✅ JM3✅ FM2✅ |
| **M4 多Agent协同** | Week 7-8 | 6-Agent完整工作流+降级机制+个性化引擎+SSE推送 | 🔄 代码就绪（schemas缺失阻断启动，JM4✅/FM4✅/AM4代码就绪） |
| **M5 功能完整** | Week 9-10 | Agent可视化+报告导出+引用溯源+矛盾发现+筛选排序 | 🔄 进行中（JM5✅ 447测试，前端11页+21组件全部实现） |
| **M6 交付就绪** | Week 11-14 | 性能优化+测试+技术报告+演示视频+答辩PPT | ⬜ |

**关键路径**: M1→M2→M3→M4→M5→M6，最关键里程碑为M4（多Agent协同）。

**复验日期**：2026-06-28（基于代码审查结论更新）

**当前阻断性缺陷**：
- `ai-service/app/models/` 目录缺失（schemas.py + enums.py 不存在），AI 服务 import 阶段崩溃，无法启动
- 个性化旁路：`AppState` 未定义 `personalization_service` 属性，所有 6 个 Agent 的个性化参数恒为 None
- ddl-auto: update：生产环境未隔离

---

## 3 功能编号体系

```
F1  前端模块
  F1.1 用户界面    F1.2 论文检索    F1.3 论文分析    F1.4 综述生成    F1.5 Agent可视化
F2  Java后端模块
  F2.1 用户管理    F2.2 论文管理    F2.3 会话管理    F2.4 分析服务    F2.5 AI服务调用    F2.6 缓存管理
F3  Python AI服务模块
  F3.1 多Agent协同引擎    F3.2 RAG检索    F3.3 LLM服务    F3.4 个性化引擎    F3.5 API服务
F4  数据模块
  F4.1 MySQL    F4.2 Redis    F4.3 Chroma向量库    F4.4 论文数据采集
F5  模型模块
  F5.1 大语言模型    F5.2 Embedding模型
```

---

## 4 架构决策记录（ADR）

| ADR | 标题 | 核心决策 |
|-----|------|---------|
| ADR-001 | 三层分离架构 | Vue3 + Spring Boot + FastAPI，关注点分离 |
| ADR-002 | 多智能体协同编排 | LangGraph StateGraph编排6个Agent |
| ADR-003 | LLM三级降级 | 软件方模型→外接API（当前=DeepSeek V4 Flash）→本地Qwen2 |
| ADR-004 | 四数据库存储 | MySQL(结构化) + Redis(缓存) + ChromaDB(向量) + Neo4j(知识图谱，计划M4+)|
| ADR-005 | 混合RAG检索 | 语义+关键词双路检索 + RRF融合 |
| ADR-006 | 个性化引擎 | 用户画像→Prompt个性化片段注入 |
| ADR-007 | Cache-Aside缓存 | 写后删 + TTL分层(5min~2h) |
| ADR-008 | JWT认证 | JWT + Redis黑名单，BCrypt密码 |
| ADR-009 | SSE实时推送 | Python→Java→前端，Agent状态实时可视化 |
| ADR-010 | Docker Compose部署 | 5服务编排，healthcheck启动顺序 |
| ADR-011 | 知识图谱增强RAG | Neo4j补充向量检索的关系推理能力（计划M4+集成） |

---

## 5 验收标准

| 验收项 | 目标值 |
|--------|--------|
| 智能检索 Top10相关性 | >80% |
| 论文分析5维度准确率 | >85% |
| 个性化综述差异度 | >60% |
| 知识溯源引用正确率 | >90% |
| 检索响应 | ≤3秒 |
| 分析响应 | ≤30秒 |
| 综述生成 | ≤60秒 |
| 流式首字节 | ≤2秒 |
| 95%请求响应 | ≤5秒 |
| 并发能力 | ≥50用户 |
| 缓存命中率 | >50% |

---

## 6 风险管理

### 6.1 高风险

| 风险 | 应对 |
|------|------|
| 大模型幻觉 | RAG强约束+审核Agent+引用核查 |
| 多Agent协同不稳定 | 渐进式开发(2→3→6个Agent)+降级机制 |
| 个性化效果不明显 | 显式画像+强Prompt+对比演示 |
| 团队单点故障 | AI Coding辅助+文档先行 |
| 需求不明确 | 与发榜单位确认+迭代开发 |

### 6.2 中风险

| 风险 | 应对 |
|------|------|
| 知识库质量 | 人工审核+分块质量检查 |
| API成本 | 软件方模型优先+本地模型兜底 |
| 响应速度 | 缓存+流式输出+异步调用 |
| 评委认为"调API" | 强调RAG+Agent编排+个性化+知识图谱创新 |
| 前端粗糙 | Element Plus组件库+核心页面优先 |

---

## 7 学习路线优先级

| 优先级 | 技术栈 |
|--------|--------|
| **P0** | Python+FastAPI, SQL+MySQL, Docker, Prompt Engineering, RAG+LangChain, Embedding+ChromaDB, **LangGraph（核心中的核心）** |
| **P1** | Java+Spring Boot, Vue3+Element Plus, JPA+Redis, Qwen2部署, BAAI/bge-m3 |

**关键提醒**: LangGraph是核心中的核心；先跑通最小闭环（检索→分析→生成）。
