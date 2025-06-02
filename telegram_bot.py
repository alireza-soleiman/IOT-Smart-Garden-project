from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from datetime import datetime
import requests
import json
import os

class TelegramBot:
    def __init__(self, token, stats_url):
        self.token = token
        self.stats_url = stats_url
        self.awaiting_date = {}  # track users awaiting a date input

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [["/status", "/pump_log"], ["/history"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "👋 Welcome to Smart Garden! Use the buttons below:",
            reply_markup=reply_markup
        )

    async def send_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            soil_response = requests.get(f"{self.stats_url}/soil")
            soil_data = soil_response.json()

            weather_response = requests.get(f"{self.stats_url}/weather")
            weather_data = weather_response.json()

            message = (
                "🌱 Garden Status 🌱\n"
                f"💧 Soil Moisture: {soil_data['latest']['moisture']:.1f}%\n"
                f"🌡 Temperature: {weather_data['latest']['temperature']:.1f}°C\n"
                f"💦 Humidity: {weather_data['latest']['humidity']:.1f}%\n"
                f"☔ Rainfall: {weather_data['latest']['rainfall']:.1f}mm"
            )

            await update.message.reply_text(message)
        except Exception as e:
            await update.message.reply_text(f"Error getting status: {e}")

    async def send_pump_log(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            response = requests.get(f"{self.stats_url}/pump")
            pump_data = response.json()

            message = "🚰 Pump Activations:\n"
            if pump_data["total_activations"] == 0:
                message += "No activations recorded"
            else:
                last = pump_data.get("last_activation")
                timestamp_str = last.get("timestamp")
                

                message += (
                    f"Total: {pump_data['total_activations']}\n"
                    f"Last: {last.get('duration', '?')}s at {timestamp_str}"
                )

            await update.message.reply_text(message)
        except Exception as e:
            await update.message.reply_text(f"Error getting pump log: {e}")

    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        self.awaiting_date[user_id] = True
        await update.message.reply_text("📅 Please send the date you want to view (format: YYYY-MM-DD):")

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        if self.awaiting_date.get(user_id):
            date_input = update.message.text.strip()
            self.awaiting_date[user_id] = False
            await self.send_history(update, date_input)
        else:
            await update.message.reply_text("❓ I didn't understand that. Please use the command buttons.")

    async def send_history(self, update: Update, date_str: str):
        try:
            if not os.path.exists("database.json"):
                await update.message.reply_text("📁 No database found.")
                return

            with open("database.json", "r") as f:
                db = json.load(f)

            if date_str not in db:
                await update.message.reply_text(f"❌ No data available for {date_str}")
                return

            day_data = db[date_str]
            message = f"📊 Data for {date_str}:\n"

            # Soil
            soil_entries = day_data.get("soil_moisture", [])
            if soil_entries:
                avg_soil = sum(d["moisture"] for d in soil_entries) / len(soil_entries)
                message += f"\n💧 Soil Moisture: {avg_soil:.1f}% (avg, {len(soil_entries)} readings)"
            else:
                message += "\n💧 Soil Moisture: No data"

            # Weather
            weather_entries = day_data.get("weather", [])
            if weather_entries:
                avg_temp = sum(d["temperature"] for d in weather_entries) / len(weather_entries)
                avg_humidity = sum(d["humidity"] for d in weather_entries) / len(weather_entries)
                total_rain = sum(d["rainfall"] for d in weather_entries)
                message += (
                    f"\n🌡 Temp: {avg_temp:.1f}°C | 💦 Humidity: {avg_humidity:.1f}% | ☔ Rain: {total_rain:.1f}mm"
                )
            else:
                message += "\n🌡 Weather: No data"

            # Pump
            pump_entries = day_data.get("pump_activations", [])
            if pump_entries:
                message += f"\n🚰 Pump Activations: {len(pump_entries)}"
            else:
                message += "\n🚰 Pump: No activations"

            await update.message.reply_text(message)
        except Exception as e:
            await update.message.reply_text(f"Error loading history: {e}")

    def run(self):
        app = ApplicationBuilder().token(self.token).build()

        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("status", self.send_status))
        app.add_handler(CommandHandler("pump_log", self.send_pump_log))
        app.add_handler(CommandHandler("history", self.history_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))

        print("Bot started...")
        app.run_polling()

    

if __name__ == "__main__":
    TOKEN = "7896439931:AAHqi7qyiTW4WUA1lHrYA-6RWpQeptVsSug"
    STATS_URL = "http://localhost:5001"
    bot = TelegramBot(TOKEN, STATS_URL)
    bot.run()
