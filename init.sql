-- PhotoCards 테이블
CREATE TABLE IF NOT EXISTS photo_cards (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(100),
    province VARCHAR(50) NOT NULL,
    city VARCHAR(50) NOT NULL,
    message TEXT,
    hashtags JSONB,
    ai_quote TEXT,
    image_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_photo_cards_created_at ON photo_cards(created_at);
CREATE INDEX idx_photo_cards_user_id ON photo_cards(user_id);
CREATE INDEX idx_photo_cards_active ON photo_cards(is_active);

-- Meeting Platform Sessions 테이블
-- status: pending, processing, completed, failed
CREATE TABLE IF NOT EXISTS meeting_platform_sessions (
    id VARCHAR(36) PRIMARY KEY,
    photo_card_id VARCHAR(36) NOT NULL UNIQUE,  -- 포토카드당 하나의 세션만
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    query TEXT,
    area_code VARCHAR(10),
    sigungu_code VARCHAR(10),
    recommendation_data JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (photo_card_id) REFERENCES photo_cards(id) ON DELETE CASCADE
);

CREATE INDEX idx_sessions_photo_card_id ON meeting_platform_sessions(photo_card_id);
CREATE INDEX idx_sessions_status ON meeting_platform_sessions(status);
CREATE INDEX idx_sessions_last_accessed ON meeting_platform_sessions(last_accessed_at);
