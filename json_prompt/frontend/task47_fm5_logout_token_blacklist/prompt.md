# Task 47：退出登录完善 + Token 黑名单

> **里程碑**：FM5 功能完善与UI打磨（Week 11 Day 5）
> **优先级**：P1
> **涉及模块**：F1.1 用户界面模块

---

## 一、任务概述

完善退出登录功能，实现 Token 黑名单。当前 AppHeader 退出按钮仅清除前端 localStorage（Token/userId/username），未调用后端 logout API 将 Token jti 加入 Redis 黑名单。

**目标**：新增 `userApi.logout` 调用 POST /users/logout（后端将 Token jti 写入 Redis 黑名单，TTL=Token 剩余有效期），`userStore.logout` 改为 async 先调用后端 API（失败不阻塞）再清除本地状态，AppHeader 退出按钮增加 loading 状态防止重复点击，401 拦截器优化区分"Token 过期"和"主动退出"。

---

## 二、涉及模块

| 模块 | 路径 | 职责 |
|------|------|------|
| userApi | `src/api/user.ts` | 用户 API（新增 logout） |
| userStore | `src/stores/userStore.ts` | 用户状态（logout 改 async） |
| AppHeader | `src/components/layout/AppHeader.vue` | 导航（退出按钮 loading） |
| Axios 拦截器 | `src/api/index.ts` | 401 拦截优化 |

---

## 三、文件变更表

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| modify | `Veritas/frontend/src/api/user.ts` | 新增 logout() 方法 |
| modify | `Veritas/frontend/src/stores/userStore.ts` | logout 改 async；新增 isManualLogout 标志 |
| modify | `Veritas/frontend/src/components/layout/AppHeader.vue` | 退出按钮 loading 状态 |
| modify | `Veritas/frontend/src/api/index.ts` | 401 拦截器优化 |

---

## 四、功能要求

| 编号 | 描述 | 优先级 |
|------|------|--------|
| FR-001 | userApi.logout 调用 POST /users/logout | P0 |
| FR-002 | userStore.logout 改 async：先调用后端 API（失败不阻塞）再清除本地状态 | P0 |
| FR-003 | AppHeader 退出按钮 loading 状态防止重复点击 | P1 |
| FR-004 | 退出后跳转登录页（携带 redirect 参数） | P0 |
| FR-005 | 401 拦截器优化：主动退出时不显示"登录已过期"提示 | P1 |

---

## 五、关键技术约束

1. **分层规范**：AppHeader → userStore.logout → userApi.logout
2. **安全约束**：必须调用后端 logout API 写入 Redis 黑名单（禁止仅清除前端状态）
3. **不阻塞退出**：后端 API 失败时仍清除本地状态（确保用户能退出）
4. **敏感信息**：禁止在日志/控制台输出 JWT Token
5. **CSS 变量**：使用 `var(--spacing-md)` 等 CSS 变量

---

## 六、验收检查点

- [ ] AC-001：退出时调用后端 logout API（POST /users/logout） — automated_test
- [ ] AC-002：退出后前端 Token/userId/username 清除 — automated_test
- [ ] AC-003：退出后跳转登录页（携带 redirect 参数） — manual_test
- [ ] AC-004：退出后旧 Token 无法访问受保护接口（后端 Redis 黑名单生效） — manual_test
- [ ] AC-005：退出按钮 loading 状态防止重复点击 — manual_test
- [ ] AC-006：主动退出时不显示"登录已过期"提示 — manual_test
- [ ] AC-007：后端 logout API 失败时用户仍能本地退出（不阻塞） — automated_test
- [ ] AC-008：所有新增/修改的代码通过 lint 和 build 验证 — code_review

---

## 七、验证命令

```bash
cd Veritas/frontend && npm run test -- --run userStore AppHeader
cd Veritas/frontend && npm run lint
cd Veritas/frontend && npm run build
```

---

## 八、参考文档

- `AGENTS.md` — 项目全景上下文与前端约束、安全规范（JWT+Redis 黑名单）
- `docs/frontend/前端模块系统架构文档.md` — 前端架构规范、API 通信层、userStore 设计
- `docs/frontend/前端模块项目里程碑文档.md` — FM5 里程碑任务分解（Week 11 Day 5）
- `docs/开发规范文档.md` — 前端编码规范、安全规范
- `docs/架构决策记录(ADR).md` — 架构决策（JWT 认证、Redis 黑名单）
