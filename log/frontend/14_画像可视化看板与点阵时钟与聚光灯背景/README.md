# 画像可视化看板与点阵时钟与聚光灯背景

## 功能描述
- **画像可视化看板**：在用户中心"我的画像"卡片中，用 ECharts 雷达图可视化4维度画像（学历、知识水平、偏好风格、研究活跃度），综合评分环 + 个性化洞察建议，替换原纯标签展示
- **点阵时钟**：首页搜索框下方添加热力图风格的点阵 LED 时钟，27×9 网格，5×7 自定义字模，冒号闪烁，方形 LED + 描边空格子 + 热力图色阶
- **聚光灯背景**：首页添加鼠标跟随聚光灯揭示第二层图片的交互效果，canvas 生成径向渐变 mask，lerp 平滑跟随
- **Bug 修复**：修复收藏/用户中心 500/404 错误、画像保存校验失败、前端 API 字段映射等启动阻断问题

## 实现逻辑
- 修改的核心文件：
  - `ProfileDashboard.vue` — 画像雷达图 + 综合评分 + 个性化洞察
  - `DotMatrixClock.vue` — 点阵时钟（5×7 字模 + 热力图色阶 + 冒号闪烁）
  - `SpotlightBackground.vue` — 鼠标聚光灯背景（canvas mask + lerp 平滑）
  - `HomeView.vue` — 集成聚光灯背景 + 点阵时钟 + 深色主题适配
  - `UserCenterView.vue` — 集成画像看板 + fetchProfile 404 降级
  - `userStore.ts` — fetchProfile 捕获 404 不抛异常
  - `api/index.ts` — 404 拦截器屏蔽 /profile 路径
  - `api/user.ts` — createProfile/updateProfile 请求体 camelCase→snake_case 转换

## 接口变更
### Request (updateProfile)
```json
// 前端 toSnakeCase 转换后发送
{
  "education_level": "master",
  "research_field": "NLP",
  "knowledge_level": "intermediate",
  "preferred_style": "balanced"
}
```

### Response (getProfile, snake_case → camelCase 由拦截器处理)
```json
{
  "user_id": "usr_test_001",
  "education_level": "master",
  "research_field": "NLP",
  "knowledge_level": "intermediate",
  "preferred_style": "balanced"
}
```

## 测试结果
- 测试场景1：登录 test_user → 点击用户中心 → 画像看板雷达图正常渲染，综合评分显示
- 测试场景2：新注册用户（无画像）→ 点击用户中心 → 不再报 404，显示"尚未设置画像"
- 测试场景3：编辑画像保存 → snake_case 请求体成功，返回 200
- 测试场景4：首页点阵时钟显示当前时间，冒号每秒闪烁，空格子描边可见
- 测试场景5：首页鼠标移动 → 聚光灯跟随揭示第二层图片
- 是否通过：是

## 相关文件
- `frontend/src/components/common/ProfileDashboard.vue`（新增）
- `frontend/src/components/common/DotMatrixClock.vue`（新增）
- `frontend/src/components/common/SpotlightBackground.vue`（新增）
- `frontend/src/views/HomeView.vue`（修改）
- `frontend/src/views/UserCenterView.vue`（修改）
- `frontend/src/stores/userStore.ts`（修改）
- `frontend/src/api/index.ts`（修改）
- `frontend/src/api/user.ts`（修改）
