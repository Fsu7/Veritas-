# XH-202630 科研文献智能助手 — 信息架构文档（IA）

> **课题编号**：XH-202630  
> **课题名称**：领域知识个性化生成与多智能体协同决策系统研究  
> **发榜单位**：上海云之脑智能科技有限公司（科大讯飞全资子公司）  
> **文档版本**：v1.1  
> **创建日期**：2026年5月23日  
> **最后更新**：2026年5月24日  
> **文档状态**：初稿

---

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0 | 2026-05-23 | 项目组 | 初始版本 |
| v1.1 | 2026-05-24 | 项目组 | 纳入Neo4j知识图谱（ADR-011）；RRF检索从双路升级为三路；修正Redis Key命名不一致（移除paper:list）；新增IC-2.5图谱信息类；新增文档生态中对ADR的引用 |

---

## 目录

- [1 引言](#1-引言)
- [2 信息架构总览](#2-信息架构总览)
- [3 信息分类体系](#3-信息分类体系)
- [4 导航架构](#4-导航架构)
- [5 内容结构层级](#5-内容结构层级)
- [6 用户任务流与信息流](#6-用户任务流与信息流)
- [7 跨系统信息映射](#7-跨系统信息映射)
- [8 数据实体与关系架构](#8-数据实体与关系架构)
- [9 标签与命名体系](#9-标签与命名体系)
- [10 可检索性设计](#10-可检索性设计)
- [11 信息安全与权限控制](#11-信息安全与权限控制)
- [12 文档生态系统](#12-文档生态系统)
- [13 IA 治理与演进](#13-ia-治理与演进)

---

## 1 引言

### 1.1 编写目的

信息架构文档（Information Architecture, IA）定义了科研文献智能助手系统中信息的组织、结构、导航、标签和检索方式。本文档旨在：

1. 为系统开发提供统一的信息组织蓝图
2. 确保用户在不同交互场景中高效获取所需信息
3. 明确跨系统（前端、Java后端、Python AI服务、数据层）的信息流转与映射关系
4. 建立信息架构的治理规范，指导后续演进

### 1.2 适用范围

本文档覆盖 XH-202630 科研文献智能助手系统的完整信息架构，包括：

- 前端用户界面的信息组织与导航
- Java后端服务的数据模型与API信息结构
- Python AI服务的Agent信息流与Prompt架构
- 数据存储层的信息分布与索引设计
- 项目文档生态的信息组织

### 1.3 信息架构原则

| 原则 | 说明 | 体现 |
|------|------|------|
| **以用户画像为中心** | 信息呈现由用户画像驱动，不同用户获取差异化内容 | 个性化引擎 → Prompt注入 → 输出适配 |
| **渐进式披露** | 按任务流程逐步呈现信息，避免信息过载 | 主题输入 → 检索结果 → 论文详情 → 分析结果 → 综述报告 |
| **可溯源性** | 所有AI生成内容可追溯到原始信息源 | 引用标注 → 原文跳转 → 知识溯源链路 |
| **分层解耦** | 信息在各系统间通过标准化接口传递，互不侵入 | DTO转换 → REST API → JSON Schema |
| **可解释性** | Agent处理过程对用户透明可见 | SSE状态推送 → Agent可视化 → 中间结果展示 |
| **降级优先** | 信息获取路径有冗余降级方案 | 三路LLM降级 → 多Agent→单Agent降级 |

### 1.4 参考文档

| 文档名称 | 版本 | IA关联 |
|---------|------|--------|
| 需求规格说明书 | v1.0 | 功能信息点定义、用户画像维度 |
| 系统架构设计文档 | v1.0 | 系统分层、数据架构、缓存架构 |
| 模块清单 | v1.0 | 模块信息边界、功能编号体系 |
| 功能实现顺序 | v1.0 | 信息构建时序 |
| 技术栈 | v1.0 | 技术约束对信息结构的影响 |
| Java后端模块系统架构文档 | v1.0 | Java层信息模型与API结构 |
| AI服务模块系统架构文档 | v1.0 | Agent信息流与Prompt架构 |
| 前端模块系统架构文档 | v1.0 | 前端信息组织与状态管理 |
| 数据库设计文档 | v1.0 | 数据实体、索引、缓存键、Neo4j图谱设计 |
| 项目里程碑文档 | v1.0 | 交付信息节点 |
| 架构决策记录(ADR) | v1.1 | ADR-011 知识图谱增强RRF三路融合 |

---

## 2 信息架构总览

### 2.1 系统信息架构全景图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          信息架构全景                                     │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                      用户交互信息层                                  │  │
│  │                                                                    │  │
│  │  输入信息                  展示信息                  反馈信息        │  │
│  │  ├── 研究主题              ├── 论文卡片              ├── 加载状态    │  │
│  │  ├── 用户画像              ├── 分析卡片              ├── Agent状态   │  │
│  │  ├── 筛选条件              ├── 对比表格              ├── 进度提示    │  │
│  │  └── 操作指令              ├── 综述报告              └── 错误提示    │  │
│  │                           ├── Agent流程图                          │  │
│  │                           └── 引用溯源                              │  │
│  └──────────────────────────────┬─────────────────────────────────────┘  │
│                                 │ HTTP REST / SSE                        │
│  ┌──────────────────────────────▼─────────────────────────────────────┐  │
│  │                      业务逻辑信息层（Java）                          │  │
│  │                                                                    │  │
│  │  实体信息                  传输信息                  缓存信息        │  │
│  │  ├── User实体              ├── UserDTO               ├── 画像缓存    │  │
│  │  ├── Paper实体             ├── PaperDTO              ├── 检索缓存    │  │
│  │  ├── Session实体           ├── AnalysisReqDTO        ├── 分析缓存    │  │
│  │  ├── UserProfile实体       ├── AnalysisResDTO        └── 会话缓存    │  │
│  │  └── AnalysisResult实体    └── AgentReqDTO                         │  │
│  └──────────────────────────────┬─────────────────────────────────────┘  │
│                                 │ HTTP REST / SSE                        │
│  ┌──────────────────────────────▼─────────────────────────────────────┐  │
│  │                    智能处理信息层（Python）                           │  │
│  │                                                                    │  │
│  │  Agent信息流               Prompt信息               向量信息        │  │
│  │  ├── StateGraph状态        ├── 系统Prompt模板        ├── 查询向量    │  │
│  │  ├── 子任务分解             ├── 个性化注入片段        ├── 文档向量    │  │
│  │  ├── 中间结果               ├── 变量占位符            ├── 相似度分数  │  │
│  │  └── Agent状态              └── 角色指令              └── RRF融合    │  │
│  └──────────────────────────────┬─────────────────────────────────────┘  │
│                                 │                                        │
│  ┌──────────────────────────────▼─────────────────────────────────────┐  │
│  │                      持久化信息层                                    │  │
│  │                                                                    │  │
│  │  MySQL（结构化）           Redis（缓存）             Chroma（向量）  │  │
│  │  ├── papers表              ├── user:profile:{id}     ├── papers集合  │  │
│  │  ├── users表               ├── search:result:{hash}  ├── 768维向量   │  │
│  │  ├── user_profiles表       ├── analysis:result:{id}  └── 元数据过滤  │  │
│  │  ├── sessions表            ├── session:state:{id}                   │  │
│  │  ├── analysis_results表    └── agent:state:{id}                    │  │
│  │  └── paper_favorites表                                             │  │
│  │                                                                      │  │
│  │  Neo4j（图谱）                                                        │  │
│  │  ├── Paper/Method/Concept/Author 节点                               │  │
│  │  ├── USES/IMPROVES/CITES 关系                                       │  │
│  │  └── 图谱推理增强检索（三路RRF融合第三路）                               │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                      模型服务信息层                                  │  │
│  │                                                                    │  │
│  │  LLM推理信息               Embedding信息                           │  │
│  │  ├── 方案A:软件方模型       ├── bge-large-zh-v1.5                   │  │
│  │  ├── 方案B:外接API          ├── 768维输出                           │  │
│  │  └── 方案C:用户本地模型     └── Embedding API备选                   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.2 信息流转核心路径

以"生成文献综述"为例，信息在系统中的完整流转：

```
[用户] 输入主题 + 画像
    │
    ▼ 信息形式：{topic, userId, profileContext}
[前端] Pinia → Axios
    │
    ▼ 信息形式：HTTP POST /api/analysis/report
[Java后端] Controller → Service
    │ 信息增强：注入UserProfile（Redis→MySQL回退）
    │ 信息转换：DTO组装（Java对象→JSON）
    ▼ 信息形式：HTTP POST http://ai-service:8000/api/agent/analyze
[Python AI] FastAPI → LangGraph
    │ 信息增强：个性化Prompt注入
    │ 信息分解：任务拆分为子任务
    ▼
[协调者Agent] 解析查询 + 分配子任务
    │
    ▼ 信息形式：StateGraph.sub_tasks[]
[检索Agent] Chroma语义检索 + MySQL关键词检索
    │ 信息形式：{query_embedding → TopK docs}
    │ 信息融合：RRF（Reciprocal Rank Fusion）
    ▼ 信息形式：StateGraph.search_results[]
[分析Agent] LLM推理 → 结构化提取
    │ 信息形式：{paper + prompt → 5维度JSON}
    ▼ 信息形式：StateGraph.analysis_results[]
[对比Agent] 多论文对比 + 矛盾发现
    │ 信息形式：{papers[] + prompt → 对比表格+矛盾}
    ▼ 信息形式：StateGraph.compare_result
[生成Agent] 个性化综述生成
    │ 信息增强：用户画像 → Prompt个性化片段
    │ 信息形式：{analysis + profile + prompt → 综述文本}
    ▼ 信息形式：StateGraph.report
[审核Agent] 引用核查 + 事实比对
    │ 信息形式：{report + original_papers → 审核结果}
    ▼ 信息形式：StateGraph.review_result
    │
    ▼ 信息形式：SSE推送Agent状态 + HTTP返回最终结果
[Java后端] 解析响应 → 存储 → 缓存
    │ 信息持久化：MySQL analysis_results
    │ 信息缓存：Redis analysis:result:{id}
    ▼
[前端] 展示综述 + Agent可视化 + 引用溯源
    │
    ▼ 信息形式：Vue组件渲染
[用户] 阅读、编辑、导出
```

---

## 3 信息分类体系

### 3.1 系统信息分类总表

系统信息按业务域划分为6大信息类、22个信息子类：

```
┌─────────────────────────────────────────────────────────────────────┐
│                    系统信息分类体系                                    │
│                                                                     │
│  IC-1 用户信息类                                                    │
│  ├── IC-1.1 身份信息（username, email, password_hash）              │
│  ├── IC-1.2 画像信息（education_level, research_field,             │
│  │                knowledge_level, preferred_style）                │
│  └── IC-1.3 行为信息（收藏、历史、偏好记录）                        │
│                                                                     │
│  IC-2 论文信息类                                                    │
│  ├── IC-2.1 元数据（title, authors, year, venue, keywords）        │
│  ├── IC-2.2 内容信息（abstract, sections, pdf_url）                │
│  ├── IC-2.3 统计信息（citation_count, relevance_score）            │
│  ├── IC-2.4 向量信息（768维embedding, chunk_index, chunk_type）   │
│  └── IC-2.5 图谱信息（Paper/Method/Concept/Author节点及关系）      │
│                                                                     │
│  IC-3 分析信息类                                                    │
│  ├── IC-3.1 论文分析（研究问题、核心方法、主要实验、               │
│  │                核心结论、局限性）                                 │
│  ├── IC-3.2 对比分析（方法对比、数据集对比、性能对比、             │
│  │                结论对比、矛盾发现）                               │
│  ├── IC-3.3 综述报告（引言、研究现状、方法对比、                   │
│  │                研究趋势、参考文献）                               │
│  └── IC-3.4 审核结果（引用正确性、事实准确性、修改建议）           │
│                                                                     │
│  IC-4 会话信息类                                                    │
│  ├── IC-4.1 会话状态（active/completed/expired）                    │
│  ├── IC-4.2 关联关系（user↔session↔analysis）                      │
│  └── IC-4.3 主题信息（topic, 创建时间）                             │
│                                                                     │
│  IC-5 Agent信息类                                                   │
│  ├── IC-5.1 状态信息（waiting/running/completed/failed）            │
│  ├── IC-5.2 中间结果（各Agent产出的摘要信息）                      │
│  ├── IC-5.3 耗时统计（各Agent执行时间、总进度）                    │
│  └── IC-5.4 工作流状态（StateGraph全局状态快照）                   │
│                                                                     │
│  IC-6 系统信息类                                                    │
│  ├── IC-6.1 模型状态（加载状态、GPU使用、当前方案）                │
│  ├── IC-6.2 健康状态（各服务健康检查）                              │
│  └── IC-6.3 配置信息（LLM_MODE、API密钥、降级策略）               │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 信息分类与功能编号映射

| 信息类 | 关联功能编号 | 存储位置 | 生命周期 |
|--------|------------|---------|---------|
| IC-1 用户信息 | F1.1.x, F2.1.x | MySQL + Redis | 用户注册至注销 |
| IC-2 论文信息 | F1.2.x, F2.2.x, F4.1.x, F4.3.x | MySQL + ChromaDB + Neo4j | 永久持久化 |
| IC-3 分析信息 | F1.3.x, F1.4.x, F2.4.x, F3.1.x | MySQL + Redis | 创建后持久化，缓存30分钟 |
| IC-4 会话信息 | F2.3.x | MySQL + Redis | 创建至过期 |
| IC-5 Agent信息 | F1.5.x, F3.1.x | Redis | 分析期间，缓存5分钟 |
| IC-6 系统信息 | F3.3.x, F3.5.x | 内存 + .env | 服务运行期间 |

### 3.3 信息优先级分类

| 优先级 | 信息类 | 说明 | 丢失影响 |
|--------|--------|------|---------|
| **P0-不可丢失** | IC-1.1 身份, IC-2 论文元数据, IC-3 分析结果, IC-4 会话 | 核心业务数据 | 系统不可用 |
| **P1-可短时丢失** | IC-1.2 画像缓存, IC-2.4 向量缓存, IC-3.3 综述缓存 | 缓存加速数据 | 性能下降，可从持久层恢复 |
| **P2-可丢弃** | IC-5 Agent状态, IC-6 系统运行时信息 | 临时运行时数据 | 影响可视化体验，不影响业务 |

---

## 4 导航架构

### 4.1 前端页面导航结构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        前端导航架构                                   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  全局导航栏（TopBar）                                        │   │
│  │  ├── Logo + 系统名称                                         │   │
│  │  ├── 首页链接                                                │   │
│  │  ├── 用户中心入口                                            │   │
│  │  └── 登录/注册/退出                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  页面层级：                                                         │
│                                                                     │
│  L1: 首页 (/)                                                      │
│  │  └── 主题输入框 + 历史输入快捷选择                              │
│  │                                                                  │
│  L2: 检索结果页 (/search)                                          │
│  │  ├── 论文卡片列表（分页10条/页）                                │
│  │  ├── 筛选面板（年份/引用数/会议）                                │
│  │  ├── 排序选项（相关度/时间/引用数）                              │
│  │  └── 操作入口：论文详情 / 对比选择 / 生成综述                    │
│  │                                                                  │
│  L3: 论文详情页 (/paper/:paperId)                                  │
│  │  ├── 论文元数据展示                                            │
│  │  ├── 智能分析结果（5维度卡片）                                  │
│  │  ├── 通俗解释（初级用户）                                      │
│  │  └── 操作入口：对比分析 / 引用溯源                              │
│  │                                                                  │
│  L3: 对比分析页 (/compare)                                         │
│  │  ├── 多论文对比表格                                            │
│  │  ├── 差异总结                                                  │
│  │  ├── 矛盾发现标注                                              │
│  │  └── 操作入口：生成综述                                        │
│  │                                                                  │
│  L4: 综述报告页 (/report/:analysisId)                              │
│  │  ├── 综述内容（引言→现状→对比→趋势→文献）                      │
│  │  ├── 引用溯源链接                                              │
│  │  ├── Agent协同可视化面板                                       │
│  │  └── 操作入口：编辑 / 导出PDF / 导出Word                       │
│  │                                                                  │
│  L4: Agent可视化页 (/agent-flow/:analysisId)                       │
│  │  ├── Agent流程图（ECharts）                                     │
│  │  ├── Agent状态面板                                              │
│  │  ├── 中间结果展示                                              │
│  │  └── 耗时统计                                                  │
│  │                                                                  │
│  L2: 登录页 (/login)                                               │
│  L2: 注册页 (/register)                                            │
│  L2: 用户中心 (/user-center)                                       │
│  │  ├── 画像设置/编辑                                              │
│  │  ├── 历史记录                                                   │
│  │  ├── 收藏论文                                                   │
│  │  └── 历史搜索                                                   │
│  └─────────────────────────────────────────────────────────────────┘
```

### 4.2 页面导航路径

```
典型导航路径：

路径1：首次用户流程
  首页 → 注册 → 登录 → 画像设置 → 首页 → 输入主题 → 检索结果 → 论文详情 → 生成综述 → 报告页

路径2：论文分析流程
  首页 → 输入主题 → 检索结果 → 论文详情 → 智能分析 → 通俗解释（初级用户）

路径3：多论文对比流程
  首页 → 输入主题 → 检索结果 → 勾选2-5篇 → 对比分析 → 矛盾发现 → 生成综述

路径4：综述生成流程
  首页 → 输入主题 → 检索结果 → 选择论文范围 → 生成综述 → Agent可视化 → 报告页 → 导出

路径5：历史回看流程
  用户中心 → 历史记录 → 查看报告 → 引用溯源 → 返回论文详情
```

### 4.3 API路由导航

```
Java后端 API路由树：

/api
├── /users                          # 用户管理
│   ├── POST   /register            # 注册
│   ├── POST   /login               # 登录
│   ├── GET    /{userId}            # 查询用户信息
│   ├── PUT    /{userId}            # 更新用户信息
│   └── /{userId}/profile           # 用户画像
│       ├── GET                      # 获取画像
│       ├── POST                     # 创建画像
│       └── PUT                      # 更新画像
│
├── /papers                         # 论文管理
│   ├── GET    /                    # 论文列表（分页）
│   ├── GET    /{paperId}           # 论文详情
│   ├── GET    /search              # 论文搜索
│   ├── POST   /import              # 论文导入
│   └── /{paperId}/favorite         # 论文收藏
│       ├── POST                     # 添加收藏
│       └── DELETE                   # 取消收藏
│
├── /sessions                       # 会话管理
│   ├── POST   /                    # 创建会话
│   ├── GET    /                    # 会话列表
│   ├── GET    /{sessionId}         # 会话详情
│   ├── PUT    /{sessionId}/status  # 更新状态
│   └── DELETE /{sessionId}         # 删除会话
│
└── /analysis                       # 分析服务
    ├── POST   /paper               # 论文分析
    ├── POST   /compare             # 对比分析
    ├── POST   /report              # 综述生成
    ├── GET    /{analysisId}        # 分析结果
    ├── GET    /{analysisId}/status # 分析状态
    └── GET    /{analysisId}/agent-stream  # Agent状态流(SSE)

Python AI服务 API路由树：

/api
├── /agent                          # Agent服务
│   └── POST   /analyze             # 启动Agent工作流
│
├── /search                         # 检索服务
│   └── POST   /                    # 语义检索
│
├── /model                          # 模型服务
│   └── GET    /status              # 模型状态
│
└── /health                         # 健康检查
    └── GET    /                    # 服务状态
```

### 4.4 Agent工作流导航

```
LangGraph StateGraph 工作流路径：

START
  │
  ▼
coordinate（协调者Agent）
  │ 输入：{query, user_profile}
  │ 输出：sub_tasks[]
  ▼
retrieve（检索Agent）
  │ 输入：sub_tasks → 检索关键词
  │ 输出：search_results[]（Top10论文）
  ▼
analyze（分析Agent）
  │ 输入：search_results → 论文列表
  │ 输出：analysis_results[]（5维度分析）
  ▼
[条件分支]
  │
  ├── 论文数 >= 2 → compare（对比Agent）
  │                  │ 输入：analysis_results
  │                  │ 输出：compare_result（对比+矛盾）
  │                  ▼
  │              generate（生成Agent）
  │
  └── 论文数 < 2 → generate（生成Agent）
                     │ 输入：analysis_results + user_profile
                     │ 输出：report（个性化综述）
                     ▼
                 review（审核Agent）
                   │ 输入：report + original_papers
                   │ 输出：review_result（审核+修改建议）
                   ▼
                 [条件判断]
                   │
                   ├── 审核通过 → END
                   └── 审核不通过 → 返回generate重新生成（最多1次）

降级路径：
  单Agent失败 → 跳过，继续后续Agent
  多Agent失败 → 降级为单Agent模式（仅retrieve + generate）
```

---

## 5 内容结构层级

### 5.1 论文信息内容层级

```
论文信息层级（IC-2）：

L0: 论文概览（检索结果卡片）
├── 标题（title）
├── 作者（authors，截断展示）
├── 摘要（abstract，截断200字）
├── 关键词标签（keywords，最多5个）
├── 相关度评分（relevance_score）
└── 推荐理由（recommendation_reason）

L1: 论文详情（详情页）
├── L0全部信息（完整展示）
├── 完整摘要
├── 发表年份（year）
├── 发表会议/期刊（venue）
├── 引用数（citation_count）
├── PDF链接（pdf_url）
└── 作者完整列表

L2: 论文分析（分析结果）
├── 研究问题（research_question）
├── 核心方法（core_method）
├── 主要实验（main_experiments）
├── 核心结论（core_conclusion）
├── 局限性（limitations）
└── 通俗解释（plain_explanation，初级用户可见）

L3: 论文对比（对比分析）
├── 方法对比矩阵
├── 数据集对比矩阵
├── 性能对比矩阵
├── 结论对比矩阵
├── 差异总结文本
└── 矛盾点标注（含原文引用）

L4: 综述报告（最终输出）
├── 引言（introduction）
├── 研究现状（current_status）
├── 方法对比（method_comparison）
├── 研究趋势（research_trends）
├── 参考文献（references）
└── 引用标注（可溯源）
```

### 5.2 用户画像内容层级

```
用户画像信息层级（IC-1.2）：

维度1: 身份信息
├── 学历层次（education_level）
│   └── undergraduate / master / phd / faculty
├── 研究方向（research_field）
│   └── NLP / CV / RL / 多模态 / ...
└── 研究阶段（research_stage）
    └── 选题 / 调研 / 实验 / 写论文

维度2: 知识水平
├── 主题了解程度（knowledge_level）
│   └── beginner / intermediate / advanced / expert
└── 基础能力（foundation）
    └── 数学基础 / 编程基础

维度3: 需求偏好
├── 需求类型（need_type）
│   └── 入门了解 / 文献综述 / 方法对比 / 寻找创新点
├── 内容深度（preferred_style）
│   └── simple / balanced / technical
└── 输出格式偏好
    └── 通俗解释 / 学术报告 / 对比表格

映射到个性化策略：
┌────────────┬──────────────┬────────────────────────────────────┐
│ 画像维度   │ 策略参数     │ 影响范围                            │
├────────────┼──────────────┼────────────────────────────────────┤
│ knowledge  │ difficulty   │ Prompt术语密度、分析深度            │
│ level      │ = 1/2/3/4    │                                    │
├────────────┼──────────────┼────────────────────────────────────┤
│ preferred  │ style        │ 表达方式、段落长度、引用密度        │
│ style      │ = casual/    │                                    │
│            │ standard/    │                                    │
│            │ formal       │                                    │
├────────────┼──────────────┼────────────────────────────────────┤
│ research   │ focus        │ 检索排序权重、推荐策略              │
│ field      │ = 领域关键词 │                                    │
├────────────┼──────────────┼────────────────────────────────────┤
│ education  │ audience     │ 通俗解释是否展示、类比方式          │
│ level      │ = 入门/标准/ │                                    │
│            │ 专业/学术    │                                    │
└────────────┴──────────────┴────────────────────────────────────┘
```

### 5.3 Agent工作流状态内容层级

```
Agent状态信息层级（IC-5）：

L0: 流程级状态
├── 总进度百分比（0% - 100%）
├── 当前活跃Agent
├── 已完成Agent数 / 总Agent数
└── 总耗时

L1: Agent级状态（每个Agent）
├── Agent名称（coordinator/retriever/analyzer/comparer/generator/reviewer）
├── 运行状态（waiting/running/completed/failed）
├── 开始时间（started_at）
├── 完成时间（completed_at）
├── 执行耗时（duration_ms）
└── 进度百分比（progress，0.0 - 1.0）

L2: 中间结果级（每个Agent产出）
├── 协调者 → "分解为N个子任务"
├── 检索Agent → "找到N篇相关论文，筛选Top10"
├── 分析Agent → "已分析 M/N 篇"
├── 对比Agent → "正在对比第X组"
├── 生成Agent → "正在生成综述..."
└── 审核Agent → "审核通过/发现N处问题"

L3: 详细结果级（可展开查看）
├── 检索Agent → 论文ID列表 + 相关度分数
├── 分析Agent → 结构化分析JSON
├── 对比Agent → 对比表格 + 矛盾点
├── 生成Agent → 综述全文
└── 审核Agent → 审核详情 + 修改建议
```

---

## 6 用户任务流与信息流

### 6.1 核心任务流与信息映射

#### 任务流1：智能检索

```
用户任务：输入研究主题，获取相关论文列表

步骤    │ 用户操作          │ 系统信息流                                    │ 信息形式
────────┼───────────────────┼───────────────────────────────────────────────┼──────────────────────
1       │ 输入研究主题       │ 前端→Java: POST /api/papers/search            │ {q, yearFrom, sort}
2       │ 等待检索结果       │ Java→Python: POST /api/search                 │ {query, top_k, filters}
3       │ -                 │ Python: bge向量化 → Chroma检索 → RRF融合       │ 768维向量→Top10
4       │ -                 │ Python→Java: 检索结果JSON                      │ [{paper_id, score, ...}]
5       │ -                 │ Java: 补充论文元数据 → Redis缓存               │ PaperDTO[]
6       │ 查看论文列表       │ Java→前端: 论文卡片数据                        │ {total, items[]}
7       │ 筛选/排序         │ 前端→Java: 带筛选条件重新请求                  │ {q, filters, sort}
8       │ 点击论文卡片       │ 导航至论文详情页                               │ paperId
```

#### 任务流2：论文深度分析

```
用户任务：选择论文，获取AI结构化分析

步骤    │ 用户操作          │ 系统信息流                                    │ 信息形式
────────┼───────────────────┼───────────────────────────────────────────────┼──────────────────────
1       │ 点击"分析"按钮     │ 前端→Java: POST /api/analysis/paper           │ {paperId, userId}
2       │ -                 │ Java: 查询用户画像（Redis→MySQL回退）          │ UserProfile
3       │ -                 │ Java→Python: POST /api/agent/analyze          │ {paperId, userProfile}
4       │ 等待分析          │ SSE: Agent状态推送                             │ {agent, status, progress}
5       │ -                 │ Python: 分析Agent → LLM推理                    │ 5维度JSON
6       │ -                 │ Python→Java: 分析结果                          │ {analysisId, result}
7       │ -                 │ Java: 存储MySQL → 缓存Redis                    │ AnalysisResult
8       │ 查看分析卡片       │ Java→前端: 分析结果展示                        │ AnalysisCard数据
9       │ 查看通俗解释       │ 前端: 根据画像判断是否展示                      │ beginner可见
```

#### 任务流3：综述生成

```
用户任务：选择论文范围，生成个性化文献综述

步骤    │ 用户操作          │ 系统信息流                                    │ 信息形式
────────┼───────────────────┼───────────────────────────────────────────────┼──────────────────────
1       │ 选择论文范围       │ 前端: Pinia记录selectedPapers                  │ paperIds[]
2       │ 点击"生成综述"     │ 前端→Java: POST /api/analysis/report          │ {topic, paperIds, userId}
3       │ -                 │ Java: JWT鉴权 + 画像查询 + DTO组装             │ AgentRequestDTO
4       │ -                 │ Java→Python: POST /api/agent/analyze          │ 完整请求JSON
5       │ 观看Agent可视化    │ SSE: 各Agent状态实时推送                       │ agentStates[]
6       │ -                 │ Python: 6-Agent协同工作流执行                  │ StateGraph状态流转
7       │ -                 │ Python→Java: 最终结果 + Agent状态              │ {report, citations, ...}
8       │ -                 │ Java: 持久化 + 缓存                            │ MySQL + Redis
9       │ 查看综述报告       │ Java→前端: 综述内容渲染                        │ ReportView
10      │ 点击引用溯源       │ 前端→Java: GET /api/papers/{paperId}          │ 原文片段
11      │ 导出报告          │ 前端→Java: 导出请求                            │ PDF / Word
```

### 6.2 个性化信息流

```
用户画像驱动的信息差异化流转：

                         ┌─────────────────┐
                         │   用户画像 JSON  │
                         │                 │
                         │ education: ...  │
                         │ knowledge: ...  │
                         │ style: ...      │
                         │ field: ...      │
                         └────────┬────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │     个性化引擎               │
                    │  (personalization_service)  │
                    │                             │
                    │  1. 解析画像维度             │
                    │  2. 映射策略参数             │
                    │  3. 构建Prompt片段           │
                    └─────────────┬──────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
     ┌────────▼────────┐ ┌───────▼───────┐ ┌────────▼────────┐
     │  检索排序调整    │ │ Prompt个性化   │ │ 前端展示控制    │
     │                 │ │ 注入           │ │                 │
     │ field权重×0.5   │ │ 【重要】       │ │ beginner:       │
     │ 历史偏好×0.3   │ │ 用户身份：本科 │ │  → 显示通俗解释 │
     │ 热度×0.2       │ │ 知识水平：初级 │ │  → 类比展示     │
     │                 │ │ 请使用通俗语言 │ │ advanced:       │
     │                 │ │ 多用类比       │ │  → 隐藏通俗解释 │
     │                 │ │ 避免复杂公式   │ │  → 专业术语     │
     └─────────────────┘ └───────────────┘ └─────────────────┘
```

---

## 7 跨系统信息映射

### 7.1 前端 ↔ Java后端信息映射

```
┌──────────────────────────────────────────────────────────────────┐
│              前端状态 ↔ Java DTO 映射                             │
│                                                                  │
│  Pinia Store         │  Java DTO          │  API Endpoint        │
│  ────────────────────┼────────────────────┼─────────────────────│
│  userStore.token     │  -                 │  POST /login 返回    │
│  userStore.profile   │  UserProfileDTO    │  GET /profile 返回   │
│  paperStore.results  │  PaperDTO[]        │  GET /search 返回    │
│  paperStore.selected │  paperIds[]        │  POST /analysis 请求 │
│  sessionStore.current│  SessionDTO        │  POST /sessions 返回 │
│  agentStore.states   │  AgentStateDTO[]   │  SSE 推送            │
│  agentStore.flowData │  FlowDataDTO       │  SSE 推送            │
└──────────────────────────────────────────────────────────────────┘
```

### 7.2 Java后端 ↔ Python AI服务信息映射

```
┌──────────────────────────────────────────────────────────────────┐
│              Java DTO ↔ Python Schema 映射                        │
│                                                                  │
│  Java (Request)              │  Python (Request)                  │
│  ────────────────────────────┼──────────────────────────────────│
│  AgentRequestDTO             │  AnalyzeRequest(BaseModel)         │
│  ├── topic: String           │  ├── topic: str                    │
│  ├── paperIds: List<String>  │  ├── paper_ids: List[str]         │
│  ├── userId: String          │  ├── user_id: str                  │
│  └── profileContext: Map     │  └── user_profile: UserProfile     │
│       ├── educationLevel     │       ├── education_level: str     │
│       ├── knowledgeLevel     │       ├── knowledge_level: str     │
│       └── preferredStyle     │       └── preferred_style: str     │
│                                                                  │
│  Java (Response)             │  Python (Response)                 │
│  ────────────────────────────┼──────────────────────────────────│
│  AnalysisResponseDTO         │  AnalyzeResponse(BaseModel)        │
│  ├── analysisId: String      │  ├── analysis_id: str              │
│  ├── report: String          │  ├── report: str                   │
│  ├── citations: List<Map>    │  ├── citations: List[Citation]     │
│  ├── agentStates: List<Map>  │  ├── agent_states: Dict[str,State] │
│  └── status: String          │  └── status: str                   │
│                                                                  │
│  Java (SSE)                  │  Python (SSE)                      │
│  ────────────────────────────┼──────────────────────────────────│
│  AgentStateDTO               │  AgentStateUpdate                  │
│  ├── agentName: String       │  ├── agent_name: str               │
│  ├── status: String          │  ├── status: str                   │
│  ├── progress: Double        │  ├── progress: float               │
│  └── intermediateResult      │  └── intermediate_result: str      │
└──────────────────────────────────────────────────────────────────┘
```

### 7.3 Python AI服务 ↔ 数据层信息映射

```
┌──────────────────────────────────────────────────────────────────┐
│              Python Service ↔ 数据存储 映射                       │
│                                                                  │
│  服务层                      │  存储层                            │
│  ────────────────────────────┼──────────────────────────────────│
│  EmbeddingService            │  ChromaDB                          │
│  ├── encode(text) → vector   │  ├── papers collection             │
│  ├── encode_batch(texts)     │  ├── 768维向量                     │
│  └── 支持本地/API双模式      │  └── cosine similarity             │
│                                                                  │
│  VectorStoreService          │  ChromaDB                          │
│  ├── add_documents(docs)     │  ├── collection.add(embeddings,   │
│  ├── similarity_search(q,k)  │  │   metadatas, ids)              │
│  └── hybrid_search(q,k)      │  ├── collection.query(query_emb)  │
│                              │  └── + MySQL全文索引 → RRF融合     │
│                                                                  │
│  LLMService                  │  模型服务层                        │
│  ├── generate(prompt)        │  ├── 方案A: 软件方模型API          │
│  ├── generate_stream(prompt) │  ├── 方案B: 外接API                │
│  └── auto_degradation()      │  └── 方案C: 本地Qwen2             │
│                                                                  │
│  PersonalizationService      │  Redis + MySQL                     │
│  ├── parse_profile(json)     │  ├── Redis: user:profile:{id}      │
│  ├── build_prompt(profile)   │  └── MySQL: user_profiles表        │
│  └── adapt_difficulty(level) │                                    │
└──────────────────────────────────────────────────────────────────┘
```

### 7.4 信息转换与一致性保障

```
信息一致性保障机制：

1. 字段命名转换规范
   Java (camelCase)     Python (snake_case)
   ────────────────     ──────────────────
   educationLevel   →   education_level
   knowledgeLevel   →   knowledge_level
   preferredStyle   →   preferred_style
   paperId          →   paper_id
   analysisId       →   analysis_id
   
   转换层：Java DTO ↔ @JsonProperty / Python Pydantic field alias

2. 数据类型一致性
   Java                 Python               一致性保障
   ────────────         ────────             ──────────
   String               str                  JSON序列化/反序列化
   Integer              int                  JSON数值类型
   Double               float                JSON数值类型
   List<String>         List[str]            JSON数组
   Map<String,Object>   Dict[str,Any]        JSON对象
   ENUM                 str(Literal)         字符串枚举值一致

3. 时序一致性
   写操作：先更新MySQL → 再删除Redis缓存（Cache-Aside）
   读操作：先读Redis → 未命中读MySQL → 回填Redis
   SSE推送：Python → Java → 前端，单向推送不回传

4. 枚举值一致性映射
   状态枚举        Java              Python            前端
   ────────        ────              ──────            ────
   画像知识水平    beginner/...      beginner/...      初级/...
   画像偏好风格    simple/...        simple/...        通俗/...
   会话状态        active/...        -                 进行中/...
   分析状态        pending/...       pending/...       等待中/...
   Agent状态       -                 waiting/...       等待/执行/完成/失败
```

---

## 8 数据实体与关系架构

### 8.1 核心数据实体关系

```
┌─────────────────────────────────────────────────────────────────────┐
│                      数据实体关系图                                   │
│                                                                     │
│  ┌──────────┐ 1    ∞ ┌──────────────┐                              │
│  │  users   │───────→│ user_profiles │                              │
│  │──────────│        │──────────────│                              │
│  │ id (PK)  │        │ id (PK)      │                              │
│  │ user_id  │        │ user_id (FK) │                              │
│  │ username │        │ education_lv │                              │
│  │ email    │        │ research_fld │                              │
│  │ password │        │ knowledge_lv │                              │
│  │ created  │        │ preferred_st │                              │
│  └────┬─────┘        │ profile_data │                              │
│       │              └──────────────┘                              │
│       │                                                            │
│       │ 1    ∞ ┌──────────────┐     ∞ ┌─────────────────┐         │
│       ├───────→│  sessions    │──────→│analysis_results │         │
│       │        │──────────────│       │─────────────────│         │
│       │        │ id (PK)      │       │ id (PK)         │         │
│       │        │ session_id   │       │ analysis_id     │         │
│       │        │ user_id (FK) │       │ session_id (FK) │         │
│       │        │ topic        │       │ type            │         │
│       │        │ status       │       │ result (JSON)   │         │
│       │        │ created_at   │       │ status          │         │
│       │        └──────────────┘       │ created_at      │         │
│       │                               └─────────────────┘         │
│       │ 1    ∞ ┌──────────────┐                                   │
│       ├───────→│paper_favorites│                                   │
│       │        │──────────────│                                    │
│       │        │ user_id (FK) │                                    │
│       │        │ paper_id(FK) │                                    │
│       │        └──────┬───────┘                                    │
│       │               │                                            │
│  ┌────▼─────┐ 1    ∞ ┌┘                                           │
│  │  papers  │←───────┘                                            │
│  │──────────│                                                      │
│  │ id (PK)  │                                                      │
│  │ paper_id │←──── ChromaDB: papers collection                     │
│  │ title    │      (embedding_id 关联)                              │
│  │ authors  │                                                      │
│  │ abstract │      Redis: 缓存热点论文                              │
│  │ year     │                                                      │
│  │ venue    │                                                      │
│  │ keywords │                                                      │
│  │ citations│                                                      │
│  │ pdf_url  │                                                      │
│  └──────────┘                                                      │
│                                                                     │
│  ChromaDB (向量空间)                                                │
│  ┌────────────────────────────────────┐                            │
│  │ papers collection                   │                            │
│  │ ├── document: 论文分块文本          │                            │
│  │ ├── embedding: 768维向量            │                            │
│  │ └── metadata: {paper_id, title,    │                            │
│  │       year, venue, citation_count, │                            │
│  │       chunk_index, chunk_type}     │                            │
│  └────────────────────────────────────┘                            │
│                                                                     │
│  Neo4j (知识图谱空间)                                                │
│  ┌────────────────────────────────────┐                            │
│  │ 节点类型：                           │                            │
│  │ ├── Paper (paper_id, title, year)  │                            │
│  │ ├── Method (name, category)        │                            │
│  │ ├── Concept (name, domain)         │                            │
│  │ └── Author (name, affiliation)     │                            │
│  │ 关系类型：                           │                            │
│  │ ├── USES (Paper→Method)            │                            │
│  │ ├── IMPROVES (Method→Method)       │                            │
│  │ ├── CITES (Paper→Paper)            │                            │
│  │ ├── RELATED_TO (Concept↔Concept)   │                            │
│  │ └── AUTHORED_BY (Paper→Author)     │                            │
│  │ 用途：图谱推理增强三路RRF融合          │                            │
│  └────────────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

### 8.2 数据分布与索引架构

```
┌──────────────────────────────────────────────────────────────────┐
│                     数据分布架构                                   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  MySQL 8.0 — 结构化数据持久化                             │   │
│  │                                                          │   │
│  │  表           │ 索引                    │ 信息量          │   │
│  │  ─────────────┼────────────────────────┼────────────────│   │
│  │  papers       │ PK(id), UQ(paper_id),  │ 200+篇         │   │
│  │               │ IDX(year), IDX(venue), │ ~50MB          │   │
│  │               │ IDX(citation_count),   │                │   │
│  │               │ FT(title,abstract)      │                │   │
│  │  users        │ PK(id), UQ(user_id)    │ +10/月         │   │
│  │  user_profiles│ PK(id), FK(user_id)    │ <1MB           │   │
│  │  sessions     │ PK(id), UQ(session_id),│ +50/月         │   │
│  │               │ FK(user_id)            │                │   │
│  │  analysis_    │ PK(id), UQ(analysis_id)│ +100/月        │   │
│  │  results      │ FK(session_id)         │ ~50MB          │   │
│  │  paper_       │ PK(id), UQ(user,paper) │ 按收藏量       │   │
│  │  favorites    │ FK(user_id,paper_id)   │                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Redis 7.0 — 缓存与实时状态                               │   │
│  │                                                          │   │
│  │  Key模式                    │ TTL     │ 数据结构          │   │
│  │  ──────────────────────────┼─────────┼─────────────────│   │
│  │  user:profile:{userId}      │ 1小时   │ String(JSON)     │   │
│  │  user:info:{userId}         │ 1小时   │ String(JSON)     │   │
│  │  paper:detail:{paperId}     │ 30分钟  │ String(JSON)     │   │
│  │  search:result:{queryHash}  │ 10分钟  │ String(JSON)     │   │
│  │  analysis:result:{analysisId}│ 30分钟 │ String(JSON)     │   │
│  │  session:state:{sessionId}  │ 2小时   │ String(JSON)     │   │
│  │  agent:state:{analysisId}   │ 5分钟   │ Hash(字段级)     │   │
│  │  auth:token:blacklist:{hash}│ Token期 │ String           │   │
│  │  ai:provider:status         │ 5分钟   │ String           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  ChromaDB 0.5+ — 向量检索                                 │   │
│  │                                                          │   │
│  │  Collection: papers                                        │   │
│  │  ├── 向量维度：768（bge-large-zh-v1.5）                    │   │
│  │  ├── 相似度：cosine                                        │   │
│  │  ├── HNSW参数：M=16, construction_ef=200                  │   │
│  │  ├── 初始文档：200+篇论文分块                              │   │
│  │  └── 存储大小：~600MB                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 8.3 JSON字段结构定义

```
核心JSON字段结构：

1. papers.authors (JSON Array)
   ["Wang, L.", "Chen, X.", "Zhang, Y."]

2. papers.keywords (JSON Array)
   ["multi-agent", "cooperation", "LLM", "survey"]

3. user_profiles.profile_data (JSON Object)
   {
     "research_stage": "调研",
     "math_foundation": "中",
     "coding_foundation": "强",
     "need_type": "文献综述",
     "output_format": "学术报告"
   }

4. analysis_results.result (JSON Object，按type分化)
   
   type=paper_analysis:
   {
     "research_question": "...",
     "core_method": "...",
     "main_experiments": "...",
     "core_conclusion": "...",
     "limitations": "...",
     "plain_explanation": "..."  // 初级用户可见
   }
   
   type=compare:
   {
     "comparison_table": {
       "dimensions": ["架构模式", "编程语言", "支持工具"],
       "papers": {
         "paper_001": ["图结构", "Python", "多种"],
         "paper_002": ["对话式", "Python", "多种"]
       }
     },
     "difference_summary": "...",
     "contradictions": [
       {
         "dimension": "性能对比",
         "paper_a_claim": "...",
         "paper_b_claim": "...",
         "explanation": "..."
       }
     ]
   }
   
   type=report:
   {
     "introduction": "...",
     "current_status": "...",
     "method_comparison": "...",
     "research_trends": "...",
     "references": ["[1] ...", "[2] ..."],
     "citations": [
       {"ref_id": 1, "paper_id": "p001", "original_text": "..."}
     ]
   }

5. Agent State (Redis Hash)
   {
     "coordinator_status": "completed",
     "coordinator_started_at": "2026-05-23T10:00:00",
     "coordinator_duration_ms": "2000",
     "coordinator_result": "分解为4个子任务",
     "retriever_status": "running",
     "retriever_progress": "0.6"
   }
```

---

## 9 标签与命名体系

### 9.1 功能编号体系

```
功能编号规范：F[模块].[子模块].[序号]

模块编号：
  F1  - 前端模块
  F2  - Java后端模块
  F3  - Python AI服务模块
  F4  - 数据模块
  F5  - 模型模块

子模块编号：
  F1.1 - 用户界面子模块        F2.1 - 用户管理子模块
  F1.2 - 论文检索子模块        F2.2 - 论文管理子模块
  F1.3 - 论文分析子模块        F2.3 - 会话管理子模块
  F1.4 - 综述生成子模块        F2.4 - 分析服务子模块
  F1.5 - Agent可视化子模块     F2.5 - AI服务调用子模块
                                F2.6 - 缓存管理子模块

  F3.1 - 多Agent协同引擎      F4.1 - MySQL数据子模块
  F3.2 - RAG检索子模块         F4.2 - Redis缓存子模块
  F3.3 - LLM服务子模块         F4.3 - Chroma向量库子模块
  F3.4 - 个性化引擎子模块      F4.4 - 论文数据采集子模块
  F3.5 - API服务子模块

  F5.1 - 大语言模型子模块
  F5.2 - Embedding模型子模块

示例：
  F1.2.3 - 前端模块.论文检索子模块.结果展示
  F3.1.5 - Python AI.Agent协同.生成Agent
  F2.4.3 - Java后端.分析服务.综述生成请求
```

### 9.2 代码命名规范

```
┌──────────────────────────────────────────────────────────────────┐
│                    代码命名规范                                    │
│                                                                  │
│  层级          │ Java                        │ Python             │
│  ─────────────┼─────────────────────────────┼───────────────────│
│  类名          │ PascalCase                  │ PascalCase         │
│               │ UserService, PaperDTO       │ LLMService,        │
│               │                             │ EmbeddingService   │
│  方法名        │ camelCase                   │ snake_case         │
│               │ getUserProfile()            │ get_user_profile() │
│               │ searchPapers()              │ search_papers()    │
│  变量名        │ camelCase                   │ snake_case         │
│               │ userId, paperList           │ user_id, paper_list│
│  常量名        │ UPPER_SNAKE_CASE            │ UPPER_SNAKE_CASE   │
│               │ MAX_RETRY_COUNT             │ MAX_RETRY_COUNT    │
│  包/模块名     │ com.literatureassistant.xxx │ app.agents         │
│               │                             │ app.services       │
│  文件名        │ PascalCase.java             │ snake_case.py      │
│               │ UserController.java         │ llm_service.py     │
│  配置键        │ kebab-case                  │ UPPER_SNAKE_CASE   │
│               │ spring.datasource.url       │ LLM_API_KEY        │
│  API路径       │ kebab-case                  │ kebab-case         │
│               │ /api/analysis/report        │ /api/agent/analyze │
└──────────────────────────────────────────────────────────────────┘
```

### 9.3 Redis键命名规范

```
Redis Key命名规范：{域}:{操作}:{标识符}

域（domain）：
  user     - 用户相关
  search   - 检索相关
  analysis - 分析相关
  session  - 会话相关
  agent    - Agent相关
  auth     - 认证相关

操作（operation）：
  profile   - 画像
  result    - 结果
  state     - 状态
  blacklist - 黑名单

标识符（identifier）：
  {userId}     - 用户ID
  {queryHash}  - 查询参数哈希
  {analysisId} - 分析ID
  {sessionId}  - 会话ID
  {tokenHash}  - Token哈希

完整示例：
  user:profile:usr_001
  search:result:a1b2c3d4
  analysis:result:anl_001
  session:state:ses_001
  agent:state:anl_001
  auth:token:blacklist:eyJhbG_hash
```

### 9.4 API响应标签体系

```
统一API响应结构标签：

成功响应：
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "timestamp": "2026-05-23T10:00:00Z"
}

错误响应：
{
  "code": 401/403/404/409/500,
  "message": "错误描述",
  "error": "ERROR_CODE",
  "details": { ... },
  "timestamp": "2026-05-23T10:00:00Z"
}

分页响应标签：
{
  "code": 200,
  "data": {
    "items": [ ... ],
    "pagination": {
      "page": 1,
      "size": 10,
      "total": 85,
      "totalPages": 9
    }
  }
}

Agent状态标签：
{
  "agent_name": "retriever",
  "status": "running",       // waiting/running/completed/failed
  "progress": 0.6,           // 0.0 - 1.0
  "started_at": "2026-05-23T10:00:02",
  "intermediate_result": "找到15篇相关论文"
}
```

---

## 10 可检索性设计

### 10.1 检索架构

```
┌──────────────────────────────────────────────────────────────────┐
│                     混合检索架构                                   │
│                                                                  │
│  用户查询 "Multi-Agent协同决策"                                    │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────┐                                │
│  │     bge-large-zh-v1.5       │                                │
│  │     文本 → 768维向量         │                                │
│  └──────────┬──────────────────┘                                │
│             │                                                    │
│     ┌───────┼───────┐                                           │
│     │       │       │                                           │
│     ▼       ▼       ▼                                           │
│  ┌──────┐┌──────┐┌──────┐    三路并行检索（ADR-011）           │
│  │路径A: ││路径B: ││路径C: │                                   │
│  │Chroma││MySQL ││Neo4j │                                    │
│  │语义  ││全文  ││图谱  │                                    │
│  │检索  ││索引  ││推理  │                                    │
│  │Top20││Top20││Top20│                                    │
│  │相似度││相关度││图谱分│                                    │
│  └──┬───┘└──┬───┘└──┬───┘                                    │
│     │       │       │                                          │
│     └───────┼───────┘                                          │
│             ▼                                                   │
│  ┌───────────────────────┐                                      │
│  │  三路RRF融合           │                                      │
│  │  Reciprocal Rank       │                                      │
│  │  Fusion                │                                      │
│  │  score = Σ 1/(k+rank_i)│                                      │
│  │  k=60                  │                                      │
│  │  语义+关键词+图谱      │                                      │
│  └──────────┬────────────┘                                      │
│             │                                                    │
│             ▼                                                    │
│  ┌───────────────────────┐                                      │
│  │  重排序（可选）         │                                      │
│  │  Cross-Encoder /       │                                      │
│  │  规则方法               │                                      │
│  └──────────┬────────────┘                                      │
│             │                                                    │
│             ▼                                                    │
│  个性化排序调整                                                   │
│  score_final = score_rrf × 0.5                                  │
│              + field_match × 0.3                                │
│              + popularity × 0.2                                 │
│             │                                                    │
│             ▼                                                    │
│  Top10 检索结果 + 推荐理由                                       │
└──────────────────────────────────────────────────────────────────┘
```

### 10.2 检索参数设计

```
检索参数配置：

参数                    │ 默认值    │ 调优范围         │ 影响
────────────────────────┼──────────┼─────────────────┼─────────────
top_k                   │ 10       │ 5-20            │ 返回结果数量
similarity_threshold    │ 0.7      │ 0.5-0.9         │ 最低相似度
chunk_size              │ 500      │ 300-1000        │ 文档分块大小
chunk_overlap           │ 50       │ 0-100           │ 分块重叠
rrf_k                   │ 60       │ 10-100          │ RRF融合参数
personalization_weight  │ 0.5/0.3/0.2 │ 可调整       │ 个性化排序权重

索引类型：
  ChromaDB: HNSW (M=16, construction_ef=200)
  MySQL: FULLTEXT (title, abstract) — ngram parser for Chinese
```

### 10.3 前端搜索与筛选设计

```
前端搜索能力：

1. 主题搜索
   ├── 输入方式：自然语言文本框
   ├── 历史记录：最近10条（localStorage）
   └── 搜索触发：回车 / 点击搜索按钮

2. 筛选面板
   ├── 年份范围：滑块选择器（2015-2026）
   ├── 引用数范围：输入框（最小值-最大值）
   ├── 发表会议/期刊：下拉多选
   └── 关键词标签：点击标签筛选

3. 排序选项
   ├── 相关度排序（默认）
   ├── 发表时间排序（新→旧）
   └── 引用数排序（高→低）

4. 分页展示
   ├── 每页10篇
   ├── 页码导航
   └── 总结果数展示

5. 结果卡片信息
   ├── 标题（完整展示）
   ├── 作者（截断展示）
   ├── 摘要（截断200字）
   ├── 关键词标签（最多5个）
   ├── 相关度评分（百分比）
   └── 推荐理由（一句话）
```

---

## 11 信息安全与权限控制

### 11.1 信息访问控制矩阵

```
┌──────────────────────────────────────────────────────────────────┐
│                    信息访问控制矩阵                                │
│                                                                  │
│  信息类           │ 未登录用户 │ 已登录用户 │ 数据所有者 │ 系统  │
│  ─────────────────┼──────────┼──────────┼──────────┼───────│
│  IC-1.1 身份信息  │    -      │  自身     │  完整    │ 完整  │
│  IC-1.2 画像信息  │    -      │  自身     │  完整    │ 完整  │
│  IC-1.3 行为信息  │    -      │  自身     │  完整    │ 完整  │
│  IC-2.1 论文元数据│   只读    │  只读     │  只读    │ 读写  │
│  IC-2.2 内容信息  │   只读    │  只读     │  只读    │ 读写  │
│  IC-2.4 向量信息  │    -      │   -       │   -      │ 读写  │
│  IC-3 分析信息    │    -      │  自身     │  完整    │ 完整  │
│  IC-4 会话信息    │    -      │  自身     │  完整    │ 完整  │
│  IC-5 Agent信息   │    -      │  自身会话 │  自身会话│ 完整  │
│  IC-6 系统信息    │  健康检查 │  部分状态 │  部分状态│ 完整  │
└──────────────────────────────────────────────────────────────────┘

数据隔离规则：
1. 用户只能访问自己的会话（sessions WHERE user_id = current_user）
2. 用户只能访问自己会话下的分析结果（analysis_results JOIN sessions）
3. 论文数据全局共享，无数据隔离
4. API密钥仅系统可读写，前端不可见
```

### 11.2 敏感信息保护

```
敏感信息保护策略：

| 信息项          │ 保护措施                          │ 存储位置       │
|----------------|----------------------------------|---------------|
| 用户密码        │ BCrypt哈希存储，盐值随机           │ MySQL only    │
| JWT Token      │ Bearer传输，Redis黑名单机制        │ 客户端+Redis  │
| API密钥         │ .env环境变量注入，不硬编码          │ .env文件      │
| 用户邮箱        │ 不在前端展示，仅后端使用            │ MySQL only    │
| 分析结果        │ 用户数据隔离，JWT鉴权              │ MySQL+Redis   │
| Agent状态       │ 会话级隔离，仅所属用户可访问        │ Redis         |

信息标注规范：
  - AI生成内容统一标注："AI生成，仅供参考"
  - 引用内容标注来源论文ID
  - 矛盾发现标注原文出处
```

---

## 12 文档生态系统

### 12.1 项目文档信息架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                     项目文档生态系统                                  │
│                                                                     │
│  docs/                                                              │
│  ├── XH-202630-科研文献助手/          ← 原始项目文档（按阶段组织）    │
│  │   ├── README.md                   ← 文档导航中心                 │
│  │   ├── 01-策划阶段/                                                │
│  │   │   ├── 01-项目策划案.md         ← 项目整体规划                 │
│  │   │   └── 02-需求规格说明书.md     ← 功能/非功能需求              │
│  │   ├── 02-设计阶段/                                                │
│  │   │   ├── 03-系统架构设计文档.md   ← 技术架构设计                 │
│  │   │   └── 04-模块清单.md           ← 模块功能清单                 │
│  │   ├── 03-开发阶段/                                                │
│  │   │   ├── 05-功能实现顺序.md       ← 14周开发计划                 │
│  │   │   └── 06-技术栈.md             ← 技术选型说明                 │
│  │   ├── 04-学习资料/                                                │
│  │   │   └── 07-零基础学习路线图.md   ← 学习路径规划                 │
│  │   └── 05-风险管理/                                                │
│  │       ├── 08-潜在风险清单.md       ← 风险识别与应对               │
│  │       └── 09-项目方案.md           ← 系统方案设计                 │
│  │                                                                   │
│  ├── backend/                        ← 架构文档（按子系统组织）      │
│  │   └── Java后端模块系统架构文档.md   ← Java后端17章               │
│  ├── ai-service/                                                     │
│  │   └── AI服务模块系统架构文档.md     ← Python AI服务19章           │
│  ├── frontend/                                                       │
│  │   └── 前端模块系统架构文档.md       ← 前端17章                    │
│  ├── database/                                                       │
│  │   └── 数据库设计文档.md             ← 数据库10章                  │
│  │                                                                   │
│  ├── 项目里程碑文档.md                ← 里程碑12章                   │
│  └── 信息架构文档(IA).md              ← 本文档                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 12.2 文档信息流向与依赖

```
文档依赖关系图：

  策划层                          设计层
  ┌──────────────┐              ┌──────────────────┐
  │ 01-项目策划案 │─────────────→│03-系统架构设计文档│
  └──────┬───────┘              └────────┬─────────┘
         │                               │
         ▼                               ▼
  ┌──────────────┐              ┌──────────────────┐
  │02-需求规格   │─────────────→│04-模块清单       │
  │  说明书      │              └────────┬─────────┘
  └──────────────┘                       │
                                         ▼
  开发层                        ┌──────────────────┐
  ┌──────────────┐             │05-功能实现顺序   │
  │06-技术栈     │────────────→│                  │
  └──────────────┘             └────────┬─────────┘
                                        │
  风险层                                 │
  ┌──────────────┐                      │
  │08-潜在风险   │──────────────────────→│
  │  清单        │                      │
  └──────┬───────┘                      ▼
         │                     ┌──────────────────┐
  ┌──────▼───────┐             │ 项目里程碑文档    │
  │09-项目方案   │────────────→│                  │
  └──────────────┘             └──────────────────┘
                                        │
  架构文档层（由设计层衍生）              │
  ┌──────────────┐ ┌──────────────┐    │
  │Java后端架构  │ │AI服务架构    │    │
  │文档          │ │文档          │    │
  └──────┬───────┘ └──────┬───────┘    │
         │                │             │
  ┌──────▼───────┐ ┌──────▼───────┐    │
  │前端架构文档  │ │数据库设计文档│    │
  └──────┬───────┘ └──────┬───────┘    │
         │                │             │
         └────────┬───────┘             │
                  ▼                     ▼
         ┌──────────────────────────────────────┐
         │       信息架构文档（IA）              │
         │  汇聚所有文档的信息结构定义            │
         └──────────────────────────────────────┘
```

### 12.3 文档命名与版本规范

```
文档命名规范：

原始文档（阶段编号）：
  [序号]-[文档名称].md
  示例：01-项目策划案.md, 02-需求规格说明书.md

架构文档（子系统命名）：
  [子系统名称]模块系统架构文档.md
  示例：Java后端模块系统架构文档.md

专项文档（功能命名）：
  [文档类型].md 或 [文档类型]([缩写]).md
  示例：项目里程碑文档.md, 信息架构文档(IA).md

版本控制规则：
  小修改（错别字、格式）→ 更新文档内版本号 v1.0 → v1.1
  大修改（内容重构、新增章节）→ v1.0 → v2.0
  在文档顶部修订历史表记录变更
```

---

## 13 IA 治理与演进

### 13.1 信息架构治理规则

```
IA治理原则：

1. 变更审批
   ├── P0信息类（用户、论文、分析）变更 → 需项目负责人审批
   ├── P1信息类（缓存、Agent状态）变更 → 开发团队协商
   └── P2信息类（系统运行时）变更 → 开发者自主决定

2. 一致性检查
   ├── 新增API接口 → 必须更新本文档第4.3节
   ├── 新增数据字段 → 必须更新本文档第8节
   ├── 新增Agent → 必须更新本文档第4.4节
   └── 修改枚举值 → 必须更新本文档第7.4节

3. 版本同步
   ├── 需求变更 → 同步更新IA分类体系和内容层级
   ├── 架构变更 → 同步更新跨系统映射
   └── 数据模型变更 → 同步更新数据实体关系

4. 定期审查
   ├── 每个里程碑（M1-M6）完成后进行IA审查
   ├── 检查信息分类是否覆盖新增功能
   └── 验证跨系统映射的一致性
```

### 13.2 IA演进路线

```
IA演进与项目里程碑对齐：

M1（Week 2）：基础设施就绪
├── 确定数据表结构（IC-2, IC-4）
├── 确定向量库Schema（IC-2.4）
├── 确定Redis缓存键设计（缓存信息类）
└── IA基线版本定稿

M2（Week 4）：单Agent可用
├── 验证Agent信息流（IC-5）
├── 验证Prompt模板信息结构
└── 更新Agent状态信息层级

M3（Week 6）：前后端联调
├── 验证前端↔Java信息映射
├── 验证Java↔Python信息映射
├── 验证SSE推送信息结构
└── 修正跨系统字段命名不一致

M4（Week 8）：多Agent协同
├── 验证StateGraph状态流转信息
├── 验证条件分支信息传递
├── 验证降级路径信息完整性
└── 更新Agent可视化信息层级

M5（Week 10）：功能完整
├── 全面审查信息分类覆盖度
├── 验证个性化信息流端到端
├── 检查所有枚举值一致性
└── IA文档v1.0正式发布

M6（Week 14）：交付就绪
├── IA文档最终审查
├── 确保文档与实现一致
└── 归档IA决策记录
```

### 13.3 IA度量指标

```
信息架构质量度量：

| 维度           | 度量指标                          | 目标值    |
|---------------|----------------------------------|----------|
| 完整性         | 功能点→信息类覆盖率               | 100%     |
| 一致性         | 跨系统枚举值不一致数              | 0        |
| 可追溯性       | AI生成内容→原始论文可溯源率        | > 90%    |
| 可检索性       | Top10检索结果相关性               | > 80%    |
| 个性化差异度   | 不同画像用户输出文本差异度          | > 60%    |
| 导航效率       | 核心任务平均点击次数               | ≤ 5次    |
| 缓存命中率     | 热点数据Redis命中率                | > 50%    |
| 信息延迟       | SSE推送→前端展示延迟               | < 500ms  |
```

---

> **文档维护**：当系统功能、数据模型或跨系统接口发生变更时，需同步更新本文档对应章节  
> **变更控制**：IC-1至IC-3信息类变更需项目负责人审批，其余变更需开发团队协商  
> **下次审查**：M1里程碑完成时进行首次IA审查
