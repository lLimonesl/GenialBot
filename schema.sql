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
    summary TEXT
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
    status TEXT
);

CREATE TABLE IF NOT EXISTS pov_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    current_pov INTEGER REFERENCES characters(id)
);