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
    return "QUOTEX FAILSAFE LIVE TIMER & 18-ASSET ENGINE ACTIVE", 200

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
# 2. TELEGRAM & 18 LIVE ASSETS CONFIG
# ==========================================
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
    {"name": "EUR/USD", "tv": "FX:EURUSD", "yahoo": "EURUSD=X", "digits": 5, "pip": 0.0001},
    {"name": "GBP/USD", "tv": "FX:GBPUSD", "yahoo": "GBPUSD=X", "digits": 5, "pip": 0.0001},
    {"name": "USD/JPY", "tv": "FX:USDJPY", "yahoo": "JPY=X", "digits": 3, "pip": 0.01},
    {"name": "AUD/USD", "tv": "FX:AUDUSD", "yahoo": "AUDUSD=X", "digits": 5, "pip": 0.0001},
    {"name": "USD/CAD", "tv": "FX:USDCAD", "yahoo": "CAD=X", "digits": 5, "pip": 0.0001},
    {"name": "USD/CHF", "tv": "FX:USDCHF", "yahoo": "CHF=X", "digits": 5, "pip": 0.0001},
    {"name": "NZD/USD", "tv": "FX:NZDUSD", "yahoo": "NZDUSD=X", "digits": 5, "pip": 0.0001},
    {"name": "EUR/GBP", "tv": "FX:EURGBP", "yahoo": "EURGBP=X", "digits": 5, "pip": 0.0001},
    {"name": "EUR/JPY", "tv": "FX:EURJPY", "yahoo": "EURJPY=X", "digits": 3, "pip": 0.01},
    {"name": "GBP/JPY", "tv": "FX:GBPJPY", "yahoo": "GBPJPY=X", "digits": 3, "pip": 0.01},
    {"name": "AUD/JPY", "tv": "FX:AUDJPY", "yahoo": "AUDJPY=X", "digits": 3, "pip": 0.01},
    {"name": "CHF/JPY", "tv": "FX:CHFJPY", "yahoo": "CHFJPY=X", "digits": 3, "pip": 0.01},
    {"name": "EUR/AUD", "tv": "FX:EURAUD", "yahoo": "EURAUD=X", "digits": 5, "pip": 0.0001},
    {"name": "GBP/AUD", "tv": "FX:GBPAUD", "yahoo": "GBPAUD=X", "digits": 5, "pip": 0.0001},
    {"name": "EUR/CAD", "tv": "FX:EURCAD", "yahoo": "EURCAD=X", "digits": 5, "pip": 0.0001},
    {"name": "GBP/CAD", "tv": "FX:GBPCAD", "yahoo": "GBPCAD=X", "digits": 5, "pip": 0.0001},
    {"name": "AUD/CAD", "tv": "FX:AUDCAD", "yahoo": "AUDCAD=X", "digits": 5, "pip": 0.0001},
    {"name": "EUR/CHF", "tv": "FX:EURCHF", "yahoo": "EURCHF=X", "digits": 5, "pip": 0.0001}
]

# ==========================================
# 3. LADDER MATH (L1-20: 4 Steps, L21-30: 6 Steps)
# ==========================================
class MasterEngineState:
    def __init__(self):
        self.global_step = 1
        self.last_pair_name = ""
        self.state_lock = threading.Lock()

state = MasterEngineState()

def get_ladder_info(g_step):
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

def get_next_30m_close(now_ist):
    if now_ist.minute < 30:
        target = now_ist.replace(minute=30, second=0, microsecond=0)
    else:
        nxt = now_ist + timedelta(hours=1)
        target = nxt.replace(minute=0, second=0, microsecond=0)
    if (target - now_ist).total_seconds() < 20:
        target = target + timedelta(minutes=30)
    return target

# ==========================================
# 4. TELEGRAM SEND & LIVE EDIT FUNCTIONS
# ==========================================
def send_tg_sync(text):
    for _ in range(3):
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode('utf-8')
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "Connection": "close"})
            with urllib.request.urlopen(req, timeout=8) as res:
                resp_data = json.loads(res.read().decode('utf-8'))
                if resp_data.get("ok"):
                    return resp_data["result"]["message_id"]
        except Exception:
            time.sleep(1.5)
    return None

def edit_tg_sync(message_id, text):
    if not message_id:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        payload = json.dumps({
            "chat_id": CHAT_ID,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML"
        }).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "Connection": "close"})
        with urllib.request.urlopen(req, timeout=6):
            pass
    except Exception:
        pass

# ==========================================
# 5. FAILSAFE DUAL-ENGINE DATA FETCHER (TV + UN-CACHED YAHOO)
# ==========================================
def fetch_tradingview_scanner():
    url = "https://scanner.tradingview.com/forex/scan"
    tickers = [p["tv"] for p in PAIRS]
    columns = [
        "close", "open", "high", "low",
        "Recommend.All", "Recommend.All|1", "Recommend.All|5",
        "Recommend.All|15", "Recommend.All|30", "Recommend.All|60"
    ]
    payload = json.dumps({
        "symbols": {"tickers": tickers, "query": {"types": []}},
        "columns": columns
    }).encode('utf-8')
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json"
    }
    tv_map = {}
    try:
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=4.0) as res:
            data = json.loads(res.read().decode('utf-8'))
            for item in data.get("data", []):
                sym = item.get("s")
                vals = item.get("d", [])
                if sym and len(vals) == len(columns):
                    tv_map[sym] = dict(zip(columns, vals))
    except Exception:
        pass
    return tv_map

def fetch_yahoo_candles(symbol, interval, rng):
    ts_b = int(time.time() * 1000)
    for host in ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]:
        url = f"https://{host}/v8/finance/chart/{symbol}?interval={interval}&range={rng}&_t={ts_b}"
        headers = {
            "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/{ts_b % 997}",
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=4.0) as res:
                data = json.loads(res.read().decode('utf-8'))
                result = data['chart']['result'][0]
                meta = result.get('meta', {})
                reg_price = meta.get('regularMarketPrice')
                quote = result['indicators']['quote'][0]
                opens = quote.get('open', [])
                highs = quote.get('high', [])
                lows = quote.get('low', [])
                closes = quote.get('close', [])
                candles = []
                for i in range(len(closes)):
                    if closes[i] is not None and opens[i] is not None:
                        candles.append({
                            "open": float(opens[i]),
                            "high": float(highs[i]) if highs[i] is not None else float(closes[i]),
                            "low": float(lows[i]) if lows[i] is not None else float(closes[i]),
                            "close": float(closes[i])
                        })
                return candles, (float(reg_price) if reg_price is not None else None)
        except Exception:
            continue
    return [], None

def fetch_live_tick_price(pair_info):
    tv_map = fetch_tradingview_scanner()
    tv_d = tv_map.get(pair_info["tv"])
    if tv_d and tv_d.get("close") is not None:
        return float(tv_d["close"])

    c_1m, reg_p = fetch_yahoo_candles(pair_info["yahoo"], "1m", "1d")
    if reg_p is not None and reg_p > 0:
        return reg_p
    if c_1m:
        return c_1m[-1]["close"]
    return None

# ==========================================
# 6. 30-DAY REAL PRICE BACKTEST & MULTI-TF ENGINE
# ==========================================
def evaluate_asset(pair_info, tv_data):
    symbol = pair_info["yahoo"]

    # Fetch 1 Month (30 Days) of 30m data + 15m + 5m + 1m live data
    c_30m, reg_30m = fetch_yahoo_candles(symbol, "30m", "1mo")
    c_15m, _       = fetch_yahoo_candles(symbol, "15m", "5d")
    c_5m,  reg_5m  = fetch_yahoo_candles(symbol, "5m",  "5d")
    c_1m,  reg_1m  = fetch_yahoo_candles(symbol, "1m",  "1d")

    if len(c_30m) < 60 or len(c_5m) < 20:
        return None

    # Determine freshest live market price (Zero Freeze)
    live_price = None
    if tv_data and tv_data.get("close") is not None:
        live_price = float(tv_data["close"])
    elif reg_1m is not None and reg_1m > 0:
        live_price = reg_1m
    elif c_1m:
        live_price = c_1m[-1]["close"]
    elif reg_5m is not None and reg_5m > 0:
        live_price = reg_5m
    else:
        live_price = c_30m[-1]["close"]

    open_30m = c_30m[-1]["open"]

    # Real Price Velocity across 5m, 15m, 30m, and 1H (60m)
    p_5m_ago  = c_5m[-2]["close"] if len(c_5m) >= 2 else c_30m[-1]["open"]
    p_15m_ago = c_15m[-2]["close"] if len(c_15m) >= 2 else c_30m[-1]["open"]
    p_30m_ago = c_30m[-2]["close"] if len(c_30m) >= 2 else c_30m[-1]["open"]
    p_60m_ago = c_30m[-3]["close"] if len(c_30m) >= 3 else c_30m[-1]["open"]

    d5  = (live_price - p_5m_ago) / live_price
    d15 = (live_price - p_15m_ago) / live_price
    d30 = (live_price - p_30m_ago) / live_price
    d60 = (live_price - p_60m_ago) / live_price

    # 30-Day Historical Price Coordinate Matching
    closes_30m = [c["close"] for c in c_30m]
    closes_30m[-1] = live_price

    scored_outcomes = []
    for i in range(6, len(closes_30m) - 2):
        p = closes_30m[i]
        if p <= 0:
            continue
        h_d30 = (p - closes_30m[i - 1]) / p
        h_d60 = (p - closes_30m[i - 2]) / p
        h_d90 = (p - closes_30m[i - 3]) / p

        dist = abs(d30 - h_d30) * 1.5 + abs(d60 - h_d60) * 1.5 + abs(d15 - h_d90) * 0.8
        next_close_30m = closes_30m[i + 1]
        diff = next_close_30m - p
        if diff != 0:
            scored_outcomes.append((dist, 1 if diff > 0 else 0, abs(diff) / p))

    if len(scored_outcomes) < 25:
        return None

    scored_outcomes.sort(key=lambda x: x[0])
    top_k = scored_outcomes[:60]

    up_w = sum((1.0 / (x[0] + 1e-6)) * (1.0 + x[2] * 100.0) for x in top_k if x[1] == 1)
    dn_w = sum((1.0 / (x[0] + 1e-6)) * (1.0 + x[2] * 100.0) for x in top_k if x[1] == 0)
    tot_w = up_w + dn_w
    if tot_w <= 0:
        return None

    hist_up_prob = (up_w / tot_w) * 100.0
    hist_dn_prob = (dn_w / tot_w) * 100.0

    # Combine with TradingView Multi-TF Matrix if available
    if tv_data and tv_data.get("Recommend.All|30") is not None:
        r5  = float(tv_data.get("Recommend.All|5") or 0.0)
        r15 = float(tv_data.get("Recommend.All|15") or 0.0)
        r30 = float(tv_data.get("Recommend.All|30") or 0.0)
        r60 = float(tv_data.get("Recommend.All|60") or 0.0)
        tv_flow = (r5 * 0.2) + (r15 * 0.25) + (r30 * 0.3) + (r60 * 0.25)
        tv_up = 50.0 + (tv_flow * 40.0)
        tv_dn = 50.0 - (tv_flow * 40.0)
        comb_up = (hist_up_prob * 0.6) + (tv_up * 0.4)
        comb_dn = (hist_dn_prob * 0.6) + (tv_dn * 0.4)
    else:
        comb_up = hist_up_prob
        comb_dn = hist_dn_prob

    up_align = (1 if d60 > 0 else 0) + (1 if d30 > 0 else 0) + (1 if d15 > 0 else 0) + (1 if d5 > 0 else 0)
    dn_align = 4 - up_align

    if comb_up >= comb_dn:
        action = "CALL (UP) 🟢"
        final_prob = comb_up + (up_align * 1.4)
    else:
        action = "PUT (DOWN) 🔴"
        final_prob = comb_dn + (dn_align * 1.4)

    final_prob = min(95.8, max(53.2, final_prob))

    s60 = "UP" if d60 >= 0 else "DOWN"
    s30 = "UP" if d30 >= 0 else "DOWN"
    s15 = "UP" if d15 >= 0 else "DOWN"
    s5  = "UP" if d5 >= 0 else "DOWN"
    logic_str = f"1H:{s60} | 30M:{s30} | 15M:{s15} | 5M:{s5}"

    return {
        "pair": pair_info,
        "action": action,
        "prob": final_prob,
        "samples": len(scored_outcomes),
        "reason": logic_str,
        "price": live_price,
        "open_30m": open_30m
    }

def build_signal_message(setup, cur_level, cur_trade, cur_max, current_stake, ent_str, exp_str, live_price, rem_sec, is_closed=False):
    pair_info = setup["pair"]
    d = pair_info["digits"]
    pip_size = pair_info["pip"]
    entry_p = setup["price"]
    open_30m = setup["open_30m"]
    action = setup["action"]
    prob = setup["prob"]
    samples = setup["samples"]
    reason = setup["reason"]

    diff = live_price - entry_p
    pips = diff / pip_size
    if "CALL" in action:
        is_winning_now = (live_price > entry_p)
        pip_signed = pips
    else:
        is_winning_now = (live_price < entry_p)
        pip_signed = -pips

    if is_closed:
        timer_line = f"🏁 <b>CANDLE CLOSED ({exp_str})</b>"
    else:
        mins = max(0, int(rem_sec) // 60)
        secs = max(0, int(rem_sec) % 60)
        timer_line = f"⏳ <b>Close Hone Mein Baki:</b> <code>{mins:02d}m {secs:02d}s</code>"

    if abs(live_price - entry_p) < (pip_size * 0.1):
        status_line = "⚪ <b>AT ENTRY PRICE (0.0 Pips)</b>"
    elif is_winning_now:
        status_line = f"🟢 <b>IN PROFIT ({pip_signed:+.1f} Pips)</b>"
    else:
        status_line = f"🔴 <b>PULLBACK ({pip_signed:+.1f} Pips)</b>"

    return (
        f"⚡ <b>LIVE REAL-TIME PRICE & TIMER SIGNAL</b>\n\n"
        f"📊 <b>Asset:</b> <code>{pair_info['name']}</code> (18-Asset Scan)\n"
        f"🚀 <b>Direction:</b> <b>{action}</b>\n"
        f"🎯 <b>Win Probability:</b> <b>{prob:.2f}%</b> ({samples} Past 30D Matches)\n\n"
        f"📍 <b>30M Candle Open:</b> <code>{open_30m:.{d}f}</code>\n"
        f"🟢 <b>Signal Entry Price:</b> <code>{entry_p:.{d}f}</code> ({ent_str})\n"
        f"💹 <b>Live Market Price:</b> <code>{live_price:.{d}f}</code>\n"
        f"📊 <b>Live Trade Status:</b> {status_line}\n\n"
        f"⏱️ <b>LIVE BROKER TIMER:</b>\n"
        f"🛑 <b>Candle Close Time:</b> <code>{exp_str}</code>\n"
        f"{timer_line}\n\n"
        f"📈 <b>Current Ladder:</b> Level {cur_level}/30 (Trade {cur_trade}/{cur_max})\n"
        f"💵 <b>Stake Amount:</b> ${current_stake}\n"
        f"🔬 <b>Real Price Flow:</b> <i>{reason}</i>"
    )

# ==========================================
# 7. MASTER EXECUTION & LIVE COUNTDOWN LOOP
# ==========================================
def market_engine():
    time.sleep(2)
    send_tg_sync(
        "🛡️ <b>FAILSAFE LIVE PRICE & TIMER ENGINE STARTED</b>\n\n"
        "• <b>18:30 Silent Bug Fixed:</b> TradingView + Direct Multi-Server Fallback active. Ab bot kabhi silent nahi hoga.\n"
        "• <b>Immediate Signal:</b> Deploy hote hi abhi turant pehla Live Timer Signal aa raha hai, aur har xx:00 / xx:30 par naya signal aayega."
    )

    while True:
        try:
            now_ist = get_ist()
            exp_dt = get_next_30m_close(now_ist)
            ent_str = now_ist.strftime("%H:%M:%S IST")
            exp_str = exp_dt.strftime("%H:%M:%S IST")

            # 1. SCAN ALL 18 ASSETS (WITH AUTOMATIC FALLBACK)
            tv_map = fetch_tradingview_scanner()

            def _worker(p):
                return evaluate_asset(p, tv_map.get(p["tv"]))

            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(_worker, PAIRS))

            valid_results = [r for r in results if r is not None]
            valid_results.sort(key=lambda x: x["prob"], reverse=True)

            if not valid_results:
                send_tg_sync("⚠️ <b>NETWORK SYNC RETRYING IN 5 SECONDS...</b>")
                time.sleep(5)
                continue

            best_setup = valid_results[0]
            if len(valid_results) > 1 and best_setup["pair"]["name"] == state.last_pair_name:
                if (best_setup["prob"] - valid_results[1]["prob"]) < 2.0:
                    best_setup = valid_results[1]

            pair_info = best_setup["pair"]
            state.last_pair_name = pair_info["name"]
            entry_price = best_setup["price"]
            action = best_setup["action"]
            d = pair_info["digits"]

            with state.state_lock:
                cur_level, cur_trade, cur_max = get_ladder_info(state.global_step)
                current_stake = LEVELS_STAKE[cur_level]

            rem_sec = max(0, (exp_dt - get_ist()).total_seconds())
            initial_msg = build_signal_message(
                best_setup, cur_level, cur_trade, cur_max, current_stake,
                ent_str, exp_str, entry_price, rem_sec, is_closed=False
            )
            msg_id = send_tg_sync(initial_msg)

            # 2. LIVE COUNTDOWN & LIVE PRICE REFRESH EVERY 15 SECONDS UNTIL CANDLE CLOSE
            live_price = entry_price
            while True:
                now_loop = get_ist()
                rem_sec = (exp_dt - now_loop).total_seconds()
                if rem_sec <= 0:
                    break

                sleep_dur = min(15.0, max(0.5, rem_sec))
                time.sleep(sleep_dur)

                now_loop = get_ist()
                rem_sec = (exp_dt - now_loop).total_seconds()
                if rem_sec <= 0:
                    break

                new_tick = fetch_live_tick_price(pair_info)
                if new_tick is not None:
                    live_price = new_tick

                updated_msg = build_signal_message(
                    best_setup, cur_level, cur_trade, cur_max, current_stake,
                    ent_str, exp_str, live_price, rem_sec, is_closed=False
                )
                edit_tg_sync(msg_id, updated_msg)

            # 3. EXACT CANDLE CLOSE (00m 00s) — LOCK FINAL BROKER PRICE
            final_tick = fetch_live_tick_price(pair_info)
            if final_tick is not None:
                live_price = final_tick

            closed_msg = build_signal_message(
                best_setup, cur_level, cur_trade, cur_max, current_stake,
                ent_str, exp_str, live_price, 0, is_closed=True
            )
            edit_tg_sync(msg_id, closed_msg)

            # 4. SEND WIN/LOSS RESULT & STEP LADDER (+1 WIN / -1 LOSS)
            with state.state_lock:
                if "CALL" in action:
                    is_win = (live_price > entry_price)
                
