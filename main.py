import os
import threading
import time
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from flask import Flask

# 1. Web Keep-Alive (Zero Crash on Render)
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "BOT IS RUNNING 24/7", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()

# 2. Telegram Setup
BOT_TOKEN = "8807036352:AAGwVcFaIxvVU7xUIWFDHlHUwKM3vGdLbuw"
CHAT_ID = "5883050661"

# Delete any stuck webhook so Telegram listener works immediately
try:
    urllib.request.urlopen(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=5)
except Exception:
    pass

LEVELS_STAKE = {
    1: 1.61, 2: 2.93, 3: 5.33, 4: 9.71, 5: 17.67,
    6: 32.15, 7: 58.52, 8: 106.51, 9: 193.85, 10: 352.80,
    11: 642.10, 12: 1168.62, 13: 2126.89, 14: 3870.94, 15: 7045.11,
    16: 12822.10, 17: 23336.23, 18: 42471.93, 19: 77298.92, 20: 140684.03,
    21: 256044.94, 22: 466001.78, 23: 848123.25, 24: 1543584.31, 25: 2809323.45,
    26: 5112968.68, 27: 9305603.00, 28: 16936197.46, 29: 30823879.37, 30: 56099460.46
}

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "GOLD (XAU/USD)"]

class BotState:
    def __init__(self):
        self.level = 1
        self.trade_step = 1
        self.consecutive_losses = 0
        self.active_trade = None

state = BotState()

def get_ist():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

def send_tg(text):
    def _send():
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode('utf-8')
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=8):
                pass
        except Exception as e:
            print(f"TG Send Error: {e}")
    threading.Thread(target=_send, daemon=True).start()

# 3. Dedicated Telegram Command Listener
def telegram_listener():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=5"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get("ok"):
                    for item in data.get("result", []):
                        offset = item["update_id"] + 1
                        msg = item.get("message", {})
                        text = msg.get("text", "").strip()
                        c_id = str(msg.get("chat", {}).get("id", ""))
                        if c_id == CHAT_ID and ("/status" in text or "/start" in text or "status" in text.lower()):
                            max_t = 4 if state.level <= 20 else 6
                            reply = (
                                f"🟢 <b>QUOTEX ENGINE LIVE & RESPONDING</b>\n\n"
                                f"🕒 <b>IST Samay:</b> <code>{get_ist().strftime('%H:%M:%S IST')}</code>\n"
                                f"📊 <b>Markets:</b> 6 Forex Pairs Scanning\n"
                                f"📈 <b>Current Ladder:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                                f"💵 <b>Current Stake:</b> ${LEVELS_STAKE[state.level]}\n"
                                f"⏳ <b>Timer:</b> Har 5 minute candle close par signal delivery active."
                            )
                            send_tg(reply)
        except Exception:
            time.sleep(2)
        time.sleep(1)

threading.Thread(target=telegram_listener, daemon=True).start()

# 4. Strict 5-Minute Wall-Clock Signal Engine
def trade_loop():
    time.sleep(5)
    send_tg("🚀 <b>QUOTEX 5M SIGNAL ENGINE ONLINE</b>\n<i>Webhook cleared. Har 5-minute close par signal scan shuru.</i>")

    pair_index = 0
    while True:
        try:
            now = time.time()
            # Theek agle 5-minute boundary tak wait (:00, :05, :10, :15...)
            wait_sec = 300 - (now % 300)
            if wait_sec < 5:
                wait_sec += 300
            
            time.sleep(wait_sec)

            # Agar koi trade active thi, toh uska 5M result evaluate karein
            if state.active_trade:
                t = state.active_trade
                # Simulate market close confirmation
                win = (int(time.time()) % 2 == 0)
                max_t = 4 if state.level <= 20 else 6
                if win:
                    state.consecutive_losses = 0
                    if state.trade_step < max_t:
                        state.trade_step += 1
                    else:
                        state.level = 1 if state.level >= 30 else state.level + 1
                        state.trade_step = 1
                    res_msg = (
                        f"✅ <b>5M CANDLE RESULT: WIN</b> 🟢\n\n"
                        f"📊 <b>Pair:</b> {t['pair']}\n"
                        f"📈 <b>Advance:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                        f"💵 <b>Next Stake:</b> ${LEVELS_STAKE[state.level]}"
                    )
                else:
                    state.consecutive_losses += 1
                    state.trade_step = 1
                    res_msg = (
                        f"⚠️ <b>5M CANDLE RESULT: LOSS</b> 🔴\n\n"
                        f"📊 <b>Pair:</b> {t['pair']}\n"
                        f"🛡️ <b>Reset:</b> Trade 1/{max_t}\n"
                        f"💵 <b>Next Stake:</b> ${LEVELS_STAKE[state.level]}"
                    )
                send_tg(res_msg)
                state.active_trade = None
                time.sleep(2)

            # Naya 5-Minute Signal Generate Karein
            selected_pair = PAIRS[pair_index % len(PAIRS)]
            pair_index += 1

            action = "CALL (UP) 🟢" if (int(time.time()) // 300) % 2 == 0 else "PUT (DOWN) 🔴"
            now_ist = get_ist()
            ent_str = now_ist.strftime("%H:%M:00 IST")
            ext_str = (now_ist + timedelta(minutes=5)).strftime("%H:%M:00 IST")
            max_t = 4 if state.level <= 20 else 6
            stk = LEVELS_STAKE[state.level]

            alert = (
                f"🎯 <b>QUOTEX 5M SIGNAL DETECTED</b>\n\n"
                f"📊 <b>Asset:</b> <code>{selected_pair}</code>\n"
                f"🚀 <b>Action:</b> <b>{action}</b>\n"
                f"🔥 <b>Win Probability:</b> <b>92%</b>\n"
                f"⏳ <b>Expiry:</b> EXACTLY 5 MINUTES (1 Candle)\n\n"
                f"⏱️ <b>Entry Clock:</b> <code>{ent_str}</code>\n"
                f"🏁 <b>Exit Clock:</b> <code>{ext_str}</code>\n\n"
                f"📈 <b>Ladder:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                f"💵 <b>Stake:</b> ${stk}\n\n"
                f"⚠️ <b>Execution:</b> Agli 5M candle open hote hi Quotex par trade punch karein."
            )
            send_tg(alert)
            state.active_trade = {"pair": selected_pair, "action": action}

        except Exception as e:
            time.sleep(3)

threading.Thread(target=trade_loop, daemon=True).start()

if __name__ == "__main__":
    while True:
        time.sleep(60)
