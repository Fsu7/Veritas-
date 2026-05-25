# 技术教学文档

## 开发思路

### 需求分析过程
本次任务的核心需求是建立前端与Java后端之间的HTTP通信基础设施。分析需求后识别出以下关键点：
1. **统一通信规范**：所有API调用必须经过同一个Axios实例，确保baseURL、timeout、headers一致
2. **认证自动化**：JWT Token需要在每次请求时自动注入，而非手动在每个API调用中添加
3. **错误处理集中化**：HTTP错误（401/403/404/超时等）和业务错误（code !== 200）需要统一处理，避免在每个页面重复编写错误逻辑
4. **API模块化**：按业务域（user/paper/analysis/session）划分API模块，每个模块封装该域的所有HTTP调用

### 技术选型考虑
- **Axios vs fetch**：选择Axios因为其提供拦截器机制、自动JSON转换、请求取消、超时控制等能力，fetch虽然原生但需要手动实现这些功能
- **对象导出 vs 独立函数导出**：选择对象导出（`export const userApi = {...}`）而非独立函数导出，因为对象形式更便于按域引用、IDE自动补全和类型推断

### 架构设计思路
采用**分层通信架构**：
```
View → Store → API模块 → Axios实例 → Java后端
```
- API层仅封装HTTP调用，不含业务逻辑
- Store层调用API并管理状态
- View层通过Store间接使用API

### 遇到的问题及解决方案
1. **循环依赖问题**：如果在`api/index.ts`模块顶层`import { useUserStore }`，当userStore也import api模块时会产生循环依赖。解决方案：在拦截器回调内函数式调用`useUserStore()`，此时Pinia已初始化完毕
2. **响应数据解包**：后端返回`ApiResponse<T>`格式（`{code, message, data, timestamp}`），前端调用方只需要`data`字段。解决方案：在响应拦截器成功分支中解包，`code===200`时直接返回`data.data`，调用方无需再`.data.data`
3. **SSE地址特殊性**：`getAgentStreamUrl`不是HTTP调用，而是返回一个URL字符串供`EventSource`使用。不能通过Axios发起请求，因为SSE需要长连接

## 实现步骤

1. **审查现有文件**：检查`api/index.ts`和`types/common.ts`是否已符合验收标准，确认无需修改
2. **创建`api/user.ts`**：封装6个用户管理API方法（register/login/getUserInfo/getProfile/createProfile/updateProfile），引用`@/types/user`中的类型
3. **创建`api/paper.ts`**：封装5个论文管理API方法（list/getDetail/search/addFavorite/removeFavorite），定义`SearchParams`接口扩展`FilterParams`
4. **创建`api/analysis.ts`**：封装6个分析服务API方法（analyzePaper/comparePapers/generateReport/getResult/getStatus/getAgentStreamUrl），注意`getAgentStreamUrl`返回字符串
5. **创建`api/session.ts`**：封装4个会话管理API方法（create/list/getDetail/delete），定义`Session`接口
6. **TypeScript编译验证**：运行`npx vue-tsc --noEmit`确认无类型错误

## 解决了什么问题

### 核心问题描述
前端项目缺少统一的HTTP通信层，每个页面如果直接使用axios会导致：
- Token注入逻辑重复
- 错误处理逻辑不一致
- API路径硬编码散落各处
- 响应数据格式不统一

### 解决方案对比
| 方案 | 优点 | 缺点 |
|------|------|------|
| 每个页面直接用axios | 简单直接 | Token/错误处理重复，难维护 |
| 全局axios+拦截器+API模块 | 统一规范，易维护 | 需要前期搭建 |
| 自定义fetch封装 | 轻量 | 需手动实现拦截器、超时等 |

### 最终方案的优势
- **一次配置，全局生效**：Token注入和错误处理在拦截器中统一实现
- **API路径集中管理**：所有后端API路径集中在api/目录，修改时只需改一处
- **类型安全**：每个API方法的参数和返回值都有TypeScript类型约束
- **解包透明**：响应拦截器自动解包ApiResponse，调用方直接获得业务数据

## 变更内容

### 新增文件
- `Veritas/frontend/src/api/user.ts` — 用户管理API，6个方法（register/login/getUserInfo/getProfile/createProfile/updateProfile）
- `Veritas/frontend/src/api/paper.ts` — 论文管理API，5个方法（list/getDetail/search/addFavorite/removeFavorite），含SearchParams接口
- `Veritas/frontend/src/api/analysis.ts` — 分析服务API，6个方法（analyzePaper/comparePapers/generateReport/getResult/getStatus/getAgentStreamUrl）
- `Veritas/frontend/src/api/session.ts` — 会话管理API，4个方法（create/list/getDetail/delete），含Session接口

### 修改文件
- 无修改文件。`api/index.ts`和`types/common.ts`由前序task创建，经审查已符合验收标准

### 配置变更
- 无配置变更。baseURL从环境变量`VITE_API_BASE_URL`读取（由task01配置）

## 关键技术点

### Axios拦截器机制
Axios拦截器分为请求拦截器和响应拦截器两种：
- **请求拦截器**（`interceptors.request.use`）：在请求发出前执行，用于修改请求配置（如注入Token）
- **响应拦截器**（`interceptors.response.use`）：在响应到达前执行，有两个回调——成功回调处理2xx响应，错误回调处理非2xx响应

```typescript
// 请求拦截器关键：函数式获取Store避免循环依赖
http.interceptors.request.use((config) => {
  const userStore = useUserStore()  // 在回调内获取，非模块顶层
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})
```

### ApiResponse解包设计
后端统一响应格式为`{code, message, data, timestamp}`，前端响应拦截器自动解包：
- `code === 200` → 返回`data`（业务数据），调用方直接使用
- `code !== 200` → `ElMessage.error`提示业务错误，reject Promise

这意味着API方法返回的是**业务数据**而非整个ApiResponse，例如：
```typescript
// 调用方代码
const profile = await userApi.getProfile('usr_001')
// profile 类型是 ProfileResponse，而非 ApiResponse<ProfileResponse>
```

### SSE地址的特殊处理
`analysisApi.getAgentStreamUrl`返回URL字符串而非发起HTTP请求，因为：
- SSE使用`EventSource` API，不是Axios的HTTP请求
- SSE需要长连接，Axios的请求-响应模式不适合
- URL需要包含认证信息，通过`EventSource`的`withCredentials`或URL参数传递

### SearchParams接口设计
```typescript
export interface SearchParams extends FilterParams {
  q: string       // 搜索关键词（必填）
  page?: number   // 页码
  size?: number   // 每页数量
}
```
继承`FilterParams`（yearFrom/yearTo/venue/minCitations/sort），增加搜索必需的`q`和分页参数，避免在API方法参数中重复定义筛选字段。

## 经验总结

### 开发过程中的收获
1. **先审查再动手**：本次任务中`api/index.ts`和`types/common.ts`已由前序task创建，经审查发现完全符合验收标准，避免了不必要的重复工作
2. **API模块设计要面向Store层**：API方法返回类型应与Store层需要的数据格式匹配，响应拦截器解包后Store层无需再做数据提取
3. **类型定义就近原则**：当types/目录中缺少某个类型（如Session），可在API模块内就近定义，后续再迁移到独立类型文件

### 踩过的坑及如何避免
1. **循环依赖陷阱**：如果在`api/index.ts`模块顶层导入`useUserStore`，当Store也import api时会产生循环依赖导致运行时错误。**避免方法**：始终在拦截器回调内函数式获取Store实例
2. **响应类型丢失**：Axios响应拦截器返回`data.data`后，TypeScript可能无法正确推断类型。**避免方法**：在API方法签名中显式声明返回类型（如`Promise<LoginResponse>`）
3. **SSE URL的baseURL问题**：`getAgentStreamUrl`返回的URL需要包含`/api`前缀，因为`EventSource`不经过Axios实例，不会自动添加baseURL

### 最佳实践建议
1. API模块中**禁止编写业务逻辑**，仅封装HTTP调用，业务逻辑放在Pinia Store中
2. 所有API方法的返回类型**必须显式声明**，利用TypeScript的类型检查能力
3. 每个API模块**导出单一对象**（如`userApi`、`paperApi`），而非多个独立函数，便于按域引用
4. **禁止在拦截器中console.log完整Token**，安全约束要求不输出敏感信息
5. 401错误**必须自动跳转登录页并清除Token**，这是JWT认证流程的关键环节
