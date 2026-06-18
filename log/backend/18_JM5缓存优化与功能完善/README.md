# JM5 缓存优化与功能完善

## 功能描述

### 解决了什么问题
- **缓存策略缺失**：JM4 之前仅 RedisConfig 定义了缓存空间，但 Service 层未使用 @Cacheable/@CacheEvict 注解，每次查询直击 DB
- **缓存雪崩风险**：所有缓存 TTL 相同，同时过期会导致 DB 瞬时压力过大
- **缓存穿透风险**：空结果未缓存，恶意查询不存在的 key 会打穿 DB
- **检索功能不完善**：原 searchPapers 仅支持 q/yearFrom/yearTo/venue 4 个过滤参数，缺少 author/keywords 过滤和排序方向控制
- **无收藏功能**：用户无法收藏感兴趣的论文
- **无报告导出**：分析结果只能在页面查看，无法导出为 PDF/Word 离线阅读

### 实现了什么功能
1. **用户画像三重缓存**：userProfile + userProfileJson + userInfo 三个缓存空间同步失效
2. **论文检索缓存**：paperSearch 复合 Key（9 参数）+ paperList 分页缓存
3. **分析结果缓存**：analysisResult TTL=30min + 手动 RedisTemplate 降级读取
4. **会话状态缓存**：sessionState TTL=2h + sessionList TTL=10min
5. **Agent 状态缓存**：agentState Hash 结构 + 5min TTL
6. **论文筛选排序扩展**：新增 author/keywords 过滤 + sortDirection 排序方向（asc/desc）
7. **论文收藏 API**：POST/DELETE/GET 三个端点 + 幂等性 + @CacheEvict 精准失效
8. **PDF 导出**：iText 7 + font-asian 中文字体 + Markdown 渲染 + 页脚
9. **Word 导出**：Apache POI 5.2.3 + 宋体 + 统一 export 入口（pdf/word/docx 别名）
10. **缓存防护机制**：TTL ±10% 抖动防雪崩 + unless=#result==null 防穿透 + 精准 evict 防击穿

### 业务价值
- **性能提升**：缓存命中率预期 >50%，DB 查询量大幅下降
- **用户体验**：支持收藏和导出，满足离线阅读和文献管理需求
- **系统稳定性**：防雪崩/防穿透/防击穿三重防护，避免缓存故障引发连锁反应
- **功能完整度**：v0.5 里程碑 Java 后端部分全部交付，P0 功能 100% 完成

---

## 实现逻辑

### 修改的核心文件列表

#### 缓存配置层
- `config/RedisConfig.java`：新增 favoriteList 缓存空间（TTL=10min），applyJitter 抖动逻辑
- `util/RedisKeyUtil.java`：新增 favoriteListKey、userProfileJsonKey、sessionListKey、paperSearchKey（9 参数）

#### Service 层（缓存注解）
- `service/UserService.java`：userProfile/userProfileJson/userInfo 三重 @CacheEvict
- `service/PaperService.java`：paperDetail/paperSearch/paperList @Cacheable + 复合 Key
- `service/AnalysisService.java`：analysisResult @Cacheable + CacheManager 手动 evict
- `service/SessionService.java`：sessionState/sessionList @Cacheable
- `service/FavoriteService.java`（新建）：favoriteList @Cacheable + @CacheEvict

#### 论文检索扩展
- `repository/PaperRepositoryCustomImpl.java`：新增 author/keywords 过滤 + sortDirection 排序方向
  - **关键修复**：`String.format(DATA_SQL_TEMPLATE, orderClause)` 与 SQL LIKE `%` 冲突，改为字符串拼接

#### 收藏功能
- `entity/PaperFavorite.java`：收藏实体
- `repository/PaperFavoriteRepository.java`：findByUserIdAndPaperId 等方法
- `dto/response/FavoriteResponse.java`：收藏响应 DTO
- `mapper/FavoriteMapper.java`：MapStruct 转换器
- `controller/PaperController.java`：3 个收藏端点 + JWT 鉴权

#### 导出功能
- `util/PdfExporter.java`（新建）：iText 7 PDF 导出
- `util/WordExporter.java`（新建）：Apache POI Word 导出
- `service/ExportService.java`（新建）：统一 export 入口编排
- `controller/AnalysisController.java`：exportAnalysis 端点扩展

### 使用的算法或设计模式

#### Cache-Aside 模式
```
读：先查 Redis → 命中返回 → 未命中查 DB → 回填 Redis
写：先写 DB → 删除 Redis 缓存（避免脏读）
```

#### TTL 抖动防雪崩
```java
private Duration applyJitter(Duration baseTtl) {
    long baseSeconds = baseTtl.getSeconds();
    long jitterSeconds = (long) (baseSeconds * TTL_JITTER_RATIO); // 0.1
    long randomOffset = ThreadLocalRandom.current().nextLong(-jitterSeconds, jitterSeconds + 1);
    return Duration.ofSeconds(Math.max(1, baseSeconds + randomOffset));
}
```

#### 统一导出入口路由
```java
public byte[] export(String userId, String analysisId, String format) {
    String normalized = format.trim().toLowerCase();
    return switch (normalized) {
        case "pdf" -> exportPdf(userId, analysisId);
        case "word", "docx" -> exportWord(userId, analysisId);
        default -> throw new BusinessException(400, "不支持的导出格式", "UNSUPPORTED_FORMAT");
    };
}
```

### 关键代码逻辑说明

#### 1. PaperRepositoryCustomImpl SQL 拼接修复
```java
// 错误：String.format 与 LIKE % 冲突
String dataSql = String.format(DATA_SQL_TEMPLATE, orderClause); // UnknownFormatConversionException

// 正确：直接字符串拼接
String dataSql = DATA_SQL_TEMPLATE + " ORDER BY " + orderClause;
```

#### 2. PdfExporter 中文字体 fallback
```java
private PdfFont resolveChineseFont() {
    try {
        return PdfFontFactory.createFont("STSong-Light", "UniGB-UCS2-H");
    } catch (Exception e) {
        log.warn("Failed to load STSong-Light font, fallback to Helvetica");
        return PdfFontFactory.createFont();
    }
}
```

#### 3. WordExporter 页脚 API
```java
// POI 5.2.3 的 HeaderFooterType 在 org.apache.poi.wp.usermodel 包下（非 xwpf.usermodel）
XWPFFooter footer = doc.createFooter(org.apache.poi.wp.usermodel.HeaderFooterType.DEFAULT);
```

---

## 接口变更

### 论文收藏 API

#### POST /api/papers/{paperId}/favorite
```json
// Request: 无 body，paperId 在 path 中
// Response:
{
  "code": 200,
  "message": "success",
  "data": {
    "favorite_id": 1,
    "paper_id": "arxiv_2024_001",
    "title": "Multi-Agent Systems: A Survey",
    "authors": ["Wang, L."],
    "year": 2024,
    "venue": "AAAI",
    "citation_count": 1200,
    "created_at": "2026-06-17T14:00:00"
  }
}
```

#### DELETE /api/papers/{paperId}/favorite
```json
// Response:
{
  "code": 200,
  "message": "success",
  "data": null
}
```

#### GET /api/papers/favorites?page=1&size=10
```json
// Response:
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [...],
    "total": 15,
    "page": 1,
    "size": 10,
    "total_pages": 2
  }
}
```

### 报告导出 API

#### GET /api/analysis/{analysisId}/export?format=pdf
```json
// Request: format=pdf（默认）/word/docx
// Response: 二进制文件流
// Headers:
//   Content-Type: application/pdf
//   Content-Disposition: attachment; filename="analysis_anl_001_20260617140000.pdf"
```

### 论文检索扩展参数

#### GET /api/papers/search（扩展参数）
```
新增参数：
- author: 作者过滤（LIKE 模糊匹配）
- keywords: 关键词过滤（JSON_CONTAINS）
- sortDirection: 排序方向 asc/desc（默认 desc，非法值 fallback desc 不抛异常）
```

---

## 测试结果

### 测试统计
- **JM5 新增测试**：95 个
- **全量测试**：447 个全部通过，0 失败 0 错误

### 测试场景
| 测试类 | 测试数 | 场景 |
|--------|--------|------|
| PaperRepositoryFilterSortTest | 9 | author/keywords 过滤、排序方向、非法值 fallback、缓存 Key 隔离 |
| FavoriteServiceTest | 11 | 收藏 CRUD、幂等性、数据隔离、缓存失效 |
| PdfExporterTest | 8 | Markdown 渲染、中文字体、citations、页脚、大文件、特殊字符 |
| ExportServiceTest | 12 | PDF/Word 路由、状态校验、空报告、数据隔离、格式大小写不敏感 |
| WordExporterTest | 12 | Word 渲染、中文字体、citations、页脚、标题字号、列表、代码块 |
| CacheHitRateTest | 11 | TTL 抖动范围、抖动随机性、缓存空间完整性、TTL 分层 |
| CacheConsistencyTest | 10 | @Cacheable/@CacheEvict 注解、Key 隔离、写后失效、幂等 evict |
| CachePenetrationAvalancheTest | 11 | 防穿透 unless、防雪崩抖动、防击穿 allEntries=false |
| Jm5IntegrationTest | 8 | 收藏 API、PDF/Word 导出 API、未认证 401、不支持格式 400 |
| RedisKeyUtilTest（修复） | 15 | 9 参数 paperSearchKey、null 规范化、新增 favoriteListKey |
| PaperControllerTest（修复） | 8 | 9 参数 searchPapers 签名适配 |
| PaperServiceCacheTest（修复） | 7 | 9 参数 searchPapers 反射、null 参数 Key 隔离 |

### 是否通过：是 ✅

### JM4 遗留问题修复
- RedisKeyUtilTest：paperListKey 签名从 (String) 改为 (int, int)，paperSearchKey 从 7 参数改为 9 参数
- PaperControllerTest：3 个 searchPapers 测试用例适配 9 参数签名
- PaperServiceCacheTest：2 个测试用例适配 9 参数签名

---

## 相关文件

### 新增文件
- `src/main/java/com/literatureassistant/dto/response/FavoriteResponse.java`
- `src/main/java/com/literatureassistant/mapper/FavoriteMapper.java`
- `src/main/java/com/literatureassistant/service/FavoriteService.java`
- `src/main/java/com/literatureassistant/service/ExportService.java`
- `src/main/java/com/literatureassistant/util/PdfExporter.java`
- `src/main/java/com/literatureassistant/util/WordExporter.java`
- `src/test/java/com/literatureassistant/repository/PaperRepositoryFilterSortTest.java`
- `src/test/java/com/literatureassistant/service/FavoriteServiceTest.java`
- `src/test/java/com/literatureassistant/service/ExportServiceTest.java`
- `src/test/java/com/literatureassistant/util/PdfExporterTest.java`
- `src/test/java/com/literatureassistant/util/WordExporterTest.java`
- `src/test/java/com/literatureassistant/cache/CacheHitRateTest.java`
- `src/test/java/com/literatureassistant/cache/CacheConsistencyTest.java`
- `src/test/java/com/literatureassistant/cache/CachePenetrationAvalancheTest.java`
- `src/test/java/com/literatureassistant/integration/Jm5IntegrationTest.java`

### 修改文件
- `pom.xml`：新增 iText 7.2.5 + font-asian 7.2.5 + Apache POI 5.2.3
- `config/RedisConfig.java`：新增 favoriteList 缓存空间
- `util/RedisKeyUtil.java`：新增 favoriteListKey/userProfileJsonKey/sessionListKey，paperSearchKey 扩展为 9 参数
- `repository/PaperRepositoryCustomImpl.java`：修复 String.format 与 LIKE % 冲突，新增 author/keywords/sortDirection
- `repository/PaperFavoriteRepository.java`：新增 findByUserIdAndPaperId
- `controller/PaperController.java`：新增 3 个收藏端点 + JWT 鉴权
- `controller/AnalysisController.java`：exportAnalysis 端点支持 pdf/word/docx
- `src/test/java/com/literatureassistant/util/RedisKeyUtilTest.java`：适配新签名
- `src/test/java/com/literatureassistant/controller/PaperControllerTest.java`：适配 9 参数签名
- `src/test/java/com/literatureassistant/service/PaperServiceCacheTest.java`：适配 9 参数签名

### 配置变更
- `pom.xml`：3 个新依赖（iText 7.2.5、font-asian 7.2.5、poi-ooxml 5.2.3）
- `RedisConfig.java`：新增 favoriteList 缓存空间配置（TTL=10min + ±10% 抖动）

### 文档变更
- `docs/版本里程碑功能清单.md`：v1.2，v0.5 状态更新为"进行中"，JM5 功能标记完成
- `docs/backend/Java后端模块项目里程碑文档.md`：v1.2，JM5 章节标记完成
