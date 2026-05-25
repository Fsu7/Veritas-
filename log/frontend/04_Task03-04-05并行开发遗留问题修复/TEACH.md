# 技术教学文档

## 开发思路
- 需求分析过程：三个前端基础设施任务（Axios拦截器、Vue Router、Pinia Store）并行开发后，需要全面审查交叉引用是否产生循环依赖、类型不一致、占位符和功能遗漏。审查发现5个问题，按优先级P0/P1分类修复。
- 技术选型考虑：循环依赖的修复方案有三种——(1) 动态 `await import()` (2) 延迟函数式获取 (3) 事件总线解耦。选择方案(1)因为最直接、最符合task规范要求，且Axios和Vue Router原生支持异步回调。
- 架构设计思路：前端模块依赖关系应为单向的 `views → stores → api`，api层和router层不应反向依赖stores。通过动态导入打破反向依赖箭头。
- 遇到的问题及解决方案：
  - 问题：ES模块循环引用在当前不崩溃，但未来可能因模块加载顺序变化而出错
  - 解决：使用 `await import()` 将依赖解析延迟到运行时，确保所有模块已初始化

## 实现步骤
1. 审查阶段：读取task03/04/05的prompt.json，逐文件对比验收标准，发现5个问题
2. 修复问题#1：`api/index.ts` 移除顶层 `import { useUserStore }` 和 `import router`，拦截器回调改为 `async`，内部使用 `await import()` 动态获取
3. 修复问题#2：`router/index.ts` 移除顶层 `import { useUserStore }`，`beforeEach` 改为 `async`，内部动态导入
4. 修复问题#3：`types/user.ts` 的 `ProfileResponse` 字段从 `string` 改为 `UserProfile['educationLevel']` 等索引类型
5. 修复问题#4：`stores/userStore.ts` 移除6处 `as` 类型断言（因ProfileResponse类型已统一），login后若 `hasProfile === true` 自动调用 `fetchProfile()`
6. 修复问题#5：`stores/paperStore.ts` 的 `filteredResults` 从空壳改为实现年份范围/会议/引用数过滤+排序
7. 验证：`vue-tsc --noEmit` 零错误 + `npm run dev` 正常启动

## 解决了什么问题
- 核心问题描述：并行开发导致模块间形成三方循环依赖链，违反task规范禁令；类型定义不一致导致Store中使用不安全的 `as` 断言；部分功能为占位符
- 解决方案对比：
  | 方案 | 循环依赖修复 | 优点 | 缺点 |
  |------|-------------|------|------|
  | 动态 `await import()` | ✅ 选中 | 最直接、符合规范、运行时安全 | Vite可能拆分chunk |
  | 延迟函数式获取 | ✅ | 无需async | 仍需顶层导入函数引用 |
  | 事件总线解耦 | ✅ | 完全解耦 | 过度设计、增加复杂度 |
- 最终方案的优势：动态导入方案最符合task03 FA-002和task04 FA-004的明确要求，且Axios/Vue Router原生支持异步回调

## 变更内容
### 新增文件
无新增文件

### 修改文件
- `Veritas/frontend/src/api/index.ts`
  - 移除顶层 `import { useUserStore }` 和 `import router`
  - 请求拦截器回调改为 `async`，内部 `await import('@/stores/userStore')`
  - 响应拦截器错误分支改为 `async`，401处理中 `await import('@/stores/userStore')` 和 `await import('@/router')`

- `Veritas/frontend/src/router/index.ts`
  - 移除顶层 `import { useUserStore }`
  - `beforeEach` 守卫改为 `async`，内部 `await import('@/stores/userStore')`

- `Veritas/frontend/src/types/user.ts`
  - `ProfileResponse.educationLevel`: `string` → `UserProfile['educationLevel']`
  - `ProfileResponse.knowledgeLevel`: `string` → `UserProfile['knowledgeLevel']`
  - `ProfileResponse.preferredStyle`: `string` → `UserProfile['preferredStyle']`

- `Veritas/frontend/src/stores/userStore.ts`
  - `fetchProfile()`: 移除3处 `as UserProfile['xxx']` 断言
  - `saveProfile()`: 移除3处 `as UserProfile['xxx']` 断言（create和update分支各3处）
  - `login()`: 新增 `if (res.hasProfile) { await fetchProfile() }` 自动获取画像

- `Veritas/frontend/src/stores/paperStore.ts`
  - `filteredResults`: 从 `computed(() => searchResults.value)` 改为完整的过滤+排序实现
  - 支持 `yearFrom`/`yearTo` 年份范围过滤
  - 支持 `venue` 会议名模糊匹配
  - 支持 `minCitations` 最低引用数过滤
  - 支持 `sort: 'year'` 按年份降序、`sort: 'citations'` 按引用数降序

### 配置变更
无配置变更

## 关键技术点
- **ES模块循环引用机制**：ES模块的 `import` 在静态分析阶段解析，形成循环时模块可能处于部分初始化状态。`await import()` 将解析延迟到运行时，确保目标模块已完全初始化
- **Axios异步拦截器**：Axios原生支持拦截器回调返回Promise，`async` 回调等价于返回Promise，请求仍会正确等待拦截器完成
- **Vue Router异步守卫**：`beforeEach` 支持 `async` 回调，路由导航会等待Promise resolve后再继续
- **TypeScript索引类型**：`UserProfile['educationLevel']` 引用已有类型的某个属性类型，避免重复定义枚举值，保证类型一致性
- **Pinia Store注册顺序**：`main.ts` 中 `app.use(createPinia())` 必须在 `app.use(router)` 之前，否则Router守卫中 `useUserStore()` 会因Pinia未初始化而报错

## 经验总结
- **并行开发必须做交叉审查**：三个任务各自独立开发时都能编译通过，但合并后产生循环依赖。并行开发完成后必须做全局交叉审查
- **循环依赖的隐蔽性**：ES模块循环引用在运行时可能不崩溃（因为拦截器/守卫是延迟执行的），但违反设计规范且未来可能因模块加载顺序变化而出错。不能因为"能跑"就忽略
- **`as` 类型断言是代码异味**：需要用 `as` 断言桥接两个类型时，说明类型定义本身有问题。应该从源头修复类型定义，而非用断言绕过
- **占位符必须标记**：空壳computed（如 `filteredResults = computed(() => searchResults.value)`）没有TODO注释，容易遗漏。占位符应明确标记或立即实现
- **main.ts注册顺序很重要**：Pinia必须在Router之前注册，这是并行开发中容易忽略的细节。当前实现正确，但未来修改main.ts时需注意
- **最佳实践建议**：
  1. API层和Router层不应顶层导入Store，应使用动态导入
  2. TypeScript类型定义应保持DRY原则，用索引类型引用而非重复定义
  3. 并行开发后必须运行全局TypeScript编译检查
  4. Store的login action应利用API返回的hasProfile等字段自动完成后续初始化
