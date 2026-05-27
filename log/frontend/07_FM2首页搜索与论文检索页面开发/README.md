# FM2 首页搜索与论文检索页面开发

## 功能描述
- 解决了FM1里程碑中HomeView仅为基础骨架、SearchView为占位符的问题
- 实现了完整的首页搜索入口→论文检索结果展示→分页浏览全流程
- paperStore从骨架升级为完整状态管理（loading/error/乐观更新/回滚）
- 新增usePagination通用分页composable，解耦分页逻辑与数据加载
- 业务价值：用户可通过首页输入研究主题进行文献检索，查看搜索结果、分页浏览、收藏论文

## 实现逻辑
- 修改的核心文件列表：
  - `Veritas/frontend/src/stores/paperStore.ts` — 扩展Store状态与Actions
  - `Veritas/frontend/src/composables/usePagination.ts` — 新建通用分页逻辑
  - `Veritas/frontend/src/views/HomeView.vue` — 完善首页搜索功能
  - `Veritas/frontend/src/components/paper/PaperCard.vue` — 新建论文卡片组件
  - `Veritas/frontend/src/views/SearchView.vue` — 重写搜索结果页
  - `Veritas/frontend/tsconfig.json` — 添加vitest/globals类型
  - 5个测试文件（paperStore/usePagination/PaperCard/SearchView/HomeView）
- 使用的设计模式：
  - Pinia Setup Store模式（组合式API风格Store）
  - Composable模式（usePagination纯逻辑+callback解耦）
  - 乐观更新+回滚模式（toggleFavorite先更新状态，API失败回滚）
  - BEM CSS命名规范
  - Props Down / Events Up组件通信
- 关键代码逻辑：
  - HomeView搜索流程：校验→保存历史→检查登录→searchPapers→跳转
  - SearchView三态互斥：Error > Empty > Results
  - paperStore.searchPapers：try-catch-finally管理loading/error

## 接口变更

### Request
```json
{
  "q": "Multi-Agent协同决策",
  "page": 1,
  "size": 10
}
```

### Response
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "paperId": "arxiv_2024_001",
        "title": "Multi-Agent Collaborative Decision Making",
        "authors": ["Zhang", "Li"],
        "abstract": "A comprehensive survey...",
        "year": 2024,
        "venue": "ACL",
        "keywords": ["Multi-Agent", "LLM"],
        "citationCount": 156,
        "score": 0.95,
        "recommendReason": "Highly relevant"
      }
    ],
    "total": 25,
    "page": 1,
    "size": 10
  }
}
```

## 测试结果
- 测试场景1：paperStore搜索流程 — 60个测试全部通过
  - searchPapers loading状态切换 ✅
  - searchPapers 成功更新searchResults/totalResults ✅
  - searchPapers 失败设置error ✅
  - togglePaperSelection 选中/取消/5篇上限 ✅
  - toggleFavorite 乐观更新+回滚 ✅
  - updateFilters 合并筛选并触发搜索 ✅
  - resetSearch 重置搜索但保留收藏/选择 ✅
- 测试场景2：usePagination分页逻辑 ✅
  - 初始化默认/自定义pageSize ✅
  - totalPages计算正确 ✅
  - handleCurrentChange/handleSizeChange回调 ✅
  - resetPage重置 ✅
- 测试场景3：PaperCard组件渲染 ✅
  - 标题/作者/摘要/关键词/评分/推荐理由渲染 ✅
  - 空数据条件渲染 ✅
  - select/analyze/favorite事件触发 ✅
  - 摘要截断超过200字符 ✅
- 测试场景4：HomeView/SearchView基础渲染 ✅
- vue-tsc --noEmit 无TypeScript错误 ✅
- npm run build 构建成功 ✅
- 是否通过：是

## 相关文件
- `Veritas/frontend/src/stores/paperStore.ts`
- `Veritas/frontend/src/composables/usePagination.ts`
- `Veritas/frontend/src/views/HomeView.vue`
- `Veritas/frontend/src/components/paper/PaperCard.vue`
- `Veritas/frontend/src/views/SearchView.vue`
- `Veritas/frontend/src/types/paper.ts`（未修改，直接复用）
- `Veritas/frontend/src/utils/storage.ts`（未修改，直接复用）
- `Veritas/frontend/src/stores/userStore.ts`（未修改，直接复用）
- `Veritas/frontend/src/api/paper.ts`（未修改，直接复用）
- `Veritas/frontend/src/router/index.ts`（未修改，直接复用）
- `Veritas/frontend/tsconfig.json`（添加vitest/globals类型）
- `Veritas/frontend/src/__tests__/stores/paperStore.spec.ts`（新建）
- `Veritas/frontend/src/__tests__/composables/usePagination.spec.ts`（新建）
- `Veritas/frontend/src/__tests__/components/paper/PaperCard.spec.ts`（新建）
- `Veritas/frontend/src/__tests__/views/SearchView.spec.ts`（新建）
- `Veritas/frontend/src/__tests__/views/HomeView.spec.ts`（更新）
