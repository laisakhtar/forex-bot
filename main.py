import os
import threading
import time
import json
import urllib.request
import concurrent.futures
from datetime import datetime, timezone, timedelta
from flask import Flask

# 1. Keep-Alive Web Server
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "QUOTEX 15M PRICE ACTION ENGINE LIVE", 200

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

PAIRS = [
    {"name": "EUR/USD", "deriv": "frxEURUSD", "yahoo": "EURUSD=X", "digits": 5},
    {"name": "GBP/USD", "deriv": "frxGBPUSD", "yahoo": "GBPUSD=X", "digits": 5},
    {"name": "USD/JPY", "deriv": "frxUSDJPY", "yahoo": "JPY=X", "digits": 3},
    {"name": "AUD/USD", "deriv": "frxAUDUSD", "yahoo": "AUDUSD=X", "digits": 5},
    {"name": "USD/CAD", "deriv": "frxUSDCAD", "yahoo": "CAD=X", "digits": 5},
    {"name": "USD/CHF", "deriv": "frxUSDCHF", "yahoo": "CHF=X", "digits": 5},
    {"name": "NZD/USD", "deriv": "frxNZDUSD", "yahoo": "NZDUSD=X", "digits": 5},
    {"name": "EUR/GBP", "deriv": "frxEURGBP", "yahoo": "EURGBP=X", "digits": 5},
    {"name": "EUR/JPY", "deriv": "frxEURJPY", "yahoo": "EURJPY=X", "digits": 3},
    {"name": "GBP/JPY", "deriv": "frxGBPJPY", "yahoo": "GBPJPY=X", "digits": 3},
    {"name": "AUD/JPY", "deriv": "frxAUDJPY", "yahoo": "AUDJPY=X", "digits": 3},
    {"name": "CAD/JPY", "deriv": "frxCADJPY", "yahoo": "CADJPY=X", "digits": 3},
    {"name": "EUR/AUD", "deriv": "frxEURAUD", "yahoo": "EURAUD=X", "digits": 5},
    {"name": "EUR/CAD", "deriv": "frxEURCAD", "yahoo": "EURCAD=X", "digits": 5},
    {"name": "GBP/AUD", "deriv": "frxGBPAUD", "yahoo": "GBPAUD=X", "digits": 5},
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
        for _ in range(3): 
            try:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "Connection": "close"})
                with urllib.request.urlopen(req, timeout=10):
                    break 
            except Exception:
                time.sleep(2)
    threading.Thread(target=_worker, daemon=True).start()

def fetch_live_price(pair_info):
    try:
        url = f"https://api.deriv.com/api/v1/candles?symbol={pair_info['deriv']}&granularity=900&count=2"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            data = json.loads(res.read().decode('utf-8'))
            candles = data.get('candles', [])
            if candles:
                return float(candles[-1]['close'])
    except Exception:
        pass
        
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair_info['yahoo']}?interval=1m&range=1d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            data = json.loads(res.read().decode('utf-8'))
            meta = data['chart']['result'][0]['meta']
            return float(meta.get('regularMarketPrice', 0))
    except Exception:
        pass
    return None

def fetch_15m_candles(pair_info):
    try:
        url = f"https://api.deriv.com/api/v1/candles?symbol={pair_info['deriv']}&granularity=900&count=50"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4.0) as res:
            data = json.loads(res.read().decode('utf-8'))
            if 'candles' in data and len(data['candles']) > 0:
                return data['candles']
    except Exception:
        pass

    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair_info['yahoo']}?interval=15m&range=5d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4.0) as res:
            data = json.loads(res.read().decode('utf-8'))
            res_data = data['chart']['result'][0]
            timestamps = res_data['timestamp']
            quote = res_data['indicators']['quote'][0]
            candles = []
            for i in range(len(timestamps)):
                if quote['close'][i] is not None:
                    candles.append({
                        'open': float(quote['open'][i]),
                        'high': float(quote['high'][i]),
                        'low': float(quote['low'][i]),
                        'close': float(quote['close'][i])
                    })
            if len(candles) > 0:
                return candles[-50:]
    except Exception:
        pass
    return []

def calculate_ema(prices, period):
    multiplier = 2 / (period + 1)
    ema = [sum(prices[:period]) / period]
    for price in prices[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema

# -------------------------------------------------------------
# PURE PRICE ACTION ALGORITHM (Candlestick Patterns + Trend)
# -------------------------------------------------------------
def predict_price_action(candles):
    if not candles or len(candles) < 40:
        return None, 0, "No Data"

    closes = [float(c['close']) for c in candles]
    opens = [float(c['open']) for c in candles]
    highs = [float(c['high']) for c in candles]
    lows = [float(c['low']) for c in candles]
    
    # Check Big Trend (EMA 20)
    ema20 = calculate_ema(closes, 20)[-1]
    
    # Last two candles
    c1_open, c1_close, c1_high, c1_low = opens[-1], closes[-1], highs[-1], lows[-1]
    c2_open, c2_close = opens[-2], closes[-2]

    # Basics
    c1_green = c1_close > c1_open
    c1_red = c1_close < c1_open
    c2_green = c2_close > c2_open
    c2_red = c2_close < c2_open
    
    c1_body = abs(c1_close - c1_open)
    c1_upper_wick = c1_high - max(c1_open, c1_close)
    c1_lower_wick = min(c1_open, c1_close) - c1_low
    
    call_score = 0
    put_score = 0
    reason_call = ""
    reason_put = ""

    # --- CALL (UP) CONDITIONS ---
    if c1_close > ema20: call_score += 20 # Align with Trend
    
    # Bullish Engulfing
    if c2_red and c1_green and c1_close > c2_open and c1_open <= c2_close:
        call_score += 40
        reason_call = "Bullish Engulfing Pattern"
    
    # Hammer / Pinbar Rejection
    if c1_lower_wick > (c1_body * 2) and c1_upper_wick < c1_body:
        call_score += 30
        reason_call = "Strong Hammer Rejection"

    # Momentum
    if c1_green and c1_close > max(highs[-4:-1]):
        call_score += 20
        reason_call = "New High Breakout"

    # --- PUT (DOWN) CONDITIONS ---
    if c1_close < ema20: put_score += 20 # Align with Trend
    
    # Bearish Engulfing
    if c2_green and c1_red and c1_close < c2_open and c1_open >= c2_close:
        put_score += 40
        reason_put = "Bearish Engulfing Pattern"
        
    # Shooting Star / Pinbar Rejection
    if c1_upper_wick > (c1_body * 2) and c1_lower_wick < c1_body:
        put_score += 30
        reason_put = "Shooting Star Rejection"

    # Momentum
    if c1_red and c1_close < min(lows[-4:-1]):
        put_score += 20
        reason_put = "New Low Breakdown"

    if call_score == 0 and put_score == 0:
        # Fallback to basic momentum so it never skips
        if c1_green: return "CALL (UP) 🟢", 60, "Basic Bullish Pressure"
        else: return "PUT (DOWN) 🔴", 60, "Basic Bearish Pressure"

    if call_score >= put_score:
        return "CALL (UP) 🟢", min(call_score + 15, 96), reason_call if reason_call else "Bullish Trend Support"
    else:
        return "PUT (DOWN) 🔴", min(put_score + 15, 96), reason_put if reason_put else "Bearish Trend Resistance"

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
                                    f"🟢 <b>PRICE ACTION ENGINE ONLINE</b>\n\n"
                                    f"🕒 <b>Clock:</b> <code>{get_ist().strftime('%H:%M:%S IST')}</code>\n"
                                    f"📉 <b>Strategy:</b> Candlestick Patterns + Trend\n"
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
        action, score, reason = predict_price_action(candles)
        if action:
            return {
                "pair": p,
                "action": action,
                "score": score,
                "reason": reason,
                "price": float(candles[-1]['close'])
            }
    return None

def market_engine():
    time.sleep(2)
    send_tg(
        "🚀 <b>PRICE ACTION ENGINE DEPLOYED</b>\n\n"
        "• <b>Real Trading Logic:</b> Indicators hata diye gaye hain. Ab bot asli traders ki tarah Candlestick patterns (Engulfing, Hammer) aur Trend par trade karega.\n"
        "• <b>Guaranteed Signal:</b> Har 15 minute par 18 pairs mein se top scored pair ko select karke signal dega."
    )

    while True:
        try:
            now = time.time()
            wait_sec = 900 - (now % 900)
            if wait_sec < 5:
                wait_sec += 900

            time.sleep(wait_sec)

            # 1. VERIFY PREVIOUS RESULT
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
                    send_tg("🚨 <b>2 CONSECUTIVE LOSSES: SYSTEM RESTING FOR 60 MINS</b>")
                    time.sleep(3600)
                    with state.state_lock:
                        state.consecutive_losses = 0
                        state.level = 1
                        state.trade_step = 1
                    send_tg("🟢 <b>60-MIN BREAK OVER: BOT RESTARTED</b>")
                    continue

            # 2. FETCH NEW BEST PAIR (GUARANTEED NO-SKIP)
            best_setup = None
            highest_score = -1
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(analyze_pair, PAIRS))
                
            for res in results:
                if res and res["score"] > highest_score:
                    highest_score = res["score"]
                    best_setup = res

            if not best_setup:
                now_ist = get_ist().strftime('%H:%M IST')
                send_tg(f"⚠️ <b>DATA FETCH ERROR ({now_ist})</b>\n<i>Servers are down. Waiting for next candle.</i>")
                continue

            pair_info = best_setup['pair']
            cur_price = best_setup['price']
            action = best_setup['action']
            score = best_setup['score']
            reason = best_setup['reason']
            d = pair_info['digits']

            with state.state_lock:
                max_t = 4 if state.level <= 20 else 6
                current_stake = LEVELS_STAKE[state.level]

            now_ist = get_ist()
            ent_str = now_ist.strftime("%H:%M:00 IST")
            ext_str = (now_ist + timedelta(minutes=15)).strftime("%H:%M:00 IST")

            alert = (
                f"🎯 <b>QUOTEX PRICE ACTION SIGNAL</b>\n\n"
                f"📊 <b>Asset:</b> <code>{pair_info['name']}</code>\n"
                f"🚀 <b>Action:</b> <b>{action}</b>\n"
                f"🔥 <b>Setup Strength:</b> <b>{score}%</b>\n"
                f"⏳ <b>Expiry:</b> EXACTLY 15 MINUTES\n\n"
                f"⏱️ <b>Entry Clock:</b> <code>{ent_str}</code>\n"
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
