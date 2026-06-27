-- P1-7 修复: analysis_results 表添加乐观锁 version 列
ALTER TABLE analysis_results ADD COLUMN version INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号';
