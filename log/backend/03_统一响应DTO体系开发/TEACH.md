# 技术教学文档 — 统一响应DTO体系

## 开发思路

### 需求分析过程
本次任务的核心需求是为全系统所有Controller建立统一的响应格式。分析prompt中的需求，提炼出三个关键类：
1. **ApiResponse<T>** — 所有API的统一返回包装，前端根据 `code` 字段判断成功/失败
2. **PageResponse<T>** — 分页查询的标准化响应，前端分页组件依赖 `page`/`total`/`total_pages` 等字段
3. **ErrorCode** — 错误码枚举，为 `GlobalExceptionHandler` 和 `BusinessException` 提供标准错误码

关键约束点：
- JSON字段必须使用snake_case（`@JsonProperty`注解）
- `data` 为null时JSON不输出该字段（`@JsonInclude(NON_NULL)`）
- `page` 必须是1-based（前端分页组件约定）
- DTO不得包含业务逻辑

### 技术选型考虑
- **Lombok注解选择**：`@Data` + `@Builder` + `@NoArgsConstructor` + `@AllArgsConstructor` — 四注解组合覆盖getter/setter/builder/构造器，是DTO类的标准配置
- **ErrorCode使用 `@Getter` + `@AllArgsConstructor`** 而非 `@Data` — 枚举不需要setter，`@Getter`更精确
- **Jackson注解**：`@JsonProperty("total_pages")` 用于camelCase→snake_case转换；`@JsonInclude(NON_NULL)` 用于null字段排除

### 架构设计思路
采用**静态工厂方法模式**而非直接构造器调用：
- `ApiResponse.success(data)` 比 `new ApiResponse<>(200, "success", data, timestamp)` 更语义化
- `ApiResponse.error(ErrorCode.NOT_FOUND)` 比手动传code/message更安全
- `PageResponse.fromPage(page)` 封装了0-based→1-based转换逻辑，调用方无需关心

### 遇到的问题及解决方案

**问题1**：`application.yml` 已全局配置 `spring.jackson.default-property-inclusion: non_null`，是否还需要在 `data` 字段上添加 `@JsonInclude(NON_NULL)`？

**解决**：保留字段级注解。原因：
1. 全局配置可能被覆盖或在不同Profile下不同
2. 字段级注解是**自文档化**的 — 明确表达"data为null时不输出"的设计意图
3. prompt明确要求在data字段上添加此注解

**问题2**：`PageResponse.fromPage(Page<T> page, List<R> items)` 方法中，泛型参数有T和R两个，如何确保类型安全？

**解决**：`Page<T>` 提供分页元数据（total/page/size/totalPages），`List<R> items` 提供转换后的DTO列表。返回类型是 `PageResponse<R>`，与items的元素类型一致。这是Entity→DTO转换的典型场景：`Page<Entity>` → `PageResponse<DTO>`。

## 实现步骤

1. **创建ErrorCode枚举** — 定义7个标准错误码（SUCCESS/BAD_REQUEST/UNAUTHORIZED/FORBIDDEN/NOT_FOUND/INTERNAL_ERROR/SERVICE_UNAVAILABLE），使用 `@Getter` + `@AllArgsConstructor` 注解
2. **创建ApiResponse泛型类** — 4字段 + 3个静态工厂方法 + `@JsonInclude(NON_NULL)` 在data字段上
3. **创建PageResponse泛型类** — 5字段 + 2个fromPage重载 + `@JsonProperty("total_pages")` 在totalPages字段上 + 0-based→1-based转换
4. **编写单元测试** — 3个测试类共18个测试用例，覆盖正常流程、边界条件、JSON序列化
5. **编译验证** — `mvn compile` 通过
6. **运行测试** — `mvn test` 18个用例全部通过

## 解决了什么问题

### 核心问题描述
前后端协作时，API响应格式不统一会导致：
- 前端需要为每个接口写不同的响应解析逻辑
- 错误处理分散，无法统一拦截
- 分页参数约定不一致（0-based vs 1-based）

### 解决方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 直接返回Entity | 简单 | 暴露数据库结构，违反分层规范 |
| 每个Controller自定义响应Map | 灵活 | 格式不统一，维护成本高 |
| **统一ApiResponse包装** | 格式统一，前端统一拦截 | 需要所有Controller遵守 |

### 最终方案的优势
1. **前端统一拦截**：Axios响应拦截器只需检查 `response.data.code === 200`
2. **类型安全**：泛型 `ApiResponse<T>` 确保编译期类型检查
3. **自文档化**：`ErrorCode` 枚举集中管理所有错误码，一目了然
4. **分页标准化**：`PageResponse` 统一分页元数据格式，前端分页组件可直接使用

## 变更内容

### 新增文件
- `Veritas/backend/src/main/java/com/literatureassistant/dto/common/ErrorCode.java` — 业务错误码枚举，7个标准错误码
- `Veritas/backend/src/main/java/com/literatureassistant/dto/common/ApiResponse.java` — 统一响应包装类，泛型T，含success/error工厂方法
- `Veritas/backend/src/main/java/com/literatureassistant/dto/common/PageResponse.java` — 分页响应DTO，泛型T，含fromPage工厂方法
- `Veritas/backend/src/test/java/com/literatureassistant/dto/common/ApiResponseTest.java` — 8个测试用例
- `Veritas/backend/src/test/java/com/literatureassistant/dto/common/PageResponseTest.java` — 6个测试用例
- `Veritas/backend/src/test/java/com/literatureassistant/dto/common/ErrorCodeTest.java` — 4个测试用例

### 修改文件
- 无（本次为纯新增，未修改已有文件）

### 配置变更
- 无（`application.yml` 中已有 `spring.jackson.default-property-inclusion: non_null` 全局配置，无需额外修改）

## 关键技术点

### 1. Lombok四注解组合
```java
@Data                    // getter/setter/toString/equals/hashCode
@Builder                 // Builder模式链式构建
@NoArgsConstructor       // 无参构造器（Jackson反序列化需要）
@AllArgsConstructor      // 全参构造器（Builder内部使用）
```
这是DTO类的标准注解组合。`@NoArgsConstructor` 是必须的，因为Jackson反序列化JSON时需要无参构造器。

### 2. @JsonInclude vs 全局配置
```java
@JsonInclude(JsonInclude.Include.NON_NULL)
private T data;
```
即使 `application.yml` 已配置全局 `non_null`，字段级注解仍然有价值：
- 自文档化：明确表达设计意图
- 防御性编程：全局配置可能被覆盖
- prompt明确要求

### 3. @JsonProperty 的snake_case转换
```java
@JsonProperty("total_pages")
private int totalPages;
```
Java字段名是camelCase（`totalPages`），JSON输出需要snake_case（`total_pages`）。`@JsonProperty` 注解指定JSON序列化/反序列化时的字段名。

### 4. Spring Data Page的0-based→1-based转换
```java
.page(page.getNumber() + 1)  // 0-based → 1-based
```
Spring Data的 `Page.getNumber()` 返回0-based页码（第一页=0），但前端分页组件和API契约约定page从1开始。`fromPage` 方法封装了这个转换，调用方无需关心。

### 5. 泛型静态工厂方法
```java
public static <T> ApiResponse<T> success(T data) {
    return ApiResponse.<T>builder()
            .code(200)
            .message("success")
            .data(data)
            .timestamp(System.currentTimeMillis())
            .build();
}
```
`<T>` 在返回类型前声明，使方法可以推断泛型类型。调用时无需手动指定类型参数：`ApiResponse.success("hello")` 自动推断为 `ApiResponse<String>`。

### 6. PageResponse的双泛型fromPage
```java
public static <T, R> PageResponse<R> fromPage(Page<T> page, List<R> items)
```
两个泛型参数：`T` 是原始Entity类型，`R` 是转换后的DTO类型。这允许 `Page<Entity>` + `List<DTO>` → `PageResponse<DTO>` 的转换，分页元数据来自原始Page，items使用转换后的列表。

## 经验总结

### 开发过程中的收获
1. **DTO设计应先于Controller** — 统一响应格式是全系统的基础设施，必须在写第一个Controller之前完成
2. **枚举优于魔法数字** — `ErrorCode.NOT_FOUND` 比 `404` 更可读、更安全
3. **工厂方法优于构造器** — `ApiResponse.success(data)` 比 `new ApiResponse<>(200, "success", data, System.currentTimeMillis())` 更简洁、更不容易出错

### 踩过的坑及如何避免
1. **0-based vs 1-based** — Spring Data Page的页码是0-based，容易忘记+1转换。解决方案：在 `fromPage` 工厂方法中统一处理，调用方无需关心
2. **@JsonProperty遗漏** — 容易忘记给camelCase字段添加 `@JsonProperty` 注解。解决方案：建立checklist，所有DTO类review时检查snake_case转换
3. **枚举使用@Data** — 枚举不应使用 `@Data`（会生成setter，枚举值不应被修改）。应使用 `@Getter` + `@AllArgsConstructor`

### 最佳实践建议
1. **所有Controller方法统一返回 `ApiResponse<T>`** — 禁止直接返回Entity或Map
2. **分页接口统一返回 `ApiResponse<PageResponse<XxxResponse>>`** — 三层嵌套：ApiResponse包装状态码 → PageResponse包装分页元数据 → XxxResponse包装业务数据
3. **错误码集中管理** — 新增业务错误码时在 `ErrorCode` 枚举中添加，不要在代码中硬编码数字
4. **JSON序列化测试必须写** — `@JsonProperty` 和 `@JsonInclude` 的效果只能通过实际序列化验证，不能仅靠字段声明
