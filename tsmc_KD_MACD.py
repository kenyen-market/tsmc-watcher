import yfinance as yf
import pandas as pd
from ta.momentum import StochasticOscillator
from ta.trend import MACD
import pytz
from datetime import datetime
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# === 設定 ===
STOCK_SYMBOL = "2330.TW"
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
FROM_EMAIL = os.environ.get("FROM_EMAIL")
TO_EMAIL = os.environ.get("TO_EMAIL")

# === 狀態追蹤 ===
notified_kd_macd = False

# === 發送 Email ===
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

# === 技術指標取得 ===
def get_ta_data():
    try:
        df = yf.download(STOCK_SYMBOL, period="60d", interval="1d", progress=False)
        if df.empty or "Close" not in df.columns:
            print(">>> 抓取資料失敗")
            return None

        df.dropna(inplace=True)
        df.columns = 
        df.columns.get_level_values(0)  # 只取第一層欄位名稱
        close = df["Close"]

        # 當前價格
        current_price = close.iloc[-1]

        # KD
        stoch = StochasticOscillator(high=df["High"], low=df["Low"], close=close, window=14, smooth_window=3)
        k = stoch.stoch().iloc[-1]
        d = stoch.stoch_signal().iloc[-1]

        # MACD
        macd = MACD(close=close)
        macd_val = macd.macd().iloc[-1]

        return current_price, k, d, macd_val
    except Exception as e:
        print(f">>> 計算指標錯誤：{e}")
        return None

# === 監控邏輯 ===
def watch_stock():
    global notified_kd_macd

    tz = pytz.timezone("Asia/Taipei")
    now = datetime.now(tz)
    print(">>> 台灣時間：", now.strftime("%Y-%m-%d %H:%M:%S"))

    if now.weekday() >= 5 or not (9 <= now.hour < 14):
        print(">>> 非開盤時間，略過")
        return

    data = get_ta_data()
    if data is None:
        print(">>> 指標資料抓取失敗")
        return

    current_price, k, d, macd_val = data
    print(f">>> 股價: {current_price:.2f}, K: {k:.2f}, D: {d:.2f}, MACD: {macd_val:.4f}")

    if k < 20 and macd_val < 0:
        if not notified_kd_macd:
            send_email(
                "【TSMC 警示】KD<20 且 MACD<0",
                f"目前股價: {current_price:.2f}\nK: {k:.2f}, D: {d:.2f}, MACD: {macd_val:.4f}"
            )
            notified_kd_macd = True
    else:
        notified_kd_macd = False

# === 執行一次監控 ===
if __name__ == "__main__":
    print(">>> 系統啟動中...")
    watch_stock()
