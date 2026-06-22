import asyncio
import json
from db import get_pool

CHARACTERS = [
    {
        "name": "Javiche",
        "race": "Ángel caído",
        "social_status": "Deidad",
        "weapon": "Alabarda",
        "amulet": "Anillo de regeneración rápida de estamina",
        "pet": {
            "name": "Puerco alado",
            "revives": True,
            "revive_days": 3
        },
        "abilities": {
            "duplicar": {
                "max_copies": 5,
                "duration_days": 7,
                "copies_weaken": True
            }
        },
        "passives": {
            "debilitar_al_tocar": "Reduce fuerza al 50%"
        },
        "final_move": {
            "transferencia_a_clon": {
                "level_loss_percent": 30,
                "recovery_days": 3,
                "cooldown_days": 7
            }
        }
    },

    {
        "name": "Red",
        "race": "Vampiro",
        "social_status": "Deidad",
        "weapon": "Cimitarras duales",
        "amulet": "Anillo de traducción de lenguajes",
        "pet": {
            "name": "Dragón",
            "variant": "Frederica (HnC)"
        },
        "abilities": {
            "copiar_poderes": {
                "exclude_passives": True
            }
        },
        "passives": {
            "zona_antimagia": "5m (incluye al usuario)"
        },
        "final_move": {
            "emular_pasivas": {
                "max_percent": 70,
                "duration_minutes": 30
            }
        }
    },

    {
        "name": "Winters",
        "race": "Hombre lobo",
        "social_status": "Ciudadano",
        "weapon": "Puños de hierro",
        "amulet": "Anillo de aumento menor de resistencias",
        "pet": {"name": "Lobo gigante", "sex": "Macho"},
        "abilities": {"correr_rapido": True},
        "passives": {"resistencia_fisica": "Alta"},
        "final_move": {"aumento_resistencia": "Temporal (Season 1)"}
    },

    {
        "name": "Alex",
        "race": "Súcubo",
        "social_status": "Esclavo",
        "weapon": "Gran mangual",
        "amulet": "Collar con gema (carga eléctrica infinita)",
        "pet": {"name": "Golem de hierro"},
        "abilities": {"rayos": "Requiere carga externa"},
        "passives": {"cambio_de_forma": True},
        "final_move": {"arma_electrificada": True}
    },

    {
        "name": "Chakas",
        "race": "Elfo",
        "social_status": "Paria",
        "weapon": "Arco largo",
        "amulet": "Anillo de aumento de daño sin recibir golpes",
        "pet": {"name": "Dragón de fuego"},
        "abilities": {"teletransporte": "Solo a lugares visibles"},
        "passives": {"aprendizaje_rapido": True},
        "final_move": {
            "teletransporte_masivo": {
                "reduce_poder": True,
                "consume_vida": True
            }
        }
    },

    {
        "name": "Flamas",
        "race": "Descendiente de dragón",
        "social_status": "Paria",
        "weapon": None,
        "amulet": "Anillo de resistencias elementales",
        "pet": {"name": "Wyvern de rayo"},
        "abilities": {"control_energias": "Requiere aprendizaje"},
        "passives": {"energia_propia": True},
        "final_move": {"indetectable": True}
    },

    {
        "name": "Gray",
        "race": "Humano",
        "social_status": "Ciudadano",
        "weapon": "Hacha",
        "amulet": "Anillo de regeneración de estamina",
        "pet": {"name": "Lobo", "habilidad": "Ocultarse en sombra"},
        "abilities": {"regeneracion": "Salud"},
        "passives": {
            "fuerza_y_velocidad": "Escala con combate"
        },
        "final_move": {
            "super_regeneracion": True,
            "aumento_velocidad": True
        }
    },

    {
        "name": "Limones",
        "race": "Elfa",
        "social_status": "Paria",
        "weapon": "Daga",
        "amulet": "Anillo de suerte +30%",
        "pet": {"name": "Zorro gigante"},
        "abilities": {"necromancia": True},
        "passives": {"ralentizar": "40% en 15m"},
        "final_move": {"invocar_minions": True}
    },

    {
        "name": "Manuel",
        "race": "Elfo",
        "social_status": "Paria",
        "weapon": "Macuahuitl",
        "amulet": "Anillo de traducción",
        "pet": {"name": "Loro parlante"},
        "abilities": {"ver_futuro": "7 segundos"},
        "passives": {"pensamiento_acelerado": True},
        "final_move": {"24_frames": "Planificación absoluta"}
    },

    {
        "name": "Tey",
        "race": "Elfa del bosque",
        "social_status": "Paria",
        "weapon": "Arco",
        "amulet": "Collar de resistencia física",
        "pet": {"name": "Búho"},
        "abilities": {"sanacion": True},
        "passives": {"detectar_heridas": True}
    },

    {
        "name": "Narcise",
        "race": "Doppelgänger",
        "social_status": "Paria",
        "weapon": "Daga",
        "amulet": "Anillo de desvío de atención",
        "pet": {"name": "Fénix", "inmortal": True},
        "abilities": {"copiar_apariencia": True},
        "passives": {"copiar_cualidades": True},
        "final_move": {"indetectable": True}
    },

    {
        "name": "Megu",
        "race": "Demonio Carmesí",
        "social_status": "Noble",
        "weapon": "Cuchillo mariposa",
        "amulet": "Anillo de regeneración de maná",
        "pet": {"name": "Gato negro", "habilidad": "Cegar"},
        "abilities": {"dimension_bolsillo": "Volumen casa"},
        "passives": {"tiempo_congelado": "Dentro dimensión"}
    },

    {
        "name": "Wenn",
        "race": "Druida",
        "social_status": "Neutral",
        "weapon": "Arco",
        "amulet": "Planta moldeable",
        "pet": {"name": "Mariposa (Caterpie)"},
        "abilities": {"control_plantas": True},
        "passives": {"robo_vida_plantas": True},
        "final_move": {"armadura_vegetal": "Escala con entorno"}
    },

    {
        "name": "Haki",
        "race": "Elfo",
        "social_status": "Paria",
        "weapon": "Daga",
        "amulet": "Amuleto de velocidad",
        "pet": {"name": "Cuervo (KnY)"},
        "abilities": {"cortes_aire": True},
        "passives": {"pasos_silenciosos": True}
    }
]

async def main():
    pool = await get_pool()
    async with pool.acquire() as conn:
        for c in CHARACTERS:
            await conn.execute("""
                INSERT INTO characters
                (name, race, social_status, status, level,
                 weapon, amulet, pet, abilities, passives, final_move)
                VALUES ($1,$2,$3,'Vivo',1,$4,$5,$6,$7,$8,$9)
                ON CONFLICT (name) DO NOTHING
            """,
            c["name"],
            c["race"],
            c["social_status"],
            c.get("weapon"),
            c.get("amulet"),
            json.dumps(c.get("pet")),
            json.dumps(c.get("abilities")),
            json.dumps(c.get("passives")),
            json.dumps(c.get("final_move"))
            )

    print("✅ TODOS los personajes fueron cargados correctamente.")

if __name__ == "__main__":
    asyncio.run(main())
