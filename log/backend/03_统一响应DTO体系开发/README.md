# 统一响应DTO体系开发

## 功能描述
- 解决了全系统API响应格式不统一的问题，为所有Controller提供统一的响应包装类型
- 实现了 `ApiResponse<T>` 统一响应包装类、`PageResponse<T>` 分页响应DTO、`ErrorCode` 业务错误码枚举
- 业务价值：前端Axios响应拦截器可根据 `code` 字段统一判断成功/失败；分页接口返回 `ApiResponse<PageResponse<XxxResponse>>` 标准格式；错误码枚举为全局异常处理提供基础

## 实现逻辑

### 修改的核心文件列表
| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `dto/common/ErrorCode.java` | 业务错误码枚举，7个标准错误码 |
| 新增 | `dto/common/ApiResponse.java` | 统一响应包装类，泛型T |
| 新增 | `dto/common/PageResponse.java` | 分页响应DTO，泛型T |
| 新增 | `test/.../dto/common/ApiResponseTest.java` | ApiResponse单元测试（8个用例） |
| 新增 | `test/.../dto/common/PageResponseTest.java` | PageResponse单元测试（6个用例） |
| 新增 | `test/.../dto/common/ErrorCodeTest.java` | ErrorCode单元测试（4个用例） |

### 使用的设计模式
- **静态工厂方法模式**：`ApiResponse.success()` / `ApiResponse.error()` / `PageResponse.fromPage()` — 隐藏构建细节，统一创建入口
- **泛型参数化**：`ApiResponse<T>` 和 `PageResponse<T>` 支持任意数据类型
- **Builder模式**：通过Lombok `@Builder` 提供链式构建能力

### 关键代码逻辑说明

1. **ApiResponse** — 4字段（code/message/data/timestamp），3个静态工厂方法：
   - `success(T data)` → code=200, message="success"
   - `error(int code, String message)` → data=null（序列化时不输出）
   - `error(ErrorCode errorCode)` → 从枚举获取code和message

2. **PageResponse** — 5字段（items/total/page/size/totalPages），2个fromPage重载：
   - `fromPage(Page<T>)` — 直接使用Spring Data Page内容
   - `fromPage(Page<T>, List<R>)` — 支持Entity→DTO转换后的items列表
   - page字段从0-based转为1-based（`page.getNumber() + 1`）

3. **ErrorCode** — 7个枚举值：SUCCESS(200)、BAD_REQUEST(400)、UNAUTHORIZED(401)、FORBIDDEN(403)、NOT_FOUND(404)、INTERNAL_ERROR(500)、SERVICE_UNAVAILABLE(503)

## 接口变更

### Request
本次为DTO定义，不涉及API请求变更。后续所有Controller的返回类型将统一为 `ApiResponse<T>`。

### Response

**成功响应示例：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "userId": "usr_001",
    "username": "张三"
  },
  "timestamp": 1716451200000
}
```

**错误响应示例（data字段为null时不输出）：**
```json
{
  "code": 404,
  "message": "资源不存在",
  "timestamp": 1716451200000
}
```

**分页响应示例：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {"paperId": "p001", "title": "论文1"},
      {"paperId": "p002", "title": "论文2"}
    ],
    "total": 85,
    "page": 1,
    "size": 10,
    "total_pages": 9
  },
  "timestamp": 1716451200000
}
```

## 测试结果
- 测试场景1：ApiResponse.success(data) 返回code=200, message="success", data不为null — **通过**
- 测试场景2：ApiResponse.error(400, "参数错误") 返回code=400, data=null — **通过**
- 测试场景3：ApiResponse.error(ErrorCode.NOT_FOUND) 从枚举获取code=404, message="资源不存在" — **通过**
- 测试场景4：error响应JSON中不包含data字段 — **通过**
- 测试场景5：PageResponse.fromPage(Page) 正确提取分页元数据 — **通过**
- 测试场景6：Spring Data Page(pageNumber=0) 转换为 PageResponse.page=1 — **通过**
- 测试场景7：totalPages JSON序列化为total_pages — **通过**
- 测试场景8：ErrorCode 7个枚举值的code和message全部正确 — **通过**
- 是否通过：**是**（18个测试用例全部通过，BUILD SUCCESS）

## 相关文件
- `Veritas/backend/src/main/java/com/literatureassistant/dto/common/ErrorCode.java`
- `Veritas/backend/src/main/java/com/literatureassistant/dto/common/ApiResponse.java`
- `Veritas/backend/src/main/java/com/literatureassistant/dto/common/PageResponse.java`
- `Veritas/backend/src/test/java/com/literatureassistant/dto/common/ApiResponseTest.java`
- `Veritas/backend/src/test/java/com/literatureassistant/dto/common/PageResponseTest.java`
- `Veritas/backend/src/test/java/com/literatureassistant/dto/common/ErrorCodeTest.java`
- 配置文件变更：无（`application.yml` 中已有 `spring.jackson.default-property-inclusion: non_null` 全局配置）
