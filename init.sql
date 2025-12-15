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

-- Reviews 테이블
CREATE TABLE IF NOT EXISTS reviews (
    id VARCHAR(36) PRIMARY KEY,
    place_id VARCHAR(100) NOT NULL,       -- 장소 ID (관광 API content_id 또는 커스텀)
    place_name VARCHAR(200) NOT NULL,     -- 장소 이름
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),  -- 별점 1~5
    content TEXT NOT NULL,                -- 리뷰 내용
    user_id VARCHAR(100),                 -- 사용자 ID (선택)
    photo_card_id VARCHAR(36),            -- 연관 포토카드 (선택)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,

    FOREIGN KEY (photo_card_id) REFERENCES photo_cards(id) ON DELETE SET NULL
);

CREATE INDEX idx_reviews_place_id ON reviews(place_id);
CREATE INDEX idx_reviews_user_id ON reviews(user_id);
CREATE INDEX idx_reviews_created_at ON reviews(created_at DESC);
CREATE INDEX idx_reviews_rating ON reviews(rating);

-- Review Images 테이블 (S3 URL 저장)
CREATE TABLE IF NOT EXISTS review_images (
    id VARCHAR(36) PRIMARY KEY,
    review_id VARCHAR(36) NOT NULL,
    image_url VARCHAR(500) NOT NULL,      -- S3 URL
    image_order INTEGER DEFAULT 0,        -- 이미지 순서
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE
);

CREATE INDEX idx_review_images_review_id ON review_images(review_id);
