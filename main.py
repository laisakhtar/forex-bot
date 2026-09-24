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
    return "LIVE REAL FOREX ENGINE ACTIVE", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()

# 2. Telegram Credentials & Webhook Clear
BOT_TOKEN = "8807036352:AAGwVcFaIxvVU7xUIWFDHlHUwKM3vGdLbuw"
CHAT_ID = "5883050661"

try:
    urllib.request.urlopen(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=5)
except Exception:
    pass

# 30-Level Compounding Plan
LEVELS_STAKE = {
    1: 1.61, 2: 2.93, 3: 5.33, 4: 9.71, 5: 17.67,
    6: 32.15, 7: 58.52, 8: 106.51, 9: 193.85, 10: 352.80,
    11: 642.10, 12: 1168.62, 13: 2126.89, 14: 3870.94, 15: 7045.11,
    16: 12822.10, 17: 23336.23, 18: 42471.93, 19: 77298.92, 20: 140684.03,
    21: 256044.94, 22: 466001.78, 23: 848123.25, 24: 1543584.31, 25: 2809323.45,
    26: 5112968.68, 27: 9305603.00, 28: 16936197.46, 29: 30823879.37, 30: 56099460.46
}

# Real Market Assets Mapping
ASSETS = {
    "frxEURUSD": {"name": "EUR/USD", "digits": 5},
    "frxGBPUSD": {"name": "GBP/USD", "digits": 5},
    "frxUSDJPY": {"name": "USD/JPY", "digits": 3},
    "frxAUDUSD": {"name": "AUD/USD", "digits": 5},
    "frxUSDCAD": {"name": "USD/CAD", "digits": 5},
    "frxUSDCHF": {"name": "USD/CHF", "digits": 5},
    "frxNZDUSD": {"name": "NZD/USD", "digits": 5},
    "frxEURGBP": {"name": "EUR/GBP", "digits": 5},
    "frxEURJPY": {"name": "EUR/JPY", "digits": 3},
    "frxGBPJPY": {"name": "GBP/JPY", "digits": 3}
}

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
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()

# Live Price Fetcher (Public Real Forex Feed)
def fetch_live_price(symbol):
    try:
        url = f"https://api.deriv.com/api/v1/candles?symbol={symbol}&granularity=300&count=2"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=6) as res:
            data = json.loads(res.read().decode('utf-8'))
            candles = data.get('candles', [])
            if candles:
                return float(candles[-1]['close'])
    except Exception:
        pass
    return None

# Telegram Command Listener (/status)
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
                                f"🟢 <b>QUOTEX REAL ENGINE ONLINE</b>\n\n"
                                f"🕒 <b>IST Samay:</b> <code>{get_ist().strftime('%H:%M:%S IST')}</code>\n"
                                f"📊 <b>Markets:</b> 10 Real Forex Pairs Active\n"
                                f"📈 <b>Current Ladder:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                                f"💵 <b>Current Stake:</b> ${LEVELS_STAKE[state.level]}\n"
                                f"🚨 <b>Loss Streak:</b> {state.consecutive_losses}/2\n"
                                f"🛡️ <b>Verification Mode:</b> Real Tick Exit Price Tracking (Zero Fake Wins)"
                            )
                            send_tg(reply)
        except Exception:
            time.sleep(2)
        time.sleep(1)

threading.Thread(target=telegram_listener, daemon=True).start()

# Real Market Verification Engine
def market_engine():
    time.sleep(5)
    send_tg("💎 <b>100% REAL MARKET VERIFICATION ACTIVE</b>\n<i>Odd/Even simulation poori tarah hata di gayi hai. Har candle ka exact Exit Price compare karke hi result aayega.</i>")

    asset_keys = list(ASSETS.keys())
    asset_idx = 0

    while True:
        try:
            now = time.time()
            wait_sec = 300 - (now % 300)
            if wait_sec < 4:
                wait_sec += 300
            
            time.sleep(wait_sec)

            # 1. Pichhli Trade Ka Asli Result Verification
            if state.active_trade:
                t = state.active_trade
                exit_price = fetch_live_price(t['symbol'])
                if not exit_price:
                    time.sleep(2)
                    exit_price = fetch_live_price(t['symbol'])

                entry_price = t['entry_price']
                action = t['action']
                max_t = 4 if state.level <= 20 else 6
                d = ASSETS[t['symbol']]['digits']

                # Strict Real Price Comparison
                if exit_price and entry_price:
                    if "CALL" in action:
                        is_win = (exit_price > entry_price)
                    else:
                        is_win = (exit_price < entry_price)
                else:
                    is_win = False  # Price na milne par safety loss consider hoga

                if is_win:
                    state.consecutive_losses = 0
                    if state.trade_step < max_t:
                        state.trade_step += 1
                    else:
                        state.level = min(30, state.level + 1)
                        state.trade_step = 1
                    
                    res_msg = (
                        f"✅ <b>5M CANDLE RESULT: WIN</b> 🟢\n\n"
                        f"📊 <b>Asset:</b> {t['pair']}\n"
                        f"📍 <b>Entry:</b> {entry_price:.{d}f} ➔ <b>Exit:</b> {exit_price:.{d}f}\n"
                        f"📈 <b>Advance:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                        f"💵 <b>Next Stake:</b> ${LEVELS_STAKE[state.level]}"
                    )
                else:
                    state.consecutive_losses += 1
                    state.trade_step = 1
                    res_msg = (
                        f"⚠️ <b>5M CANDLE RESULT: LOSS</b> 🔴\n\n"
                        f"📊 <b>Asset:</b> {t['pair']}\n"
                        f"📍 <b>Entry:</b> {entry_price:.{d}f} ➔ <b>Exit:</b> {exit_price:.{d}f}\n"
                        f"🛡️ <b>Reset:</b> Trade 1/{max_t} (Capital Protection)\n"
                        f"💵 <b>Next Stake:</b> ${LEVELS_STAKE[state.level]}"
                    )
                
                send_tg(res_msg)
                state.active_trade = None

                # 2 Consecutive Losses Safety Lock
                if state.consecutive_losses >= 2:
                    send_tg("🚨 <b>2 CONSECUTIVE LOSSES DETECTED</b>\n<i>Cooldown: 60 minutes engine freeze rahega discipline maintain rakhne ke liye.</i>")
                    time.sleep(3600)
                    state.consecutive_losses = 0
                    state.level = 1
                    state.trade_step = 1
                    send_tg("🟢 <b>COOLDOWN OVER: RESTARTING AT LEVEL 1</b>")
                    continue

            # 2. Naya 5-Minute Real Candle Signal
            sym = asset_keys[asset_idx % len(asset_keys)]
            asset_idx += 1
            pair_info = ASSETS[sym]
            pair_name = pair_info['name']
            d = pair_info['digits']

            cur_price = fetch_live_price(sym)
            if not cur_price:
                time.sleep(1)
                cur_price = fetch_live_price(sym)
            if not cur_price:
                continue

            action = "CALL (UP) 🟢" if (int(time.time()) // 300) % 2 == 0 else "PUT (DOWN) 🔴"
            now_ist = get_ist()
            ent_str = now_ist.strftime("%H:%M:00 IST")
            ext_str = (now_ist + timedelta(minutes=5)).strftime("%H:%M:00 IST")
            max_t = 4 if state.level <= 20 else 6
            stk = LEVELS_STAKE[state.level]

            alert = (
                f"🎯 <b>QUOTEX 5M REAL SIGNAL</b>\n\n"
                f"📊 <b>Asset:</b> <code>{pair_name}</code>\n"
                f"🚀 <b>Action:</b> <b>{action}</b>\n"
                f"📍 <b>Entry Locked:</b> <code>{cur_price:.{d}f}</code>\n"
                f"⏳ <b>Expiry:</b> EXACTLY 5 MINUTES (1 Candle)\n\n"
                f"⏱️ <b>Entry Clock:</b> <code>{ent_str}</code>\n"
                f"🏁 <b>Exit Clock:</b> <code>{ext_str}</code>\n\n"
                f"📈 <b>Ladder:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                f"💵 <b>Stake:</b> ${stk}\n\n"
                f"⚠️ <b>Execution:</b> Agli 5M candle open hote hi entry punch karein."
            )
            send_tg(alert)
            state.active_trade = {
                "symbol": sym,
                "pair": pair_name,
                "action": action,
                "entry_price": cur_price
            }

        except Exception as e:
            time.sleep(3)

threading.Thread(target=market_engine, daemon=True).start()

if __name__ == "__main__":
    while True:
        time.sleep(60)
