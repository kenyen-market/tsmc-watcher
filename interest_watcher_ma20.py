
import yfinance as yf
import time
import threading
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import pandas as pd
from datetime import datetime
import pytz

def is_check_time():
    tz = pytz.timezone("Asia/Taipei")
    now = datetime.now(tz)
    hour = now.hour
    minute = now.minute

    # 只在 10:00 與 13:00 當下執行
    return (hour == 10 and minute == 0) or (hour == 13 and minute == 0)
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
FROM_EMAIL = os.environ.get("FROM_EMAIL")
TO_EMAIL = os.environ.get("TO_EMAIL")

STOCKS = {
    "2330.TW": "台積電",
    "2891.TW": "中信金",
    "1216.tw": "統一",
    "2327.tw": "國巨",
    "00878.TW": "國泰永續高股息",
    "00919.tw": "群益台灣精選高息"
}

# 個別股票狀態記錄
stock_states = {
    symbol: {
        "is_below_ma": False,
        "notified_below": False,
        "notified_5_down": False,
        "notified_10_down": False,
        "below_price": 0
    } for symbol in STOCKS
}
# === 寄 Email ===
def send_email(subject, content):
    try:
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=TO_EMAIL,
            subject=subject,
            plain_text_content=content
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        print(f">>> Email sent: {subject}")
    except Exception as e:
        print(f">>> Email failed: {e}")
def get_price_data(symbol):
    try:
        df = yf.download(symbol, period="30d", interval="1d", progress=False)
        df_today = yf.download(symbol, period="1d", interval="1m", progress=False)
        if df_today.empty or df.empty or "Close" not in df.columns:
            print(f">>> {symbol} 資料抓取失敗")
            return None
        current_price = df["Close"].iloc[-1].item()
        ma20 = df["Close"].rolling(window=20).mean().iloc[-1].item()
        if pd.isna(ma20):
            return None
        return float(current_price), float(ma20)
    except Exception as e:
        print(f">>> {symbol} 抓取資料錯誤：{e}")
        return None

def monitor_stock(symbol, name):
    state = stock_states[symbol]
    result = get_price_data(symbol)
    if not result:
        return
    current_price, ma20 = result
    print(f">>> {name}：現價 {current_price:.2f}, MA20 {ma20:.2f}")

    if current_price < ma20:
        if not state["is_below_ma"]:
            state.update({
                "is_below_ma": True,
                "below_price": current_price,
                "notified_below": False,
                "notified_5_down": False,
                "notified_10_down": False
            })
        if not state["notified_below"]:
            send_email(f"【{name}】跌破 20 日均線", f"目前股價 {current_price:.2f}，已跌破均線 {ma20:.2f}")
            state["notified_below"] = True

        drop_pct = (state["below_price"] - current_price) / state["below_price"] * 100
        if drop_pct >= 5 and not state["notified_5_down"]:
            send_email(f"【{name}】跌破後再跌 5%", f"股價 {current_price:.2f}，跌幅 {drop_pct:.2f}%")
            state["notified_5_down"] = True
        if drop_pct >= 10 and not state["notified_10_down"]:
            send_email(f"【{name}】跌破後再跌 10%", f"股價 {current_price:.2f}，跌幅 {drop_pct:.2f}%")
            state["notified_10_down"] = True
    else:
        state.update({
            "is_below_ma": False,
            "notified_below": False,
            "notified_5_down": False,
            "notified_10_down": False,
            "below_price": 0
        })

def watch_all_stocks():
    tz = pytz.timezone("Asia/Taipei")
    now = datetime.now(tz)
    if now.weekday() >= 5:
        print(">>> 週末不執行，略過")
        return
    print(f">>> 開始檢查股票（{now.strftime('%Y-%m-%d %H:%M:%S')}）")
    for symbol, name in STOCKS.items():
        monitor_stock(symbol, name)

if __name__ == "__main__":
    tz = pytz.timezone("Asia/Taipei")
    now = datetime.now(tz)
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    print(f">>> 系統啟動於：{now_str}")
    send_email(
        "【監控啟動通知】",
        f"系統於台灣時間 {now_str} 啟動監控。"
    ）
        watch_all_stocks()
