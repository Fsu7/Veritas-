# UserProfileForm 用户画像表单组件

## 任务概述

实现用户画像表单通用组件 UserProfileForm.vue，包含 4 维度枚举选项（学历层次/研究方向/知识水平/偏好风格）、Element Plus 表单校验、保存逻辑（调用 userStore.saveProfile）、保存成功/失败提示、按钮 loading 状态、支持新增和编辑两种模式（通过 props 区分）、emit 事件通知父组件保存结果。

## 里程碑

FM2: 用户+检索页面

## 涉及模块

- F1.1 用户界面模块（F1.1.2 画像设置、F1.1.3 画像编辑）

## 文件变更

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | Veritas/frontend/src/components/common/UserProfileForm.vue | 用户画像表单通用组件 |

## 已有可复用实现

| 文件 | 说明 | 复用方式 |
|------|------|---------|
| stores/userStore.ts | saveProfile/fetchProfile/profile/hasProfile | 直接复用 |
| types/user.ts | UserProfile 接口（4维度枚举类型） | 直接复用 |
| api/user.ts | createProfile/updateProfile | 通过 userStore 间接复用 |

## 功能要求

| ID | 描述 | 优先级 | 验收条件 |
|----|------|--------|---------|
| FR-001 | 4维度枚举选项表单 | P0 | 4个表单项正确渲染 |
| FR-002 | 学历层次4选项：本科生/硕士/博士/教师 | P0 | value 与枚举一致 |
| FR-003 | 知识水平4选项：初级/中级/高级/专家 | P0 | 含说明文字 |
| FR-004 | 偏好风格3选项：通俗/均衡/专业 | P0 | 含说明文字 |
| FR-005 | 研究方向自由输入 | P0 | required 校验 |
| FR-006 | 表单校验：4字段required | P0 | 为空时校验失败 |
| FR-007 | 保存逻辑：validate → userStore.saveProfile | P0 | 成功提示+emit |
| FR-008 | 保存按钮loading | P0 | 请求期间不可重复点击 |
| FR-009 | Props: initialData?: UserProfile | P1 | 编辑模式预填充 |
| FR-010 | Emits: saved | P1 | 保存成功通知父组件 |
| FR-011 | watch initialData 预填充 | P1 | 传入数据自动填充 |
| FR-012 | 默认值：master/intermediate/balanced | P2 | 新建画像默认值 |

## 4维度枚举值对照表

### 学历层次 (educationLevel)

| 中文标签 | value | 个性化策略 |
|---------|-------|-----------|
| 本科生 | undergraduate | 通俗解释+类比 |
| 硕士研究生 | master | 方法对比+代码 |
| 博士研究生 | phd | 前沿分析+创新建议 |
| 教师/研究者 | faculty | 知识体系+教学案例 |

### 知识水平 (knowledgeLevel)

| 中文标签 | value | 术语密度 |
|---------|-------|---------|
| 初级（对该领域了解较少） | beginner | <5% |
| 中级（有基础了解） | intermediate | ~20% |
| 高级（深入研究） | advanced | ~40% |
| 专家（领域权威） | expert | >50% |

### 偏好风格 (preferredStyle)

| 中文标签 | value | 风格描述 |
|---------|-------|---------|
| 通俗（日常用语+比喻） | simple | 日常用语+比喻 |
| 均衡（标准学术表达） | balanced | 标准学术 |
| 专业（正式学术+引用） | technical | 正式学术+引用 |

## 数据流

```
UserProfileForm → userStore.saveProfile(data) → userApi.create/updateProfile
→ Java后端 → ProfileResponse → userStore.profile更新 → emit('saved')
```

## 跨系统字段映射

```
前端 camelCase     →  JSON snake_case
educationLevel     →  education_level
researchField      →  research_field
knowledgeLevel     →  knowledge_level
preferredStyle     →  preferred_style
```

## 编码约束

- `<script setup lang="ts">` + Composition API
- Props/Emits 使用 TypeScript 泛型定义
- API 调用通过 userStore.saveProfile()
- BEM 命名：user-profile-form__item / user-profile-form__actions
- 8px 间距系统
- CSS 变量取色
- 组件不超过 300 行
- scoped 样式
- 枚举 value 必须与 types/user.ts 中 UserProfile 接口完全一致

## 禁止行为

- ❌ 直接调用 userApi（必须通过 userStore）
- ❌ 保存请求无 loading 状态
- ❌ 枚举 value 与 types/user.ts 不一致
- ❌ 硬编码颜色值
- ❌ 非 8px 倍数间距
- ❌ 输出伪代码或 TODO
- ❌ 组件超过 300 行
- ❌ 在组件内部管理 userId

## 验收标准

- [ ] 4维度枚举选项正确渲染，value 与 UserProfile 接口一致
- [ ] 表单校验：4字段 required
- [ ] 保存成功：ElMessage.success + emit('saved')
- [ ] 保存失败：ElMessage.error + loading 恢复
- [ ] 传入 initialData 时表单自动预填充
- [ ] Props/Emits 使用 TypeScript 泛型
- [ ] TypeScript 无类型错误
- [ ] 组件不超过 300 行