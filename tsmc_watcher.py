import yfinance as yf
import time
import threading
import os
from flask import Flask
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import pandas as pd

app = Flask(__name__)

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
        if df.empty or "Close" not in df.columns:
            print(">>> 資料抓取失敗或缺少欄位")
            return None

        current_price = df["Close"].iloc[-1].item()
        ma20 = df["Close"].rolling(window=20).mean().iloc[-1]
        if pd.isna(ma20):
            print(">>> MA20 資料不足")
            return None

        return current_price, ma20.item()
    except Exception as e:
        print(f">>> 取得資料錯誤：{e}")
        return None

# === 監控邏輯 ===
def watch_stock():
    global is_below_ma, notified_below, notified_5_down, notified_10_down, below_price
    print(">>> 執行 watch_stock() 執行緒中...")

    while True:
        try:
            local_time = time.localtime()
            weekday = local_time.tm_wday  # 0=Monday, 6=Sunday
            hour = local_time.tm_hour
            minute = local_time.tm_min

            if 0 <= weekday <= 4 and (9 <= hour <= 12 or (hour == 13 and minute <= 30)):
                print(">>> 台股開盤時間內，開始檢查股價")
                result = get_price_data()
                if not result:
                    print(">>> 股價資料取得失敗；略過")
                    time.sleep(CHECK_INTERVAL)
                    continue
    current_price, ma20 = result
    print(f">>> 現在股價：{current_price:.2f}，MA20：{ma20:.2f}")
            else:
                print(">>> 非開盤時間，略過檢查")
                time.sleep(CHECK_INTERVAL)
                continue

            current_price, ma20 = result
            print(f">>> 現價：{current_price:.2f} / MA20：{ma20:.2f}")

            # 這裡接下來的判斷通知邏輯...

            # 後續邏輯繼續寫在這裡...
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
            print(f">>> 在監控過程中發生錯誤：{e}")

        time.sleep(CHECK_INTERVAL)

# === Flask 路由 ===
@app.route("/")
def home():
    return "TSMC Watcher is running."

# === 主程式 ===
if __name__ == "__main__":
    print(">>> 系統啟動中...")
    send_email("TSMC Watcher 啟動成功", "監控系統已啟動，將每 5 分鐘檢查台積電股價。")

    # 啟動監控背景執行緒
    print(">>> 嘗試啟動 watch_stock 執行緒...")
    threading.Thread(target=watch_stock, daemon=True).start()

    # 啟動 Flask Web Server
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
