# Task04: 统一响应DTO体系实施计划

## 任务概述

创建统一响应DTO体系，包含 `ApiResponse<T>`、`PageResponse<T>`、`ErrorCode` 三个类，为全系统所有Controller提供统一的响应包装。

## 现状分析

- **项目骨架已就绪**：`dto/common/` 目录已存在（含 `.gitkeep`），但尚无任何Java类
- **依赖已配置**：`pom.xml` 中已包含 Lombok、Spring Data JPA、Spring Boot Starter WebFlux、Jackson
- **Jackson全局配置**：`application.yml` 已配置 `default-property-inclusion: non_null`，全局排除null字段
- **架构文档已有设计**：`Java后端模块系统架构文档.md` §12.1-12.2 已有 `ApiResponse` 和 `PageResponse` 的类设计参考

## 关键设计决策

### 决策1：`@JsonInclude(NON_NULL)` 放置位置

- **prompt要求**：`data` 字段为null时JSON序列化不输出data字段（通过 `@JsonInclude(JsonInclude.Include.NON_NULL)` 注解在data字段上）
- **全局配置**：`application.yml` 已配置 `spring.jackson.default-property-inclusion: non_null`
- **决策**：由于全局已配置 `non_null`，所有null字段默认不输出。但为了代码自文档化（显式声明意图），仍在 `ApiResponse.data` 字段上添加 `@JsonInclude(JsonInclude.Include.NON_NULL)` 注解

### 决策2：`timestamp` 字段类型

- **prompt要求**：`timestamp(long)` 字段
- **架构文档参考**：`timestamp` 为 `long` 类型
- **决策**：使用 `long` 类型，存储 `System.currentTimeMillis()` 毫秒时间戳

### 决策3：`PageResponse.page` 的1-based转换

- **prompt要求**：`page` 字段从0-based转为1-based（Spring Data Page.getNumber()返回0-based，PageResponse.page应为1-based）
- **决策**：在 `fromPage` 工厂方法中执行 `page.getNumber() + 1` 转换

### 决策4：`@JsonProperty` 注解范围

- **prompt要求**：JSON字段统一使用snake_case（通过 `@JsonProperty` 注解）
- **已有全局配置**：`application.yml` 中 `spring.jackson.default-property-inclusion: non_null`
- **决策**：仅对 camelCase 字段添加 `@JsonProperty` 注解（如 `totalPages` → `total_pages`），已经是snake_case的字段无需注解。具体需要注解的字段：
  - `PageResponse.totalPages` → `@JsonProperty("total_pages")`
  - `ApiResponse` 中 `code`、`message`、`data`、`timestamp` 本身已是单字或snake_case兼容，无需 `@JsonProperty`

## 实施步骤

### Step 1: 创建 `ErrorCode` 枚举

**文件**：`Veritas/backend/src/main/java/com/literatureassistant/dto/common/ErrorCode.java`

```java
package com.literatureassistant.dto.common;

@Getter
@AllArgsConstructor
public enum ErrorCode {
    SUCCESS(200, "success"),
    BAD_REQUEST(400, "请求参数错误"),
    UNAUTHORIZED(401, "未认证，请先登录"),
    FORBIDDEN(403, "无权限访问"),
    NOT_FOUND(404, "资源不存在"),
    INTERNAL_ERROR(500, "服务器内部错误"),
    SERVICE_UNAVAILABLE(503, "服务暂时不可用");

    private final int code;
    private final String message;
}
```

**要点**：
- 使用 `@Getter`（Lombok）代替手写getter
- 使用 `@AllArgsConstructor`（Lombok）生成构造器
- 枚举值使用 `UPPER_SNAKE_CASE`（规范要求）
- 7个标准错误码，与prompt FR-003完全一致

### Step 2: 创建 `ApiResponse<T>` 泛型类

**文件**：`Veritas/backend/src/main/java/com/literatureassistant/dto/common/ApiResponse.java`

```java
package com.literatureassistant.dto.common;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ApiResponse<T> {
    private int code;
    private String message;

    @JsonInclude(JsonInclude.Include.NON_NULL)
    private T data;

    private long timestamp;

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

    public static <T> ApiResponse<T> error(ErrorCode errorCode) {
        return ApiResponse.<T>builder()
                .code(errorCode.getCode())
                .message(errorCode.getMessage())
                .timestamp(System.currentTimeMillis())
                .build();
    }
}
```

**要点**：
- 4个字段：`code(int)`、`message(String)`、`data(T泛型)`、`timestamp(long)`
- `@Data @Builder @NoArgsConstructor @AllArgsConstructor` 四注解
- `data` 字段添加 `@JsonInclude(JsonInclude.Include.NON_NULL)` — error响应时data=null不输出
- 3个静态工厂方法：`success(T data)`、`error(int, String)`、`error(ErrorCode)`
- 不包含任何业务逻辑方法（FA-DTO1禁止）
- `success` 方法 code=200, message="success"
- `error` 方法不设置data（data=null，序列化时不输出）

### Step 3: 创建 `PageResponse<T>` 泛型类

**文件**：`Veritas/backend/src/main/java/com/literatureassistant/dto/common/PageResponse.java`

```java
package com.literatureassistant.dto.common;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PageResponse<T> {
    private List<T> items;
    private long total;
    private int page;
    private int size;

    @JsonProperty("total_pages")
    private int totalPages;

    public static <T> PageResponse<T> fromPage(Page<T> page) {
        return PageResponse.<T>builder()
                .items(page.getContent())
                .total(page.getTotalElements())
                .page(page.getNumber() + 1)  // 0-based → 1-based
                .size(page.getSize())
                .totalPages(page.getTotalPages())
                .build();
    }

    public static <T, R> PageResponse<R> fromPage(Page<T> page, List<R> items) {
        return PageResponse.<R>builder()
                .items(items)
                .total(page.getTotalElements())
                .page(page.getNumber() + 1)  // 0-based → 1-based
                .size(page.getSize())
                .totalPages(page.getTotalPages())
                .build();
    }
}
```

**要点**：
- 5个字段：`items(List<T>)`、`total(long)`、`page(int)`、`size(int)`、`totalPages(int)`
- `totalPages` 字段添加 `@JsonProperty("total_pages")` — JSON序列化为snake_case（FA-DTO3禁止省略）
- `page` 字段从0-based转为1-based（FA-DTO2禁止使用0-based）
- 2个 `fromPage` 重载方法：
  - `fromPage(Page<T>)` — 直接使用Page内容
  - `fromPage(Page<T>, List<R>)` — 支持Entity→DTO转换后的items列表
- 需要导入 `org.springframework.data.domain.Page`

### Step 4: 创建单元测试

#### 4.1 `ApiResponseTest`

**文件**：`Veritas/backend/src/test/java/com/literatureassistant/dto/common/ApiResponseTest.java`

**测试用例**：
1. `testSuccessWithData` — 验证 `success(data)` 返回 code=200, message="success", data不为null, timestamp>0
2. `testSuccessWithNullData` — 验证 `success(null)` 返回 code=200, data=null
3. `testErrorWithCodeAndMessage` — 验证 `error(400, "参数错误")` 返回 code=400, message="参数错误", data=null
4. `testErrorWithErrorCode` — 验证 `error(ErrorCode.NOT_FOUND)` 返回 code=404, message="资源不存在", data=null
5. `testErrorDataNullNotSerialized` — 验证error响应JSON中不包含data字段（JSON序列化测试）
6. `testTimestampIsCurrentTime` — 验证timestamp接近当前时间

#### 4.2 `PageResponseTest`

**文件**：`Veritas/backend/src/test/java/com/literatureassistant/dto/common/PageResponseTest.java`

**测试用例**：
1. `testFromPageDirectConversion` — 验证 `fromPage(Page)` 正确提取分页元数据
2. `testFromPageWithConvertedItems` — 验证 `fromPage(Page, List)` 使用转换后的列表
3. `testPageIsOneBased` — 验证 Spring Data Page(pageNumber=0) → PageResponse.page=1
4. `testEmptyPage` — 验证空页处理
5. `testTotalPagesJsonSerialization` — 验证 `totalPages` 序列化为 `total_pages`（JSON测试）

#### 4.3 `ErrorCodeTest`

**文件**：`Veritas/backend/src/test/java/com/literatureassistant/dto/common/ErrorCodeTest.java`

**测试用例**：
1. `testAllErrorCodes` — 验证7个枚举值的code和message正确
2. `testSpecificCodeValues` — 验证 `BAD_REQUEST.getCode()=400`, `UNAUTHORIZED.getMessage()="未认证，请先登录"` 等

### Step 5: 编译验证

```bash
cd Veritas/backend && mvn compile
```

### Step 6: 运行单元测试

```bash
cd Veritas/backend && mvn test -Dtest=ApiResponseTest,PageResponseTest,ErrorCodeTest
```

## 文件清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 创建 | `dto/common/ErrorCode.java` | 业务错误码枚举 |
| 创建 | `dto/common/ApiResponse.java` | 统一响应包装类 |
| 创建 | `dto/common/PageResponse.java` | 分页响应DTO |
| 创建 | `test/.../dto/common/ApiResponseTest.java` | ApiResponse单元测试 |
| 创建 | `test/.../dto/common/PageResponseTest.java` | PageResponse单元测试 |
| 创建 | `test/.../dto/common/ErrorCodeTest.java` | ErrorCode单元测试 |

## 验收标准对照

| AC编号 | 验收标准 | 对应实现 |
|--------|---------|---------|
| AC-001 | ApiResponse包含code/message/data/timestamp四字段，提供success和error静态工厂方法 | Step 2 |
| AC-002 | ApiResponse.success(data)返回code=200, message='success' | Step 2 + Test |
| AC-003 | ApiResponse.error(code, message)返回data=null | Step 2 + Test |
| AC-004 | PageResponse包含items/total/page/size/totalPages五字段 | Step 3 + Test |
| AC-005 | PageResponse.fromPage()正确从Spring Data Page转换，page从0-based转为1-based | Step 3 + Test |
| AC-006 | ErrorCode枚举定义7个标准错误码，code和message正确 | Step 1 + Test |
| AC-007 | 所有DTO使用Lombok注解（@Data @Builder @NoArgsConstructor @AllArgsConstructor） | Step 1-3 |
| AC-008 | JSON序列化时totalPages字段输出为total_pages（@JsonProperty注解） | Step 3 + Test |
| AC-009 | error响应JSON中data字段为null时不输出（@JsonInclude(NON_NULL)） | Step 2 + Test |
| AC-010 | 单元测试全部通过 | Step 6 |
