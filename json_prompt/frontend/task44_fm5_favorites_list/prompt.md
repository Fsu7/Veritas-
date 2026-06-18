# Task 44：论文收藏列表完整功能

> **里程碑**：FM5 功能完善与UI打磨（Week 11 Day 2）
> **优先级**：P1
> **涉及模块**：F1.2 论文检索模块

---

## 一、任务概述

实现论文收藏列表完整功能。当前 PaperCard 已实现收藏/取消收藏按钮（乐观更新+失败回滚），但 `fetchFavorites` 是空实现，无独立收藏列表页面、无 `/favorites` 路由、UserCenterView 无收藏数量统计。

**目标**：新增 `paperApi.getFavorites`、实现 `paperStore.fetchFavorites` 真实拉取、新建 FavoritesView 页面、新增 `/favorites` 路由、AppHeader 菜单增加"我的收藏"入口、UserCenterView 增加收藏数量统计卡片。

---

## 二、涉及模块

| 模块 | 路径 | 职责 |
|------|------|------|
| paperApi | `src/api/paper.ts` | 论文API（新增 getFavorites） |
| paperStore | `src/stores/paperStore.ts` | 论文状态（实现 fetchFavorites） |
| FavoritesView | `src/views/FavoritesView.vue` | 收藏列表页（新建） |
| router | `src/router/index.ts` | 路由（新增 /favorites） |
| AppHeader | `src/components/layout/AppHeader.vue` | 导航（新增"我的收藏"） |
| UserCenterView | `src/views/UserCenterView.vue` | 用户中心（新增收藏统计） |
| PaperCard | `src/components/paper/PaperCard.vue` | 论文卡片（复用） |
| usePagination | `src/composables/usePagination.ts` | 分页（复用） |

---

## 三、文件变更表

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| modify | `Veritas/frontend/src/api/paper.ts` | 新增 getFavorites(params) 方法 |
| modify | `Veritas/frontend/src/stores/paperStore.ts` | 实现 fetchFavorites 真实拉取；新增 favoritesList/favoritesTotal 状态 |
| create | `Veritas/frontend/src/views/FavoritesView.vue` | 新建收藏列表页 |
| modify | `Veritas/frontend/src/router/index.ts` | 新增 /favorites 路由 |
| modify | `Veritas/frontend/src/components/layout/AppHeader.vue` | 菜单增加"我的收藏" |
| modify | `Veritas/frontend/src/views/UserCenterView.vue` | 增加收藏数量统计卡片 |

---

## 四、功能要求

| 编号 | 描述 | 优先级 |
|------|------|--------|
| FR-001 | paperApi.getFavorites(params) 调用 GET /papers/favorites | P0 |
| FR-002 | paperStore.fetchFavorites 真实拉取，更新 favoritesList 和 favoritesTotal | P0 |
| FR-003 | FavoritesView 展示 PaperCard 列表 + 分页 + 空状态 + loading | P0 |
| FR-004 | 空收藏列表展示友好提示 + "去检索"按钮 | P1 |
| FR-005 | AppHeader 菜单增加"我的收藏"入口 | P0 |
| FR-006 | UserCenterView 增加收藏数量统计卡片 | P2 |
| FR-007 | 页面 onMounted 加载第一页，页码切换重新拉取 | P0 |

---

## 五、关键技术约束

1. **分层规范**：View → Store → API，FavoritesView 内不直接调用 paperApi
2. **数据同步**：toggleFavorite 取消收藏后从 favoritesList 移除并 favoritesTotal 减1
3. **CSS 变量**：使用 `var(--spacing-md)` 等 CSS 变量，禁止硬编码尺寸值
4. **无前端缓存**：每次进入页面或切换页码都重新请求后端
5. **空状态友好**：空收藏列表展示"暂无收藏论文，去检索看看吧" + 操作入口

---

## 六、验收检查点

- [ ] AC-001：收藏/取消收藏后，收藏列表实时同步 — manual_test
- [ ] AC-002：访问 /favorites 展示收藏论文列表，PaperCard 正确渲染 — manual_test
- [ ] AC-003：收藏列表分页正常，页码切换无报错 — automated_test
- [ ] AC-004：空收藏列表展示友好提示和"去检索"操作入口 — automated_test
- [ ] AC-005：AppHeader 菜单显示"我的收藏"，点击跳转 /favorites — manual_test
- [ ] AC-006：UserCenterView 展示收藏数量统计，点击跳转收藏列表 — manual_test
- [ ] AC-007：所有新增/修改的代码通过 lint 和 build 验证 — code_review

---

## 七、验证命令

```bash
cd Veritas/frontend && npm run test -- --run FavoritesView paperStore
cd Veritas/frontend && npm run lint
cd Veritas/frontend && npm run build
```

---

## 八、参考文档

- `AGENTS.md` — 项目全景上下文与前端约束
- `docs/frontend/前端模块系统架构文档.md` — 前端架构规范、F1.2 论文检索模块设计
- `docs/frontend/前端模块项目里程碑文档.md` — FM5 里程碑任务分解（Week 11 Day 2）
- `docs/开发规范文档.md` — 前端编码规范
- `docs/架构决策记录(ADR).md` — 架构决策
