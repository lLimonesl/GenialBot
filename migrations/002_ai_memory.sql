CREATE TABLE IF NOT EXISTS prompt_snapshots (
    id SERIAL PRIMARY KEY,
    purpose TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    token_estimate INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_runs (
    id SERIAL PRIMARY KEY,
    purpose TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_snapshot_id INTEGER REFERENCES prompt_snapshots(id) ON DELETE SET NULL,
    output_text TEXT,
    status TEXT NOT NULL DEFAULT 'success',
    error TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS story_facts (
    id SERIAL PRIMARY KEY,
    day INTEGER,
    entity_type TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    fact_type TEXT NOT NULL,
    fact_text TEXT NOT NULL,
    source_table TEXT,
    source_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS entity_relationships (
    id SERIAL PRIMARY KEY,
    left_entity_type TEXT NOT NULL,
    left_entity_name TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    right_entity_type TEXT NOT NULL,
    right_entity_name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memory_chunks (
    id SERIAL PRIMARY KEY,
    day_start INTEGER,
    day_end INTEGER,
    chunk_type TEXT NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    importance INTEGER NOT NULL DEFAULT 1,
    token_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prompt_snapshots_created_at ON prompt_snapshots(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_runs_created_at ON ai_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_story_facts_entity ON story_facts(entity_type, entity_name, is_active);
CREATE INDEX IF NOT EXISTS idx_relationships_left ON entity_relationships(left_entity_type, left_entity_name, is_active);
CREATE INDEX IF NOT EXISTS idx_memory_chunks_type_days ON memory_chunks(chunk_type, day_start, day_end);
