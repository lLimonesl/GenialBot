CREATE TABLE IF NOT EXISTS characters (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    race TEXT NOT NULL,
    social_status TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Vivo',
    level INTEGER NOT NULL DEFAULT 1,
    weapon TEXT,
    amulet TEXT,
    pet JSONB,
    abilities JSONB,
    passives JSONB,
    final_move JSONB,
    current_kingdom TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS world (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    current_day INTEGER NOT NULL,
    rules TEXT NOT NULL,
    hierarchy JSONB NOT NULL,
    meta JSONB
);

CREATE TABLE IF NOT EXISTS daily_logs (
    id SERIAL PRIMARY KEY,
    day INTEGER NOT NULL UNIQUE,
    title TEXT,
    full_text TEXT,
    summary TEXT,
    weather TEXT
);

CREATE TABLE IF NOT EXISTS character_arcs (
    id SERIAL PRIMARY KEY,
    character_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
    arc_name TEXT,
    arc_goal TEXT,
    arc_status TEXT,
    arc_progress INTEGER
);

CREATE TABLE IF NOT EXISTS votes (
    id SERIAL PRIMARY KEY,
    day INTEGER,
    question TEXT,
    options JSONB,
    result TEXT,
    status TEXT,
    source TEXT,
    message_id BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    consequence TEXT,
    vote_type TEXT DEFAULT 'critical',
    parent_vote_id INTEGER REFERENCES votes(id),
    close_after_hours INTEGER DEFAULT 15
);

ALTER TABLE votes ADD COLUMN IF NOT EXISTS consequence TEXT;
ALTER TABLE votes ADD COLUMN IF NOT EXISTS vote_type TEXT DEFAULT 'critical';
ALTER TABLE votes ADD COLUMN IF NOT EXISTS parent_vote_id INTEGER REFERENCES votes(id);
ALTER TABLE votes ADD COLUMN IF NOT EXISTS close_after_hours INTEGER DEFAULT 15;

CREATE TABLE IF NOT EXISTS quotes (
    id SERIAL PRIMARY KEY,
    day INTEGER,
    character_id INTEGER REFERENCES characters(id) ON DELETE SET NULL,
    character_name TEXT,
    quote TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    character_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    item_type TEXT,
    item_description TEXT,
    quantity INTEGER NOT NULL DEFAULT 1,
    obtained_day INTEGER,
    equipped BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(character_id, item_name)
);

CREATE TABLE IF NOT EXISTS reputation (
    id SERIAL PRIMARY KEY,
    character_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
    kingdom TEXT NOT NULL,
    fame_level INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    UNIQUE(character_id, kingdom)
);

CREATE TABLE IF NOT EXISTS npcs (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    race TEXT,
    description TEXT,
    role TEXT,
    kingdom TEXT,
    status TEXT NOT NULL DEFAULT 'Active',
    first_appearance_day INTEGER,
    last_appearance_day INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS battle_logs (
    id SERIAL PRIMARY KEY,
    day INTEGER,
    participants JSONB,
    enemies JSONB,
    outcome TEXT,
    summary TEXT
);

ALTER TABLE world ADD COLUMN IF NOT EXISTS season TEXT DEFAULT 'Primavera';
ALTER TABLE world ADD COLUMN IF NOT EXISTS season_day INTEGER DEFAULT 0;

CREATE TABLE IF NOT EXISTS narrative_memory (
    id SERIAL PRIMARY KEY,
    day INTEGER NOT NULL,
    summary_type TEXT NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS key_events (
    id SERIAL PRIMARY KEY,
    day INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    title TEXT,
    description TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS ability_unlock_votes (
    id SERIAL PRIMARY KEY,
    character_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
    day INTEGER,
    suggested_abilities JSONB NOT NULL,
    vote_id INTEGER REFERENCES votes(id),
    unlocked_ability TEXT,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS trade_logs (
    id SERIAL PRIMARY KEY,
    day INTEGER,
    character_id INTEGER REFERENCES characters(id) ON DELETE SET NULL,
    character_name TEXT,
    origin_kingdom TEXT,
    destination_kingdom TEXT NOT NULL,
    item_name TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS legends (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    power_level TEXT,
    kingdom TEXT,
    status TEXT NOT NULL DEFAULT 'Active',
    description TEXT,
    first_appearance_day INTEGER,
    last_appearance_day INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS character_progression (
    id SERIAL PRIMARY KEY,
    day INTEGER NOT NULL,
    character_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
    character_name TEXT NOT NULL,
    level INTEGER NOT NULL,
    total_fame INTEGER NOT NULL DEFAULT 0,
    UNIQUE(day, character_id)
);
