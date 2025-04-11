import yfinance as yf
import pandas as pd
import schedule
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr
from flask import Flask
import threading
import os

# === 設定區 ===
STOCK_SYMBOL = "2330.TW"
CHECK_INTERVAL = 300  # 每 5 分鐘檢查一次
GMAIL_USER = "你的Gmail帳號@gmail.com"
GMAIL_PASSWORD = "應用程式密碼"
TO_EMAIL = "你要接收通知的Email"

# === 狀態紀錄 ===
last_below_ma = False
last_alert_5_percent = False
drop_start_price = None

# === 發送 Email 通知 ===
def send_email(subject, body):
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER  # 用最簡單格式避免編碼錯誤
    msg["To"] = TO_EMAIL
    msg["Subject"] = subject  # 先不轉編碼

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.send_message(msg)
        print(f"已發送 Email：{subject}")
    except Exception as e:
        print(f"Email 發送失敗：{e}")

# === 檢查股價 ===
def check_tsmc_price():
    global last_below_ma, last_alert_5_percent, drop_start_price

    try:
        df = yf.download(STOCK_SYMBOL, period="30d", interval="1d")
        df["MA20"] = df["Close"].rolling(window=20).mean()

        current_price = df["Close"].iloc[-1]
        current_ma20 = df["MA20"].iloc[-1]

        print(f"目前股價：{current_price}，20日均線：{current_ma20}")

        if current_price < current_ma20:
            if not last_below_ma:
                send_email("【台積電提醒】跌破20日均線", f"目前股價：{current_price}，已跌破20日均線：{current_ma20}")
                last_below_ma = True
                drop_start_price = current_price
                last_alert_5_percent = False
            elif drop_start_price and current_price < drop_start_price * 0.95 and not last_alert_5_percent:
                send_email("【台積電警示】跌破20日均線後再跌5%以上", f"目前股價：{current_price}，自跌破價：{drop_start_price}")
                last_alert_5_percent = True
        else:
            last_below_ma = False
            last_alert_5_percent = False
            drop_start_price = None

    except Exception as e:
        print(f"檢查時出錯：{e}")

# === 排程每 5 分鐘執行一次 ===
schedule.every(CHECK_INTERVAL).seconds.do(check_tsmc_price)

# === 啟動 Flask 偽 Web Server 讓 Render 不報錯 ===
app = Flask(__name__)

@app.route('/')
def home():
    return "TSMC watcher is running."

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# === 主程式 ===
if __name__ == "__main__":
    send_email("Test", "This is a test email.")
# 寄送啟動通知 Email
    send_email("TSMC Watcher 啟動通知", "監控系統已成功啟動，將每 5 分鐘檢查一次台積電股價。")
# 啟動 Flask 背景執行
    threading.Thread(target=run_web).start()
# 持續執行排程任務
    while True:
        schedule.run_pending()
        time.sleep(60)
