import asyncio
import json
from db import get_pool

WORLD_RULES = """
REENCARNACIÓN
Los protagonistas reencarnan desde nuestro mundo a un mundo mágico medieval de fantasía poco próspero.
Existen dioses del mundo original que observan y permiten la reencarnación.

CONDICIÓN INICIAL
Cada protagonista aparece solo, en un reino correspondiente a su raza.
Cada uno es designado campeón de su reino y recibe apoyo total del mismo.
Cada combate importante transporta automáticamente a los campeones a la zona designada.

CONFLICTO CENTRAL
Los protagonistas deben competir contra leyendas de otro mundo por los recursos del mundo.
Las leyendas NO son reencarnados.
Los reinos son pacíficos entre sí, no existen guerras internas.

ESCALA DE PODER
El más débil de los protagonistas es tan fuerte como 3 caballeros de élite.
Existen muchos caballeros de élite.
Los enemigos comunes tienen un nivel equivalente a un Kulu-Ya-Ku de Monster Hunter.

MAGIA
La magia funciona mediante la imaginación.
Cada energía debe ser comprendida para poder usarse correctamente.

IDIOMAS
Cada raza tiene su propio idioma.
Todos recuerdan su idioma natal (español).
Algunos amuletos permiten traducción universal.

SOCIEDAD
La belleza promedio del mundo es considerada fea en nuestro mundo.
La inteligencia promedio de la población es baja.
Las leyes son estrictas y universales.
La esclavitud es legal, costosa y regulada.

NIVELES
El límite inicial de nivel es 100.
Para superar el nivel 100, y cada 10 niveles posteriores, se debe cumplir un requisito especial.

MARCAS
Todos los campeones tienen una marca inconfundible en la mano que los identifica.

APARICIÓN
Los campeones aparecen aleatoriamente dentro de los reinos correspondientes a su raza.
"""

SOCIAL_HIERARCHY = {
    "Ángeles": "Deidad",
    "Vampiros": "Deidad",
    "Hombres lobo": "Ciudadanos",
    "Humanos": "Ciudadanos",
    "Demonio Carmesí": "Noble",
    "Súcubos": "Esclavos",
    "Elfos": "Paria",
    "Elfos del bosque": "Paria",
    "Descendientes de dragón": "Paria",
    "Doppelgänger": "Paria"
}

WORLD_META = {
    "slavery_legal": True,
    "slavery_expensive": True,
    "magic_imagination_based": True,
    "kingdoms_at_peace": True,
    "max_base_level": 100,
    "elite_knight_power_ratio": 3,
    "enemy_baseline": "Kulu-Ya-Ku",
    "hero_mark": True,
    "languages_per_race": True
}

async def main():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE world
            SET rules = $1,
                hierarchy = $2,
                meta = $3
            WHERE id = 1
        """,
        WORLD_RULES,
        json.dumps(SOCIAL_HIERARCHY),
        json.dumps(WORLD_META)
        )

    print("🌍 Mundo cargado correctamente.")

asyncio.run(main())
