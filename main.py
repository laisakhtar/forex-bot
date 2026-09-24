import os
import threading
import time
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from flask import Flask
import asyncio
import numpy as np
import websockets

# Flask Web Server
app = Flask(__name__)

@app.route('/')
def home():
    return "QX FAST SIGNAL ENGINE ONLINE", 200

def start_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=start_flask, daemon=True).start()

# Credentials
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

FOREX_PAIRS = {
    "frxEURUSD": {"name": "EUR/USD", "digits": 5},
    "frxGBPUSD": {"name": "GBP/USD", "digits": 5},
    "frxUSDJPY": {"name": "USD/JPY", "digits": 3},
    "frxAUDUSD": {"name": "AUD/USD", "digits": 5},
    "frxUSDCAD": {"name": "USD/CAD", "digits": 5},
    "frxUSDCHF": {"name": "USD/CHF", "digits": 5},
    "frxNZDUSD": {"name": "NZD/USD", "digits": 5},
    "frxEURGBP": {"name": "EUR/GBP", "digits": 5},
    "frxEURJPY": {"name": "EUR/JPY", "digits": 3},
    "frxGBPJPY": {"name": "GBP/JPY", "digits": 3},
    "frxXAUUSD": {"name": "GOLD (XAU/USD)", "digits": 2}
}

candles_history = {pair: [] for pair in FOREX_PAIRS}
latest_quotes = {pair: 0.0 for pair in FOREX_PAIRS}
last_checked_bucket = {pair: 0 for pair in FOREX_PAIRS}

def get_ist():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

def format_price(sym, p):
    d = FOREX_PAIRS.get(sym, {}).get("digits", 5)
    return f"{p:.{d}f}"

def send_tg(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception as e:
        print(f"TG Error: {e}")

class EngineState:
    def __init__(self):
        self.level = 1
        self.trade_step = 1
        self.consecutive_losses = 0
        self.active_trade = False

state = EngineState()

# Non-blocking Telegram Polling
def telegram_listener():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=2"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as r:
                res = json.loads(r.read().decode('utf-8'))
                if res.get("ok"):
                    for u in res.get("result", []):
                        offset = u["update_id"] + 1
                        msg = u.get("message", {})
                        text = msg.get("text", "").strip()
                        c_id = str(msg.get("chat", {}).get("id", ""))
                        if c_id == CHAT_ID and text in ["/status", "status", "/start", "/test"]:
                            max_t = 4 if state.level <= 20 else 6
                            st = LEVELS_STAKE[state.level]
                            t_str = get_ist().strftime("%H:%M:%S IST")
                            reply = (
                                f"🟢 <b>QUOTEX SCANNER LIVE</b>\n\n"
                                f"🕒 <b>Time:</b> <code>{t_str}</code>\n"
                                f"📈 <b>Ladder:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                                f"💵 <b>Stake:</b> ${st}\n"
                                f"🚨 <b>Loss Count:</b> {state.consecutive_losses}/2\n"
                                f"🔍 <b>Pairs:</b> 11 Live Pairs Scanning"
                            )
                            send_tg(reply)
        except Exception:
            time.sleep(2)
        time.sleep(1)

threading.Thread(target=telegram_listener, daemon=True).start()

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def evaluate_fast_qx_signal(sym, candles):
    if len(candles) < 20:
        return "NO_TRADE", 0.0, {}

    closes = np.array([c['close'] for c in candles])
    highs = np.array([c['high'] for c in candles])
    lows = np.array([c['low'] for c in candles])
    opens = np.array([c['open'] for c in candles])

    c1, o1, h1, l1 = closes[-1], opens[-1], highs[-1], lows[-1]
    c2, o2 = closes[-2], opens[-2]

    body = max(abs(c1 - o1), 1e-5)
    lower_wick = min(o1, c1) - l1
    upper_wick = h1 - max(o1, c1)

    # Bollinger Bands
    sma20 = np.mean(closes[-20:])
    std20 = np.std(closes[-20:])
    upper_band = sma20 + (1.95 * std20)
    lower_band = sma20 - (1.95 * std20)

    # RSI
    rsi = calculate_rsi(closes, 14)

    meta = {
        "RSI": round(rsi, 2),
        "Setup": ""
    }

    # Setup 1: High-Probability Bollinger Wick Rejection
    if h1 >= upper_band and upper_wick >= body * 0.25:
        meta["Setup"] = "Bollinger Upper Wick Rejection"
        return "PUT (DOWN) 🔴", c1, meta

    if l1 <= lower_band and lower_wick >= body * 0.25:
        meta["Setup"] = "Bollinger Lower Wick Rejection"
        return "CALL (UP) 🟢", c1, meta

    # Setup 2: RSI Exhaustion Snatch
    if rsi >= 68:
        meta["Setup"] = f"RSI Overbought Snatch ({round(rsi, 1)})"
        return "PUT (DOWN) 🔴", c1, meta

    if rsi <= 32:
        meta["Setup"] = f"RSI Oversold Snatch ({round(rsi, 1)})"
        return "CALL (UP) 🟢", c1, meta

    # Setup 3: Solid Engulfing Strike
    if (c2 < o2) and (c1 > o1) and (c1 >= o2) and (o1 <= c2):
        meta["Setup"] = "Bullish Engulfing Candle"
        return "CALL (UP) 🟢", c1, meta

    if (c2 > o2) and (c1 < o1) and (c1 <= o2) and (o1 >= c2):
        meta["Setup"] = "Bearish Engulfing Candle"
        return "PUT (DOWN) 🔴", c1, meta

    return "NO_TRADE", c1, meta

async def monitor_trade(sym, pair_name, action, entry_price, entry_t, exit_t):
    await asyncio.sleep(295)
    exit_p = latest_quotes.get(sym, entry_price)
    win = (exit_p > entry_price) if "CALL" in action else (exit_p < entry_price)
    max_t = 4 if state.level <= 20 else 6

    if win:
        state.consecutive_losses = 0
        if state.trade_step < max_t:
            state.trade_step += 1
        else:
            state.level = 1 if state.level >= 30 else state.level + 1
            state.trade_step = 1
        res_msg = (
            f"✅ <b>QUOTEX 5M RESULT: WIN</b> 🟢\n\n"
            f"📊 <b>Asset:</b> {pair_name}\n"
            f"📍 <b>Entry:</b> <code>{format_price(sym, entry_price)}</code> ➔ <b>Exit:</b> <code>{format_price(sym, exit_p)}</code>\n"
            f"📈 <b>Ladder:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
            f"💵 <b>Next Stake:</b> ${LEVELS_STAKE[state.level]}"
        )
    else:
        state.consecutive_losses += 1
        state.trade_step = 1
        res_msg = (
            f"⚠️ <b>QUOTEX 5M RESULT: LOSS</b> 🔴\n\n"
            f"📊 <b>Asset:</b> {pair_name}\n"
            f"📍 <b>Entry:</b> <code>{format_price(sym, entry_price)}</code> ➔ <b>Exit:</b> <code>{format_price(sym, exit_p)}</code>\n"
            f"🛡️ <b>Step Reset:</b> Trade 1/{max_t}\n"
            f"💵 <b>Stake:</b> ${LEVELS_STAKE[state.level]}"
        )
        if state.consecutive_losses >= 2:
            send_tg("🚨 <b>DISCIPLINE LOCK: 2 LOSSES</b>\n⏳ <i>Bot paused for 60 mins.</i>")
            await asyncio.sleep(3600)
            state.consecutive_losses = 0
            state.level = 1
            send_tg("🟢 <b>LOCK OVER: RESUMING AT LEVEL 1</b>")

    send_tg(res_msg)
    state.active_trade = False

async def main():
    send_tg("🚀 <b>QUOTEX BOT ENGAGED: READY FOR SIGNALS</b>")
    uri = "wss://ws.derivws.com/websockets/v3?app_id=1089"

    while True:
        try:
            async with websockets.connect(uri, ping_interval=15, ping_timeout=15) as ws:
                for sym in FOREX_PAIRS:
                    await ws.send(json.dumps({
                        "ticks_history": sym,
                        "adjust_start_time": 1,
                        "count": 30,
                        "end": "latest",
                        "style": "candles",
                        "granularity": 300
                    }))
                    await ws.send(json.dumps({"ticks": sym}))
                    await asyncio.sleep(0.04)

                while True:
                    try:
                        res = await asyncio.wait_for(ws.recv(), timeout=20.0)
                    except asyncio.TimeoutError:
                        await ws.send(json.dumps({"ping": 1}))
                        continue

                    data = json.loads(res)

                    if "candles" in data:
                        sym = data.get("echo_req", {}).get("ticks_history", "")
                        if sym in FOREX_PAIRS:
                            candles_history[sym] = [
                                {'open': float(c['open']), 'high': float(c['high']), 'low': float(c['low']), 'close': float(c['close'])}
                                for c in data["candles"]
                            ]
                        continue

                    if "tick" not in data:
                        continue

                    tick = data["tick"]
                    sym = tick.get("symbol", "")
                    if sym not in FOREX_PAIRS:
                        continue

                    price = float(tick.get("quote", 0.0))
                    epoch = int(tick.get("epoch", time.time()))
                    latest_quotes[sym] = price

                    bucket = epoch // 300

                    if len(candles_history[sym]) > 0:
                        candles_history[sym][-1]['close'] = price
                        candles_history[sym][-1]['high'] = max(candles_history[sym][-1]['high'], price)
                        candles_history[sym][-1]['low'] = min(candles_history[sym][-1]['low'], price)

                    if last_checked_bucket[sym] != bucket:
                        last_checked_bucket[sym] = bucket
                        candles_history[sym].append({'open': price, 'high': price, 'low': price, 'close': price})
                        if len(candles_history[sym]) > 40:
                            candles_history[sym].pop(0)

                        if not state.active_trade and len(candles_history[sym]) >= 20:
                            sig, alert_p, meta = evaluate_fast_qx_signal(sym, candles_history[sym][:-1])
                            if sig != "NO_TRADE":
                                state.active_trade = True
                                now_ist = get_ist()
                                ent_str = now_ist.strftime("%H:%M:00 IST")
                                ext_str = (now_ist + timedelta(minutes=5)).strftime("%H:%M:00 IST")
                                p_name = FOREX_PAIRS[sym]['name']
                                max_t = 4 if state.level <= 20 else 6
                                stk = LEVELS_STAKE[state.level]

                                alert = (
                                    f"🎯 <b>QUOTEX 5M SIGNAL DETECTED</b>\n\n"
                                    f"📊 <b>Asset:</b> <code>{p_name}</code>\n"
                                    f"🚀 <b>Action:</b> {sig}\n"
                                    f"⏳ <b>Expiry:</b> 5 Minutes\n"
                                    f"⏱️ <b>Entry:</b> <code>{ent_str}</code> ➔ <b>Exit:</b> <code>{ext_str}</code>\n"
                                    f"📈 <b>Ladder:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                                    f"💵 <b>Stake:</b> ${stk}\n"
                                    f"📍 <b>Spot:</b> <code>{format_price(sym, alert_p)}</code>\n\n"
                                    f"⚙️ <b>Trigger:</b> {meta.get('Setup')}\n"
                                    f"📊 <b>RSI:</b> {meta.get('RSI')}\n\n"
                                    f"⚠️ <b>Execution:</b> Quotex me agli candle open hote hi trade lagayein."
                                )
                                send_tg(alert)
                                asyncio.create_task(monitor_trade(sym, p_name, sig, alert_p, ent_str, ext_str))

        except Exception as e:
            print(f"WS Exception: {e}")
            await asyncio.sleep(2)

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except Exception as err:
            print(f"Process Restart: {err}")
            time.sleep(2)
