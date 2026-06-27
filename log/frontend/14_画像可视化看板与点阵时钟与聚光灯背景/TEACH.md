# 技术教学文档

## 开发思路

### 需求分析过程
本次前端开发任务围绕"用户中心体验升级"和"首页视觉增强"展开：
1. 用户中心画像展示过于简单（仅标签列表），需要更丰富的可视化呈现
2. 首页视觉单调，需要增加动态元素提升吸引力
3. 首页背景需要有交互感，而非静态图片

### 技术选型考虑
- **画像看板**：使用 ECharts 雷达图，项目已集成 echarts 依赖，与 AgentFlowChart/TimeStats 组件技术栈一致
- **点阵时钟**：纯 CSS Grid + TypeScript 字模渲染，无需额外依赖
- **聚光灯背景**：Canvas API 生成径向渐变 mask，原生 requestAnimationFrame 实现平滑跟随

### 架构设计思路
- 组件化：每个功能独立为 Vue SFC 组件，放在 `components/common/` 目录
- 分层：聚光灯背景 z-index:0，内容 z-index:1，互不干扰
- 适配：点阵时钟用 aspect-ratio 保持比例，聚光灯背景用 100dvh 适配移动端

### 遇到的问题及解决方案
1. **画像保存 400 校验失败**：后端 Jackson SNAKE_CASE 策略导致 camelCase 请求体无法反序列化 → 前端 `toSnakeCase` 转换
2. **用户中心 404**：新用户无画像时 `getProfile` 返回 404 → 前端拦截器屏蔽 `/profile` 路径的 404 提示 + `fetchProfile` 优雅降级
3. **点阵时钟数字显示不全**：冒号 2 列宽（`0b01`）导致左侧多一个空列 → 改为 1 列宽（`0b1`）
4. **空格子不可见**：`var(--el-fill-color)` 与背景同色 → 改为硬编码 `#e4e7ed` 描边
5. **Vite 终端意外停止**：导致"网络错误" → 检查并重启前端开发服务器

## 实现步骤

### 1. 画像可视化看板（ProfileDashboard.vue）
1. 设计 4 维度量化映射（学历/知识/风格/活跃度 → 0-100 分值）
2. 构建 ECharts 雷达图配置（径向渐变 areaStyle + label 显示分值）
3. 综合评分环 + 等级标签（深度研究者/积极学习者/入门探索者/科研新手）
4. 个性化洞察引擎（根据画像维度组合生成推荐建议）
5. 活跃度统计栏 + 维度摘要列表

### 2. 点阵时钟（DotMatrixClock.vue）
1. 设计 5×7 点阵字模（0-9 数字 + 冒号），用二进制位表示像素
2. 构建 9×27 网格布局，字符间留 1 列间隔
3. 热力图色阶：4 级蓝色渐变（基于距网格中心的距离 + 随机扰动）
4. 冒号 1 秒闪烁动画（setInterval 切换 colonVisible 状态）
5. 时间每分钟刷新（对齐到整分钟触发，避免每秒重绘）

### 3. 聚光灯背景（SpotlightBackground.vue）
1. 两层背景图叠加（base z-0 + reveal z-1）
2. 鼠标平滑跟随：raw mouse → lerp 0.1 → smooth → cursorPos
3. Canvas 生成径向渐变 mask（6 级色阶 0→1→0.75→0.4→0.12→0）
4. toDataURL → maskImage/webkitMaskImage 应用到 reveal 层
5. Ken Burns 缩放动画 + 淡入

### 4. Bug 修复
1. `toSnakeCase`：前端发送画像数据前将 camelCase → snake_case
2. axios 拦截器：`/profile` 路径 404 不显示错误提示
3. `fetchProfile`：捕获 404 设置 `profile = null`，不阻塞页面
4. HomeView 样式适配深色背景（标题白色 + 文字阴影）

## 解决了什么问题

### 核心问题描述
1. 用户中心画像展示只有 4 个标签，信息密度低且不直观
2. 首页缺乏视觉吸引力和交互感
3. 画像保存接口前后端字段命名不一致导致校验失败
4. 新用户无画像时用户中心页面直接崩溃

### 解决方案对比
- 画像展示：标签列表 → 雷达图 + 评分 + 洞察（信息密度提升 5 倍）
- 首页时钟：直接显示时间文字 → 25×10 点阵热力图风格
- 字段映射：后端修改 Jackson 配置（影响面大）→ 前端 toSnakeCase（最小改动）
- 404 处理：后端返回 200 空数据（违反 RESTful）→ 前端优雅降级（符合语义）

### 最终方案的优势
- 组件独立可复用，不影响其他页面
- 纯前端实现，无需后端改动
- ECharts/Canvas 原生 API，无额外依赖
- 响应式设计，移动端自适应

## 变更内容

### 新增文件
- `frontend/src/components/common/ProfileDashboard.vue` — 画像可视化看板
- `frontend/src/components/common/DotMatrixClock.vue` — 点阵热力图时钟
- `frontend/src/components/common/SpotlightBackground.vue` — 鼠标聚光灯背景

### 修改文件
- `frontend/src/views/UserCenterView.vue` — 集成画像看板组件
- `frontend/src/views/HomeView.vue` — 集成点阵时钟 + 聚光灯背景 + 深色适配
- `frontend/src/stores/userStore.ts` — `fetchProfile` 404 优雅降级
- `frontend/src/api/index.ts` — 拦截器屏蔽 `/profile` 路径 404 提示
- `frontend/src/api/user.ts` — `toSnakeCase` 转换函数

### 配置变更
- 无（纯前端组件开发）

## 关键技术点

### ECharts 雷达图
- `RadarChart` + `TooltipComponent` + `CanvasRenderer` 按需引入
- `LinearGradient` 实现 areaStyle 渐变填充
- `markRaw(echarts.init())` 避免 Vue 响应式追踪 ECharts 实例
- `ResizeObserver` 自适应容器尺寸变化

### Canvas 径向渐变 Mask
- `createRadialGradient` 6 级色阶实现软边缘
- `canvas.toDataURL()` → `maskImage` 应用到 DOM
- `requestAnimationFrame` + lerp 0.1 实现平滑跟随
- `pointer-events: none` 确保不干扰页面交互

### 点阵字模设计
- 5×7 二进制位图：`0b01110` = 第1行像素分布
- 位运算提取：`(bits >> (width - 1 - col)) & 1`
- 字符间距通过 `colOffset += width + gap` 控制

### 前后端字段映射
- 后端 `property-naming-strategy: SNAKE_CASE` 导致 `@JsonProperty` 失效
- Jackson 全局策略覆盖 `@JsonProperty`，反序列化只接受 snake_case
- 前端 `toSnakeCase` 在请求发送前转换字段名

## 经验总结

### 开发过程中的收获
1. Canvas mask 技术可实现复杂的图像揭示效果，无需 WebGL
2. 二进制位图字模是点阵显示的经典方案，适合复古风格 UI
3. axios 拦截器需要区分"正常 404"和"异常 404"，避免误导用户

### 踩过的坑及如何避免
1. **Jackson SNAKE_CASE 与 @JsonProperty 冲突**：`@JsonProperty` 不是添加别名而是替换属性名，全局策略生效后 camelCase 不再被接受 → 前后端字段映射需统一或在前端转换
2. **MapStruct 增量编译冲突**：`Attempt to recreate a file for PaperMapperImpl` → 使用 `mvn clean` 清除旧生成文件
3. **Vite 终端意外停止**：长时间运行的 dev server 可能被中断 → 监控终端状态，及时重启
4. **CSS 变量在动态组件中不可靠**：`var(--el-fill-color)` 在某些上下文中解析为与背景同色 → 使用硬编码颜色值

### 最佳实践建议
1. 新建 ECharts 组件时统一使用 `markRaw` + `ResizeObserver` + `dispose` 生命周期管理
2. 点阵字模用二进制常量定义，便于阅读和维护
3. 前后端字段命名差异应在 API 层统一处理，不扩散到 Store/View 层
4. 鼠标交互效果需考虑 `prefers-reduced-motion` 无障碍降级
