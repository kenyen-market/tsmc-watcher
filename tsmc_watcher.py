import yfinance as yf
import time
import threading
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import pandas as pd
from datetime import datetime
import pytz
# === 設定區 ===
STOCK_SYMBOL = "2330.TW"
CHECK_INTERVAL = 300  # 每 5 分鐘
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
FROM_EMAIL = os.environ.get("FROM_EMAIL")
TO_EMAIL = os.environ.get("TO_EMAIL")

# === 狀態紀錄 ===
is_below_ma = False
notified_below = False
notified_5_down = False
notified_10_down = False
below_price = 0

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
        response = sg.send(message)
        print(f">>> Email sent: {subject}")
    except Exception as e:
        print(f">>> Failed to send email: {e}")

# === 取得台積電股價與 20 日均線 ===
def get_price_data():
    try:
        df = yf.download(STOCK_SYMBOL, period="30d", interval="1d", progress=False)
        df_today = yf.download(STOCK_SYMBOL, period="1d", interval="1m", progress=False)
        if df_today.empty:
            print(">>> 今天無分鐘級股價資料，可能為休市日")
            return None
        if df.empty or ("Close" not in df.columns):
            print(">>> 資料抓取失敗或缺少欄位")
            return None
            current_price = df["Close"].iloc[-1].item()
            ma20 = df["Close"].rolling(window=20).mean().iloc[-1].item()
        if pd.isna(ma20):
            print(">>> MA20 資料不足")
            return None

        return float(current_price), float(ma20)
    except Exception as e:
        print(f">>> 取得資料錯誤：{e}")
        return None

# === 監控邏輯 ===
def watch_stock():
    global is_below_ma, notified_below, notified_5_down, notified_10_down, below_price

    try:
        tz = pytz.timezone("Asia/Taipei")
        local_time = datetime.now(tz)
        weekday = local_time.weekday()
        hour = local_time.hour
        minute = local_time.minute

        print(">>> 當前時間（台灣時區）：", local_time.strftime("%Y-%m-%d %H:%M:%S"))

        is_trading_time = (
            0 <= weekday <= 4 and
            (
                (hour == 9 and minute >= 0) or
                (10 <= hour < 13) or
                (hour == 13 and minute <= 30)
            )
        )
        if not is_trading_time:
            print(">>> 非台股開盤時間，略過檢查")
            return

        print(">>> 已在開盤時間，開始檢查股價")

        result = get_price_data()
        if not result:
            print(">>> 股價資料取得失敗；略過")
            return

        current_price, ma20 = result
        print(f">>> 現在價格: {current_price:.2f}，MA20: {ma20:.2f}")

        if current_price < ma20:
            if not is_below_ma:
                is_below_ma = True
                below_price = current_price
                notified_below = False
                notified_5_down = False
                notified_10_down = False

            if not notified_below:
                send_email("【TSMC 警示】跌破 20 日均線", f"目前股價 {current_price:.2f}，已跌破均線 {ma20:.2f}")
                notified_below = True

            drop_pct = (below_price - current_price) / below_price * 100

            if drop_pct >= 5 and not notified_5_down:
                send_email("【TSMC 警示】跌破後再跌 5%", f"股價已跌至 {current_price:.2f}，下跌 {drop_pct:.2f}%")
                notified_5_down = True

            if drop_pct >= 10 and not notified_10_down:
                send_email("【TSMC 警示】跌破後再跌 10%", f"股價已跌至 {current_price:.2f}，下跌 {drop_pct:.2f}%")
                notified_10_down = True
        else:
            is_below_ma = False
            notified_below = False
            notified_5_down = False
            notified_10_down = False
            below_price = 0

    except Exception as e:
        print(f">>> 發生錯誤：{e}")

        time.sleep(CHECK_INTERVAL)

# === 主程式 ===
if __name__ == "__main__":
    print(">>> 系統啟動中...")
    watch_stock()
