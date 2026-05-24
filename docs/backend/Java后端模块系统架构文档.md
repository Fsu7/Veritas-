# XH-202630 科研文献智能助手 — Java后端模块系统架构文档

> **课题编号**：XH-202630  
> **课题名称**：领域知识个性化生成与多智能体协同决策系统研究  
> **发榜单位**：上海云之脑智能科技有限公司（科大讯飞全资子公司）  
> **文档版本**：v1.0  
> **创建日期**：2026年5月23日  
> **文档状态**：初稿

---

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0 | 2026-05-23 | 项目组 | 初始版本 |

---

## 目录

- [1 文档概述](#1-文档概述)
- [2 Java后端总体架构](#2-java后端总体架构)
- [3 项目结构与规范](#3-项目结构与规范)
- [4 用户管理模块（F2.1）](#4-用户管理模块f21)
- [5 论文管理模块（F2.2）](#5-论文管理模块f22)
- [6 会话管理模块（F2.3）](#6-会话管理模块f23)
- [7 分析服务模块（F2.4）](#7-分析服务模块f24)
- [8 AI服务调用模块（F2.5）](#8-ai服务调用模块f25)
- [9 缓存管理模块（F2.6）](#9-缓存管理模块f26)
- [10 模块间依赖与交互](#10-模块间依赖与交互)
- [11 数据模型规范](#11-数据模型规范)
- [12 统一响应与异常处理](#12-统一响应与异常处理)
- [13 安全架构](#13-安全架构)
- [14 配置管理](#14-配置管理)
- [15 性能规范](#15-性能规范)
- [16 日志与监控](#16-日志与监控)
- [17 部署架构](#17-部署架构)

---

## 1 文档概述

### 1.1 编写目的

本文档详细定义科研文献智能助手系统中Java后端6大模块的系统架构，包括模块职责、类设计、接口规范、数据流转、异常处理、缓存策略等内容，为Java后端开发提供完整的设计蓝图。

### 1.2 适用范围

本文档覆盖Java后端全部6个子模块：

| 模块编号 | 模块名称 | 核心职责 |
|---------|---------|---------|
| F2.1 | 用户管理模块 | 用户注册/登录、画像CRUD、JWT鉴权 |
| F2.2 | 论文管理模块 | 论文元数据查询、搜索、收藏 |
| F2.3 | 会话管理模块 | 分析会话生命周期管理 |
| F2.4 | 分析服务模块 | 论文分析/对比/综述的任务编排 |
| F2.5 | AI服务调用模块 | Java-Python通信、请求转换、降级机制 |
| F2.6 | 缓存管理模块 | Redis缓存策略、一致性保障 |

### 1.3 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Spring Boot** | 3.2+ | 主框架 |
| **Spring WebFlux** | 6.1+ | 异步响应式编程、SSE推送 |
| **Spring Data JPA** | 3.2+ | 数据库访问（MySQL） |
| **Spring Data Redis** | 3.2+ | 缓存（Redis 7.0+） |
| **Spring Validation** | 3.2+ | 请求参数校验 |
| **MySQL Connector** | 8.0+ | MySQL驱动 |
| **Lombok** | 1.18+ | 代码简化 |
| **MapStruct** | 1.5+ | DTO/Entity对象映射 |
| **JWT (jjwt)** | 0.12+ | Token生成与验证 |
| **Maven** | 3.9+ | 构建工具 |
| **JDK** | 17+ | 运行时环境 |

---

## 2 Java后端总体架构

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Controller 层                           │
│  接收HTTP请求 → 参数校验(@Valid) → 调用Service → 返回Response │
│  统一异常处理(@ControllerAdvice) → 统一响应格式(ApiResponse)  │
│  JWT鉴权拦截 → 用户身份注入请求上下文                         │
├─────────────────────────────────────────────────────────────┤
│                      Service 层                              │
│  业务逻辑编排 → @Transactional事务管理 → @Cacheable缓存管理   │
│  调用Repository → 调用PythonAIClient → 调用RedisTemplate    │
│  DTO/Entity转换（MapStruct）                                 │
├─────────────────────────────────────────────────────────────┤
│                     Repository 层                            │
│  Spring Data JPA → 数据库CRUD → 自定义@Query查询            │
│  JpaRepository<Entity, ID> → 动态条件构造(Specification)     │
├─────────────────────────────────────────────────────────────┤
│                      Client 层                               │
│  PythonAIClient → WebClient调用Python AI服务                 │
│  超时控制(30s) → 重试机制(1次) → 降级处理 → SSE流式接收      │
├─────────────────────────────────────────────────────────────┤
│                     Infrastructure 层                        │
│  RedisTemplate → 缓存读写 → 分布式锁                         │
│  JwtUtil → Token生成/验证 → 黑名单管理                       │
│  RestTemplate/WebClient → 外部HTTP调用                       │
│  ObjectMapper → JSON序列化/反序列化                           │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 请求流转

```
客户端请求
    │
    ▼
JwtAuthFilter（鉴权拦截器）
    │ 验证Token → 解析userId → 注入SecurityContext
    ▼
Controller（API控制器）
    │ @Valid参数校验 → 调用Service方法
    ▼
Service（业务逻辑）
    │ 查缓存(Redis) → 查数据库(JPA) → 调AI服务(PythonAIClient)
    ▼
Repository（数据访问）
    │ JPA查询 → 返回Entity
    ▼
Service组装结果
    │ Entity → DTO(MapStruct) → 缓存结果(Redis)
    ▼
Controller返回
    │ 封装ApiResponse → JSON响应
    ▼
客户端
```

### 2.3 Java后端与Python AI服务通信架构

```
┌──────────────────────────────────────┐     ┌──────────────────────────────────────┐
│           Java后端 (Spring Boot)      │     │         Python AI服务 (FastAPI)       │
│                                      │     │                                      │
│  AnalysisService                     │     │  /api/agent/analyze                  │
│    │                                 │     │  /api/search                         │
│    ▼                                 │     │  /health                             │
│  AgentClientService                  │     │  /api/model/status                   │
│    │                                 │     │                                      │
│    ├── 同步调用 ──── POST ────────────┼────►│  接收请求                            │
│    │   (WebClient)                   │     │    │                                 │
│    │                                 │     │    ▼                                 │
│    ├── SSE接收 ◄─── SSE Stream ──────┼─────┤  Agent状态推送                      │
│    │   (Flux<ServerSentEvent>)       │     │    │                                 │
│    │                                 │     │    ▼                                 │
│    └── 结果接收 ◄─── HTTP 200 ───────┼─────┤  返回最终结果                       │
│        (Mono<AnalysisResponseDTO>)   │     │                                      │
└──────────────────────────────────────┘     └──────────────────────────────────────┘

通信协议：HTTP REST + SSE
数据格式：JSON
超时设置：同步调用30秒，SSE流120秒
重试策略：失败后重试1次，间隔3秒
降级策略：Python服务不可用时返回缓存结果或提示稍后重试
```

---

## 3 项目结构与规范

### 3.1 包结构

```
com.literatureassistant/
├── LiteratureAssistantApplication.java     # Spring Boot启动类
│
├── config/                                  # 配置类
│   ├── WebConfig.java                      # CORS、拦截器、消息转换器配置
│   ├── RedisConfig.java                    # Redis序列化、TTL、连接池配置
│   ├── WebClientConfig.java                # WebClient（调用Python服务）配置
│   └── SecurityConfig.java                 # JWT鉴权过滤器链配置
│
├── controller/                              # API控制器层
│   ├── UserController.java                 # 用户管理API（F2.1）
│   ├── PaperController.java                # 论文管理API（F2.2）
│   ├── SessionController.java              # 会话管理API（F2.3）
│   ├── AnalysisController.java             # 分析服务API（F2.4）
│   └── AgentController.java               # Agent状态推送API（F2.4+SSE）
│
├── service/                                 # 业务逻辑层
│   ├── UserService.java                    # 用户管理业务（F2.1）
│   ├── PaperService.java                   # 论文管理业务（F2.2）
│   ├── SessionService.java                 # 会话管理业务（F2.3）
│   ├── AnalysisService.java               # 分析服务业务（F2.4）
│   └── AgentClientService.java             # AI服务调用编排（F2.5）
│
├── repository/                              # 数据访问层
│   ├── UserRepository.java
│   ├── PaperRepository.java
│   ├── SessionRepository.java
│   ├── UserProfileRepository.java
│   ├── AnalysisResultRepository.java
│   └── PaperFavoriteRepository.java
│
├── entity/                                  # JPA实体类
│   ├── User.java
│   ├── Paper.java
│   ├── Session.java
│   ├── UserProfile.java
│   ├── AnalysisResult.java
│   └── PaperFavorite.java
│
├── dto/                                     # 数据传输对象
│   ├── request/                            # 请求DTO
│   │   ├── RegisterRequest.java
│   │   ├── LoginRequest.java
│   │   ├── ProfileUpdateRequest.java
│   │   ├── PaperSearchRequest.java
│   │   ├── AnalysisRequest.java
│   │   ├── CompareRequest.java
│   │   └── ReportRequest.java
│   ├── response/                           # 响应DTO
│   │   ├── UserResponse.java
│   │   ├── ProfileResponse.java
│   │   ├── PaperResponse.java
│   │   ├── PaperDetailResponse.java
│   │   ├── SessionResponse.java
│   │   ├── AnalysisResponse.java
│   │   ├── AnalysisStatusResponse.java
│   │   └── AgentStateResponse.java
│   └── common/                             # 通用DTO
│       ├── ApiResponse.java                # 统一响应包装
│       ├── PageResponse.java               # 分页响应
│       └── AgentRequest.java               # 发送给Python服务的请求
│
├── client/                                  # 外部服务客户端
│   └── PythonAIClient.java                # 调用Python AI服务
│
├── mapper/                                  # MapStruct映射器
│   ├── UserMapper.java
│   ├── PaperMapper.java
│   ├── SessionMapper.java
│   └── AnalysisMapper.java
│
├── filter/                                  # 过滤器/拦截器
│   └── JwtAuthFilter.java                  # JWT鉴权过滤器
│
├── exception/                               # 异常定义
│   ├── BusinessException.java              # 业务异常
│   ├── AuthenticationException.java        # 认证异常
│   ├── ResourceNotFoundException.java      # 资源不存在异常
│   ├── AIServiceException.java             # AI服务调用异常
│   └── GlobalExceptionHandler.java         # 全局异常处理器
│
├── enums/                                   # 枚举定义
│   ├── EducationLevel.java                 # 学历层次
│   ├── KnowledgeLevel.java                 # 知识水平
│   ├── PreferredStyle.java                 # 偏好风格
│   ├── SessionStatus.java                  # 会话状态
│   ├── AnalysisType.java                   # 分析类型
│   └── AnalysisStatus.java                 # 分析状态
│
└── util/                                    # 工具类
    ├── JwtUtil.java                        # JWT工具
    ├── RedisKeyUtil.java                   # Redis Key生成工具
    └── DateTimeUtil.java                   # 日期工具
```

### 3.2 命名规范

| 类别 | 规范 | 示例 |
|------|------|------|
| Controller | `{Domain}Controller` | `UserController` |
| Service | `{Domain}Service` | `UserService` |
| Repository | `{Domain}Repository` | `UserRepository` |
| Entity | `{Domain}` | `User` |
| 请求DTO | `{Domain}Request` | `RegisterRequest` |
| 响应DTO | `{Domain}Response` | `UserResponse` |
| Mapper | `{Domain}Mapper` | `UserMapper` |
| API路径 | `/api/{domain}s` | `/api/users` |
| 方法名-查询 | `get/find/list/query` | `getUserById` |
| 方法名-创建 | `create/add/save` | `createUser` |
| 方法名-更新 | `update/modify` | `updateProfile` |
| 方法名-删除 | `delete/remove` | `deleteSession` |

---

## 4 用户管理模块（F2.1）

### 4.1 模块概述

负责用户注册、登录鉴权、用户画像的全生命周期管理。是系统安全的基础模块，为其他模块提供用户身份上下文。

### 4.2 类设计

#### 4.2.1 UserController

```java
@RestController
@RequestMapping("/api/users")
public class UserController {

    @PostMapping("/register")
    public ApiResponse<UserResponse> register(@Valid @RequestBody RegisterRequest request);

    @PostMapping("/login")
    public ApiResponse<LoginResponse> login(@Valid @RequestBody LoginRequest request);

    @GetMapping("/{userId}")
    public ApiResponse<UserResponse> getUserInfo(@PathVariable String userId);

    @PutMapping("/{userId}")
    public ApiResponse<UserResponse> updateUser(@PathVariable String userId,
                                                 @Valid @RequestBody UserUpdateRequest request);

    @GetMapping("/{userId}/profile")
    public ApiResponse<ProfileResponse> getProfile(@PathVariable String userId);

    @PostMapping("/{userId}/profile")
    public ApiResponse<ProfileResponse> createProfile(@PathVariable String userId,
                                                       @Valid @RequestBody ProfileUpdateRequest request);

    @PutMapping("/{userId}/profile")
    public ApiResponse<ProfileResponse> updateProfile(@PathVariable String userId,
                                                       @Valid @RequestBody ProfileUpdateRequest request);

    @PostMapping("/logout")
    public ApiResponse<Void> logout(@RequestHeader("Authorization") String token);
}
```

#### 4.2.2 UserService

```java
@Service
public class UserService {

    // 用户注册
    public UserResponse register(RegisterRequest request);
    // 密码BCrypt加密 → 检查用户名唯一性 → 保存User → 返回UserResponse

    // 用户登录
    public LoginResponse login(LoginRequest request);
    // 查询User → BCrypt验证密码 → 生成JWT Token → 返回Token+userId

    // 查询用户信息
    @Cacheable(value = "userInfo", key = "#userId")
    public UserResponse getUserInfo(String userId);

    // 更新用户信息
    @CacheEvict(value = "userInfo", key = "#userId")
    public UserResponse updateUser(String userId, UserUpdateRequest request);

    // 获取用户画像
    @Cacheable(value = "userProfile", key = "#userId", unless = "#result == null")
    public ProfileResponse getProfile(String userId);
    // 先查Redis缓存 → 缓存未命中查MySQL → 回填缓存

    // 创建用户画像
    @CacheEvict(value = "userProfile", key = "#userId")
    public ProfileResponse createProfile(String userId, ProfileUpdateRequest request);

    // 更新用户画像
    @CacheEvict(value = {"userProfile", "userProfileJson"}, key = "#userId")
    public ProfileResponse updateProfile(String userId, ProfileUpdateRequest request);
    // 更新数据库 → 删除缓存（Cache-Aside Pattern写策略）

    // 退出登录
    public void logout(String token);
    // 解析Token → 将Token加入Redis黑名单（TTL=Token剩余有效期）
}
```

#### 4.2.3 JwtAuthFilter

```java
@Component
public class JwtAuthFilter extends OncePerRequestFilter {

    // 过滤逻辑：
    // 1. 从Header提取Bearer Token
    // 2. 校验Token格式、签名、过期时间
    // 3. 查Redis黑名单（已退出的Token不可用）
    // 4. 解析userId → 注入SecurityContext
    // 5. 放行请求

    // 白名单路径（无需鉴权）：
    // POST /api/users/register
    // POST /api/users/login
    // GET /health
}
```

#### 4.2.4 请求/响应DTO

**RegisterRequest：**
```java
public class RegisterRequest {
    @NotBlank(message = "用户名不能为空")
    @Size(min = 3, max = 50, message = "用户名长度3-50")
    private String username;

    @NotBlank(message = "邮箱不能为空")
    @Email(message = "邮箱格式不正确")
    private String email;

    @NotBlank(message = "密码不能为空")
    @Size(min = 8, max = 100, message = "密码长度8-100")
    private String password;
}
```

**ProfileUpdateRequest：**
```java
public class ProfileUpdateRequest {
    @NotNull(message = "学历层次不能为空")
    private EducationLevel educationLevel;  // undergraduate/master/phd/faculty

    @NotBlank(message = "研究方向不能为空")
    private String researchField;            // NLP/CV/RL/多模态/...

    @NotNull(message = "知识水平不能为空")
    private KnowledgeLevel knowledgeLevel;   // beginner/intermediate/advanced/expert

    @NotNull(message = "偏好风格不能为空")
    private PreferredStyle preferredStyle;   // simple/balanced/technical
}
```

**LoginResponse：**
```java
public class LoginResponse {
    private String token;    // JWT Token
    private String userId;
    private String username;
    private boolean hasProfile;  // 是否已设置画像
}
```

### 4.3 核心业务流程

#### 4.3.1 用户注册流程

```
客户端 POST /api/users/register {username, email, password}
    │
    ▼
UserController.register()
    │ @Valid参数校验
    ▼
UserService.register()
    │ 1. 检查username唯一性（UserRepository.findByUsername）
    │ 2. BCrypt加密密码（BCryptPasswordEncoder.encode）
    │ 3. 生成userId（UUID）
    │ 4. 保存User实体（UserRepository.save）
    ▼
返回 ApiResponse<UserResponse> {userId, username}
```

#### 4.3.2 用户登录流程

```
客户端 POST /api/users/login {username, password}
    │
    ▼
UserService.login()
    │ 1. 根据username查询User
    │ 2. BCrypt验证密码（BCryptPasswordEncoder.matches）
    │ 3. 验证失败 → 抛出AuthenticationException
    │ 4. 生成JWT Token（JwtUtil.generateToken）
    │    Payload: {userId, username, exp: 24h}
    │ 5. 查询用户画像是否存在
    ▼
返回 ApiResponse<LoginResponse> {token, userId, username, hasProfile}
```

#### 4.3.3 画像管理流程

```
创建画像 POST /api/users/{userId}/profile
    │
    ▼
UserService.createProfile()
    │ 1. 验证userId存在
    │ 2. 检查画像是否已存在（不允许重复创建）
    │ 3. RequestDTO → Entity（ProfileMapper）
    │ 4. 保存UserProfile（UserProfileRepository.save）
    │ 5. 删除用户画像缓存（@CacheEvict）
    │ 6. 同步更新Redis中画像JSON（供Python服务使用）
    ▼
返回 ApiResponse<ProfileResponse>

更新画像 PUT /api/users/{userId}/profile
    │
    ▼
UserService.updateProfile()
    │ 1. 查询现有画像
    │ 2. 合并更新字段
    │ 3. 保存更新
    │ 4. 双重缓存失效：userProfile + userProfileJson
    ▼
返回 ApiResponse<ProfileResponse>
```

### 4.4 API接口清单

| 编号 | 方法 | 路径 | 优先级 | 鉴权 | 说明 |
|------|------|------|--------|------|------|
| F2.1.1 | POST | `/api/users/register` | P0 | 否 | 用户注册 |
| F2.1.2 | POST | `/api/users/login` | P0 | 否 | 用户登录 |
| F2.1.3 | GET | `/api/users/{userId}` | P0 | 是 | 查询用户信息 |
| F2.1.4 | PUT | `/api/users/{userId}` | P1 | 是 | 更新用户信息 |
| F2.1.5 | GET | `/api/users/{userId}/profile` | P0 | 是 | 获取用户画像 |
| F2.1.5 | POST | `/api/users/{userId}/profile` | P0 | 是 | 创建用户画像 |
| F2.1.5 | PUT | `/api/users/{userId}/profile` | P0 | 是 | 更新用户画像 |
| - | POST | `/api/users/logout` | P1 | 是 | 退出登录 |

---

## 5 论文管理模块（F2.2）

### 5.1 模块概述

负责论文元数据的存储、查询、搜索和收藏管理。是系统的核心数据模块，为分析服务模块提供论文数据支撑。

### 5.2 类设计

#### 5.2.1 PaperController

```java
@RestController
@RequestMapping("/api/papers")
public class PaperController {

    @GetMapping
    public ApiResponse<PageResponse<PaperResponse>> listPapers(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size);

    @GetMapping("/{paperId}")
    public ApiResponse<PaperDetailResponse> getPaperDetail(@PathVariable String paperId);

    @GetMapping("/search")
    public ApiResponse<PageResponse<PaperResponse>> searchPapers(
            @RequestParam String q,
            @RequestParam(required = false) Integer yearFrom,
            @RequestParam(required = false) Integer yearTo,
            @RequestParam(required = false) String venue,
            @RequestParam(defaultValue = "relevance") String sort,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size);

    @PostMapping("/{paperId}/favorite")
    public ApiResponse<Void> addFavorite(@PathVariable String paperId);

    @DeleteMapping("/{paperId}/favorite")
    public ApiResponse<Void> removeFavorite(@PathVariable String paperId);

    @GetMapping("/favorites")
    public ApiResponse<PageResponse<PaperResponse>> listFavorites(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size);

    @PostMapping("/import")
    public ApiResponse<ImportResult> importPapers(@RequestBody List<PaperImportRequest> papers);
}
```

#### 5.2.2 PaperService

```java
@Service
public class PaperService {

    // 分页查询论文列表
    public PageResponse<PaperResponse> listPapers(int page, int size);
    // PaperRepository.findAll(PageRequest) → Page<Paper> → PageResponse<PaperResponse>

    // 论文详情
    @Cacheable(value = "paperDetail", key = "#paperId", unless = "#result == null")
    public PaperDetailResponse getPaperDetail(String paperId);
    // 查缓存 → 查数据库 → 回填缓存

    // 论文搜索（核心方法）
    @Cacheable(value = "paperSearch", key = "#q + '_' + #yearFrom + '_' + #yearTo + '_' + #venue + '_' + #sort + '_' + #page")
    public PageResponse<PaperResponse> searchPapers(String q, Integer yearFrom,
            Integer yearTo, String venue, String sort, int page, int size);
    // 1. MySQL全文索引检索（MATCH...AGAINST）
    // 2. 条件过滤（年份范围、会议、排序）
    // 3. 返回分页结果

    // 收藏论文
    public void addFavorite(String userId, String paperId);

    // 取消收藏
    public void removeFavorite(String userId, String paperId);

    // 收藏列表
    public PageResponse<PaperResponse> listFavorites(String userId, int page, int size);

    // 批量导入论文
    @Transactional
    public ImportResult importPapers(List<PaperImportRequest> papers);
    // 批量保存 → 去重检查 → 返回导入结果
}
```

#### 5.2.3 PaperRepository 自定义查询

```java
public interface PaperRepository extends JpaRepository<Paper, Long>, JpaSpecificationExecutor<Paper> {

    Optional<Paper> findByPaperId(String paperId);

    // MySQL全文检索
    @Query(value = "SELECT * FROM papers WHERE MATCH(title, abstract) AGAINST(:keyword IN NATURAL LANGUAGE MODE) " +
            "AND (:yearFrom IS NULL OR year >= :yearFrom) " +
            "AND (:yearTo IS NULL OR year <= :yearTo) " +
            "AND (:venue IS NULL OR venue = :venue) " +
            "ORDER BY CASE WHEN :sort = 'relevance' THEN MATCH(title, abstract) AGAINST(:keyword IN NATURAL LANGUAGE MODE) " +
            "WHEN :sort = 'year' THEN year " +
            "WHEN :sort = 'citations' THEN citation_count " +
            "END DESC",
            nativeQuery = true)
    Page<Paper> searchByKeyword(@Param("keyword") String keyword,
                                 @Param("yearFrom") Integer yearFrom,
                                 @Param("yearTo") Integer yearTo,
                                 @Param("venue") String venue,
                                 @Param("sort") String sort,
                                 Pageable pageable);

    List<Paper> findByPaperIdIn(List<String> paperIds);
}
```

### 5.3 搜索策略

```
论文搜索流程：

1. 关键词搜索（MySQL全文索引）
   ├── 输入关键词 → MATCH(title, abstract) AGAINST(keyword)
   ├── 支持中英文混合搜索
   └── 返回按相关度排序的结果

2. 条件过滤
   ├── 年份范围：yearFrom ~ yearTo
   ├── 发表会议：venue
   └── 排序：relevance（相关度）/ year（发表时间）/ citations（引用数）

3. 语义检索（委托Python AI服务）
   ├── Java后端调用 PythonAIClient.search()
   ├── Python端执行Chroma向量检索
   └── 结果返回Java后端

4. 混合检索（P1，RRF融合）
   ├── 并行执行：MySQL关键词检索 + Chroma语义检索
   ├── Reciprocal Rank Fusion融合两路结果
   └── 返回融合排序后的结果
```

### 5.4 API接口清单

| 编号 | 方法 | 路径 | 优先级 | 鉴权 | 说明 |
|------|------|------|--------|------|------|
| F2.2.1 | GET | `/api/papers` | P0 | 是 | 论文分页列表 |
| F2.2.2 | GET | `/api/papers/{paperId}` | P0 | 是 | 论文详情 |
| F2.2.3 | GET | `/api/papers/search` | P0 | 是 | 论文搜索 |
| F2.2.4 | POST | `/api/papers/{paperId}/favorite` | P2 | 是 | 收藏论文 |
| F2.2.4 | DELETE | `/api/papers/{paperId}/favorite` | P2 | 是 | 取消收藏 |
| F2.2.5 | POST | `/api/papers/import` | P2 | 是 | 批量导入论文 |

---

## 6 会话管理模块（F2.3）

### 6.1 模块概述

管理用户的研究分析会话，一个会话代表一次完整的分析流程（从输入主题到获取结果）。会话是连接用户、论文和分析结果的纽带。

### 6.2 类设计

#### 6.2.1 SessionController

```java
@RestController
@RequestMapping("/api/sessions")
public class SessionController {

    @PostMapping
    public ApiResponse<SessionResponse> createSession(@Valid @RequestBody SessionCreateRequest request);

    @GetMapping
    public ApiResponse<PageResponse<SessionResponse>> listSessions(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size);

    @GetMapping("/{sessionId}")
    public ApiResponse<SessionDetailResponse> getSessionDetail(@PathVariable String sessionId);

    @PutMapping("/{sessionId}/status")
    public ApiResponse<Void> updateStatus(@PathVariable String sessionId,
                                           @RequestBody SessionStatusUpdateRequest request);

    @DeleteMapping("/{sessionId}")
    public ApiResponse<Void> deleteSession(@PathVariable String sessionId);
}
```

#### 6.2.2 SessionService

```java
@Service
public class SessionService {

    // 创建会话
    public SessionResponse createSession(String userId, SessionCreateRequest request);
    // 1. 生成sessionId（UUID）
    // 2. 创建Session实体（userId, topic, status=active）
    // 3. 保存到数据库
    // 4. 缓存会话状态到Redis

    // 会话列表
    public PageResponse<SessionResponse> listSessions(String userId, int page, int size);
    // 按用户ID查询，按创建时间倒序

    // 会话详情
    public SessionDetailResponse getSessionDetail(String sessionId);
    // 返回会话信息 + 关联的分析结果列表

    // 更新会话状态
    @CacheEvict(value = "sessionState", key = "#sessionId")
    public void updateStatus(String sessionId, SessionStatus status);
    // active → completed / expired

    // 删除会话
    @Transactional
    public void deleteSession(String sessionId);
    // 删除会话 → 级联删除关联分析结果 → 清除缓存
}
```

### 6.3 会话状态机

```
                    创建
                     │
                     ▼
              ┌─────────────┐
              │   active    │ ← 用户创建会话
              └──────┬──────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
  ┌────────────┐ ┌────────────┐ ┌────────────┐
  │  completed │ │  expired   │ │  (手动关闭) │
  │  分析完成  │ │  超时过期  │ │            │
  └────────────┘ └────────────┘ └────────────┘

状态转换规则：
- active → completed：分析任务完成
- active → expired：会话超过24小时未操作
```

### 6.4 API接口清单

| 编号 | 方法 | 路径 | 优先级 | 鉴权 | 说明 |
|------|------|------|--------|------|------|
| F2.3.1 | POST | `/api/sessions` | P0 | 是 | 创建会话 |
| F2.3.2 | GET | `/api/sessions` | P0 | 是 | 会话列表 |
| F2.3.3 | GET | `/api/sessions/{sessionId}` | P1 | 是 | 会话详情 |
| F2.3.4 | PUT | `/api/sessions/{sessionId}/status` | P1 | 是 | 更新状态 |
| F2.3.5 | DELETE | `/api/sessions/{sessionId}` | P1 | 是 | 删除会话 |

---

## 7 分析服务模块（F2.4）

### 7.1 模块概述

系统的核心业务模块，负责编排论文分析、对比分析和综述生成的完整流程。作为业务编排层，协调用户管理、论文管理、会话管理和AI服务调用模块。

### 7.2 类设计

#### 7.2.1 AnalysisController

```java
@RestController
@RequestMapping("/api/analysis")
public class AnalysisController {

    // 论文分析
    @PostMapping("/paper")
    public ApiResponse<AnalysisTaskResponse> analyzePaper(
            @Valid @RequestBody PaperAnalysisRequest request);

    // 对比分析
    @PostMapping("/compare")
    public ApiResponse<AnalysisTaskResponse> comparePapers(
            @Valid @RequestBody CompareRequest request);

    // 综述生成
    @PostMapping("/report")
    public ApiResponse<AnalysisTaskResponse> generateReport(
            @Valid @RequestBody ReportRequest request);

    // 查询分析结果
    @GetMapping("/{analysisId}")
    public ApiResponse<AnalysisResponse> getAnalysisResult(@PathVariable String analysisId);

    // 查询分析状态
    @GetMapping("/{analysisId}/status")
    public ApiResponse<AnalysisStatusResponse> getAnalysisStatus(@PathVariable String analysisId);

    // Agent状态SSE推送
    @GetMapping(value = "/{analysisId}/agent-stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<AgentStateResponse>> streamAgentStates(@PathVariable String analysisId);
}
```

#### 7.2.2 AnalysisService

```java
@Service
public class AnalysisService {

    private final AgentClientService agentClientService;
    private final UserService userService;
    private final PaperService paperService;
    private final SessionService sessionService;
    private final AnalysisResultRepository analysisResultRepository;

    // 论文分析
    public AnalysisTaskResponse analyzePaper(String userId, PaperAnalysisRequest request) {
        // 1. 获取用户画像（UserService.getProfile → 用于个性化）
        // 2. 获取论文信息（PaperService.getPaperDetail → 用于分析）
        // 3. 创建/获取活跃会话
        // 4. 创建分析任务记录（status=pending）
        // 5. 构建AgentRequest（含用户画像、论文ID、分析类型）
        // 6. 异步调用AgentClientService.analyzePaper()
        // 7. 返回analysisId + status=pending
    }

    // 对比分析
    public AnalysisTaskResponse comparePapers(String userId, CompareRequest request) {
        // 1. 校验论文数量（2-5篇）
        // 2. 获取用户画像
        // 3. 获取所有选中论文信息
        // 4. 创建分析任务记录
        // 5. 构建AgentRequest（type=compare）
        // 6. 异步调用AgentClientService.comparePapers()
        // 7. 返回analysisId
    }

    // 综述生成（核心流程）
    public AnalysisTaskResponse generateReport(String userId, ReportRequest request) {
        // 1. 获取用户画像
        // 2. 获取论文列表（全部检索结果或自选论文）
        // 3. 创建分析会话
        // 4. 创建分析任务记录（type=report, status=pending）
        // 5. 构建完整的AgentRequest：
        //    {
        //      topic: "研究主题",
        //      paperIds: ["p001", "p002", ...],
        //      userProfile: {educationLevel, knowledgeLevel, preferredStyle, researchField},
        //      analysisType: "report"
        //    }
        // 6. 异步调用AgentClientService.generateReport()
        // 7. 启动SSE状态推送
        // 8. 返回analysisId
    }

    // 查询分析结果
    @Cacheable(value = "analysisResult", key = "#analysisId", unless = "#result == null")
    public AnalysisResponse getAnalysisResult(String analysisId) {
        // 1. 查询AnalysisResult实体
        // 2. 解析JSON结果字段
        // 3. 返回结构化响应
    }

    // 查询分析状态
    public AnalysisStatusResponse getAnalysisStatus(String analysisId) {
        // 1. 查询分析任务状态
        // 2. 查询Agent实时状态（从Redis）
        // 3. 返回 {status, progress, currentAgent, agentStates[]}
    }

    // 更新分析结果（由Agent回调或轮询触发）
    @CacheEvict(value = "analysisResult", key = "#analysisId")
    public void updateAnalysisResult(String analysisId, AnalysisStatus status, String resultJson) {
        // 1. 更新AnalysisResult实体
        // 2. 如果完成，更新Session状态
        // 3. 缓存结果到Redis
    }
}
```

### 7.3 分析任务状态机

```
                    创建任务
                     │
                     ▼
              ┌─────────────┐
              │   pending   │ ← 任务创建
              └──────┬──────┘
                     │ Agent开始执行
                     ▼
              ┌─────────────┐
              │  processing │ ← Agent协同执行中
              └──────┬──────┘
                     │
         ┌───────────┼───────────┐
         │                       │
         ▼                       ▼
  ┌────────────┐          ┌────────────┐
  │  completed │          │   failed   │
  │  分析完成  │          │  分析失败  │
  └────────────┘          └────────────┘
```

### 7.4 综述生成完整时序

```
前端 → Java后端 → Python AI服务

1. POST /api/analysis/report {topic, paperIds[], userId}
    │
    ▼ Java后端
    AnalysisService.generateReport()
    ├── 获取用户画像
    ├── 创建Session + AnalysisResult
    ├── 构建AgentRequest
    └── 调用AgentClientService.generateReport()
         │
         ▼ Python AI服务
         POST /api/agent/analyze
         {topic, paperIds, userProfile, analysisType}
              │
              ├── 协调者Agent分解任务
              ├── 检索Agent检索论文
              ├── 分析Agent分析内容
              ├── 对比Agent对比（可选）
              ├── 生成Agent生成综述
              └── 审核Agent审核内容
              │
              ▼ SSE推送Agent状态
         ← SSE: agent_state_update
              │
              ▼ 最终结果返回
         ← HTTP 200: {report, citations, agentStates}
    │
    ▼ Java后端
    ├── 解析响应 → 保存AnalysisResult
    ├── 缓存结果到Redis
    └── 更新Session状态为completed
    │
    ▼ 前端
    GET /api/analysis/{analysisId} → 展示综述内容
```

### 7.5 API接口清单

| 编号 | 方法 | 路径 | 优先级 | 鉴权 | 说明 |
|------|------|------|--------|------|------|
| F2.4.1 | POST | `/api/analysis/paper` | P0 | 是 | 论文分析请求 |
| F2.4.2 | POST | `/api/analysis/compare` | P1 | 是 | 对比分析请求 |
| F2.4.3 | POST | `/api/analysis/report` | P0 | 是 | 综述生成请求 |
| F2.4.4 | GET | `/api/analysis/{analysisId}` | P0 | 是 | 分析结果查询 |
| F2.4.5 | GET | `/api/analysis/{analysisId}/status` | P0 | 是 | 分析状态查询 |
| - | GET | `/api/analysis/{analysisId}/agent-stream` | P1 | 是 | Agent状态SSE推送 |

---

## 8 AI服务调用模块（F2.5）

### 8.1 模块概述

封装Java后端与Python AI服务之间的所有通信逻辑，是Java与Python混合架构的核心桥梁。负责请求转换、HTTP调用、SSE接收、错误处理和降级机制。

### 8.2 类设计

#### 8.2.1 PythonAIClient

```java
@Component
public class PythonAIClient {

    private final WebClient webClient;  // Spring WebFlux WebClient

    // Python AI服务基础URL，从配置读取
    @Value("${ai-service.url}")
    private String aiServiceUrl;

    // 同步调用Python服务（论文分析）
    public AnalysisResultDTO analyzePaper(AgentRequest request) {
        // POST {aiServiceUrl}/api/agent/analyze
        // 超时：30秒
        // 重试：1次（间隔3秒）
    }

    // 同步调用Python服务（对比分析）
    public AnalysisResultDTO comparePapers(AgentRequest request) {
        // POST {aiServiceUrl}/api/agent/analyze
        // type=compare
    }

    // 异步调用Python服务（综述生成，支持SSE）
    public Mono<AnalysisResultDTO> generateReport(AgentRequest request) {
        // POST {aiServiceUrl}/api/agent/analyze
        // type=report
        // 接收SSE流 → 实时更新Agent状态到Redis → 最终接收完整结果
    }

    // 语义检索（委托Python服务）
    public List<PaperSearchResultDTO> search(String query, int topK) {
        // POST {aiServiceUrl}/api/search
        // {query, topK}
    }

    // 健康检查
    public boolean isHealthy() {
        // GET {aiServiceUrl}/health
        // 超时：5秒
    }

    // 查询模型状态
    public ModelStatusDTO getModelStatus() {
        // GET {aiServiceUrl}/api/model/status
    }
}
```

#### 8.2.2 AgentClientService

```java
@Service
public class AgentClientService {

    private final PythonAIClient pythonAIClient;
    private final RedisTemplate<String, String> redisTemplate;

    // 论文分析调用
    public AnalysisResultDTO analyzePaper(AgentRequest request) {
        try {
            return pythonAIClient.analyzePaper(request);
        } catch (AIServiceException e) {
            // 降级处理：返回缓存结果或提示错误
            return handleFallback(request, e);
        }
    }

    // 对比分析调用
    public AnalysisResultDTO comparePapers(AgentRequest request) {
        try {
            return pythonAIClient.comparePapers(request);
        } catch (AIServiceException e) {
            return handleFallback(request, e);
        }
    }

    // 综述生成调用（异步 + SSE）
    public Mono<AnalysisResultDTO> generateReport(AgentRequest request) {
        return pythonAIClient.generateReport(request)
            .doOnNext(result -> {
                // 1. 保存结果到Redis
                cacheResult(request.getAnalysisId(), result);
                // 2. 更新Agent状态
                updateAgentStates(request.getAnalysisId(), result.getAgentStates());
            })
            .onErrorResume(e -> {
                // 降级：返回缓存或部分结果
                return Mono.just(handleFallback(request, e));
            });
    }

    // 降级处理
    private AnalysisResultDTO handleFallback(AgentRequest request, Exception e) {
        // 1. 查询Redis缓存（之前相同或类似的分析结果）
        AnalysisResultDTO cached = getFromCache(request);
        if (cached != null) {
            cached.setDegraded(true);
            cached.setDegradedReason("AI服务暂时不可用，返回缓存结果");
            return cached;
        }
        // 2. 无缓存，返回降级提示
        return AnalysisResultDTO.degraded("AI服务暂时不可用，请稍后重试");
    }

    // Agent状态更新到Redis
    private void updateAgentStates(String analysisId, List<AgentStateDTO> agentStates) {
        String key = RedisKeyUtil.agentStateKey(analysisId);
        redisTemplate.opsForValue().set(key,
            objectMapper.writeValueAsString(agentStates),
            Duration.ofMinutes(5));
    }
}
```

### 8.3 请求/响应格式

#### 发送给Python服务的请求格式

```json
{
    "topic": "Multi-Agent协同决策",
    "paperIds": ["arxiv_2024_001", "arxiv_2024_002"],
    "userProfile": {
        "educationLevel": "master",
        "researchField": "NLP",
        "knowledgeLevel": "intermediate",
        "preferredStyle": "balanced"
    },
    "analysisType": "report",        // paper_analysis / compare / report
    "analysisId": "anl_20240523_001"  // Java端生成的分析任务ID
}
```

#### Python服务返回的响应格式

```json
{
    "analysisId": "anl_20240523_001",
    "status": "completed",
    "result": {
        "report": "## 文献综述\n...",
        "citations": [
            {"paperId": "arxiv_2024_001", "text": "原文片段", "location": "第3段"}
        ],
        "structure": {
            "introduction": "...",
            "currentStatus": "...",
            "methodComparison": "...",
            "trends": "...",
            "references": "..."
        }
    },
    "agentStates": [
        {"name": "coordinator", "status": "completed", "durationMs": 2000, "intermediateResult": "分解为4个子任务"},
        {"name": "retriever", "status": "completed", "durationMs": 1200, "intermediateResult": "找到15篇相关论文"},
        {"name": "analyzer", "status": "completed", "durationMs": 8000, "intermediateResult": "已分析10篇论文"},
        {"name": "generator", "status": "completed", "durationMs": 15000, "intermediateResult": "综述生成完毕"},
        {"name": "reviewer", "status": "completed", "durationMs": 5000, "intermediateResult": "审核通过"}
    ]
}
```

#### SSE事件格式

```
event: agent_state_update
data: {"agentName":"retriever","status":"running","progress":0.3,"analysisId":"anl_001"}

event: agent_state_update
data: {"agentName":"retriever","status":"completed","intermediateResult":"找到10篇论文","durationMs":1200,"analysisId":"anl_001"}

event: agent_state_update
data: {"agentName":"analyzer","status":"running","progress":0.8,"intermediateResult":"已分析8/10篇","analysisId":"anl_001"}

event: analysis_completed
data: {"analysisId":"anl_001","status":"completed"}
```

### 8.4 降级策略

```
降级层级：

Level 1：Python服务正常
├── 直接调用Python AI服务
└── 正常返回结果

Level 2：Python服务超时（>30秒）
├── 重试1次（间隔3秒）
├── 仍然超时 → 进入Level 3
└── 记录超时日志

Level 3：Python服务不可用
├── 查询Redis缓存（同主题/同论文的历史分析结果）
├── 有缓存 → 返回缓存结果 + 降级标记
└── 无缓存 → 返回降级提示"AI服务暂时不可用，请稍后重试"

降级响应格式：
{
    "analysisId": "anl_001",
    "status": "degraded",
    "result": null,
    "degradedReason": "AI服务暂时不可用，返回缓存结果",
    "cachedAt": "2026-05-23T10:30:00"
}
```

### 8.5 功能清单

| 编号 | 功能 | 优先级 | 说明 |
|------|------|--------|------|
| F2.5.1 | Python服务客户端 | P0 | WebClient封装，连接池管理，超时30秒，重试1次 |
| F2.5.2 | 请求转换 | P0 | Java DTO → Python JSON格式，包含用户画像、论文ID列表 |
| F2.5.3 | 响应解析 | P0 | Python JSON → Java DTO，处理嵌套JSON |
| F2.5.4 | 异步调用 | P1 | WebFlux + SSE，支持流式推送Agent状态 |
| F2.5.5 | 错误处理 | P1 | 超时/不可用/返回错误 → 降级机制 |

---

## 9 缓存管理模块（F2.6）

### 9.1 模块概述

基于Spring Data Redis实现的统一缓存管理层，为所有业务模块提供缓存读写、失效、一致性保障能力。

### 9.2 RedisConfig

```java
@Configuration
@EnableCaching
public class RedisConfig {

    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory factory) {
        // 默认TTL：30分钟
        RedisCacheConfiguration defaultConfig = RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(30))
            .serializeKeysWith(RedisSerializationContext.SerializationPair
                .fromSerializer(new StringRedisSerializer()))
            .serializeValuesWith(RedisSerializationContext.SerializationPair
                .fromSerializer(new GenericJackson2JsonRedisSerializer()));

        // 各缓存空间的自定义TTL
        Map<String, RedisCacheConfiguration> cacheConfigurations = new HashMap<>();
        cacheConfigurations.put("userProfile", defaultConfig.entryTtl(Duration.ofHours(1)));
        cacheConfigurations.put("userInfo", defaultConfig.entryTtl(Duration.ofHours(1)));
        cacheConfigurations.put("paperDetail", defaultConfig.entryTtl(Duration.ofMinutes(30)));
        cacheConfigurations.put("paperSearch", defaultConfig.entryTtl(Duration.ofMinutes(10)));
        cacheConfigurations.put("analysisResult", defaultConfig.entryTtl(Duration.ofMinutes(30)));
        cacheConfigurations.put("sessionState", defaultConfig.entryTtl(Duration.ofHours(2)));

        return RedisCacheManager.builder(factory)
            .cacheDefaults(defaultConfig)
            .withInitialCacheConfigurations(cacheConfigurations)
            .build();
    }

    @Bean
    public RedisTemplate<String, String> redisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, String> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new StringRedisSerializer());
        return template;
    }
}
```

### 9.3 缓存策略详情

| 缓存空间 | Key格式 | TTL | 数据结构 | 失效策略 | 命中率预期 |
|---------|---------|-----|---------|---------|-----------|
| **用户画像** | `user:profile:{userId}` | 1小时 | String(JSON) | 画像更新时主动失效（@CacheEvict） | >50% |
| **用户信息** | `user:info:{userId}` | 1小时 | String(JSON) | 用户信息更新时主动失效 | >60% |
| **论文详情** | `paper:detail:{paperId}` | 30分钟 | String(JSON) | 论文导入时批量失效 | >40% |
| **论文搜索** | `search:result:{queryHash}` | 10分钟 | String(JSON) | 新论文导入时清空搜索缓存 | >30% |
| **分析结果** | `analysis:result:{analysisId}` | 30分钟 | String(JSON) | 结果更新时失效 | >20% |
| **会话状态** | `session:state:{sessionId}` | 2小时 | String(JSON) | 会话完成/删除时失效 | >80% |
| **Agent状态** | `agent:state:{analysisId}` | 5分钟 | Hash | 分析完成后自然过期 | 实时数据 |
| **Token黑名单** | `auth:blacklist:{tokenHash}` | Token剩余有效期 | String | 自然过期 | - |

### 9.4 缓存一致性策略

```
Cache-Aside Pattern（旁路缓存）：

读操作：
1. 先读Redis缓存
2. 缓存命中 → 直接返回
3. 缓存未命中 → 查MySQL → 回填Redis → 返回

写操作：
1. 先更新MySQL
2. 再删除Redis缓存（@CacheEvict）
3. 下次读取时从MySQL重新加载

特殊场景：
- 用户画像更新：双重失效（userProfile + userProfileJson）
  userProfileJson供Python服务使用，需同步失效
- 论文导入：清空所有搜索缓存
  因为新论文会影响搜索结果
- Agent状态：仅通过Redis存储，不经过MySQL
  实时性要求高，自然过期即可
```

### 9.5 功能清单

| 编号 | 功能 | 优先级 | 缓存策略 | 验收标准 |
|------|------|--------|---------|---------|
| F2.6.1 | 用户画像缓存 | P0 | TTL 1小时，画像更新时主动失效 | 缓存命中率>50%，画像更新后缓存失效 |
| F2.6.2 | 论文检索缓存 | P1 | TTL 10分钟，基于查询参数生成Key | 相同查询直接返回缓存 |
| F2.6.3 | 分析结果缓存 | P1 | TTL 30分钟，同一论文+同一画像可复用 | 相同分析请求命中缓存 |
| F2.6.4 | 会话状态缓存 | P1 | TTL 2小时，会话结束时清除 | 会话状态读写正确 |

---

## 10 模块间依赖与交互

### 10.1 模块依赖关系图

```
┌─────────────────────────────────────────────────────────────┐
│                     Controller 层                            │
│                                                             │
│  UserController    PaperController    SessionController     │
│  AnalysisController                                   │
└────────┬──────────────┬──────────────┬──────────────┬───────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service 层                              │
│                                                             │
│  UserService ────────────────────────────────────────────── │
│      │         PaperService ─────────────────────────────── │
│      │             │         SessionService ────────────────│
│      │             │             │         AnalysisService  │
│      │             │             │             │            │
│      │             │             │             │            │
│      ▼             ▼             ▼             ▼            │
│  ┌────────────────────────────────────────────────────┐     │
│  │          AgentClientService (F2.5)                  │     │
│  │          编排AI服务调用                              │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                   基础设施层                                  │
│                                                             │
│  UserRepository  PaperRepository  SessionRepository         │
│  UserProfileRepository  AnalysisResultRepository            │
│  PaperFavoriteRepository                                    │
│                                                             │
│  PythonAIClient ──── HTTP ──── Python AI Service            │
│  RedisTemplate ──── Redis Cache                             │
│  JwtUtil ──── Token Management                              │
└─────────────────────────────────────────────────────────────┘
```

### 10.2 模块调用关系矩阵

| 调用方 | 被调用方 | 调用方式 | 说明 |
|--------|---------|---------|------|
| AnalysisService | UserService | 方法调用 | 获取用户画像 |
| AnalysisService | PaperService | 方法调用 | 获取论文信息 |
| AnalysisService | SessionService | 方法调用 | 创建/管理会话 |
| AnalysisService | AgentClientService | 方法调用 | 发起AI分析 |
| AgentClientService | PythonAIClient | 方法调用 | HTTP调用Python服务 |
| AnalysisService | RedisTemplate | 直接调用 | Agent状态缓存 |
| UserService | RedisTemplate | 注解调用 | 用户画像缓存 |
| PaperService | RedisTemplate | 注解调用 | 搜索结果缓存 |

### 10.3 跨模块数据流

#### 综述生成完整数据流

```
1. AnalysisController.generateReport()
   │ 接收 ReportRequest {topic, paperIds[], userId}
   ▼
2. AnalysisService.generateReport()
   │
   ├──→ UserService.getProfile(userId)
   │    │ Redis缓存命中？→ 返回ProfileResponse
   │    │ 缓存未命中 → MySQL查询 → 回填Redis
   │    └── 返回 ProfileResponse {educationLevel, knowledgeLevel, ...}
   │
   ├──→ PaperService.getPapersByIds(paperIds)
   │    │ 批量查询论文信息
   │    └── 返回 List<PaperDetailResponse>
   │
   ├──→ SessionService.createSession(userId, topic)
   │    │ 创建分析会话
   │    └── 返回 SessionResponse {sessionId}
   │
   ├──→ 创建 AnalysisResult（status=pending）
   │    └── 保存到MySQL
   │
   └──→ AgentClientService.generateReport(agentRequest)
        │
        └──→ PythonAIClient.generateReport()
             │ POST /api/agent/analyze
             │ 异步WebClient调用
             │
             ├── SSE: Agent状态推送 → 更新Redis
             └── 最终结果返回 → 解析响应

3. 结果处理
   │
   ├── 保存 AnalysisResult（status=completed, result=JSON）
   ├── 缓存到Redis
   └── 更新Session状态
```

---

## 11 数据模型规范

### 11.1 Entity类设计规范

```java
// Entity类规范示例
@Entity
@Table(name = "users")
@Data                              // Lombok: getter/setter/toString/equals/hashCode
@NoArgsConstructor                 // Lombok: 无参构造器
@AllArgsConstructor                // Lombok: 全参构造器
@Builder                           // Lombok: Builder模式
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", unique = true, nullable = false, length = 100)
    private String userId;

    @Column(nullable = false, length = 100)
    private String username;

    @Column(length = 200)
    private String email;

    @Column(name = "password_hash", nullable = false, length = 200)
    private String passwordHash;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
```

### 11.2 Entity-Repository映射

| Entity | Repository | 主表 | 说明 |
|--------|-----------|------|------|
| `User` | `UserRepository` | users | 用户基础信息 |
| `UserProfile` | `UserProfileRepository` | user_profiles | 用户画像（1:1关联User） |
| `Paper` | `PaperRepository` | papers | 论文元数据 |
| `Session` | `SessionRepository` | sessions | 分析会话 |
| `AnalysisResult` | `AnalysisResultRepository` | analysis_results | 分析结果 |
| `PaperFavorite` | `PaperFavoriteRepository` | paper_favorites | 论文收藏 |

### 11.3 枚举类型定义

```java
// 学历层次
public enum EducationLevel {
    UNDERGRADUATE("undergraduate", "本科"),
    MASTER("master", "硕士"),
    PHD("phd", "博士"),
    FACULTY("faculty", "教师");

    private final String code;
    private final String label;
}

// 知识水平
public enum KnowledgeLevel {
    BEGINNER("beginner", "初级"),
    INTERMEDIATE("intermediate", "中级"),
    ADVANCED("advanced", "高级"),
    EXPERT("expert", "专家");
}

// 偏好风格
public enum PreferredStyle {
    SIMPLE("simple", "通俗"),
    BALANCED("balanced", "均衡"),
    TECHNICAL("technical", "专业");
}

// 会话状态
public enum SessionStatus {
    ACTIVE, COMPLETED, EXPIRED
}

// 分析类型
public enum AnalysisType {
    PAPER_ANALYSIS, COMPARE, REPORT
}

// 分析状态
public enum AnalysisStatus {
    PENDING, PROCESSING, COMPLETED, FAILED
}
```

---

## 12 统一响应与异常处理

### 12.1 统一响应格式

```java
@Data
@Builder
public class ApiResponse<T> {
    private int code;        // 业务状态码：200成功，400参数错误，401未认证，403无权限，500服务器错误
    private String message;  // 响应消息
    private T data;          // 响应数据
    private long timestamp;  // 时间戳

    public static <T> ApiResponse<T> success(T data) {
        return ApiResponse.<T>builder()
            .code(200)
            .message("success")
            .data(data)
            .timestamp(System.currentTimeMillis())
            .build();
    }

    public static <T> ApiResponse<T> error(int code, String message) {
        return ApiResponse.<T>builder()
            .code(code)
            .message(message)
            .timestamp(System.currentTimeMillis())
            .build();
    }
}
```

### 12.2 分页响应格式

```java
@Data
@Builder
public class PageResponse<T> {
    private List<T> items;     // 数据列表
    private long total;        // 总记录数
    private int page;          // 当前页码
    private int size;          // 每页大小
    private int totalPages;    // 总页数
}
```

### 12.3 异常体系

```java
// 业务异常基类
public class BusinessException extends RuntimeException {
    private final int code;
    public BusinessException(int code, String message) {
        super(message);
        this.code = code;
    }
}

// 认证异常
public class AuthenticationException extends BusinessException {
    public AuthenticationException(String message) {
        super(401, message);
    }
}

// 资源不存在异常
public class ResourceNotFoundException extends BusinessException {
    public ResourceNotFoundException(String resource, String id) {
        super(404, resource + " not found: " + id);
    }
}

// AI服务调用异常
public class AIServiceException extends BusinessException {
    public AIServiceException(String message, Throwable cause) {
        super(503, message, cause);
    }
}
```

### 12.4 全局异常处理器

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    // 参数校验异常
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ApiResponse<Void> handleValidation(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
            .map(f -> f.getField() + ": " + f.getDefaultMessage())
            .collect(Collectors.joining("; "));
        return ApiResponse.error(400, message);
    }

    // 认证异常
    @ExceptionHandler(AuthenticationException.class)
    public ApiResponse<Void> handleAuth(AuthenticationException e) {
        return ApiResponse.error(e.getCode(), e.getMessage());
    }

    // 资源不存在
    @ExceptionHandler(ResourceNotFoundException.class)
    public ApiResponse<Void> handleNotFound(ResourceNotFoundException e) {
        return ApiResponse.error(e.getCode(), e.getMessage());
    }

    // AI服务异常
    @ExceptionHandler(AIServiceException.class)
    public ApiResponse<Void> handleAIService(AIServiceException e) {
        return ApiResponse.error(e.getCode(), "AI服务暂时不可用，请稍后重试");
    }

    // 其他异常
    @ExceptionHandler(Exception.class)
    public ApiResponse<Void> handleGeneral(Exception e) {
        log.error("Unexpected error", e);
        return ApiResponse.error(500, "服务器内部错误");
    }
}
```

---

## 13 安全架构

### 13.1 JWT鉴权流程

```
┌──────────────────────────────────────────────────────────┐
│                     JWT鉴权流程                           │
│                                                          │
│  1. 用户登录                                             │
│     POST /api/users/login {username, password}            │
│     │                                                    │
│     ▼                                                    │
│  2. 验证密码（BCrypt比对）                               │
│     │                                                    │
│     ▼                                                    │
│  3. 生成JWT Token                                        │
│     Header:  {"alg":"HS256","typ":"JWT"}                 │
│     Payload: {"userId":"usr_001","username":"张三",       │
│               "exp":1716451200}                           │
│     Signature: HMACSHA256(base64(header)+"."+            │
│                base64(payload), secret)                   │
│     过期时间：24小时                                     │
│     │                                                    │
│     ▼                                                    │
│  4. 返回Token                                            │
│     {token: "eyJhbG...", userId: "usr_001"}              │
│                                                          │
│  5. 后续请求                                             │
│     Authorization: Bearer eyJhbG...                      │
│     │                                                    │
│     ▼                                                    │
│  6. JwtAuthFilter拦截                                    │
│     ├── 提取Bearer Token                                │
│     ├── 验证签名 + 过期时间                              │
│     ├── 查Redis黑名单（退出登录的Token）                 │
│     ├── 解析userId → 注入SecurityContext                 │
│     └── 放行请求                                         │
│                                                          │
│  7. 退出登录                                             │
│     POST /api/users/logout                               │
│     │                                                    │
│     ▼                                                    │
│  8. Token加入Redis黑名单                                 │
│     Key: auth:blacklist:{tokenHash}                      │
│     TTL: Token剩余有效期                                 │
└──────────────────────────────────────────────────────────┘
```

### 13.2 安全措施清单

| 措施 | 实现方式 | 优先级 |
|------|---------|--------|
| 密码加密 | BCrypt哈希存储，盐值随机 | P0 |
| 传输加密 | 生产环境HTTPS | P1 |
| 请求鉴权 | JWT Token + Redis黑名单 | P0 |
| 参数校验 | Spring Validation (@Valid) | P0 |
| SQL注入防护 | JPA参数化查询，禁止拼接SQL | P0 |
| XSS防护 | 前端输入转义，Content-Security-Policy头 | P1 |
| 敏感配置 | API密钥通过环境变量注入(.env) | P0 |
| 数据隔离 | 用户只能访问自己的会话和分析结果 | P0 |
| CORS配置 | 限制允许的Origin | P0 |
| 请求限流 | Spring Boot Rate Limiter（可选） | P2 |

---

## 14 配置管理

### 14.1 application.yml 主配置

```yaml
server:
  port: 8080
  servlet:
    context-path: /

spring:
  application:
    name: literature-assistant

  # MySQL配置
  datasource:
    url: ${MYSQL_URL:jdbc:mysql://localhost:3306/literature_assistant?useUnicode=true&characterEncoding=utf8mb4&serverTimezone=Asia/Shanghai}
    username: ${MYSQL_USERNAME:root}
    password: ${MYSQL_PASSWORD:root123}
    driver-class-name: com.mysql.cj.jdbc.Driver
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
      connection-timeout: 30000

  # JPA配置
  jpa:
    hibernate:
      ddl-auto: update    # 开发环境: update; 生产环境: validate
    show-sql: false
    properties:
      hibernate:
        dialect: org.hibernate.dialect.MySQL8Dialect
        format_sql: true

  # Redis配置
  data:
    redis:
      host: ${REDIS_HOST:localhost}
      port: ${REDIS_PORT:6379}
      password: ${REDIS_PASSWORD:}
      timeout: 5000
      lettuce:
        pool:
          max-active: 20
          max-idle: 10
          min-idle: 5

  # Jackson配置
  jackson:
    date-format: yyyy-MM-dd HH:mm:ss
    time-zone: Asia/Shanghai
    default-property-inclusion: non_null

# AI服务配置
ai-service:
  url: ${AI_SERVICE_URL:http://localhost:8000}
  timeout: 30000          # 调用超时30秒
  retry-count: 1          # 重试1次
  retry-interval: 3000    # 重试间隔3秒

# JWT配置
jwt:
  secret: ${JWT_SECRET:literature-assistant-jwt-secret-key-2026}
  expiration: 86400000    # 24小时（毫秒）

# 日志配置
logging:
  level:
    root: INFO
    com.literatureassistant: DEBUG
    org.springframework.web: INFO
    org.hibernate.SQL: DEBUG
  pattern:
    console: "%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - [%X{requestId}] %msg%n"
```

### 14.2 环境配置分离

```
application.yml           # 公共配置
application-dev.yml       # 开发环境（本地MySQL、Redis、AI服务）
application-prod.yml      # 生产环境（Docker内服务发现）
```

### 14.3 环境变量清单

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `MYSQL_URL` | MySQL连接URL | `jdbc:mysql://localhost:3306/literature_assistant` |
| `MYSQL_USERNAME` | MySQL用户名 | `root` |
| `MYSQL_PASSWORD` | MySQL密码 | `root123` |
| `REDIS_HOST` | Redis主机 | `localhost` |
| `REDIS_PORT` | Redis端口 | `6379` |
| `REDIS_PASSWORD` | Redis密码 | 空 |
| `AI_SERVICE_URL` | Python AI服务URL | `http://localhost:8000` |
| `JWT_SECRET` | JWT签名密钥 | 内置默认值 |
| `SPRING_PROFILES_ACTIVE` | 激活的Profile | `dev` |

---

## 15 性能规范

### 15.1 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| API接口平均响应时间（非AI调用） | ≤ 500ms | 用户、论文、会话等CRUD接口 |
| 论文检索响应时间 | ≤ 3秒 | MySQL全文索引 + Redis缓存 |
| JWT鉴权耗时 | ≤ 10ms | Token验证 + Redis黑名单查询 |
| Redis缓存命中率 | > 50% | 用户画像和检索结果缓存 |
| 数据库连接池利用率 | < 80% | HikariCP监控 |
| 并发用户支持 | ≥ 50 | 单机部署 |

### 15.2 性能优化策略

| 优化项 | 策略 | 涉及模块 |
|--------|------|---------|
| 数据库查询 | JPA JOIN FETCH避免N+1问题；分页查询；索引优化 | Repository层 |
| 缓存 | Cache-Aside Pattern；TTL分级；主动失效 | F2.6 |
| 异步调用 | WebFlux异步调用Python服务；SSE流式推送 | F2.5 |
| 连接池 | HikariCP(max=20)；Redis连接池(max-active=20) | Config |
| 分页 | 所有列表接口强制分页，避免全量加载 | Controller层 |

---

## 16 日志与监控

### 16.1 日志规范

```
日志格式：
{时间} [{线程}] {级别} {类名} - [{请求ID}] {消息}

日志级别使用规范：
- ERROR：系统异常、AI服务不可用、数据库连接失败
- WARN：业务异常（用户不存在、参数错误）、降级触发
- INFO：关键业务操作（用户注册/登录、分析任务创建/完成）
- DEBUG：SQL查询、缓存命中/未命中、API请求/响应

请求ID（RequestId）：
- 每个HTTP请求进入时生成UUID
- 通过MDC注入日志上下文
- 用于链路追踪（前端 → Java → Python）
```

### 16.2 关键日志点

| 操作 | 日志级别 | 日志内容 |
|------|---------|---------|
| 用户注册 | INFO | `User registered: userId={}` |
| 用户登录 | INFO | `User logged in: userId={}` |
| 论文搜索 | DEBUG | `Paper search: query={}, results={}, time={}ms` |
| 分析任务创建 | INFO | `Analysis created: analysisId={}, type={}, userId={}` |
| AI服务调用 | DEBUG | `AI service call: url={}, duration={}ms` |
| AI服务超时 | WARN | `AI service timeout: url={}, timeout={}ms` |
| AI服务降级 | WARN | `AI service fallback: analysisId={}, reason={}` |
| 缓存命中 | DEBUG | `Cache hit: key={}` |
| 缓存未命中 | DEBUG | `Cache miss: key={}` |
| 异常 | ERROR | `Exception: {}`, exception |

### 16.3 健康检查

```java
// Spring Boot Actuator健康检查
@RestController
public class HealthController {

    @GetMapping("/health")
    public Map<String, Object> health() {
        Map<String, Object> status = new HashMap<>();
        status.put("status", "UP");
        status.put("timestamp", System.currentTimeMillis());

        // 检查MySQL连接
        status.put("mysql", checkMySQL() ? "UP" : "DOWN");

        // 检查Redis连接
        status.put("redis", checkRedis() ? "UP" : "DOWN");

        // 检查Python AI服务
        status.put("aiService", pythonAIClient.isHealthy() ? "UP" : "DOWN");

        return status;
    }
}
```

---

## 17 部署架构

### 17.1 Java后端Dockerfile

```dockerfile
FROM eclipse-temurin:17-jdk-alpine
VOLUME /tmp
ARG JAR_FILE=target/*.jar
COPY ${JAR_FILE} app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app.jar", "--spring.profiles.active=prod"]
```

### 17.2 Docker Compose中的Java后端配置

```yaml
java-backend:
  build: ./backend-java
  ports:
    - "8080:8080"
  environment:
    - SPRING_PROFILES_ACTIVE=prod
    - AI_SERVICE_URL=http://ai-service:8000
    - MYSQL_URL=jdbc:mysql://mysql:3306/literature_assistant?useUnicode=true&characterEncoding=utf8mb4&serverTimezone=Asia/Shanghai
    - MYSQL_USERNAME=root
    - MYSQL_PASSWORD=${MYSQL_ROOT_PASSWORD}
    - REDIS_HOST=redis
    - JWT_SECRET=${JWT_SECRET}
  networks:
    - app-network
  depends_on:
    mysql:
      condition: service_healthy
    redis:
      condition: service_healthy
    ai-service:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### 17.3 启动依赖顺序

```
MySQL (健康检查通过)
    │
    ▼
Redis (健康检查通过)
    │
    ▼
Python AI服务 (健康检查通过)
    │
    ▼
Java后端 (依赖以上三个服务)
    │
    ▼
Nginx前端 (依赖Java后端)
```

---

## 附录A：核心Maven依赖

```xml
<dependencies>
    <!-- Spring Boot Starters -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-webflux</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-redis</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>

    <!-- Database -->
    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-j</artifactId>
        <scope>runtime</scope>
    </dependency>

    <!-- JWT -->
    <dependency>
        <groupId>io.jsonwebtoken</groupId>
        <artifactId>jjwt-api</artifactId>
        <version>0.12.5</version>
    </dependency>
    <dependency>
        <groupId>io.jsonwebtoken</groupId>
        <artifactId>jjwt-impl</artifactId>
        <version>0.12.5</version>
        <scope>runtime</scope>
    </dependency>
    <dependency>
        <groupId>io.jsonwebtoken</groupId>
        <artifactId>jjwt-jackson</artifactId>
        <version>0.12.5</version>
        <scope>runtime</scope>
    </dependency>

    <!-- Tools -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
    <dependency>
        <groupId>org.mapstruct</groupId>
        <artifactId>mapstruct</artifactId>
        <version>1.5.5.Final</version>
    </dependency>

    <!-- Testing -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

---

## 附录B：Java后端开发检查清单

```
□ 每个Controller方法是否有@Valid参数校验？
□ 每个Service写操作是否有@Transactional？
□ 缓存Key是否使用RedisKeyUtil统一生成？
□ 缓存失效是否使用@CacheEvict（写操作）？
□ 敏感信息是否通过环境变量注入？
□ API响应是否使用ApiResponse统一包装？
□ 异常是否使用BusinessException体系？
□ 日志是否包含requestId用于链路追踪？
□ 用户数据隔离是否正确（只能访问自己的数据）？
□ JPA查询是否避免了N+1问题？
□ 分页接口是否正确使用Pageable？
□ 枚举字段是否使用@Enumerated(EnumType.STRING)？
□ JSON字段是否使用@Convert或@Type注解？
□ 密码是否使用BCrypt加密存储？
□ JWT Token验证是否包含黑名单检查？
```

---

> **文档维护**：架构变更时需更新本文档，重大变更需记录修订历史  
> **变更控制**：模块间接口变更需项目组讨论确认  
> **下一步**：依据本文档开始Java后端模块开发，按F2.1→F2.2→F2.3→F2.4→F2.5→F2.6顺序实现
