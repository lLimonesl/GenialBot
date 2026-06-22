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
    created_at TIMESTAMP DEFAULT NOW()
);

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
