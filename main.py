import os, threading, time, json, urllib.request, concurrent.futures
from datetime import datetime, timezone, timedelta
from flask import Flask

app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "QUOTEX LIVE TIMER & 18-ASSET ENGINE ACTIVE", 200

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), use_reloader=False, threaded=True)

threading.Thread(target=run_flask, daemon=True).start()

BOT_TOKEN = "8807036352:AAGwVcFaIxvVU7xUIWFDHlHUwKM3vGdLbuw"
CHAT_ID = "5883050661"

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

class EngineState:
    def __init__(self):
        self.global_step = 1
        self.last_pair = ""
        self.lock = threading.Lock()

state = EngineState()

def get_ladder(g_step):
    if g_step <= 80:
        return ((g_step - 1) // 4) + 1, ((g_step - 1) % 4) + 1, 4
    rem = g_step - 80
    lvl = min(30, ((rem - 1) // 6) + 21)
    trd = 6 if lvl == 30 and rem > 60 else ((rem - 1) % 6) + 1
    return lvl, trd, 6

def get_ist():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

def next_close_time(now_ist):
    if now_ist.minute < 30:
        t = now_ist.replace(minute=30, second=0, microsecond=0)
    else:
        t = (now_ist + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return t + timedelta(minutes=30) if (t - now_ist).total_seconds() < 20 else t

def send_tg(text):
    for _ in range(3):
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as r:
                res = json.loads(r.read().decode())
                if res.get("ok"):
                    return res["result"]["message_id"]
        except Exception:
            time.sleep(1)
    return None

def edit_tg(msg_id, text):
    if not msg_id:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        data = json.dumps({"chat_id": CHAT_ID, "message_id": msg_id, "text": text, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=6):
            pass
    except Exception:
        pass

def fetch_tv_all():
    url = "https://scanner.tradingview.com/forex/scan"
    cols = ["close", "open", "Recommend.All|5", "Recommend.All|15", "Recommend.All|30", "Recommend.All|60"]
    payload = json.dumps({"symbols": {"tickers": [p["tv"] for p in PAIRS], "query": {"types": []}}, "columns": cols}).encode()
    out = {}
    try:
        req = urllib.request.Request(url, data=payload, headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=4.0) as r:
            for item in json.loads(r.read().decode()).get("data", []):
                if item.get("s") and len(item.get("d", [])) == len(cols):
                    out[item["s"]] = dict(zip(cols, item["d"]))
    except Exception:
        pass
    return out

def fetch_yahoo(symbol, interval, rng):
    ts = int(time.time() * 1000)
    for host in ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]:
        url = f"https://{host}/v8/finance/chart/{symbol}?interval={interval}&range={rng}&_t={ts}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": f"Mozilla/5.0/{ts%991}", "Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=4.0) as r:
                res = json.loads(r.read().decode())["chart"]["result"][0]
                reg = res.get("meta", {}).get("regularMarketPrice")
                q = res["indicators']['quote'][0]" if False else res["indicators"]["quote"][0]
                c_list = [{"open": float(o), "close": float(c)} for o, c in zip(q.get("open", []), q.get("close", [])) if o is not None and c is not None]
                return c_list, (float(reg) if reg is not None else None)
        except Exception:
            continue
    return [], None

def get_live_tick(pair_info):
    tv = fetch_tv_all().get(pair_info["tv"])
    if tv and tv.get("close") is not None:
        return float(tv["close"])
    c_1m, reg = fetch_yahoo(pair_info["yahoo"], "1m", "1d")
    return reg if (reg and reg > 0) else (c_1m[-1]["close"] if c_1m else None)

def analyze_pair(pair_info, tv_data):
    sym = pair_info["yahoo"]
    c_30m, _     = fetch_yahoo(sym, "30m", "1mo")
    c_15m, _     = fetch_yahoo(sym, "15m", "5d")
    c_5m, reg_5m = fetch_yahoo(sym, "5m", "5d")
    c_1m, reg_1m = fetch_yahoo(sym, "1m", "1d")

    if len(c_30m) < 60 or len(c_5m) < 15:
        return None

    if tv_data and tv_data.get("close") is not None:
        live_p = float(tv_data["close"])
    elif reg_1m and reg_1m > 0:
        live_p = reg_1m
    elif c_1m:
        live_p = c_1m[-1]["close"]
    else:
        live_p = reg_5m if (reg_5m and reg_5m > 0) else c_30m[-1]["close"]

    open_30m = c_30m[-1]["open"]
    d5  = (live_p - c_5m[-2]["close"]) / live_p
    d15 = (live_p - (c_15m[-2]["close"] if len(c_15m) >= 2 else open_30m)) / live_p
    d30 = (live_p - c_30m[-2]["close"]) / live_p
    d60 = (live_p - c_30m[-3]["close"]) / live_p

    closes = [x["close"] for x in c_30m]
    closes[-1] = live_p
    matches = []
    for i in range(5, len(closes) - 2):
        p = closes[i]
        if p <= 0:
            continue
        dist = abs(d30 - (p - closes[i-1])/p)*1.5 + abs(d60 - (p - closes[i-2])/p)*1.5 + abs(d15 - (p - closes[i-3])/p)*0.8
        diff = closes[i+1] - p
        if diff != 0:
            matches.append((dist, 1 if diff > 0 else 0, abs(diff)/p))

    if len(matches) < 25:
        return None

    matches.sort(key=lambda x: x[0])
    top_k = matches[:60]
    up_w = sum((1.0 / (x[0] + 1e-6)) * (1.0 + x[2]*100.0) for x in top_k if x[1] == 1)
    dn_w = sum((1.0 / (x[0] + 1e-6)) * (1.0 + x[2]*100.0) for x in top_k if x[1] == 0)
    if (up_w + dn_w) <= 0:
        return None

    up_prob = (up_w / (up_w + dn_w)) * 100.0
    dn_prob = (dn_w / (up_w + dn_w)) * 100.0

    if tv_data and tv_data.get("Recommend.All|30") is not None:
        tf_flow = (float(tv_data.get("Recommend.All|5") or 0)*0.2 + float(tv_data.get("Recommend.All|15") or 0)*0.25 +
                   float(tv_data.get("Recommend.All|30") or 0)*0.3 + float(tv_data.get("Recommend.All|60") or 0)*0.25)
        up_prob = up_prob * 0.6 + (50.0 + tf_flow * 40.0) * 0.4
        dn_prob = dn_prob * 0.6 + (50.0 - tf_flow * 40.0) * 0.4

    up_align = (1 if d60 > 0 else 0) + (1 if d30 > 0 else 0) + (1 if d15 > 0 else 0) + (1 if d5 > 0 else 0)
    if up_prob >= dn_prob:
        act, prob = "CALL (UP) 🟢", min(95.8, max(53.2, up_prob + up_align * 1.4))
    else:
        act, prob = "PUT (DOWN) 🔴", min(95.8, max(53.2, dn_prob + (4 - up_align) * 1.4))

    logic = f"1H:{'UP' if d60>=0 else 'DOWN'} | 30M:{'UP' if d30>=0 else 'DOWN'} | 15M:{'UP' if d15>=0 else 'DOWN'} | 5M:{'UP' if d5>=0 else 'DOWN'}"
    return {"pair": pair_info, "action": act, "prob": prob, "samples": len(matches), "reason": logic, "price": live_p, "open_30m": open_30m}

def format_msg(s, lvl, trd, mx, stake, ent_s, exp_s, live_p, rem_s, closed=False):
    p = s["pair"]
    d, pip, ent_p = p["digits"], p["pip"], s["price"]
    pips = (live_p - ent_p) / pip
    signed_pips = pips if "CALL" in s["action"] else -pips
    status = "⚪ <b>AT ENTRY (0.0 Pips)</b>" if abs(live_p - ent_p) < pip*0.1 else (f"🟢 <b>IN PROFIT ({signed_pips:+.1f} Pips)</b>" if signed_pips > 0 else f"🔴 <b>PULLBACK ({signed_pips:+.1f} Pips)</b>")
    timer_str = f"🏁 <b>CANDLE CLOSED ({exp_s})</b>" if closed else f"⏳ <b>Close Hone Mein Baki:</b> <code>{int(rem_s)//60:02d}m {int(rem_s)%60:02d}s</code>"
    return (
        f"⚡ <b>LIVE REAL-TIME PRICE & TIMER SIGNAL</b>\n\n"
        f"📊 <b>Asset:</b> <code>{p['name']}</code> (18-Asset Scan)\n"
        f"🚀 <b>Direction:</b> <b>{s['action']}</b>\n"
        f"🎯 <b>Win Probability:</b> <b>{s['prob']:.2f}%</b> ({s['samples']} Past 30D Matches)\n\n"
        f"📍 <b>30M Candle Open:</b> <code>{s['open_30m']:.{d}f}</code>\n"
        f"🟢 <b>Signal Entry Price:</b> <code>{ent_p:.{d}f}</code> ({ent_s})\n"
        f"💹 <b>Live Market Price:</b> <code>{live_p:.{d}f}</code>\n"
        f"📊 <b>Live Status:</b> {status}\n\n"
        f"⏱️ <b>LIVE BROKER TIMER:</b>\n"
        f"🛑 <b>Candle Close Time:</b> <code>{exp_s}</code>\n"
        f"{timer_str}\n\n"
        f"📈 <b>Current Ladder:</b> Level {lvl}/30 (Trade {trd}/{mx})\n"
        f"💵 <b>Stake Amount:</b> ${stake}\n"
        f"🔬 <b>Price Data:</b> <i>{s['reason']}</i>"
    )

def run_cycle():
    now_ist = get_ist()
    exp_dt = next_close_time(now_ist)
    ent_s, exp_s = now_ist.strftime("%H:%M:%S IST"), exp_dt.strftime("%H:%M:%S IST")

    tv_map = fetch_tv_all()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        res_list = [r for r in ex.map(lambda p: analyze_pair(p, tv_map.get(p["tv"])), PAIRS) if r]

    if not res_list:
        time.sleep(5)
        return

    res_list.sort(key=lambda x: x["prob"], reverse=True)
    best = res_list[1] if (len(res_list) > 1 and res_list[0]["pair"]["name"] == state.last_pair and (res_list[0]["prob"] - res_list[1]["prob"]) < 2.0) else res_list[0]
    p_info = best["pair"]
    state.last_pair = p_info["name"]
    ent_p, d = best["price"], p_info["digits"]

    with state.lock:
        lvl, trd, mx = get_ladder(state.global_step)
        stake = LEVELS_STAKE[lvl]

    rem_s = max(0, (exp_dt - get_ist()).total_seconds())
    msg_id = send_tg(format_msg(best, lvl, trd, mx, stake, ent_s, exp_s, ent_p, rem_s, False))

    live_p = ent_p
    while True:
        rem_s = (exp_dt - get_ist()).total_seconds()
        if rem_s <= 0:
            break
        time.sleep(min(15.0, max(0.5, rem_s)))
        rem_s = (exp_dt - get_ist()).total_seconds()
        if rem_s <= 0:
            break
        tick = get_live_tick(p_info)
        if tick:
            live_p = tick
        edit_tg(msg_id, format_msg(best, lvl, trd, mx, stake, ent_s, exp_s, live_p, rem_s, False))

    final_tick = get_live_tick(p_info)
    if final_tick:
        live_p = final_tick
    edit_tg(msg_id, format_msg(best, lvl, trd, mx, stake, ent_s, exp_s, live_p, 0, True))

    with state.lock:
        win = (live_p > ent_p) if "CALL" in best["action"] else (live_p < ent_p)
        state.global_step = (state.global_step + 1) if win else max(1, state.global_step - 1)
        n_lvl, n_trd, n_mx = get_ladder(state.global_step)
        n_stake = LEVELS_STAKE[n_lvl]
        title = "✅ <b>30M CANDLE CLOSE RESULT: WIN (+1 STEP)</b> 🟢" if win else "⚠️ <b>30M CANDLE CLOSE RESULT: LOSS (-1 STEP)</b> 🔴"
        send_tg(
            f"{title}\n\n"
            f"📊 <b>Asset:</b> <code>{p_info['name']}</code>\n"
            f"📍 <b>Entry Price:</b> <code>{ent_p:.{d}f}</code> ➔ <b>Close Price:</b> <code>{live_p:.{d}f}</code>\n"
            f"📈 <b>New Ladder Position:</b> Level {n_lvl}/30 (Trade {n_trd}/{n_mx})\n"
            f"💵 <b>Next Stake:</b> ${n_stake}"
        )

def market_engine():
    time.sleep(2)
    send_tg("⚡ <b>18-ASSET LIVE PRICE & TIMER ENGINE DEPLOYED</b>\n• Live Countdown Timer & Real-Time Price active.")
    while True:
        try:
            run_cycle()
        except Exception as e:
            print("Cycle error:", e)
            time.sleep(5)

threading.Thread(target=market_engine, daemon=True).start()

if __name__ == "__main__":
    while True:
        time.sleep(60)
# === END OF FILE ===
