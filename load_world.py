import asyncio
import json
from db import get_pool


WORLD_RULES = """
PREMISA CENTRAL
- Los protagonistas reencarnan desde su mundo original en un mundo magico medieval de fantasia poco prospero.
- Existen dioses del lado de los protagonistas, aunque no intervienen de forma constante ni solucionan los conflictos por ellos.
- Los protagonistas compiten contra las leyendas de otro mundo por los recursos.
- Las leyendas son heroes poderosos nativos o ligados a ese mundo rival; no son reencarnados como los protagonistas.

MEMORIA, IDENTIDAD Y MARCAS
- Todos conservan sus recuerdos, conocimientos, personalidad, vinculos emocionales y relaciones del mundo anterior.
- Todos recuerdan su idioma natal: espanol.
- Cada raza posee su propio idioma. De inicio, cada protagonista conoce el idioma de su raza y espanol.
- Todos poseen una marca inconfundible en la mano que los identifica como heroes reencarnados.

CONDICION INICIAL Y REINOS
- Cada protagonista aparece solo y aleatoriamente dentro de un reino correspondiente a su raza.
- Cada protagonista representa y defiende a su reino como campeon.
- Por lo general, el reino de cada campeon le da todo su apoyo.
- En combates contra el otro mundo, los campeones son transportados automaticamente a la zona del combate.
- Los reinos de este mundo son pacificos entre si. No hay guerras internas entre reinos salvo que un evento futuro lo cambie explicitamente.

RELACIONES CANONICAS
- Existen relaciones sentimentales establecidas desde antes de la reencarnacion.
- Estas relaciones son permanentes y deben respetarse estrictamente.
- La narracion no debe crear romances, coqueteos ni vinculos amorosos que contradigan estas reglas.
- Tey y Gray son pareja estable.
- Wenn tiene pareja en su mundo original. Esa pareja no esta en el isekai. Wenn no puede enamorarse ni desarrollar vinculos romanticos con nadie mas.

ESCALA DE PODER
- El mas debil de los protagonistas es tan fuerte como tres caballeros de elite.
- Existen muchos caballeros de elite; son comunes dentro de la elite militar de los reinos.
- Los enemigos comunes tienen un nivel equivalente a un Kulu-Ya-Ku de Monster Hunter.
- Los movimientos finales solo estan disponibles a partir de nivel 30 y deben reservarse para situaciones extremas.
- Para superar el nivel 100, y despues por cada 10 niveles adicionales, el personaje debe cumplir un requisito especial.

MAGIA Y RECURSOS
- La magia se usa con la imaginacion.
- Entender un fenomeno, energia o concepto ayuda a manipularlo mejor.
- Existen minerales tipicos de fantasia estilo D&D.
- Los recursos importantes del mundo son limitados y motivan el conflicto contra las leyendas.

SOCIEDAD Y LEYES
- La belleza promedio de este mundo es lo que el mundo original consideraria fealdad.
- La inteligencia promedio de la poblacion es baja.
- Las leyes son universalmente estrictas.
- Existen esclavos legales. Son caros y la esclavitud esta regulada.
- La jerarquia racial afecta como la poblacion ve a cada raza, aunque puede variar levemente entre reinos.

JERARQUIA SOCIAL RACIAL
- Angeles: Deidad. Venerados y extremadamente raros de ver.
- Vampiros: Deidad. Raros de ver; se respeta su linaje.
- Hombres lobo: Ciudadanos. Comunes entre la poblacion; estandar social.
- Humanos: Ciudadanos. Comunes entre la poblacion; estandar social.
- Sucubos: Esclavos. Usualmente se busca capturarlos para venderlos.
- Elfos: Paria. Discriminados, mal vistos y sujetos a prejuicios.
- Elfos del bosque: Paria. Discriminados, mal vistos y sujetos a prejuicios.
- Descendientes de dragon: Paria. Discriminados por sangre considerada impura.
- Doppelganger: Paria. Discriminados, mal vistos y sujetos a prejuicios.
- Demonio Carmesi: Noble. Alto estatus y respeto social.
- Kitsune: Noble. Alto estatus y respeto social.
- Druidas: Neutral hasta nueva informacion canonica.
"""


SOCIAL_HIERARCHY = {
    "Angeles": {
        "status": "Deidad",
        "description": "Son venerados y considerados extremadamente raros de ver."
    },
    "Vampiros": {
        "status": "Deidad",
        "description": "Raros de ver; se respeta su linaje."
    },
    "Hombres lobo": {
        "status": "Ciudadanos",
        "description": "Comunes entre la poblacion; representan el estandar social."
    },
    "Sucubos": {
        "status": "Esclavos",
        "description": "Usualmente se busca capturarlos para venderlos como esclavos legales."
    },
    "Elfos": {
        "status": "Paria",
        "description": "Discriminados, mal vistos y sujetos a muchos prejuicios."
    },
    "Elfos del bosque": {
        "status": "Paria",
        "description": "Discriminados, mal vistos y sujetos a muchos prejuicios."
    },
    "Descendientes de dragon": {
        "status": "Paria",
        "description": "Discriminados, mal vistos y sujetos a prejuicios por sangre considerada impura."
    },
    "Humanos": {
        "status": "Ciudadanos",
        "description": "Comunes entre la poblacion; representan el estandar social."
    },
    "Doppelganger": {
        "status": "Paria",
        "description": "Discriminados, mal vistos y sujetos a muchos prejuicios."
    },
    "Demonio Carmesi": {
        "status": "Noble",
        "description": "Alto estatus y respeto social."
    },
    "Kitsune": {
        "status": "Noble",
        "description": "Alto estatus y respeto social."
    },
    "Druidas": {
        "status": "Neutral",
        "description": "Estatus racial no definido explicitamente; mantenerlo neutral hasta nueva informacion canonica."
    }
}


WORLD_META = {
    "gods_on_heroes_side": True,
    "slavery_legal": True,
    "slavery_expensive": True,
    "magic_imagination_based": True,
    "kingdoms_at_peace": True,
    "max_base_level": 100,
    "post_100_requirement_every_10_levels": True,
    "elite_knight_power_ratio": 3,
    "enemy_baseline": "Kulu-Ya-Ku",
    "hero_mark": True,
    "languages_per_race": True,
    "native_language": "espanol",
    "memory_from_previous_world": True,
    "fixed_romantic_relationships": True,
    "final_moves_unlock_level": 30,
    "fantasy_minerals_dnd_style": True,
    "average_beauty_seen_as_ugly_by_original_world": True,
    "average_intelligence_low": True
}


async def main():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE world
            SET rules = $1,
                hierarchy = $2::jsonb,
                meta = $3::jsonb
            WHERE id = 1
        """,
        WORLD_RULES,
        json.dumps(SOCIAL_HIERARCHY, ensure_ascii=False),
        json.dumps(WORLD_META, ensure_ascii=False)
        )

    print("Mundo actualizado con reglas canonicas y jerarquia social.")


if __name__ == "__main__":
    asyncio.run(main())
