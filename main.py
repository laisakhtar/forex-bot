import os
import threading
import time
import json
import urllib.request
import concurrent.futures
from datetime import datetime, timezone, timedelta
from flask import Flask

# ==========================================
# 1. SERVER KEEP-ALIVE (Render Anti-Sleep)
# ==========================================
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "QUOTEX PRO LADDER & MTFA ENGINE LIVE", 200

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

# ==========================================
# 2. TELEGRAM CONFIG & ASSETS
# ==========================================
BOT_TOKEN = "8807036352:AAGwVcFaIxvVU7xUIWFDHlHUwKM3vGdLbuw"
CHAT_ID = "5883050661"

try:
    urllib.request.urlopen(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=4)
except Exception:
    pass

# 30-LEVEL STAKE AMOUNTS
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
    {"name": "GOLD (XAU/USD)", "deriv": "frxXAUUSD", "yahoo": "GC=F", "digits": 2},
    {"name": "BTC/USD", "deriv": "cryBTCUSD", "yahoo": "BTC-USD", "digits": 2},
    {"name": "ETH/USD", "deriv": "cryETHUSD", "yahoo": "ETH-USD", "digits": 2}
]

# ==========================================
# 3. THE MASTER LADDER SYSTEM (Global Step)
# ==========================================
class MasterEngineState:
    def __init__(self):
        self.global_step = 1 # Starts at Trade 1 of Level 1
        self.active_trade = None
        self.state_lock = threading.Lock()

state = MasterEngineState()

def get_ladder_info(g_step):
    """
    Translates global_step into (Level, Trade_In_Level, Max_Trades_For_Level)
    Levels 1-20: 4 trades each (80 steps total)
    Levels 21-30: 6 trades each (60 steps total)
    Total steps = 140
    """
    if g_step <= 80:
        level = ((g_step - 1) // 4) + 1
        trade_num = ((g_step - 1) % 4) + 1
        return level, trade_num, 4
    else:
        rem_step = g_step - 80
        level = ((rem_step - 1) // 6) + 21
        trade_num = ((rem_step - 1) % 6) + 1
        if level > 30:
            level = 30
            trade_num = 6
        return level, trade_num, 6

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

# ==========================================
# 4. DATA FETCHING (Yahoo Finance Multi-Timeframe)
# ==========================================
def fetch_live_price(pair_info):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair_info['yahoo']}?interval=1m&range=1d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3.5) as res:
            data = json.loads(res.read().decode('utf-8'))
            meta = data['chart']['result'][0]['meta']
            return float(meta.get('regularMarketPrice', 0))
    except Exception:
        pass
    return None

def fetch_yahoo_data(symbol, interval, rng):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={rng}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4.0) as res:
            data = json.loads(res.read().decode('utf-8'))
            res_data = data['chart']['result'][0]
            timestamps = res_data['timestamp']
            quote = res_data['indicators']['quote'][0]
            candles = []
            for i in range(len(timestamps)):
                if quote['close'][i] is not None and quote['open'][i] is not None:
                    vol = quote.get('volume', [0]*len(timestamps))[i]
                    if vol is None: vol = 0
                    candles.append({
                        'open': float(quote['open'][i]),
                        'high': float(quote['high'][i]),
                        'low': float(quote['low'][i]),
                        'close': float(quote['close'][i]),
                        'volume': float(vol)
                    })
            return candles
    except Exception:
        return []

def calculate_ema(prices, period):
    if len(prices) < period:
        return [prices[-1]]
    multiplier = 2 / (period + 1)
    ema = [sum(prices[:period]) / period]
    for price in prices[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema

# ==========================================
# 5. AI MTFA & VOLUME ANALYSIS (Core Engine)
# ==========================================
def analyze_mtfa_volume(pair_info):
    symbol = pair_info['yahoo']
    
    # Fetch 3 timeframes for institutional level confirmation
    c_30m = fetch_yahoo_data(symbol, '30m', '5d')
    c_15m = fetch_yahoo_data(symbol, '15m', '3d')
    c_5m = fetch_yahoo_data(symbol, '5m', '1d')
    
    if len(c_30m) < 10 or len(c_15m) < 10 or len(c_5m) < 10:
        return None

    call_score = 0
    put_score = 0
    logic = []

    # 1. 30M Macro Price Action (Body vs Wick)
    last_30m = c_30m[-1]
    body_30m = abs(last_30m['close'] - last_30m['open'])
    rng_30m = max(last_30m['high'] - last_30m['low'], 1e-6)
    
    if last_30m['close'] > last_30m['open']:
        if body_30m > rng_30m * 0.5: # Strong Bullish Candle
            call_score += 30
            logic.append("30M Bullish Control")
    else:
        if body_30m > rng_30m * 0.5: # Strong Bearish Candle
            put_score += 30
            logic.append("30M Bearish Control")

    # 2. 15M Continuation Flow
    if c_15m[-1]['close'] > c_15m[-2]['close']:
        call_score += 20
        logic.append("15M Momentum UP")
    else:
        put_score += 20
        logic.append("15M Momentum DOWN")

    # 3. 5M Volume Anomaly (Where is the smart money?)
    vols_5m = [c['volume'] for c in c_5m[-6:-1]] 
    avg_vol_5m = sum(vols_5m) / 5.0 if vols_5m else 1.0
    current_vol_5m = c_5m[-1]['volume']
    
    vol_bonus = 25 if current_vol_5m > (avg_vol_5m * 1.2) else 10 # Extra points for volume spike
    
    if c_5m[-1]['close'] > c_5m[-1]['open']:
        call_score += vol_bonus
        if vol_bonus == 25: logic.append("5M High Buy Volume")
    else:
        put_score += vol_bonus
        if vol_bonus == 25: logic.append("5M High Sell Volume")

    final_action = "CALL (UP) 🟢" if call_score >= put_score else "PUT (DOWN) 🔴"
    final_score = max(call_score, put_score)
    final_reason = " | ".join(logic[:3])

    return {
        "pair": pair_info,
        "action": final_action,
        "score": final_score,
        "reason": final_reason,
        "price": c_5m[-1]['close']
    }

# ==========================================
# 6. MARKET SYNCHRONIZATION & EXECUTION
# ==========================================
def market_engine():
    time.sleep(2)
    send_tg(
        "🛡️ <b>MASTER LADDER ENGINE DEPLOYED</b>\n\n"
        "• <b>Ladder Fixed:</b> Win par +1 Step, Loss par -1 Step Backward (Safe Buffer).\n"
        "• <b>Level Rule:</b> L1-L20 (4 Trades), L21-L30 (6 Trades).\n"
        "• <b>MTFA Algo:</b> 30m, 15m aur 5m Volume sync, API load balanced (max_workers=3)."
    )

    first_run = True

    while True:
        try:
            now_ist = get_ist()

            # TRIGGER EXACTLY AT XX:00 AND XX:30
            if not first_run:
                if now_ist.minute not in [0, 30]:
                    time.sleep(5) 
                    continue

            first_run = False

            # --- 1. RESULT CHECK (Step Math Applied Here) ---
            if state.active_trade:
                t = state.active_trade
                exit_price = fetch_live_price(t['pair_info'])
                entry_price = t['entry_price']
                action = t['action']
                d = t['pair_info']['digits']

                with state.state_lock:
                    if exit_price and entry_price:
                        if "CALL" in action:
                            is_win = (exit_price > entry_price) 
                        else:
                            is_win = (exit_price < entry_price)
                    else:
                        is_win = False

                    prev_level, prev_trade, _ = get_ladder_info(state.global_step)

                    # THE EXACT COMPOUNDING MATH (1 Step Forward, 1 Step Back)
                    if is_win:
                        state.global_step += 1 # 1 STEP FORWARD
                        res_title = "✅ <b>30M RESULT: WIN (+1 STEP)</b> 🟢"
                    else:
                        state.global_step = max(1, state.global_step - 1) # 1 STEP BACK (Never below 1)
                        res_title = "⚠️ <b>30M RESULT: LOSS (-1 STEP BACK)</b> 🔴"

                    new_level, new_trade, new_max = get_ladder_info(state.global_step)
                    new_stake = LEVELS_STAKE[new_level]

                    exit_disp = f"{exit_price:.{d}f}" if exit_price else "API Error"
                    
                    res_msg = (
                        f"{res_title}\n\n"
                        f"📊 <b>Asset:</b> {t['name']}\n"
                        f"📍 <b>Entry:</b> {entry_price:.{d}f} ➔ <b>Exit:</b> {exit_disp}\n"
                        f"📈 <b>New Ladder Position:</b> Level {new_level}/30 (Trade {new_trade}/{new_max})\n"
                        f"💵 <b>Next Stake:</b> ${new_stake}"
                    )
                send_tg(res_msg)
                state.active_trade = None

            # --- 2. FIND NEW PERFECT SETUP (API Safe mode: max_workers=3) ---
            best_setup = None
            highest_score = 65 # Minimum AI confidence required
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                results = list(executor.map(analyze_mtfa_volume, PAIRS))
                
            for res in results:
                if res and res["score"] > highest_score:
                    highest_score = res["score"]
                    best_setup = res

            if not best_setup:
                now_ist = get_ist().strftime('%H:%M IST')
                send_tg(f"⚠️ <b>NO CLEAR SETUP ({now_ist})</b>\n<i>Market is choppy. Capital protection active. Waiting for next 30m cycle.</i>")
                time.sleep(65)
                continue

            # --- 3. SEND SIGNAL ---
            pair_info = best_setup['pair']
            cur_price = best_setup['price']
            action = best_setup['action']
            score = best_setup['score']
            reason = best_setup['reason']
            d = pair_info['digits']

            with state.state_lock:
                cur_level, cur_trade, cur_max = get_ladder_info(state.global_step)
                current_stake = LEVELS_STAKE[cur_level]

            now_ist = get_ist()
            ent_str = now_ist.strftime("%H:%M IST")
            exp_30m = (now_ist + timedelta(minutes=30)).strftime("%H:%M IST")

            alert = (
                f"🧠 <b>MTFA VOLUME SIGNAL</b>\n\n"
                f"📊 <b>Asset:</b> <code>{pair_info['name']}</code>\n"
                f"🚀 <b>Direction:</b> <b>{action}</b>\n"
                f"🔥 <b>AI Confidence:</b> <b>{score}/100</b>\n\n"
                f"⏳ <b>TRADING WINDOW:</b>\n"
                f"🟢 <b>Entry Time:</b> <code>{ent_str}</code> (Now)\n"
                f"🛑 <b>Expiry Set:</b> <code>{exp_30m}</code> (30 Minutes)\n\n"
                f"📈 <b>Current Ladder:</b> Level {cur_level}/30 (Trade {cur_trade}/{cur_max})\n"
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

            # Prevent double trigger in same minute
            time.sleep(65)

        except Exception as err:
            print(f">> [Runtime Error]: {err}")
            time.sleep(15)

threading.Thread(target=market_engine, daemon=True).start()

if __name__ == "__main__":
    while True:
        time.sleep(60)
