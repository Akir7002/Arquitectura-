# Imagen ligera y reproducible (buena práctica: pin de versión exacta).
FROM python:3.12-slim

# Evita bytecode y fuerza logs sin buffer (mejor para logs en contenedores).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Usuario no-root: buena práctica de seguridad en contenedores
# (mitiga escalado de privilegios si el proceso es comprometido).
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# En producción: quitar --reload y ajustar --workers según CPU disponible.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
