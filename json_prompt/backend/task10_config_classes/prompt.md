# Task10: RedisConfig + WebClientConfig + SecurityConfig

| 项目 | 内容 |
|------|------|
| **项目** | XH-202630 科研文献智能助手 |
| **版本** | v0.1 |
| **里程碑** | M1：基础设施就绪 / JM1：项目骨架与数据层就绪 |
| **功能编号** | F2.1, F2.5, F2.6 |

## 需求描述

创建3个核心配置类：RedisConfig（缓存管理器+RedisTemplate+TTL分层）、WebClientConfig（WebClient+连接池+超时30s+SSE支持）、SecurityConfig（Spring Security过滤器链+JWT鉴权+白名单路径+CORS配置）。

## 涉及层级

- **java_backend** — com.literatureassistant.config
- **data_layer** — Redis连接

## 需要修改/新增的文件

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `config/RedisConfig.java` | Redis配置：@EnableCaching + CacheManager(6个缓存空间TTL) + RedisTemplate |
| 新增 | `config/WebClientConfig.java` | WebClient配置：连接池(max=50) + 响应超时30s + SSE流超时120s |
| 新增 | `config/SecurityConfig.java` | Security配置：JWT过滤器链 + 白名单 + CORS + CSRF禁用 |

## 功能要求

| ID | 优先级 | 描述 |
|----|--------|------|
| FR-001 | P0 | RedisConfig：CacheManager默认TTL 30min，6个缓存空间自定义TTL（userProfile:1h, userInfo:1h, paperDetail:30min, paperSearch:10min, analysisResult:30min, sessionState:2h），Value使用GenericJackson2JsonRedisSerializer |
| FR-002 | P0 | WebClientConfig：连接超时5s、响应超时30s、SSE流超时120s、基础URL从配置读取 |
| FR-003 | P0 | SecurityConfig：CSRF禁用、CORS配置、Session STATELESS、白名单路径放行、其余需认证、JWT过滤器预留位置 |
| FR-004 | P1 | RedisConfig缓存穿透防护（空值缓存TTL=60s）、缓存雪崩防护（TTL随机偏移±10%） |
| FR-005 | P1 | SecurityConfig CORS配置从yml读取allowed-origins，支持多Origin |

## Redis缓存TTL分层

| 缓存空间 | Key格式 | TTL |
|---------|---------|-----|
| userProfile | user:profile:{userId} | 1小时 |
| userInfo | user:info:{userId} | 1小时 |
| paperDetail | paper:detail:{paperId} | 30分钟 |
| paperSearch | search:result:{queryHash} | 10分钟 |
| analysisResult | analysis:result:{analysisId} | 30分钟 |
| sessionState | session:state:{sessionId} | 2小时 |

## Security白名单路径

- `POST /api/users/register` — 用户注册
- `POST /api/users/login` — 用户登录
- `GET /health` — 健康检查
- `/actuator/**` — Spring Boot Actuator
- `/error` — Spring默认错误页

## 关键约束

- **禁止**硬编码JWT Secret或AI服务URL
- **禁止**CORS使用`allowedOrigins("*")`
- **禁止**Redis使用JDK默认序列化
- **禁止**WebClient不配置超时
- **禁止**SecurityConfig启用CSRF
- **禁止**在日志中输出JWT Secret或Redis密码

## 验收标准

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-001 | CacheManager配置6个缓存空间，TTL正确 | 自动化测试 |
| AC-002 | RedisTemplate使用StringRedisSerializer | 代码审查 |
| AC-003 | CacheManager使用GenericJackson2JsonRedisSerializer | 代码审查 |
| AC-004 | WebClient连接超时5s、响应超时30s | 自动化测试 |
| AC-005 | WebClient基础URL从配置读取 | 代码审查 |
| AC-006 | 白名单路径无需Token可访问 | 自动化测试 |
| AC-007 | 非白名单路径未携带Token返回401 | 自动化测试 |
| AC-008 | CSRF禁用、Session STATELESS、formLogin禁用 | 代码审查 |
| AC-009 | CORS从yml读取allowed-origins | 代码审查 |
| AC-010 | JWT Secret通过环境变量注入 | 代码审查 |
| AC-011 | 单元测试全部通过 | 自动化测试 |

## 验证命令

```bash
cd Veritas/backend && mvn compile
cd Veritas/backend && mvn test -Dtest=RedisConfigTest,WebClientConfigTest,SecurityConfigTest
cd Veritas/backend && mvn spring-boot:run
```
