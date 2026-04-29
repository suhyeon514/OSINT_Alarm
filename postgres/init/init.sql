-- 기존 테이블이 있다면 삭제 (구조 변경을 위해 깔끔하게 재생성 추천)
DROP TABLE IF EXISTS collected_data CASCADE;
DROP TABLE IF EXISTS search_keywords CASCADE;
DROP TABLE IF EXISTS alert_rules CASCADE;

-- [1] 사용자 감시 키워드 테이블 (관리 포인트 분리)
CREATE TABLE search_keywords (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(100) NOT NULL UNIQUE, -- 예: "samsung", "project_x"
    category VARCHAR(50) DEFAULT 'general', -- general, personal, crypto 등
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- (테스트용 데이터 입력)
INSERT INTO search_keywords (keyword) VALUES ('samsung'), ('password'), ('secret_key'), ('lazarus') ON CONFLICT DO NOTHING;

-- [2] 통합 데이터 수집 테이블 (Raw Data + 분석 결과 + 중복 방지)
CREATE TABLE collected_data (
    id SERIAL PRIMARY KEY,
    
    -- 기본 수집 정보
    source VARCHAR(50) NOT NULL,        -- telegram, twitter, google...
    raw_data JSONB NOT NULL,            -- 전체 데이터 (제목, 내용, 날짜, 파일해시 등)
    
    -- 중복 방지용 고유키 (URL 또는 내용 해시)
    unique_key VARCHAR(255) UNIQUE NOT NULL,
    
    -- 분석 결과 (Worker가 채워넣을 공간)
    extracted_tags JSONB DEFAULT '{}',  -- 정규식 추출 결과 (이메일, IP, 마스킹된 주민번호 등)
    matched_keywords TEXT[],            -- 매칭된 키워드 리스트
    
    -- LLM 분석 및 위험도
    llm_summary TEXT,                   -- AI 요약 내용
    risk_level VARCHAR(20) DEFAULT 'LOW', -- HIGH, MEDIUM, LOW
    
    -- 상태 관리
    processed BOOLEAN DEFAULT FALSE,    -- Worker 처리 완료 여부
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- 인덱스 생성 (속도 최적화)
CREATE INDEX idx_collected_source ON collected_data(source);
CREATE INDEX idx_collected_processed ON collected_data(processed);
CREATE INDEX idx_unique_key ON collected_data(unique_key);

-- [3] 알림 발송 로그 (중복 알림 방지용)
CREATE TABLE notification_logs (
    id SERIAL PRIMARY KEY,
    data_id INT REFERENCES collected_data(id) ON DELETE CASCADE,
    channel VARCHAR(20), -- telegram, email
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
