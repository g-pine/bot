# Bot de Confirmación de Citas Médicas

Bot de Telegram para confirmar, cancelar y reagendar citas médicas.

## Requisitos

```bash
pip install python-telegram-bot[job-queue]==20.7
```

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `TELEGRAM_TOKEN` | Token del bot obtenido desde @BotFather |

## Correr localmente

```bash
export TELEGRAM_TOKEN="tu_token_aqui"
python bot_citas.py
```

## Despliegue en Railway

1. Sube este repositorio a GitHub
2. Entra a [railway.app](https://railway.app) y conecta el repo
3. En **Variables**, agrega `TELEGRAM_TOKEN` con tu token
4. Railway detecta el `Procfile` y despliega automáticamente

## Comandos disponibles

| Comando | Descripción |
|---------|-------------|
| `/start` | Iniciar el bot |
| `/micita` | Ver y gestionar tu cita |
| `/estado` | Ver estado actual |
| `/reset` | Reiniciar datos (pruebas) |
| `/ayuda` | Ver todos los comandos |
