# 04 — 个性化引擎

> 加载时机：修改个性化逻辑、用户画像相关功能开发时加载。
> 关联文件：[03-agent-system.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/agents/03-agent-system.md) | [05-database.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/agents/05-database.md)

---

## 1 用户画像4维度

| 维度 | 字段 | 枚举值 | 个性化策略 |
|------|------|--------|-----------|
| 学历层次 | education_level | undergraduate / master / phd / faculty | 通俗解释+类比 / 方法对比+代码 / 前沿分析+创新建议 / 知识体系+教学案例 |
| 研究方向 | research_field | NLP / CV / RL / 多模态 / ... | 检索排序权重、领域上下文注入 |
| 知识水平 | knowledge_level | beginner / intermediate / advanced / expert | 术语密度<5% / ~20% / ~40% / >50% |
| 偏好风格 | preferred_style | simple / balanced / technical | 日常用语+比喻 / 标准学术 / 正式学术+引用 |

---

## 2 PersonalizationService映射

```python
DIFFICULTY_MAP = {
    "beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4
}
STYLE_MAP = {
    "simple": "casual", "balanced": "standard", "technical": "formal"
}
```
