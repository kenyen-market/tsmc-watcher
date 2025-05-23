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
STOCKS = {
    "2330.TW": "台積電",
    "2891.TW": "中信金",
    "00878.TW": "國泰永續高股息"
}
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
FROM_EMAIL = os.environ.get("FROM_EMAIL")
TO_EMAIL = os.environ.get("TO_EMAIL")

# === 狀態追蹤（每支股票獨立）===
notified = {symbol: False for symbol in STOCKS}

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

# === 技術指標取得 ===
def get_ta_data(symbol):
    try:
        df = yf.download(symbol, period="60d", interval="1d", progress=False)
        if df.empty or "Close" not in df.columns:
            print(f">>> 抓取 {symbol} 資料失敗")
            return None

        df.dropna(inplace=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df["Close"]

        current_price = close.iloc[-1]

        stoch = StochasticOscillator(high=df["High"], low=df["Low"], close=close, window=9, smooth_window=9)
        k = stoch.stoch().iloc[-1]
        d = stoch.stoch_signal().iloc[-1]

        macd = MACD(close=close)
        macd_diff = macd.macd().iloc[-1] - macd.macd_signal().iloc[-1]

        return current_price, k, d, macd_diff
    except Exception as e:
        print(f">>> 計算 {symbol} 指標錯誤：{e}")
        return None

# === 監控邏輯 ===
def watch_stock():
    global notified

    tz = pytz.timezone("Asia/Taipei")
    now = datetime.now(tz)
    if now.weekday() >= 5 or not (9 <= now.hour < 14):
        print(f">>> 非開盤時間（{now.strftime('%Y-%m-%d %H:%M:%S')}），略過")
        return
    print(f">>> 開始檢查股票（{now.strftime('%Y-%m-%d %H:%M:%S')}）")
    watch_all_stock()
        

def watch_all_stock():
    for symbol, name in STOCKS.items():
        print(f">>> 正在檢查：{name}（{symbol}）")
        data = get_ta_data(symbol)
        if data is None:
            print(f">>> 無法取得 {name} 資料")
            continue

        current_price, k, d, macd_diff = data
        print(f">>> {name}：股價 {current_price:.2f}, K: {k:.2f}, D: {d:.2f}, MACD差值: {macd_diff:.4f}")

        if k < 30 and macd_diff < 0:
            if not notified[symbol]:
                send_email(
                    f"【{name} 警示】KD<30 且 MACD差值<0",
                    f"{name}（{symbol}）\n股價: {current_price:.2f}\nK: {k:.2f}, D: {d:.2f}, MACD差值: {macd_diff:.4f}"
                )
                notified[symbol] = True
        else:
            notified[symbol] = False

# === 主程式 ===
if __name__ == "__main__":
    print(">>> 系統啟動中...")
    watch_stock()
