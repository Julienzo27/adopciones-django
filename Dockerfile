# Imagen de DEMOSTRACIÓN (usa el servidor de desarrollo de Django; no es para producción).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Crea la base, carga los datos ficticios, crea el usuario admin si se pasaron las
# variables DJANGO_SUPERUSER_* y levanta el servidor.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py loaddata datos_ficticios && (python manage.py createsuperuser --noinput 2>/dev/null || true) && python manage.py runserver 0.0.0.0:8000"]
