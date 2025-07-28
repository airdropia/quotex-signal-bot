import os
import requests
import pytz
import datetime
import ta
import pandas as pd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TIMEZONE = pytz.timezone("Asia/Karachi")

PAIRS = ["AUDCHF-OTC", "EURUSD-OTC", "GBPJPY-OTC", "USDJPY-OTC", "GBPUSD-OTC", 
         "AUDJPY-OTC", "EURJPY-OTC", "USDCHF-OTC", "AUDUSD-OTC", "NZDJPY-OTC"]

EXPIRY_OPTIONS = ["M1", "M5"]
BROKERS = ["Quotex", "Binomo", "IQOption"]
TRADE_TYPE = ["OTC", "LIVE"]

user_data = {}

def generate_signal(pair):
    data = pd.DataFrame({
        "close": [1.1, 1.2, 1.3, 1.25, 1.28, 1.24, 1.22, 1.26, 1.3, 1.28],
        "high":  [1.12, 1.23, 1.33, 1.3, 1.29, 1.26, 1.24, 1.28, 1.32, 1.3],
        "low":   [1.08, 1.18, 1.28, 1.22, 1.25, 1.22, 1.2, 1.24, 1.28, 1.26]
    })

    data['ema_fast'] = ta.trend.ema_indicator(data['close'], window=5)
    data['ema_slow'] = ta.trend.ema_indicator(data['close'], window=10)
    data['rsi'] = ta.momentum.rsi(data['close'], window=14)

    if data['ema_fast'].iloc[-1] > data['ema_slow'].iloc[-1] and data['rsi'].iloc[-1] < 70:
        direction = "CALL"
    elif data['ema_fast'].iloc[-1] < data['ema_slow'].iloc[-1] and data['rsi'].iloc[-1] > 30:
        direction = "PUT"
    else:
        direction = "NO_TRADE"

    accuracy = round(75 + (5 * (hash(pair) % 5)), 1)
    payout = round(80 + (hash(pair) % 10), 1)

    return direction, accuracy, payout


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📈 Get a Test Signal", callback_data="get_signal")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to Quotex Signal Bot!", reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "get_signal":
        keyboard = [[InlineKeyboardButton(pair, callback_data=f"pair|{pair}")] for pair in PAIRS]
        await query.edit_message_text("Select Currency Pair:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("pair|"):
        pair = query.data.split("|")[1]
        user_data[query.from_user.id] = {"pair": pair}
        keyboard = [[InlineKeyboardButton(exp, callback_data=f"expiry|{exp}")] for exp in EXPIRY_OPTIONS]
        await query.edit_message_text(f"✅ Selected Pair: {pair}\nNow select expiry:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("expiry|"):
        expiry = query.data.split("|")[1]
        user_data[query.from_user.id]["expiry"] = expiry
        keyboard = [[InlineKeyboardButton(t, callback_data=f"type|{t}")] for t in TRADE_TYPE]
        await query.edit_message_text(f"✅ Expiry: {expiry}\nSelect trade type:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("type|"):
        t_type = query.data.split("|")[1]
        user_data[query.from_user.id]["type"] = t_type
        keyboard = [[InlineKeyboardButton(b, callback_data=f"broker|{b}")] for b in BROKERS]
        await query.edit_message_text(f"✅ Trade Type: {t_type}\nSelect Broker:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("broker|"):
        broker = query.data.split("|")[1]
        info = user_data[query.from_user.id]
        info["broker"] = broker

        direction, accuracy, payout = generate_signal(info["pair"])
        now = datetime.datetime.now(TIMEZONE).strftime("%H:%M:%S")

        msg = (f"🔹 {info['pair']} ({info['type']})\n"
               f"🔥 Expiry: {info['expiry']}\n"
               f"🏦 Broker: {info['broker']}\n"
               f"🕘 {now}\n"
               f"📢 Signal: {direction}\n\n"
               f"📈 Accuracy: {accuracy}%\n💰 Payout: {payout}%")

        await query.edit_message_text(msg)


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
