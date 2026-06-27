-- P1-7 修复: users 表添加 username/email 唯一约束
ALTER TABLE users ADD UNIQUE KEY uk_username (username);
ALTER TABLE users ADD UNIQUE KEY uk_email (email);
