# 06 — API契约

> 加载时机：编写 API 接口、跨服务调用、前后端联调时加载。
> 关联文件：[07-standards.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/agents/07-standards.md) | [05-database.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/agents/05-database.md)

---

## 1 Java后端API

```
/api/users/register          POST   注册
/api/users/login             POST   登录
/api/users/{userId}          GET    查询用户
/api/users/{userId}/profile  GET/POST/PUT  画像CRUD
/api/papers                  GET    论文列表(分页)
/api/papers/{paperId}        GET    论文详情
/api/papers/search           GET    论文搜索
/api/papers/{paperId}/favorite  POST/DELETE  收藏/取消
/api/sessions                POST/GET  创建/列表会话
/api/sessions/{sessionId}    GET/DELETE  详情/删除
/api/analysis/paper          POST   论文分析
/api/analysis/compare        POST   对比分析
/api/analysis/report         POST   综述生成
/api/analysis/{analysisId}   GET    分析结果
/api/analysis/{analysisId}/status  GET    分析状态
/api/analysis/{analysisId}/agent-stream  GET(SSE)  Agent状态流
```

---

## 2 Python AI服务API

```
/api/agent/analyze           POST   启动Agent工作流
/api/search                  POST   语义检索
/api/model/status            GET    模型状态
/health                      GET    健康检查
```

---

## 3 统一响应格式

```json
{"code": 200, "message": "success", "data": {...}, "timestamp": "..."}
```

---

## 4 Java→Python请求契约

```json
{
  "topic": "Multi-Agent协同决策",
  "paper_ids": ["arxiv_2024_001"],
  "user_id": "usr_001",
  "user_profile": {
    "education_level": "master",
    "research_field": "NLP",
    "knowledge_level": "intermediate",
    "preferred_style": "balanced"
  }
}
```

---

## 5 SSE事件格式

```
event: agent_state_update
data: {"agent_name": "retriever", "status": "running", "progress": 0.6, "intermediate_result": "找到15篇相关论文"}
```
