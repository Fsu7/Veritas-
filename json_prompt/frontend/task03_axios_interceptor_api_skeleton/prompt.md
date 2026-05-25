# Task 03: Axios实例 + 请求/响应拦截器 + API模块骨架

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.1 |
| **里程碑** | M1 / FM1：项目骨架与基础设施就绪 |
| **涉及层级** | 前端 (frontend) |
| **功能编号** | F1.1, F1.2, F1.3, F1.4, F1.5 |

## 需求描述

创建Axios HTTP客户端实例，配置请求拦截器（自动注入JWT Token）和响应拦截器（统一错误处理：401跳转登录/403无权限/404资源不存在/超时提示/网络错误），并创建4个API模块骨架（user.ts、paper.ts、analysis.ts、session.ts）封装所有后端API调用，同时创建TypeScript通用类型定义（ApiResponse、PageResponse等）。

## 影响范围

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `src/types/common.ts` | 通用TypeScript类型：ApiResponse<T>、PageResponse<T> |
| 新增 | `src/api/index.ts` | Axios实例+请求拦截器(JWT Token)+响应拦截器(统一错误处理) |
| 新增 | `src/api/user.ts` | 用户管理API：register/login/getUserInfo/getProfile/createProfile/updateProfile |
| 新增 | `src/api/paper.ts` | 论文管理API：list/getDetail/search/addFavorite/removeFavorite |
| 新增 | `src/api/analysis.ts` | 分析服务API：analyzePaper/comparePapers/generateReport/getResult/getStatus/getAgentStreamUrl |
| 新增 | `src/api/session.ts` | 会话管理API：create/list/getDetail/delete |

## 实现要求

### 核心功能

1. **Axios实例**：baseURL从`VITE_API_BASE_URL`读取，timeout 30000ms，Content-Type: application/json
2. **请求拦截器**：函数式获取userStore，有Token时注入`Authorization: Bearer {token}`
3. **响应拦截器（成功）**：解包ApiResponse，code===200返回data，否则ElMessage.error提示
4. **响应拦截器（错误）**：401→跳转登录+清除Token；403→无权限；404→不存在；超时→提示；其他→网络错误
5. **4个API模块**：userApi(6方法)、paperApi(5方法)、analysisApi(6方法)、sessionApi(4方法)
6. **通用类型**：ApiResponse<T>、PageResponse<T>

### 跨系统一致性

- 字段命名：Java camelCase ↔ Python/JSON snake_case，前端API层使用snake_case
- API契约：与Java后端API路径和请求/响应格式保持一致
- 数据流：前端Axios → Vite proxy → Java后端:8080 → Python AI服务:8000

### 安全要求

- JWT Token自动注入，401自动跳转登录
- 禁止在日志中输出Token内容
- 前端不直接调用Python AI服务API

## 约束

- API层仅封装HTTP调用，不含业务逻辑
- 请求拦截器必须在回调内函数式获取userStore（避免循环依赖）
- 禁止硬编码API baseURL
- 前端只能调用Java后端API，不能直接调用Python AI服务

## 验收标准

- [ ] Axios实例baseURL从环境变量读取，timeout 30000ms
- [ ] 请求拦截器自动注入JWT Token
- [ ] 响应拦截器：code===200返回data，业务错误ElMessage提示
- [ ] 响应拦截器：401跳转登录+清除Token，403/404/超时有友好提示
- [ ] userApi 6个方法定义完整
- [ ] paperApi 5个方法定义完整
- [ ] analysisApi 6个方法定义完整
- [ ] sessionApi 4个方法定义完整
- [ ] types/common.ts定义ApiResponse<T>和PageResponse<T>
- [ ] 请求拦截器无循环依赖

## 验证命令

```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npm run dev
```
