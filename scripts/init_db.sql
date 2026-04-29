-- 病虫害检测系统 MySQL 初始化脚本
-- 创建数据库
CREATE DATABASE IF NOT EXISTS pdds DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE pdds;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('user', 'admin') DEFAULT 'user',
    phone VARCHAR(20),
    language VARCHAR(5) DEFAULT 'zh',
    is_active BOOLEAN DEFAULT TRUE,
    login_fail_count INT DEFAULT 0,
    locked_until DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 检测记录表
CREATE TABLE IF NOT EXISTS detections (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    detection_type ENUM('image', 'video', 'camera') NOT NULL,
    source ENUM('local_model', 'cloud_ai') NOT NULL,
    file_path VARCHAR(500),
    thumbnail_path VARCHAR(500),
    crop_type VARCHAR(50),
    disease_name VARCHAR(100),
    confidence FLOAT,
    severity ENUM('low', 'medium', 'high'),
    bounding_boxes JSON,
    ai_analysis JSON,
    prevention_advice TEXT,
    latitude FLOAT,
    longitude FLOAT,
    address VARCHAR(200),
    weather VARCHAR(50),
    temperature FLOAT,
    humidity FLOAT,
    review_status ENUM('pending', 'reviewed', 'false_positive') DEFAULT 'pending',
    review_result JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at),
    INDEX idx_disease_name (disease_name),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 虫害跟踪任务表
CREATE TABLE IF NOT EXISTS tracking_tasks (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    detection_id VARCHAR(36),
    disease_name VARCHAR(100) NOT NULL,
    latitude FLOAT,
    longitude FLOAT,
    severity ENUM('low', 'medium', 'high') DEFAULT 'medium',
    status ENUM('active', 'resolved', 'archived') DEFAULT 'active',
    resolved_at DATETIME,
    resolved_measure TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_disease_name (disease_name),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (detection_id) REFERENCES detections(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 跟踪更新记录表
CREATE TABLE IF NOT EXISTS tracking_updates (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    description TEXT,
    image_path VARCHAR(500),
    severity ENUM('low', 'medium', 'high'),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    FOREIGN KEY (task_id) REFERENCES tracking_tasks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 模型注册表
CREATE TABLE IF NOT EXISTS model_registry (
    id VARCHAR(36) PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL UNIQUE,
    model_version VARCHAR(20) NOT NULL,
    model_path VARCHAR(500) NOT NULL,
    supported_pests JSON NOT NULL,
    supported_crops JSON NOT NULL,
    input_size VARCHAR(20) DEFAULT '640x640',
    confidence_threshold FLOAT DEFAULT 0.5,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    metrics JSON,
    deployed_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 通知表
CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    type ENUM('warning', 'system', 'agent_push', 'regional_alert') NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    related_detection_id VARCHAR(36),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_is_read (is_read),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (related_detection_id) REFERENCES detections(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 病害知识库表
CREATE TABLE IF NOT EXISTS knowledge_base (
    id VARCHAR(36) PRIMARY KEY,
    disease_name VARCHAR(100) NOT NULL,
    crop_type VARCHAR(50) NOT NULL,
    symptoms TEXT,
    conditions TEXT,
    prevention TEXT,
    cases TEXT,
    image_urls JSON,
    language VARCHAR(5) DEFAULT 'zh',
    embedding_id VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_disease_name (disease_name),
    INDEX idx_crop_type (crop_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 视频检测帧表
CREATE TABLE IF NOT EXISTS video_frames (
    id VARCHAR(36) PRIMARY KEY,
    detection_id VARCHAR(36) NOT NULL,
    frame_index INT NOT NULL,
    timestamp FLOAT NOT NULL,
    detections JSON,
    track_ids JSON,
    annotated_frame_path VARCHAR(500),
    FOREIGN KEY (detection_id) REFERENCES detections(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- API密钥表
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    rate_limit INT DEFAULT 60,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 操作日志表
CREATE TABLE IF NOT EXISTS operation_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    action VARCHAR(50) NOT NULL,
    resource VARCHAR(100),
    detail JSON,
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_action (action),
    INDEX idx_created_at (created_at),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 对话记录表
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    messages JSON NOT NULL DEFAULT '[]',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认管理员账户 (密码: admin123)
INSERT INTO users (id, username, email, password_hash, role)
VALUES (
    '550e8400-e29b-41d4-a716-446655440000',
    'admin',
    'admin@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lWkJ8RfL9O4K',
    'admin'
) ON DUPLICATE KEY UPDATE username=username;
