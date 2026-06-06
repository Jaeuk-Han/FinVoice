CREATE DATABASE IF NOT EXISTS stock_briefing CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE stock_briefing;

CREATE TABLE IF NOT EXISTS briefing (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    briefing_date DATE NOT NULL,
    market_summary TEXT,
    market_audio_url VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_date (briefing_date)
);

CREATE TABLE IF NOT EXISTS briefing_item (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    briefing_id BIGINT NULL,
    symbol VARCHAR(16) NOT NULL,
    company VARCHAR(100),
    summary_ko TEXT NOT NULL,
    sentiment ENUM('positive','neutral','negative') DEFAULT 'neutral',
    audio_url VARCHAR(500),
    item_date DATE NOT NULL,
    source ENUM('batch','ondemand') DEFAULT 'batch',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (briefing_id) REFERENCES briefing(id),
    KEY idx_symbol_date (symbol, item_date)
);

CREATE TABLE IF NOT EXISTS article (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    item_id BIGINT NOT NULL,
    title_en VARCHAR(500),
    title_ko VARCHAR(500),
    url VARCHAR(1000),
    source_name VARCHAR(100),
    published_at DATETIME NULL,
    url_hash CHAR(64),
    FOREIGN KEY (item_id) REFERENCES briefing_item(id),
    -- non-unique: same article URL may legitimately relate to multiple symbols/items; dedup is done in-memory per fetch
    KEY idx_url_hash (url_hash)
);

CREATE TABLE IF NOT EXISTS user (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_watchlist (
    id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id   BIGINT NOT NULL,
    symbol    VARCHAR(16) NOT NULL,
    company   VARCHAR(100) NOT NULL,
    position  TINYINT DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_symbol (user_id, symbol)
);
