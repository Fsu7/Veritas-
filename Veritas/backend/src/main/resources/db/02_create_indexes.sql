-- ============================================================
-- XH-202630 科研文献智能助手 — MySQL 补充索引
-- 数据库：literature_assistant
-- 创建日期：2026-05-24
-- 里程碑：v0.1 M1 基础设施就绪
-- ============================================================
-- 注意：FULLTEXT索引已在01_create_tables.sql的papers表定义中内联创建
-- 本脚本用于补充或重建索引（如需独立管理索引时使用）
-- ============================================================

USE literature_assistant;

-- 验证FULLTEXT索引是否已存在，如不存在则创建
-- SET @ft_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
--     WHERE TABLE_SCHEMA = 'literature_assistant'
--     AND TABLE_NAME = 'papers'
--     AND INDEX_NAME = 'ft_title_abstract');

-- 如果01脚本执行成功，以下语句会报索引已存在，属正常情况
-- CREATE FULLTEXT INDEX ft_title_abstract ON papers(title, abstract) WITH PARSER ngram;
