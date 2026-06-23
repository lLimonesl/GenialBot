import asyncio
import json
from db import get_pool


def ability(name, description, limits=None, notes=None):
    return {
        "name": name,
        "description": description,
        "limits": limits or "Sin limite adicional definido.",
        "notes": notes or ""
    }


def final_move(name, description, cost=None, cooldown=None, requirement="Nivel 30 o superior"):
    return {
        "name": name,
        "requirement": requirement,
        "description": description,
        "cost": cost or "Sin coste adicional definido.",
        "cooldown": cooldown or "Sin enfriamiento definido."
    }


CHARACTERS = [
    {
        "name": "Javiche",
        "race": "Angel caido",
        "social_status": "Deidad",
        "weapon": "Alabarda",
        "amulet": "Anillo de regeneracion rapida de estamina",
        "pet": {
            "name": "Puerco alado",
            "description": "Mascota alada; si muere revive al tercer dia.",
            "revives": True,
            "revive_days": 3
        },
        "abilities": {
            "duplicar": ability(
                "Duplicar objetos y seres",
                "Crea copias temporales de objetos o seres.",
                "Maximo 5 copias; puede crear un poco mas si son objetos pequenos. Mientras mas copias existan, menos resistentes son. Duran como maximo una semana."
            )
        },
        "passives": {
            "debilitar_al_tocar": ability(
                "Debilitar al tocar",
                "Al tocar a un ser puede reducirlo a la mitad de su fuerza.",
                "Debe haber contacto fisico."
            )
        },
        "final_move": final_move(
            "Transferencia a clon",
            "Si muere, puede transferirse a uno de sus clones.",
            "Pierde todos sus objetos y un 30% de su nivel. Tras transferirse tarda 3 dias en recuperar el poder del original.",
            "7 dias despues de recuperar el poder completo."
        )
    },
    {
        "name": "Red",
        "race": "Vampiro",
        "social_status": "Deidad",
        "weapon": "Cimitarras duales",
        "amulet": "Anillo de traduccion de lenguajes",
        "pet": {"name": "Dragon", "variant": "Variante tipo Frederica de HnC"},
        "abilities": {
            "copiar_poderes": ability(
                "Copiar poderes",
                "Copia poderes activos de otros seres.",
                "No puede copiar pasivas."
            )
        },
        "passives": {
            "zona_antimagia": ability(
                "Deshabilitar poderes",
                "Deshabilita poderes en un radio de 5 metros.",
                "Tambien se afecta a si mismo."
            )
        },
        "final_move": final_move(
            "Emular pasivas",
            "Emula pasivas de otros usuarios hasta un maximo del 75% del efecto original. Puede dividir ese porcentaje entre distintas pasivas.",
            "Sufre desgaste fisico durante el uso.",
            "Duracion maxima: 30 minutos."
        )
    },
    {
        "name": "Winters",
        "race": "Hombre lobo",
        "social_status": "Ciudadano",
        "weapon": "Punos de hierro",
        "amulet": "Anillo de aumento menor de resistencias generales",
        "pet": {"name": "Lobo gigante", "sex": "Macho"},
        "abilities": {"correr_rapido": ability("Correr rapido", "Puede desplazarse a gran velocidad.")},
        "passives": {"resistencia_fisica": ability("Resistencia fisica alta", "Tiene resistencia fisica alta de forma permanente.")},
        "final_move": final_move("Aumento de resistencia", "Aumenta drasticamente su resistencia.", cooldown="Ulti de season 1")
    },
    {
        "name": "Alex",
        "race": "Sucubo",
        "social_status": "Esclavo",
        "weapon": "Gran mangual",
        "amulet": "Collar con gema que genera una pequena carga electrica infinita",
        "pet": {"name": "Golem de hierro"},
        "abilities": {
            "rayos": ability(
                "Controlar electricidad en forma de rayos",
                "Manipula electricidad como rayos ofensivos o utilitarios.",
                "Requiere cargarse con una fuente externa; su amuleto aporta una carga pequena constante."
            )
        },
        "passives": {"cambio_de_forma": ability("Cambio de forma", "Rasgo de sucubo que permite alterar su apariencia.")},
        "final_move": final_move("Arma electrificada", "Infunde su arma con electricidad.")
    },
    {
        "name": "Chakas",
        "race": "Elfo",
        "social_status": "Paria",
        "weapon": "Arco largo",
        "amulet": "Anillo de aumento considerable de dano mientras no haya recibido ningun golpe",
        "pet": {"name": "Dragon de fuego"},
        "abilities": {
            "teletransporte": ability(
                "Teletransporte",
                "Puede teletransportarse a lugares que pueda ver por algun medio.",
                "No funciona hacia ubicaciones no observadas."
            )
        },
        "passives": {"aprendizaje_rapido": ability("Aprendizaje rapido", "Aprende y adapta tecnicas con rapidez superior.")},
        "final_move": final_move(
            "Teletransporte masivo de objeto",
            "Teletransporta un objeto de gran tamano a cualquier ubicacion.",
            "Segun la distancia, su poder queda muy reducido temporalmente y consume anos de esperanza de vida."
        )
    },
    {
        "name": "Flamas",
        "race": "Descendiente de dragon",
        "social_status": "Paria",
        "weapon": None,
        "amulet": "Anillo de aumento menor de resistencias elementales",
        "pet": {"name": "Wyvern de rayo"},
        "abilities": {
            "control_energias": ability(
                "Control de energias",
                "Controla energias despues de comprender como funciona cada una.",
                "Debe aprender el funcionamiento de cada energia antes de usarla bien."
            )
        },
        "passives": {"energia_propia": ability("Energia propia", "Posee una energia personal unica.")},
        "final_move": final_move(
            "Presencia minima",
            "Reduce todos sus poderes y resistencias al minimo para hacerse imposible de detectar a simple vista.",
            "Queda extremadamente vulnerable mientras mantiene el estado."
        )
    },
    {
        "name": "Gray",
        "race": "Humano",
        "social_status": "Ciudadano",
        "weapon": "Hacha",
        "amulet": "Anillo de regeneracion rapida de estamina",
        "pet": {"name": "Lobo", "habilidad": "Puede ocultarse en la sombra de Gray y volverse indetectable."},
        "abilities": {"regeneracion": ability("Regeneracion fisica", "Regenera salud fisica.")},
        "passives": {
            "fuerza_y_velocidad_escalables": ability(
                "Escalada de fuerza y velocidad",
                "Obtiene aumento menor de fuerza y velocidad que escala mientras se prolongue el combate."
            )
        },
        "final_move": final_move("Super regeneracion", "Regenera al instante y obtiene un aumento considerable de velocidad.")
    },
    {
        "name": "Limones",
        "race": "Elfa",
        "social_status": "Paria",
        "weapon": "Daga",
        "amulet": "Anillo de aumento de suerte 30%",
        "pet": {"name": "Zorro gigante"},
        "abilities": {
            "necromancia": ability("Necromancia", "Puede reanimar y controlar a los muertos.")
        },
        "passives": {
            "ralentizar": ability("Aura de ralentizacion", "Cualquier persona dentro de 15 metros se ralentiza 40%.")
        },
        "final_move": final_move(
            "Invocar minions",
            "Invoca a su ubicacion uno de sus minions mas fuertes o tres minions de menor nivel."
        )
    },
    {
        "name": "Manuel",
        "race": "Elfo",
        "social_status": "Paria",
        "weapon": "Macuahuitl",
        "amulet": "Anillo de traduccion de lenguajes",
        "pet": {"name": "Loro parlante"},
        "abilities": {"ver_futuro": ability("Ver 7 segundos adelante", "Puede ver siete segundos en el futuro.")},
        "passives": {"pensamiento_acelerado": ability("Pensamiento acelerado", "Procesa informacion y decisiones con velocidad anormal.")},
        "final_move": final_move(
            "Trazo de 24 frames",
            "Hace que sus movimientos y lo que toquen sus manos se realicen en un trazo de 24 frames por segundo. Planea mentalmente todo lo que ocurrira en esos 24 frames, incluidos sus movimientos, y luego debe ejecutarlo exactamente.",
            "Si no realiza el movimiento como fue planeado, queda congelado durante 1 segundo.",
            "Ulti de season 20"
        )
    },
    {
        "name": "Tey",
        "race": "Elfa del bosque",
        "social_status": "Paria",
        "weapon": "Arco",
        "amulet": "Collar de resistencia fisica aumentada",
        "pet": {"name": "Buho"},
        "abilities": {"sanacion": ability("Sanacion", "Puede curar heridas y malestares.")},
        "passives": {"detectar_heridas": ability("Identificar heridas", "Identifica heridas y malestares con la vista.")},
        "final_move": final_move("Curacion acelerada", "Realiza curacion muy rapida.", cooldown="Ulti de season 2")
    },
    {
        "name": "Narcise",
        "race": "Doppelganger",
        "social_status": "Paria",
        "weapon": "Daga",
        "amulet": "Anillo de desvio de atencion",
        "pet": {"name": "Fenix", "inmortal": True, "description": "Es inmortal, pero su poder de combate esta limitado."},
        "abilities": {"copiar_apariencia": ability("Copiar apariencia", "Puede tomar el aspecto de cualquier ser.")},
        "passives": {
            "copiar_cualidades_raciales": ability(
                "Copia racial",
                "Rasgo de doppelganger: copia cualidades de raza y un porcentaje de la fuerza de los seres a los que imita."
            )
        },
        "final_move": final_move(
            "Presencia anulada",
            "Reduce todos sus poderes y resistencias al minimo para hacerse imposible de detectar a simple vista.",
            "Aunque se parece al final move de Flamas, su origen y funcionamiento no son exactamente iguales. Queda vulnerable mientras lo usa."
        )
    },
    {
        "name": "Megu",
        "race": "Demonio Carmesi",
        "social_status": "Noble",
        "weapon": "Cuchillo mariposa",
        "amulet": "Anillo de regeneracion de mana considerablemente lenta",
        "pet": {"name": "Gato negro", "habilidad": "Puede cegar objetivos."},
        "abilities": {
            "dimension_bolsillo": ability(
                "Dimension de bolsillo",
                "Almacena cosas en una dimension de bolsillo con volumen similar al de una casa.",
                "Solo puede almacenar cosas no mas grandes que una persona."
            )
        },
        "passives": {"tiempo_congelado": ability("Tiempo congelado interno", "El tiempo se congela dentro de su dimension de bolsillo.")},
        "final_move": None
    },
    {
        "name": "Wenn",
        "race": "Druida",
        "social_status": "Neutral",
        "weapon": "Arco",
        "amulet": "Planta moldeable",
        "pet": {"name": "Mariposa", "stage": "Inicia como Caterpie"},
        "abilities": {"control_plantas": ability("Control de plantas", "Controla plantas cercanas o disponibles.")},
        "passives": {"robo_vida_plantas": ability("Robo de vida vegetal", "Roba vida a las plantas.")},
        "final_move": final_move(
            "Armadura vegetal",
            "Imbuye de energia su amuleto de planta y lo convierte en una armadura.",
            "La armadura se hace mas poderosa dependiendo de las plantas cercanas."
        )
    },
    {
        "name": "Haki",
        "race": "Elfo",
        "social_status": "Paria",
        "weapon": "Daga",
        "amulet": "Amuleto de velocidad",
        "pet": {"name": "Cuervo", "variant": "KnY"},
        "abilities": {"cortes_aire": ability("Cortes de aire", "Genera cortes de aire ofensivos.")},
        "passives": {"pasos_silenciosos": ability("Pies ligeros", "Sus pasos son silenciosos.")},
        "final_move": final_move("Corte decisivo", "Realiza un corte extremadamente poderoso.", cooldown="Ulti de season 3")
    },
    {
        "name": "Star",
        "race": "Kitsune",
        "social_status": "Noble",
        "weapon": "Sarten de hierro",
        "amulet": "Omamori de regeneracion de mana considerablemente lenta",
        "pet": {"name": "Felyne", "variant": "Monster Hunter"},
        "abilities": {
            "buffs_vitalidad": ability(
                "Aumento de vitalidad y buffs",
                "Aumenta vitalidad y aplica mejoras a personas y objetos."
            )
        },
        "passives": {"hablar_con_animales": ability("Hablar con animales", "Puede comunicarse con animales.")},
        "final_move": final_move(
            "Milagro compartido",
            "Aumenta sus habilidades de curacion y vuelve imbatibles a sus companeros durante 90 minutos divididos entre la cantidad de afectados: 1 por 90 min, 2 por 45 min, etc.",
            "Al terminar queda inconsciente durante 2 dias."
        )
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
                ON CONFLICT (name) DO UPDATE SET
                    race = EXCLUDED.race,
                    social_status = EXCLUDED.social_status,
                    weapon = EXCLUDED.weapon,
                    amulet = EXCLUDED.amulet,
                    pet = EXCLUDED.pet,
                    abilities = EXCLUDED.abilities,
                    passives = EXCLUDED.passives,
                    final_move = EXCLUDED.final_move
            """,
            c["name"],
            c["race"],
            c["social_status"],
            c.get("weapon"),
            c.get("amulet"),
            json.dumps(c.get("pet"), ensure_ascii=False),
            json.dumps(c.get("abilities"), ensure_ascii=False),
            json.dumps(c.get("passives"), ensure_ascii=False),
            json.dumps(c.get("final_move"), ensure_ascii=False)
            )

    print("Personajes cargados/actualizados correctamente.")


if __name__ == "__main__":
    asyncio.run(main())
