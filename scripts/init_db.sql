CREATE DATABASE IF NOT EXISTS stock_briefing CHARACTER SET utf8mb4;
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
    KEY idx_url_hash (url_hash)
);
