# Task09: 6个Repository接口 + 自定义查询

| 项目 | 内容 |
|------|------|
| **项目** | XH-202630 科研文献智能助手 |
| **版本** | v0.1 |
| **里程碑** | M1：基础设施就绪 / JM1：项目骨架与数据层就绪 |
| **功能编号** | F2.1, F2.2, F2.3, F2.4, F4.1 |

## 需求描述

创建6个Spring Data JPA Repository接口，每个继承`JpaRepository<Entity, Long>`，并定义自定义查询方法。核心包括PaperRepository的MySQL全文索引检索（MATCH...AGAINST + 条件过滤 + 排序 + 分页）、用户数据隔离查询、重复检查查询等。所有查询必须使用参数化绑定，涉及用户数据的查询强制加入userId条件。

## 涉及层级

- **java_backend** — com.literatureassistant.repository
- **data_layer** — MySQL查询

## 需要修改/新增的文件

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `repository/UserRepository.java` | 用户Repository，含findByUsername/existsByUsername |
| 新增 | `repository/UserProfileRepository.java` | 用户画像Repository，含findByUserId/existsByUserId |
| 新增 | `repository/PaperRepository.java` | 论文Repository，含全文检索searchByKeyword原生查询 |
| 新增 | `repository/SessionRepository.java` | 会话Repository，含按userId分页查询（数据隔离） |
| 新增 | `repository/AnalysisResultRepository.java` | 分析结果Repository，含按sessionId/status查询 |
| 新增 | `repository/PaperFavoriteRepository.java` | 论文收藏Repository，含existsByUserIdAndPaperId防重复 |

## 功能要求

| ID | 优先级 | 描述 |
|----|--------|------|
| FR-001 | P0 | UserRepository：findByUserId/findByUsername/existsByUsername/existsByEmail |
| FR-002 | P0 | UserProfileRepository：findByUserId/existsByUserId |
| FR-003 | P0 | PaperRepository：findByPaperId/searchByKeyword(全文检索+条件过滤+排序+分页)/findByPaperIdIn，同时继承JpaSpecificationExecutor |
| FR-004 | P0 | SessionRepository：findBySessionId/findByUserIdOrderByCreatedAtDesc（数据隔离） |
| FR-005 | P0 | AnalysisResultRepository：findByAnalysisId/findBySessionId/findBySessionIdAndStatus |
| FR-006 | P0 | PaperFavoriteRepository：findByUserIdOrderByCreatedAtDesc（数据隔离）/existsByUserIdAndPaperId/deleteByUserIdAndPaperId |
| FR-007 | P1 | 所有Repository类级别@Transactional(readOnly=true)，写操作方法@Transactional覆盖 |

## 关键查询：PaperRepository.searchByKeyword

```sql
SELECT * FROM papers 
WHERE MATCH(title, abstract) AGAINST(:keyword IN NATURAL LANGUAGE MODE) 
  AND (:yearFrom IS NULL OR year >= :yearFrom) 
  AND (:yearTo IS NULL OR year <= :yearTo) 
  AND (:venue IS NULL OR venue = :venue) 
ORDER BY CASE 
  WHEN :sort = 'relevance' THEN MATCH(title, abstract) AGAINST(:keyword IN NATURAL LANGUAGE MODE) 
  WHEN :sort = 'year' THEN year 
  WHEN :sort = 'citations' THEN citation_count 
END DESC
```

## 跨系统一致性

- Repository查询返回Entity，Service层负责Entity→DTO转换
- 数据隔离通过Repository查询方法中的userId条件实现

## 关键约束

- **禁止**Controller直接操作Repository
- **禁止**SQL拼接，必须使用@Param参数化查询
- **禁止**省略数据隔离条件（userId过滤）
- **禁止**大表查询不加LIMIT分页

## 验收标准

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-001 | 6个Repository接口编译通过 | 自动化测试 |
| AC-002 | searchByKeyword支持全文检索+条件过滤+排序+分页 | 自动化测试 |
| AC-003 | Session/PaperFavorite查询强制按userId过滤 | 自动化测试 |
| AC-004 | 所有自定义查询使用@Param参数化绑定 | 代码审查 |
| AC-005 | PaperRepository继承JpaSpecificationExecutor | 代码审查 |
| AC-006 | Repository类级别@Transactional(readOnly=true) | 代码审查 |
| AC-007 | existsByUsername/existsByEmail注册唯一性校验 | 自动化测试 |
| AC-008 | existsByUserIdAndPaperId防止重复收藏 | 自动化测试 |
| AC-009 | 分页查询方法正确使用Pageable参数 | 自动化测试 |
| AC-010 | 单元测试全部通过 | 自动化测试 |

## 验证命令

```bash
cd Veritas/backend && mvn compile
cd Veritas/backend && mvn test -Dtest=UserRepositoryTest,SessionRepositoryTest,PaperFavoriteRepositoryTest
```
