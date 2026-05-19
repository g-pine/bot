"""
Bot de confirmación de citas médicas — versión consolidada
Requiere: pip install python-telegram-bot[job-queue]
"""

import os
import threading
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ─── Configuración ────────────────────────────────────────────────────────────
TOKEN = os.environ["TELEGRAM_TOKEN"]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ─── Memoria temporal ─────────────────────────────────────────────────────────
CITAS = {}

NUEVA_HORA  = "15:30"

# Fechas dinámicas basadas en la fecha del sistema
_hoy        = datetime.now()
FECHA_CITA  = (_hoy + timedelta(days=2)).strftime("%d/%m/%Y")  # cita original: hoy + 2 días
NUEVA_FECHA = (_hoy + timedelta(days=5)).strftime("%d/%m/%Y")  # reagendada:    hoy + 5 días

# ─── Funciones auxiliares ─────────────────────────────────────────────────────
def obtener_cita(chat_id: int) -> dict | None:
    return CITAS.get(chat_id)

def registrar_cita(chat_id: int, datos: dict):
    CITAS[chat_id] = datos

def formatear_cita(cita: dict) -> str:
    return (
        f"📅 *Fecha:* {cita['fecha']}\n"
        f"🕐 *Hora:* {cita['hora']}\n"
        f"👨‍⚕️ *Profesional:* {cita.get('doctor', 'Por confirmar')}\n"
        f"👤 *Paciente:* {cita.get('paciente', 'Sin nombre')}"
    )

# ─── Teclados ─────────────────────────────────────────────────────────────────
def teclado_confirmacion() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirmar asistencia", callback_data="confirmar"),
            InlineKeyboardButton("❌ Cancelar cita",        callback_data="cancelar"),
        ],
        [
            InlineKeyboardButton("🔄 Reagendar",            callback_data="reagendar"),
        ]
    ])

def teclado_solo_reagendar() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Reagendar cita", callback_data="reagendar")]
    ])

def teclado_cancelacion() -> InlineKeyboardMarkup:
    """5 motivos de cancelación para recopilar información del paciente."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏥 Emergencia médica",              callback_data="motivo_emergencia")],
        [InlineKeyboardButton("💼 Trabajo o estudios",             callback_data="motivo_laboral")],
        [InlineKeyboardButton("🚗 Problemas de transporte",        callback_data="motivo_transporte")],
        [InlineKeyboardButton("💊 Me siento mejor / sin síntomas", callback_data="motivo_mejoria")],
        [InlineKeyboardButton("📌 Otro motivo",                    callback_data="motivo_otro")],
    ])

# ─── Comandos ─────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    nombre  = update.effective_user.first_name
    cita    = obtener_cita(chat_id)
    estado  = context.user_data.get("estado", "pendiente")

    if cita and estado == "confirmada":
        await update.message.reply_text(
            f"👋 Hola nuevamente, *{nombre}*.\n\n"
            f"✅ Ya tienes una cita confirmada:\n\n"
            f"{formatear_cita(cita)}\n\n"
            f"Usa /estado para revisar el detalle de tu cita.",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        f"👋 Hola, *{nombre}*.\n\n"
        f"Soy el asistente de confirmación de citas médicas.\n\n"
        f"Usa /micita para revisar tu próxima cita.\n"
        f"Usa /ayuda para ver todos los comandos disponibles.",
        parse_mode="Markdown"
    )

async def micita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cita    = obtener_cita(chat_id)

    if not cita:
        cita = {
            "paciente": update.effective_user.first_name,
            "fecha":    FECHA_CITA,
            "hora":     "11:00",
            "doctor":   "Dra. García"
        }
        registrar_cita(chat_id, cita)

    estado       = context.user_data.get("estado", "pendiente")
    estado_texto = {
        "pendiente":  "⏳ Pendiente de confirmación",
        "confirmada": "✅ Confirmada",
        "cancelada":  "❌ Cancelada",
        "reagendada": "🔄 Reagendada",
        "no_asistio": "⚠️ No asistió",
    }.get(estado, "⏳ Pendiente")

    motivo = context.user_data.get("motivo_cancelacion")
    motivos_texto = {
        "emergencia": "🏥 Emergencia médica",
        "laboral":    "💼 Trabajo o estudios",
        "transporte": "🚗 Problemas de transporte",
        "mejoria":    "💊 Mejoría / sin síntomas",
        "otro":       "📌 Otro motivo",
    }
    motivo_linea = (
        f"\n📝 *Motivo de cancelación:* {motivos_texto.get(motivo, motivo)}"
        if estado == "cancelada" and motivo else ""
    )

    await update.message.reply_text(
        f"📋 *Tu próxima cita:*\n\n"
        f"{formatear_cita(cita)}\n\n"
        f"📌 *Estado:* {estado_texto}{motivo_linea}\n\n"
        f"¿Qué deseas hacer?",
        parse_mode="Markdown",
        reply_markup=teclado_confirmacion() if estado == "pendiente" else None
    )

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Comandos disponibles:*\n\n"
        "/start    — Iniciar el bot\n"
        "/micita   — Ver tu próxima cita y confirmar/cancelar\n"
        "/estado   — Ver el estado actual de tu cita\n"
        "/reset    — Borrar datos y reiniciar prueba\n"
        "/ayuda    — Mostrar este mensaje",
        parse_mode="Markdown"
    )

async def estado_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    estado_actual = context.user_data.get("estado", "pendiente")
    motivo        = context.user_data.get("motivo_cancelacion")
    motivos_texto = {
        "emergencia": "🏥 Emergencia médica",
        "laboral":    "💼 Trabajo o estudios",
        "transporte": "🚗 Problemas de transporte",
        "mejoria":    "💊 Mejoría / sin síntomas",
        "otro":       "📌 Otro motivo",
    }

    textos = {
        "pendiente":  "⏳ Tu cita está *pendiente* de confirmación. Usa /micita para responder.",
        "confirmada": "✅ Tu cita está *confirmada*. ¡Te esperamos!",
        "cancelada":  (
            "❌ Tu cita fue *cancelada*."
            + (f"\n📝 Motivo: {motivos_texto.get(motivo, motivo)}" if motivo else "")
            + "\n\nPuedes reagendar con /micita."
        ),
        "reagendada": "🔄 Tu cita fue *reagendada*. ¡Te esperamos en la nueva fecha!",
        "no_asistio": "⚠️ La cita quedó marcada como *no asistida*. Usa /micita para agendar una nueva.",
    }

    await update.message.reply_text(
        textos.get(estado_actual, "Estado desconocido."),
        parse_mode="Markdown"
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in CITAS:
        del CITAS[chat_id]
    context.user_data.clear()
    await update.message.reply_text(
        "🗑️ Datos eliminados correctamente.\n\n"
        "Puedes comenzar una nueva prueba con /start o /micita."
    )

# ─── Callbacks de botones ─────────────────────────────────────────────────────
async def manejar_boton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    accion  = query.data
    cita    = obtener_cita(chat_id)

    # ── Confirmar ────────────────────────────────────────────────────────────
    if accion == "confirmar":
        context.user_data["estado"] = "confirmada"

        await query.edit_message_text(
            text=(
                "✅ *CITA CONFIRMADA*\n\n"
                "Tu hora fue confirmada exitosamente.\n\n"
                f"{formatear_cita(cita)}\n\n"
                "📍 Por favor llega 10 minutos antes.\n"
                "📞 Si no puedes asistir, avísanos con anticipación.\n\n"
                "Gracias por confirmar 😊"
            ),
            parse_mode="Markdown",
            reply_markup=teclado_solo_reagendar()
        )

        context.job_queue.run_once(
            recordatorio,
            when=timedelta(seconds=15),
            chat_id=chat_id,
            data=cita,
            name=f"recordatorio1_{chat_id}"
        )
        context.job_queue.run_once(
            segundo_recordatorio,
            when=timedelta(seconds=30),
            chat_id=chat_id,
            data=cita,
            name=f"recordatorio2_{chat_id}"
        )
        context.job_queue.run_once(
            verificar_asistencia,
            when=timedelta(seconds=45),
            chat_id=chat_id,
            data=cita,
            name=f"verificacion_{chat_id}"
        )

    # ── Cancelar: mostrar menú de motivos ────────────────────────────────────
    elif accion == "cancelar":
        await query.edit_message_text(
            text=(
                "❌ *Cancelación de cita*\n\n"
                "Para registrar la cancelación, selecciona el motivo principal:"
            ),
            parse_mode="Markdown",
            reply_markup=teclado_cancelacion()
        )

    # ── Motivo de cancelación ─────────────────────────────────────────────────
    elif accion.startswith("motivo_"):
        motivo = accion.replace("motivo_", "")
        context.user_data["estado"]             = "cancelada"
        context.user_data["motivo_cancelacion"] = motivo

        motivos_texto = {
            "emergencia": "🏥 Emergencia médica",
            "laboral":    "💼 Trabajo o estudios",
            "transporte": "🚗 Problemas de transporte",
            "mejoria":    "💊 Mejoría / sin síntomas",
            "otro":       "📌 Otro motivo",
        }

        await query.edit_message_text(
            text=(
                "❌ *Cita cancelada correctamente*\n\n"
                f"📝 *Motivo registrado:* {motivos_texto.get(motivo, motivo)}\n\n"
                "✅ El cupo podrá ser reasignado a otro paciente "
                "o utilizado para una atención de urgencia.\n\n"
                "Si deseas reagendar para otra fecha, usa el botón de abajo."
            ),
            parse_mode="Markdown",
            reply_markup=teclado_solo_reagendar()
        )

    # ── Reagendar ─────────────────────────────────────────────────────────────
    elif accion == "reagendar":
        context.user_data["estado"] = "reagendada"

        cita_reagendada = {**cita, "fecha": NUEVA_FECHA, "hora": NUEVA_HORA}
        registrar_cita(chat_id, cita_reagendada)

        await query.edit_message_text(
            text=(
                "🔄 *¡Cita reagendada exitosamente!*\n\n"
                f"{formatear_cita(cita_reagendada)}\n\n"
                "Usa /micita para revisar tu nueva cita."
            ),
            parse_mode="Markdown"
        )

# ─── Jobs de recordatorio ─────────────────────────────────────────────────────
async def recordatorio(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    cita    = context.job.data

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"⏰ *Recordatorio de cita*\n\n"
            f"{formatear_cita(cita)}\n\n"
            "Tu cita es próximamente. "
            "Recuerda llegar con 10 minutos de anticipación."
        ),
        parse_mode="Markdown"
    )

async def segundo_recordatorio(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🔔 *Segundo recordatorio*\n\n"
            "Tu atención comenzará pronto.\n\n"
            "Si no podrás asistir, por favor cancela tu cita "
            "para liberar el cupo a otro paciente."
        ),
        parse_mode="Markdown"
    )

async def verificar_asistencia(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "⚠️ *Verificación de asistencia*\n\n"
            "Han pasado algunos minutos desde tu hora agendada.\n\n"
            "Si no asistirás, tu cupo podrá ser reasignado "
            "a otro paciente con atención de urgencia."
        ),
        parse_mode="Markdown"
    )

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    print("🌐 Health server iniciado...")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("micita", micita))
    app.add_handler(CommandHandler("ayuda",  ayuda))
    app.add_handler(CommandHandler("estado", estado_cmd))
    app.add_handler(CommandHandler("reset",  reset))
    app.add_handler(CallbackQueryHandler(manejar_boton))

    print("🤖 Bot de citas iniciado...")
    app.run_polling()


# ─── Health check server (requerido por Fly.io) ───────────────────────────────
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args):
        pass  # silencia los logs del servidor HTTP

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()
