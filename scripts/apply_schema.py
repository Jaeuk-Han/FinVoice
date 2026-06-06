"""init_db.sql 을 Cloud DB 에 적용하는 일회성 스크립트."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pymysql
from app import config

DDL = """
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
"""

def main():
    conn = pymysql.connect(
        host=config.get_env("DB_HOST"),
        port=int(config.get_env("DB_PORT")),
        user=config.get_env("DB_USER"),
        password=config.get_env("DB_PASSWORD"),
        database=config.get_env("DB_NAME"),
        charset="utf8mb4",
    )
    with conn:
        with conn.cursor() as cur:
            for stmt in DDL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
                    print(f"OK: {stmt[:60].replace(chr(10), ' ')}...")
        conn.commit()
    print("\nSchema applied successfully.")

if __name__ == "__main__":
    main()
