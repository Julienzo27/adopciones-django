# Adopciones — sistema de matching adoptante–perro

**English summary:** Django web app for a dog shelter. Adopters fill in a questionnaire and the system ranks the available dogs by compatibility (exclusion filters + weighted criteria). Shelter staff manage dogs and approve requests. Personal project based on an academic design; all data is fictional.

## Qué es
Aplicación web para un refugio de perros. Cada adoptante completa un cuestionario y el sistema le muestra los perros disponibles ordenados por compatibilidad. El personal del refugio gestiona los perros y decide las solicitudes. La decisión final siempre es del personal.

El **motor de compatibilidad** aplica primero filtros excluyentes (niños, otras mascotas, tipo de vivienda) y después calcula un porcentaje con criterios ponderados y configurables, sin inteligencia artificial:

`% = puntos obtenidos ÷ suma de pesos activos × 100`

## Estado del proyecto
- [X] Etapa 0: preparación del repositorio
- [X] Etapa 1: modelo de datos y admin
- [X] Etapa 2: motor de compatibilidad con tests
- [ ] Etapa 3: lado del adoptante (cuestionario y listado)
- [ ] Etapa 4: solicitudes y aprobación
- [ ] Etapa 5: pesos configurables
- [ ] Etapa 6: API REST y frontend en JavaScript
- [ ] Etapa 7: tests automáticos, documentación y capturas

## Tecnologías
Python 3 · Django · SQLite · HTML · CSS · JavaScript (más adelante: Django REST Framework, GitHub Actions)

## Cómo ejecutarlo (Windows, PowerShell)
```powershell
git clone https://github.com/<tu-usuario>/adopciones-django.git
cd adopciones-django
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
Abrir http://127.0.0.1:8000/

## Origen y créditos
El diseño original (requerimientos, arquitectura de 11 módulos, modelo de datos y prueba de concepto) fue elaborado por el equipo **Código Digital** (María Rita Zumbo, Jimena Obella y Samanta Godoy) para Prácticas Profesionales III, IFTS N° 12. Esta implementación es un desarrollo personal posterior.

## Uso de IA
Parte del código se escribe con ayuda de Claude (IA) y es revisado por la autora.

## Datos
Todos los adoptantes y perros son ficticios.

## Licencia
MIT
