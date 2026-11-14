"""
Motor de compatibilidad (solo lectura).

Decisión de diseño validada en la PoC: el motor es un módulo independiente que
SOLO LEE datos. Primero aplica filtros excluyentes y después calcula el
porcentaje con los criterios ponderados activos:

    % = puntos obtenidos ÷ suma de pesos activos × 100

No usa inteligencia artificial: son reglas configurables.
Este módulo nunca crea, modifica ni borra registros.
"""
from dataclasses import dataclass, field

from adopciones.models import Adoptante, Criterio, Perro

# Niveles ordenados de menor a mayor (para comparar por diferencia).
NIVEL = {
    "bajo": 0, "medio": 1, "alto": 2,                 # energía / actividad
    "ninguna": 0, "alguna": 1, "mucha": 2,            # experiencia
    "ninguno": 0, "chico": 1, "amplio": 2,            # espacio exterior del adoptante
}
ESPACIO_NECESARIO = {"poco": 0, "medio": 1, "mucho": 2}
EDAD_CATEGORIA = {"cachorro": 0, "adulto": 1, "mayor": 2}


class RechazoMotor(Exception):
    """El motor se niega a calcular (perfil incompleto, sin criterios, etc.)."""


@dataclass
class Compatible:
    perro: Perro
    porcentaje: float
    puntos: dict = field(default_factory=dict)   # puntos obtenidos por criterio


@dataclass
class Excluido:
    perro: Perro
    motivo: str


# ------------------------------------------------------------------ utilidades
def categoria_edad(anios):
    """Cachorro: menos de 2 años. Adulto: de 2 a 7. Mayor: 8 o más."""
    if anios < 2:
        return "cachorro"
    return "adulto" if anios < 8 else "mayor"


def _por_diferencia(d):
    """Grado de coincidencia según la diferencia de niveles: 1, 0,5 o 0."""
    if d <= 0:
        return 1.0
    return 0.5 if d == 1 else 0.0


# ------------------------------------------------------- grado de cada criterio
def grado_energia(a, p):
    return _por_diferencia(abs(NIVEL[a.nivel_actividad] - NIVEL[p.nivel_energia]))


def grado_experiencia(a, p):
    # Falta = experiencia que pide el perro − experiencia que tiene el adoptante.
    return _por_diferencia(NIVEL[p.experiencia_requerida] - NIVEL[a.experiencia_previa])


def grado_espacio(a, p):
    return _por_diferencia(ESPACIO_NECESARIO[p.espacio_necesario] - NIVEL[a.espacio_exterior])


def grado_edad(a, p):
    if a.edad_preferida == "sin preferencia":
        return 1.0
    diferencia = abs(EDAD_CATEGORIA[a.edad_preferida] - EDAD_CATEGORIA[categoria_edad(p.edad)])
    return _por_diferencia(diferencia)


def grado_preferencias(a, p):
    """Proporción de preferencias marcadas que el perro cumple (1 si no marcó ninguna)."""
    pares = [
        (a.pref_apto_ninos, p.apto_ninos),
        (a.pref_apto_otras_mascotas, p.apto_otras_mascotas),
        (a.pref_apto_departamento, p.apto_departamento),
    ]
    marcadas = [cumple for marcada, cumple in pares if marcada]
    if not marcadas:
        return 1.0
    return sum(1 for cumple in marcadas if cumple) / len(marcadas)


GRADOS = {
    "energia": grado_energia,
    "experiencia": grado_experiencia,
    "espacio": grado_espacio,
    "edad": grado_edad,
    "preferencias": grado_preferencias,
}


# ------------------------------------------------------------------- filtros
def filtro_excluyente(a, p):
    """Devuelve el motivo de exclusión, o None si el perro supera los filtros."""
    if a.hay_ninos and not p.apto_ninos:
        return "no es apto para convivir con niños"
    if a.tiene_otras_mascotas and not p.apto_otras_mascotas:
        return "no es apto para convivir con otras mascotas"
    if a.tipo_vivienda == "departamento" and not p.apto_departamento:
        return "no es apto para departamento"
    return None


# ---------------------------------------------------------------- operación
def calcular_compatibilidades(adoptante):
    """Para un adoptante, devuelve (compatibles, excluidos).

    - compatibles: perros disponibles que superan los filtros, con su % y el
      detalle por criterio, ordenados de mayor a menor.
    - excluidos: perros disponibles que no superan los filtros, con su motivo
      (no reciben porcentaje).
    """
    if not adoptante.perfil_completo:
        raise RechazoMotor("perfil incompleto")

    criterios = list(Criterio.objects.filter(activo=True))
    total = sum(c.peso for c in criterios)
    if not criterios or total == 0:
        raise RechazoMotor("sin criterios configurados")

    compatibles, excluidos = [], []
    for perro in Perro.objects.filter(estado=Perro.Estado.DISPONIBLE):
        motivo = filtro_excluyente(adoptante, perro)
        if motivo:
            excluidos.append(Excluido(perro, motivo))
            continue
        puntos = {c.nombre: GRADOS[c.nombre](adoptante, perro) * c.peso for c in criterios}
        porcentaje = round(sum(puntos.values()) / total * 100, 1)   # siempre entre 0 y 100
        compatibles.append(Compatible(perro, porcentaje, puntos))

    compatibles.sort(key=lambda c: -c.porcentaje)
    return compatibles, excluidos
