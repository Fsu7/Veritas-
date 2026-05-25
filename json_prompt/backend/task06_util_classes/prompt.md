# Task06: JwtUtil + RedisKeyUtil + DateTimeUtil 工具类

| 项目 | 内容 |
|------|------|
| **项目** | XH-202630 科研文献智能助手 |
| **版本** | v0.1 |
| **里程碑** | M1：基础设施就绪 / JM1：项目骨架与数据层就绪 |
| **功能编号** | F2.1, F2.2, F2.3, F2.4, F2.5, F2.6 |

## 需求描述

创建3个工具类：`JwtUtil`（JWT Token生成/验证/解析/黑名单检查，使用jjwt 0.12+库）、`RedisKeyUtil`（Redis Key生成工具，按 `{域}:{操作}:{标识符}` 格式）、`DateTimeUtil`（日期时间工具，格式化/解析/过期判断）。所有工具类使用final类+private构造方法，禁止实例化。

## 涉及层级

- **java_backend** — com.literatureassistant.util
- **java_backend** — com.literatureassistant.config（JwtUtil依赖jwt.secret/jwt.expiration配置）

## 需要修改/新增的文件

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/util/JwtUtil.java` | JWT工具类，@Component，Token生成/验证/解析/黑名单检查 |
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/util/RedisKeyUtil.java` | Redis Key生成工具，final类，9个静态方法 |
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/util/DateTimeUtil.java` | 日期时间工具类，final类，4个静态方法 |

## 功能要求

| ID | 优先级 | 描述 |
|----|--------|------|
| FR-001 | P0 | JwtUtil：generateToken(userId, username)生成含sub/username/jti/iat/exp(24h)的Token，parseToken解析Claims（无效返回null），validateToken验证有效性，isTokenBlacklisted检查Redis黑名单，getUserIdFromToken/getUsernameFromToken/getTokenJti提取载荷，getTokenRemainingTime获取剩余有效期 |
| FR-002 | P0 | RedisKeyUtil：9个静态方法生成Key——userProfileKey/userInfoKey/paperDetailKey/paperListKey/searchResultKey/analysisResultKey/sessionStateKey/agentStateKey/authBlacklistKey |
| FR-003 | P0 | DateTimeUtil：formatDateTime(yyyy-MM-dd HH:mm:ss)、parseDateTime、getCurrentTimestamp、isExpired |
| FR-004 | P1 | JwtUtil校验secret长度≥32字节（HMAC-SHA256要求），不足时抛IllegalStateException |
| FR-005 | P1 | JwtUtil中parseToken捕获异常时日志级别DEBUG（Token无效是常见业务场景） |

## 安全要求

- JWT Secret通过 `@Value('${jwt.secret}')` 注入，**禁止硬编码**
- Token过期时间24小时，通过 `@Value('${jwt.expiration:86400000}')` 注入
- **禁止**在日志中输出完整Token内容，最多输出前8位+省略号
- isTokenBlacklisted检查Redis黑名单，退出登录时将jti写入黑名单

## 关键约束

- **禁止**硬编码JWT Secret
- **禁止**在日志中输出完整Token内容
- **禁止**JwtUtil中parseToken抛出异常（应返回null）
- **禁止**工具类可被实例化（必须final+private构造）
- **禁止**DateTimeFormatter作为局部变量每次创建（必须static final常量）

## 验收标准

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-001 | JwtUtil.generateToken生成包含userId/username/jti的24h有效期Token | 单元测试 |
| AC-002 | JwtUtil.parseToken正确解析，无效Token返回null | 单元测试 |
| AC-003 | JwtUtil.validateToken验证Token有效性 | 单元测试 |
| AC-004 | JwtUtil.isTokenBlacklisted检查Redis黑名单 | 单元测试 |
| AC-005 | JwtUtil.getTokenRemainingTime返回剩余有效期毫秒数 | 单元测试 |
| AC-006 | RedisKeyUtil 9个方法生成符合格式的Key | 单元测试 |
| AC-007 | DateTimeUtil formatDateTime/parseDateTime互为逆运算 | 单元测试 |
| AC-008 | RedisKeyUtil和DateTimeUtil为final类+private构造 | 代码审查 |
| AC-009 | JWT Secret通过@Value注入，不硬编码 | 代码审查 |
| AC-010 | parseToken捕获异常时日志级别DEBUG | 代码审查 |
| AC-011 | 单元测试全部通过 | 自动化测试 |

## 验证命令

```bash
cd Veritas/backend && mvn test -Dtest=JwtUtilTest,RedisKeyUtilTest,DateTimeUtilTest
cd Veritas/backend && mvn compile
```
