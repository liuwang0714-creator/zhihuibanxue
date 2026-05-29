-- ============================================================
-- 智学伴行 —— AI大学生全能学习助手 数据库Schema
-- ============================================================
CREATE DATABASE IF NOT EXISTS ai_learn CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ai_learn;

-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(100) UNIQUE NOT NULL COMMENT '用户邮箱',
    password VARCHAR(100) NOT NULL COMMENT '密码',
    nickname VARCHAR(50) DEFAULT '' COMMENT '昵称',
    avatar VARCHAR(255) DEFAULT '' COMMENT '头像URL',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 课程表
CREATE TABLE IF NOT EXISTS courses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    course_name VARCHAR(200) NOT NULL,
    category VARCHAR(50) DEFAULT '' COMMENT '课程分类',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. 学习路径表
CREATE TABLE IF NOT EXISTS learning_paths (
    id INT PRIMARY KEY AUTO_INCREMENT,
    course_id INT NOT NULL,
    step_order INT NOT NULL,
    step_description TEXT NOT NULL,
    completed BOOLEAN DEFAULT 0,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- 4. AI对话记录表（多轮对话支持）
CREATE TABLE IF NOT EXISTS ai_conversations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    course_id INT DEFAULT NULL,
    role ENUM('user','assistant') NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL
);

-- 5. 智能资料库表
CREATE TABLE IF NOT EXISTS materials (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    course_id INT DEFAULT NULL,
    topic VARCHAR(200) DEFAULT '' COMMENT '主题/关键词',
    content TEXT NOT NULL COMMENT 'AI推荐结果',
    material_type VARCHAR(20) DEFAULT 'recommend' COMMENT 'recommend/search',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL
);

-- 6. 错题本表
CREATE TABLE IF NOT EXISTS error_books (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    course_id INT DEFAULT NULL,
    subject VARCHAR(100) DEFAULT '' COMMENT '学科',
    error_content TEXT NOT NULL COMMENT '错题内容',
    ai_analysis TEXT COMMENT 'AI分析结果',
    error_type VARCHAR(50) DEFAULT '' COMMENT '错误类型',
    weak_points TEXT COMMENT '薄弱知识点',
    improvement_suggestions TEXT COMMENT '改进建议',
    resolved BOOLEAN DEFAULT 0 COMMENT '是否已解决',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL
);

-- 7. 写作记录表
CREATE TABLE IF NOT EXISTS writings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    topic VARCHAR(300) NOT NULL COMMENT '主题',
    writing_type VARCHAR(50) DEFAULT 'paper' COMMENT 'paper/report/essay',
    requirements TEXT COMMENT '额外要求',
    content TEXT COMMENT '生成内容',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 8. 学习记录表（监督与激励）
CREATE TABLE IF NOT EXISTS study_records (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    course_id INT DEFAULT NULL,
    study_date DATE NOT NULL COMMENT '学习日期',
    study_minutes INT DEFAULT 0 COMMENT '学习时长（分钟）',
    tasks_completed INT DEFAULT 0 COMMENT '完成任务数',
    notes TEXT COMMENT '学习笔记',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL
);

-- 9. 知识图谱标签表
CREATE TABLE IF NOT EXISTS knowledge_tags (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    course_id INT DEFAULT NULL,
    tag_name VARCHAR(100) NOT NULL COMMENT '知识点名称',
    parent_tag_id INT DEFAULT NULL COMMENT '父标签（构建图谱层级）',
    strength ENUM('weak','moderate','strong') DEFAULT 'moderate' COMMENT '掌握程度',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL
);
