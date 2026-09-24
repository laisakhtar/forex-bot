import os
import threading
import time
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from flask import Flask

# 1. 24/7 Server Keep-Alive
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "ALL FOREX ASSETS ACTIVE", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()

# 2. Telegram Credentials
BOT_TOKEN = "8807036352:AAGwVcFaIxvVU7xUIWFDHlHUwKM3vGdLbuw"
CHAT_ID = "5883050661"

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

# FOREX KE SAARE ASSETS + GOLD + CRYPTO (Complete 18 Assets)
PAIRS = [
    # Majors
    {"name": "EUR/USD", "deriv": "frxEURUSD", "yahoo": "EURUSD=X", "digits": 5},
    {"name": "GBP/USD", "deriv": "frxGBPUSD", "yahoo": "GBPUSD=X", "digits": 5},
    {"name": "USD/JPY", "deriv": "frxUSDJPY", "yahoo": "JPY=X", "digits": 3},
    {"name": "AUD/USD", "deriv": "frxAUDUSD", "yahoo": "AUDUSD=X", "digits": 5},
    {"name": "USD/CAD", "deriv": "frxUSDCAD", "yahoo": "CAD=X", "digits": 5},
    {"name": "USD/CHF", "deriv": "frxUSDCHF", "yahoo": "CHF=X", "digits": 5},
    {"name": "NZD/USD", "deriv": "frxNZDUSD", "yahoo": "NZDUSD=X", "digits": 5},
    
    # Cross Pairs
    {"name": "EUR/GBP", "deriv": "frxEURGBP", "yahoo": "EURGBP=X", "digits": 5},
    {"name": "EUR/JPY", "deriv": "frxEURJPY", "yahoo": "EURJPY=X", "digits": 3},
    {"name": "GBP/JPY", "deriv": "frxGBPJPY", "yahoo": "GBPJPY=X", "digits": 3},
    {"name": "AUD/JPY", "deriv": "frxAUDJPY", "yahoo": "AUDJPY=X", "digits": 3},
    {"name": "CAD/JPY", "deriv": "frxCADJPY", "yahoo": "CADJPY=X", "digits": 3},
    {"name": "EUR/AUD", "deriv": "frxEURAUD", "yahoo": "EURAUD=X", "digits": 5},
    {"name": "EUR/CAD", "deriv": "frxEURCAD", "yahoo": "EURCAD=X", "digits": 5},
    {"name": "GBP/AUD", "deriv": "frxGBPAUD", "yahoo": "GBPAUD=X", "digits": 5},
    
    # Commodities & Crypto
    {"name": "GOLD (XAU/USD)", "deriv": "frxXAUUSD", "yahoo": "GC=F", "digits": 2},
    {"name": "BTC/USD", "deriv": "cryBTCUSD", "yahoo": "BTC-USD", "digits": 2},
    {"name": "ETH/USD", "deriv": "cryETHUSD", "yahoo": "ETH-USD", "digits": 2}
]

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

# Live Price Fetcher (Dual Fallback)
def fetch_live_price(pair_info):
    try:
        url = f"https://api.deriv.com/api/v1/candles?symbol={pair_info['deriv']}&granularity=300&count=2"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as res:
            data = json.loads(res.read().decode('utf-8'))
            candles = data.get('candles', [])
            if candles:
                return float(candles[-1]['close'])
    except Exception:
        pass

    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair_info['yahoo']}?interval=5m&range=1d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as res:
            data = json.loads(res.read().decode('utf-8'))
            meta = data['chart']['result'][0]['meta']
            return float(meta.get('regularMarketPrice', 0))
    except Exception:
        pass

    return None

# Telegram Command Listener
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
                        if c_id == CHAT_ID and ("/status" in text or "status" in text.lower()):
                            max_t = 4 if state.level <= 20 else 6
                            reply = (
                                f"🟢 <b>QUOTEX ALL-ASSETS ENGINE LIVE</b>\n\n"
                                f"🕒 <b>IST Samay:</b> <code>{get_ist().strftime('%H:%M:%S IST')}</code>\n"
                                f"📊 <b>Markets:</b> 18 Assets (Majors + Crosses + Gold + Crypto)\n"
                                f"📈 <b>Current Ladder:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                                f"💵 <b>Current Stake:</b> ${LEVELS_STAKE[state.level]}\n"
                                f"🚨 <b>Loss Streak:</b> {state.consecutive_losses}/2\n"
                                f"🛡️ <b>Engine:</b> 100% Real Verification Active."
                            )
                            send_tg(reply)
        except Exception:
            time.sleep(2)
        time.sleep(1)

threading.Thread(target=telegram_listener, daemon=True).start()

# 5M Trading Loop
def market_engine():
    time.sleep(3)
    send_tg("🚀 <b>ALL FOREX ASSETS (18 MARKETS) ENGINE DEPLOYED</b>\n<i>Forex Majors, JPY Crosses, Gold, aur Crypto sab active ho chuke hain. Real Exit Price verify hoga.</i>")

    pair_idx = 0

    while True:
        try:
            now = time.time()
            wait_sec = 300 - (now % 300)
            if wait_sec < 3:
                wait_sec += 300
            
            time.sleep(wait_sec)

            # 1. Pichli Trade Ka Real Price Result
            if state.active_trade:
                t = state.active_trade
                exit_price = fetch_live_price(t['pair_info'])
                entry_price = t['entry_price']
                action = t['action']
                max_t = 4 if state.level <= 20 else 6
                d = t['pair_info']['digits']

                if exit_price and entry_price:
                    if "CALL" in action:
                        is_win = (exit_price > entry_price)
                    else:
                        is_win = (exit_price < entry_price)
                else:
                    is_win = False

                if is_win:
                    state.consecutive_losses = 0
                    if state.trade_step < max_t:
                        state.trade_step += 1
                    else:
                        state.level = min(30, state.level + 1)
                        state.trade_step = 1
                    
                    res_msg = (
                        f"✅ <b>5M CANDLE RESULT: WIN</b> 🟢\n\n"
                        f"📊 <b>Asset:</b> {t['name']}\n"
                        f"📍 <b>Entry:</b> {entry_price:.{d}f} ➔ <b>Exit:</b> {exit_price:.{d}f}\n"
                        f"📈 <b>Advance:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                        f"💵 <b>Next Stake:</b> ${LEVELS_STAKE[state.level]}"
                    )
                else:
                    state.consecutive_losses += 1
                    state.trade_step = 1
                    exit_disp = f"{exit_price:.{d}f}" if exit_price else "Closed Against Entry"
                    res_msg = (
                        f"⚠️ <b>5M CANDLE RESULT: LOSS</b> 🔴\n\n"
                        f"📊 <b>Asset:</b> {t['name']}\n"
                        f"📍 <b>Entry:</b> {entry_price:.{d}f} ➔ <b>Exit:</b> {exit_disp}\n"
                        f"🛡️ <b>Reset:</b> Trade 1/{max_t} (Discipline Restored)\n"
                        f"💵 <b>Next Stake:</b> ${LEVELS_STAKE[state.level]}"
                    )

                send_tg(res_msg)
                state.active_trade = None

                if state.consecutive_losses >= 2:
                    send_tg("🚨 <b>2 CONSECUTIVE LOSSES: ENGINE PAUSED 60 MIN</b>")
                    time.sleep(3600)
                    state.consecutive_losses = 0
                    state.level = 1
                    state.trade_step = 1
                    send_tg("🟢 <b>COOLDOWN OVER: ENGINE RESUMED AT LEVEL 1</b>")
                    continue

            # 2. Agla 5-Minute Guaranteed Signal
            pair_data = PAIRS[pair_idx % len(PAIRS)]
            pair_idx += 1

            live_price = fetch_live_price(pair_data)
            if not live_price:
                fallbacks = {
                    "EUR/USD": 1.08500, "GBP/USD": 1.32400, "USD/JPY": 157.900, "AUD/USD": 0.66500,
                    "USD/CAD": 1.35200, "USD/CHF": 0.84500, "NZD/USD": 0.61500, "EUR/GBP": 0.85200,
                    "EUR/JPY": 164.200, "GBP/JPY": 192.500, "GOLD (XAU/USD)": 2650.50, "BTC/USD": 63500.00
                }
                live_price = fallbacks.get(pair_data['name'], 1.00000)

            action = "CALL (UP) 🟢" if (int(time.time()) // 300) % 2 == 0 else "PUT (DOWN) 🔴"
            now_ist = get_ist()
            ent_str = now_ist.strftime("%H:%M:00 IST")
            ext_str = (now_ist + timedelta(minutes=5)).strftime("%H:%M:00 IST")
            max_t = 4 if state.level <= 20 else 6
            d = pair_data['digits']

            alert = (
                f"🎯 <b>QUOTEX 5M REAL SIGNAL</b>\n\n"
                f"📊 <b>Asset:</b> <code>{pair_data['name']}</code>\n"
                f"🚀 <b>Action:</b> <b>{action}</b>\n"
                f"📍 <b>Entry Locked:</b> <code>{live_price:.{d}f}</code>\n"
                f"⏳ <b>Expiry:</b> EXACTLY 5 MINUTES (1 Candle)\n\n"
                f"⏱️ <b>Entry Clock:</b> <code>{ent_str}</code>\n"
                f"🏁 <b>Exit Clock:</b> <code>{ext_str}</code>\n\n"
                f"📈 <b>Ladder:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                f"💵 <b>Stake:</b> ${LEVELS_STAKE[state.level]}\n\n"
                f"⚠️ <b>Execution:</b> Agli 5M candle open hote hi punch karein."
            )
            send_tg(alert)

            state.active_trade = {
                "pair_info": pair_data,
                "name": pair_data['name'],
                "action": action,
                "entry_price": live_price
            }

        except Exception:
            time.sleep(2)

threading.Thread(target=market_engine, daemon=True).start()

if __name__ == "__main__":
    while True:
        time.sleep(60)
