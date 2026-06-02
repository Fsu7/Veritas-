# 05 — 数据库设计

> 加载时机：创建/修改数据库表、配置缓存策略、设置向量存储时加载。
> 关联文件：[03-agent-system.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/agents/03-agent-system.md)

---

## 1 MySQL核心表

| 表名 | 用途 | 核心字段 | 索引 |
|------|------|---------|------|
| `users` | 用户账号 | user_id(UQ), username, email, password_hash | PK(id), UQ(user_id) |
| `user_profiles` | 用户画像 | user_id(FK), education_level(ENUM), research_field, knowledge_level(ENUM), preferred_style(ENUM), profile_data(JSON) | PK(id), FK(user_id) |
| `papers` | 论文元数据 | paper_id(UQ), title, authors(JSON), abstract(TEXT), year, venue, keywords(JSON), citation_count | PK(id), UQ(paper_id), IDX(year/venue/citation), FULLTEXT(title,abstract) |
| `sessions` | 分析会话 | session_id(UQ), user_id(FK), topic, status(ENUM:active/completed/expired) | PK(id), UQ(session_id), IDX(user_id/status) |
| `analysis_results` | 分析结果 | analysis_id(UQ), session_id(FK), type(ENUM:paper_analysis/compare/report), result(JSON), status(ENUM:pending/processing/completed/failed) | PK(id), UQ(analysis_id), IDX(session_id/status/type) |
| `paper_favorites` | 论文收藏 | user_id(FK), paper_id(FK) | PK(id), UQ(user_id,paper_id) |

**枚举值**:
- education_level: `undergraduate` / `master` / `phd` / `faculty`
- knowledge_level: `beginner` / `intermediate` / `advanced` / `expert`
- preferred_style: `simple` / `balanced` / `technical`
- session status: `active` / `completed` / `expired`
- analysis type: `paper_analysis` / `compare` / `report`
- analysis status: `pending` / `processing` / `completed` / `failed`

---

## 2 Redis缓存Key

| Key模式 | TTL | 数据结构 | 用途 |
|---------|-----|---------|------|
| `user:profile:{userId}` | 1小时 | String(JSON) | 用户画像缓存 |
| `user:info:{userId}` | 1小时 | String(JSON) | 用户信息缓存 |
| `paper:detail:{paperId}` | 30分钟 | String(JSON) | 论文详情缓存 |
| `paper:list:{queryHash}` | 10分钟 | String(JSON) | 论文列表缓存 |
| `search:result:{queryHash}` | 10分钟 | String(JSON) | 检索结果缓存 |
| `analysis:result:{analysisId}` | 30分钟 | String(JSON) | 分析结果缓存 |
| `session:state:{sessionId}` | 2小时 | String(JSON) | 会话状态缓存 |
| `agent:state:{analysisId}` | 5分钟 | Hash | Agent执行状态 |
| `auth:blacklist:{tokenHash}` | Token有效期 | String | JWT黑名单 |
| `ai:provider:status` | 5分钟 | String | AI降级状态 |

**缓存策略**: Cache-Aside模式 — 写操作先更新MySQL再删除Redis缓存；读操作先查Redis，未命中查MySQL后回填。

---

## 3 ChromaDB

- Collection: `papers`
- 向量维度: 1024 (BAAI/bge-m3 / text-embedding-v4)
- 相似度: cosine
- HNSW参数: M=16, construction_ef=200
- 元数据: paper_id, title, year, venue, citation_count, chunk_index, chunk_type
- 分块: 500-1000字/块，重叠50-100字

---

## 4 Neo4j知识图谱（计划 M4+）

- 节点: Paper / Method / Concept / Author
- 关系: USES / IMPROVES / RELATED_TO / AUTHORED_BY / CITES / BELONGS_TO
- 端口: 7687(Bolt) / 7474(HTTP)
- **状态**: 当前 docker-compose 未包含，计划在 M4 阶段集成
