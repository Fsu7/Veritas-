# FULLTEXT 原生查询 MATCH 语法修复

## 功能描述
- **解决的问题**：PaperRepository 中使用 `@Query(nativeQuery=true)` 调用 MySQL FULLTEXT 的 `MATCH(title, abstract) AGAINST(:keyword IN NATURAL LANGUAGE MODE)` 时，Spring Data JPA 3.x 内部 SQL 解析器不识别 MySQL 专有的 `MATCH...AGAINST` 语法，抛出 ANTLR 解析错误。
- **实现的功能**：采用 Spring Data JPA 官方 Custom Repository 模式，用 `EntityManager.createNativeQuery()` 直接执行原生 SQL，绕过 JPA 查询解析器。
- **业务价值**：论文全文检索（混合检索的关键词路）能够正常执行，支持分页 + 排序（relevance/year/citations）+ 年份/venue 过滤。

## 实现逻辑
- **设计模式**：Spring Data JPA Custom Repository 模式（接口 + Impl 后缀实现类）
- **核心逻辑**：
  1. `PaperRepository` 接口新增 `extends PaperRepositoryCustom`
  2. `PaperRepositoryCustom` 定义 `searchByKeyword` 方法签名
  3. `PaperRepositoryCustomImpl` 使用 `EntityManager.createNativeQuery()` 分别执行 DATA_SQL（分页数据）和 COUNT_SQL（总数统计）
  4. 用 `PageImpl` 组装分页结果返回
- **关键 SQL**：
  ```sql
  -- 数据查询（带 ORDER BY + LIMIT/OFFSET）
  SELECT * FROM papers
  WHERE MATCH(title, abstract) AGAINST(?1 IN NATURAL LANGUAGE MODE)
  AND (?2 IS NULL OR year >= ?2)
  AND (?3 IS NULL OR year <= ?3)
  AND (?4 IS NULL OR venue = ?4)
  ORDER BY CASE
    WHEN ?5 = 'relevance' THEN MATCH(title, abstract) AGAINST(?1 IN NATURAL LANGUAGE MODE)
    WHEN ?5 = 'year' THEN year
    WHEN ?5 = 'citations' THEN citation_count
  END DESC

  -- 统计查询
  SELECT COUNT(*) FROM papers
  WHERE MATCH(title, abstract) AGAINST(?1 IN NATURAL LANGUAGE MODE)
  AND (?2 IS NULL OR year >= ?2)
  AND (?3 IS NULL OR year <= ?3)
  AND (?4 IS NULL OR venue = ?4)
  ```

## 接口变更
无接口变更。`searchByKeyword` 方法签名保持不变：
```java
Page<Paper> searchByKeyword(String keyword, Integer yearFrom, Integer yearTo,
                            String venue, String sort, Pageable pageable);
```

## 测试结果
- 编译验证：`mvn compile` 通过（exit code 0）
- 数据库验证：FULLTEXT 索引 `ft_title_abstract` 存在，`MATCH...AGAINST` 语法在 MySQL 9 上正常执行
- 端到端运行时测试：待 `mvn spring-boot:run` 启动后验证

## 相关文件
### 新增文件
- `backend/src/main/java/com/literatureassistant/repository/PaperRepositoryCustom.java` — 自定义接口
- `backend/src/main/java/com/literatureassistant/repository/PaperRepositoryCustomImpl.java` — EntityManager 实现

### 修改文件
- `backend/src/main/java/com/literatureassistant/repository/PaperRepository.java` — 移除 `@Query` 方法，新增 `extends PaperRepositoryCustom`