-- Panel Discussion Database Schema
-- PostgreSQL 15.4

-- 1. Panel Discussions (メインテーブル)
CREATE TABLE IF NOT EXISTS panel_discussions (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(10) NOT NULL,
    topic TEXT NOT NULL,

    -- 結果
    final_mood VARCHAR(20) NOT NULL, -- 'happy', 'neutral', 'sad'
    final_score DECIMAL(5,2) NOT NULL, -- 0-100

    -- 内容
    introduction TEXT,
    conclusion TEXT,

    -- メタデータ
    discussion_date DATE NOT NULL DEFAULT CURRENT_DATE,
    total_turns INTEGER,
    debate_rounds INTEGER,

    -- タイムスタンプ
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 制約: 1国1日1回
    UNIQUE(country_code, discussion_date)
);

-- インデックス
CREATE INDEX idx_panel_country ON panel_discussions(country_code);
CREATE INDEX idx_panel_date ON panel_discussions(discussion_date DESC);
CREATE INDEX idx_panel_mood ON panel_discussions(final_mood);
CREATE INDEX idx_panel_score ON panel_discussions(final_score DESC);

-- 2. Expert Analyses (専門家分析)
CREATE TABLE IF NOT EXISTS panel_expert_analyses (
    id SERIAL PRIMARY KEY,
    discussion_id INTEGER REFERENCES panel_discussions(id) ON DELETE CASCADE,

    expert_role VARCHAR(50) NOT NULL, -- 'news_analyst', 'weather_analyst', etc.
    analysis_text TEXT NOT NULL,
    round_number INTEGER DEFAULT 0, -- 0 = initial, 1+ = debate rounds

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_expert_discussion ON panel_expert_analyses(discussion_id);
CREATE INDEX idx_expert_role ON panel_expert_analyses(expert_role);

-- 3. Votes (投票結果)
CREATE TABLE IF NOT EXISTS panel_votes (
    id SERIAL PRIMARY KEY,
    discussion_id INTEGER REFERENCES panel_discussions(id) ON DELETE CASCADE,

    expert_role VARCHAR(50) NOT NULL,
    vote_mood VARCHAR(20) NOT NULL, -- 'happy', 'neutral', 'sad'
    confidence DECIMAL(5,2) NOT NULL, -- 0-100
    reasoning TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_votes_discussion ON panel_votes(discussion_id);

-- 4. Transcripts (フル会話ログ)
CREATE TABLE IF NOT EXISTS panel_transcripts (
    id SERIAL PRIMARY KEY,
    discussion_id INTEGER REFERENCES panel_discussions(id) ON DELETE CASCADE,

    speaker VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    round_number INTEGER,
    turn_order INTEGER,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transcript_discussion ON panel_transcripts(discussion_id, turn_order);

-- 5. ビュー: 最新のディスカッション（よく使うクエリ）
CREATE OR REPLACE VIEW latest_panel_discussions AS
SELECT
    d.*,
    COALESCE(json_agg(
        json_build_object(
            'expert_role', e.expert_role,
            'analysis_text', e.analysis_text,
            'round_number', e.round_number
        ) ORDER BY e.round_number, e.id
    ) FILTER (WHERE e.id IS NOT NULL), '[]'::json) as expert_analyses,
    COALESCE(json_agg(
        json_build_object(
            'expert_role', v.expert_role,
            'vote_mood', v.vote_mood,
            'confidence', v.confidence,
            'reasoning', v.reasoning
        )
    ) FILTER (WHERE v.id IS NOT NULL), '[]'::json) as votes
FROM panel_discussions d
LEFT JOIN panel_expert_analyses e ON d.id = e.discussion_id
LEFT JOIN panel_votes v ON d.id = v.discussion_id
GROUP BY d.id;

-- サンプルデータ（テスト用）
INSERT INTO panel_discussions
(country_code, topic, final_mood, final_score, introduction, conclusion, total_turns, debate_rounds)
VALUES
('JP', 'Current mood analysis', 'happy', 75.5,
 'Welcome to the panel discussion about Japan''s current mood.',
 'Based on our analysis, Japan is experiencing a positive mood today.',
 12, 2)
ON CONFLICT (country_code, discussion_date) DO NOTHING;

-- 確認クエリ
SELECT
    'panel_discussions' as table_name,
    COUNT(*) as row_count
FROM panel_discussions
UNION ALL
SELECT
    'panel_expert_analyses',
    COUNT(*)
FROM panel_expert_analyses
UNION ALL
SELECT
    'panel_votes',
    COUNT(*)
FROM panel_votes
UNION ALL
SELECT
    'panel_transcripts',
    COUNT(*)
FROM panel_transcripts;
