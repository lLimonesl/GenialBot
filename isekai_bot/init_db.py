import sqlite3
from world_data import WORLD_RULES, SOCIAL_HIERARCHY

conn = sqlite3.connect("isekai.db")
conn.execute("PRAGMA journal_mode=WAL;")
c = conn.cursor()

# Tablas
c.execute("""
CREATE TABLE IF NOT EXISTS world (
    id INTEGER PRIMARY KEY,
    current_day INTEGER,
    rules TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS daily_logs (
    day INTEGER PRIMARY KEY,
    title TEXT,
    full_text TEXT,
    summary TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    race TEXT,
    social_status TEXT,
    abilities TEXT,
    passives TEXT,
    weapon TEXT,
    amulet TEXT,
    pet TEXT,
    status TEXT,
    level INTEGER
)
""")

# Insertar mundo
c.execute("INSERT INTO world (current_day, rules) VALUES (?, ?)", (1, WORLD_RULES))

# Insertar personajes (ejemplo inicial)
characters = [
    ("Javiche", "Ángel Caído", "Deidad",
     "Duplicar objetos y seres (máx 5 copias)",
     "Debilitar al 50% por contacto",
     "Alabarda",
     "Anillo de regeneración de estamina",
     "Puerco Alado (revive)",
     "Vivo",
     1
    ),
    ("Red", "Vampiro", "Deidad",
     "Copiar poderes (sin pasivas)",
     "Deshabilita poderes en 5m",
     "Cimitarras duales",
     "Anillo de traducción",
     "Dragón",
     "Vivo",
     1
    )
]

c.executemany("""
INSERT INTO characters
(name, race, social_status, abilities, passives, weapon, amulet, pet, status, level)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", characters)

conn.commit()
conn.close()

print("Base de datos creada con mundo y personajes")


