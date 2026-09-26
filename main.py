
import os
import threading
import time
import json
import urllib.request
import math
import concurrent.futures
from datetime import datetime, timezone, timedelta
from flask import Flask

# 1. Keep-Alive Web Server
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "QUOTEX 15M AGGRESSIVE ENGINE", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False, threaded=True)

threading.Thread(target=run_flask, daemon=True).start()

def render_anti_freeze():
    time.sleep(10)
    external_url = os.environ.get("RENDER_EXTERNAL_URL", f"http://127.0.0.1:{os.environ.get('PORT', 10000)}")
    url = f"{external_url}/health"
    while True:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'KeepAlivePing'})
            with urllib.request.urlopen(req, timeout=5) as r:
                pass
        except Exception:
            pass
        time.sleep(240)

threading.Thread(target=render_anti_freeze, daemon=True).start()

# 2. Telegram Credentials
BOT_TOKEN = "8807036352:AAGwVcFaIxvVU7xUIWFDHlHUwKM3vGdLbuw"
CHAT_ID = "5883050661"

try:
    urllib.request.urlopen(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=4)
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

# SAARE 18 ASSETS (Forex Majors, Crosses, Gold, aur Crypto)
PAIRS = [
    # Majors
    {"name": "EUR/USD", "deriv": "frxEURUSD", "yahoo": "EURUSD=X", "digits": 5},
    {"name": "GBP/USD", "deriv": "frxGBPUSD", "yahoo": "GBPUSD=X", "digits": 5},
    {"name": "USD/JPY", "deriv": "frxUSDJPY", "yahoo": "JPY=X", "digits": 3},
    {"name": "AUD/USD", "deriv": "frxAUDUSD", "yahoo": "AUDUSD=X", "digits": 5},
    {"name": "USD/CAD", "deriv": "frxUSDCAD", "yahoo": "CAD=X", "digits": 5},
    {"name": "USD/CHF", "deriv": "frxUSDCHF", "yahoo": "CHF=X", "digits": 5},
    {"name": "NZD/USD", "deriv": "frxNZDUSD", "yahoo": "NZDUSD=X", "digits": 5},
    
    # Crosses
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

class SafeEngineState:
    def __init__(self):
        self.level = 1
        self.trade_step = 1
        self.consecutive_losses = 0
        self.active_trade = None
        self.state_lock = threading.Lock()

state = SafeEngineState()

def get_ist():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

def send_tg(text):
    def _worker():
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode('utf-8')
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=6):
                pass
        except Exception:
            pass
    threading.Thread(target=_worker, daemon=True).start()

def fetch_live_price(pair_info):
    try:
        url = f"https://api.deriv.com/api/v1/candles?symbol={pair_info['deriv']}&granularity=900&count=2"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2.5) as res:
            data = json.loads(res.read().decode('utf-8'))
            candles = data.get('candles', [])
            if candles:
                return float(candles[-1]['close'])
    except Exception:
        pass
    return None

def fetch_15m_candles(pair_info):
    try:
        url = f"https://api.deriv.com/api/v1/candles?symbol={pair_info['deriv']}&granularity=900&count=25"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            data = json.loads(res.read().decode('utf-8'))
            return data.get('candles', [])
    except Exception:
        return []

def calculate_ema(prices, period):
    multiplier = 2 / (period + 1)
    ema = [sum(prices[:period]) / period]
    for price in prices[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema

# AGGRESSIVE QUOTEX LOGIC (GUARANTEES A SIGNAL)
def evaluate_quotex_confluence(candles):
    if not candles or len(candles) < 20:
        return "NO_TRADE", 0, "No Data"

    closes = [float(c['close']) for c in candles]
    opens = [float(c['open']) for c in candles]
    
    # RSI (14)
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains[-14:]) / 14.0
    avg_loss = sum(losses[-14:]) / 14.0
    rsi = 100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + (avg_gain / avg_loss)))

    # EMA 3 & EMA 9 for Aggressive Short Term Binary Trend
    ema3 = calculate_ema(closes, 3)[-1]
    ema9 = calculate_ema(closes, 9)[-1]
    
    last_close = closes[-1]
    last_open = opens[-1]

    prob = 75
    
    # Aggressive Trend Scoring
    if ema3 > ema9:
        if rsi > 50: prob += 10
        if last_close > last_open: prob += 5
        return "CALL (UP) 🟢", prob, "Aggressive Bullish Momentum"
    else:
        if rsi < 50: prob += 10
        if last_close < last_open: prob += 5
        return "PUT (DOWN) 🔴", prob, "Aggressive Bearish Momentum"

def telegram_listener():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=5"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get("ok"):
                    for item in data.get("result", []):
                        offset = item["update_id"] + 1
                        msg = item.get("message", {})
                        text = msg.get("text", "").strip()
                        c_id = str(msg.get("chat", {}).get("id", ""))
                        if c_id == CHAT_ID and ("/status" in text or "/start" in text or "status" in text.lower()):
                            with state.state_lock:
                                max_t = 4 if state.level <= 20 else 6
                                reply = (
                                    f"🟢 <b>QUOTEX AGGRESSIVE ENGINE ONLINE</b>\n\n"
                                    f"🕒 <b>Clock:</b> <code>{get_ist().strftime('%H:%M:%S IST')}</code>\n"
                                    f"📊 <b>Markets:</b> All 18 (Forex, Gold, Crypto)\n"
                                    f"📉 <b>Strategy:</b> Always-On Momentum Predictor\n"
                                    f"📈 <b>Ladder:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                                    f"💵 <b>Current Stake:</b> ${LEVELS_STAKE[state.level]}"
                                )
                            send_tg(reply)
        except Exception:
            time.sleep(2)
        time.sleep(1)

threading.Thread(target=telegram_listener, daemon=True).start()

def analyze_pair(p):
    candles = fetch_15m_candles(p)
    if candles:
        sig, prob, reason = evaluate_quotex_confluence(candles)
        if sig != "NO_TRADE":
            return {
                "pair": p,
                "action": sig,
                "prob": prob,
                "reason": reason,
                "price": float(candles[-1]['close'])
            }
    return None

def market_engine():
    time.sleep(2)
    send_tg(
        "⚡ <b>AGGRESSIVE FREQUENCY ENGINE ACTIVATED</b>\n\n"
        "• <b>Testing Mode:</b> Bot will now force the BEST available setup every 15 minutes.\n"
        "• <b>Zero Skips:</b> You will get a signal every cycle from 18 Assets."
    )

    while True:
        try:
            now = time.time()
            wait_sec = 900 - (now % 900)
            if wait_sec < 5:
                wait_sec += 900

            time.sleep(wait_sec)

            # 1. Result Check
            if state.active_trade:
                t = state.active_trade
                exit_price = fetch_live_price(t['pair_info'])
                entry_price = t['entry_price']
                action = t['action']
                d = t['pair_info']['digits']

                with state.state_lock:
                    max_t = 4 if state.level <= 20 else 6
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
                            f"✅ <b>15M CANDLE RESULT: WIN</b> 🟢\n\n"
                            f"📊 <b>Asset:</b> {t['name']}\n"
                            f"📍 <b>Entry:</b> {entry_price:.{d}f} ➔ <b>Exit:</b> {exit_price:.{d}f}\n"
                            f"📈 <b>Progress:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                            f"💵 <b>Next Stake:</b> ${LEVELS_STAKE[state.level]}"
                        )
                    else:
                        state.consecutive_losses += 1
                        state.trade_step = 1
                        exit_disp = f"{exit_price:.{d}f}" if exit_price else "API Error"
                        res_msg = (
                            f"⚠️ <b>15M CANDLE RESULT: LOSS</b> 🔴\n\n"
                            f"📊 <b>Asset:</b> {t['name']}\n"
                            f"📍 <b>Entry:</b> {entry_price:.{d}f} ➔ <b>Exit:</b> {exit_disp}\n"
                            f"🛡️ <b>Step Reset:</b> Level {state.level} (Trade 1/{max_t})\n"
                            f"💵 <b>Stake:</b> ${LEVELS_STAKE[state.level]}"
                        )

                send_tg(res_msg)
                state.active_trade = None

                if state.consecutive_losses >= 2:
                    send_tg("🚨 <b>2 CONSECUTIVE LOSSES: PAUSING FOR 60 MIN</b>")
                    time.sleep(3600)
                    with state.state_lock:
                        state.consecutive_losses = 0
                        state.level = 1
                        state.trade_step = 1
                    send_tg("🟢 <b>60-MIN SESSION UNLOCKED: SCANNING RESUMED</b>")
                    continue

            # 2. Aggressive Scan (Checking all 18 pairs with 20 parallel workers)
            chosen_setup = None
            best_prob = 0
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                results = list(executor.map(analyze_pair, PAIRS))
                
            for res in results:
                if res and res["prob"] > best_prob:
                    best_prob = res["prob"]
                    chosen_setup = res

            if not chosen_setup:
                continue

            pair_info = chosen_setup['pair']
            cur_price = chosen_setup['price']
            action = chosen_setup['action']
            prob = chosen_setup['prob']
            reason = chosen_setup['reason']
            d = pair_info['digits']

            with state.state_lock:
                max_t = 4 if state.level <= 20 else 6
                current_stake = LEVELS_STAKE[state.level]

            now_ist = get_ist()
            ent_str = now_ist.strftime("%H:%M:00 IST")
            ext_str = (now_ist + timedelta(minutes=15)).strftime("%H:%M:00 IST")

            alert = (
                f"🎯 <b>QUOTEX AGGRESSIVE SIGNAL DETECTED</b>\n\n"
                f"📊 <b>Asset:</b> <code>{pair_info['name']}</code>\n"
                f"🚀 <b>Action:</b> <b>{action}</b>\n"
                f"🔥 <b>Win Probability:</b> <b>{prob}%</b>\n"
                f"⏳ <b>Expiry:</b> EXACTLY 15 MINUTES (1 Candle)\n\n"
                f"⏱️ <b>Entry Clock:</b> <code>{ent_str}</code> (Exact Open)\n"
                f"🏁 <b>Exit Clock:</b> <code>{ext_str}</code>\n\n"
                f"📈 <b>Ladder:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                f"💵 <b>Stake Amount:</b> ${current_stake}\n"
                f"📍 <b>Current Price:</b> <code>{cur_price:.{d}f}</code>\n"
                f"🔬 <b>Logic:</b> <i>{reason}</i>"
            )
            send_tg(alert)

            state.active_trade = {
                "pair_info": pair_info,
                "name": pair_info['name'],
                "action": action,
                "entry_price": cur_price
            }

        except Exception as err:
            print(f">> [Runtime Error]: {err}")
            time.sleep(3)

threading.Thread(target=market_engine, daemon=True).start()

if __name__ == "__main__":
    while True:
        time.sleep(60)
