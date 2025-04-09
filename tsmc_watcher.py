import os

# Set environment variables
os.environ["EMAIL_SENDER"] = "your_email@gmail.com"  # Replace with your email
os.environ["EMAIL_PASSWORD"] = "your_email_password"  # Replace with your email password
os.environ["EMAIL_RECEIVER"] = "recipient_email@example.com"  # Replace with the recipient's email


import yfinance as yf
import pandas as pd
import schedule
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, time as dt_time

EMAIL_SENDER = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_RECEIVER = os.environ["EMAIL_RECEIVER"]

# ... (Rest of your code)
import yfinance as yf
import pandas as pd
import schedule
import time
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, time as dt_time

EMAIL_SENDER = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_RECEIVER = os.environ["EMAIL_RECEIVER"]

has_broken_sma20 = False
has_dropped_5_percent = False
break_price = None

def is_market_open():
    now = datetime.now().time()
    return dt_time(9, 0) <= now <= dt_time(13, 30)

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("✅ Email 已寄出")
    except Exception as e:
        print(f"❌ Email 發送失敗: {e}")

def check_tsmc():
    global has_broken_sma20, break_price, has_dropped_5_percent

    if not is_market_open():
        print("⏳ 非開盤時間，跳過")
        return

    df = yf.Ticker("2330.TW").history(period="2mo", interval="1d")
    df["SMA20"] = df["Close"].rolling(window=20).mean()
    if df.shape[0] < 20:
        print("⚠️ 資料不足")
        return

    close = df["Close"].iloc[-1]
    sma20 = df["SMA20"].iloc[-1]
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 收盤: {close:.2f}, SMA20: {sma20:.2f}")

    if close < sma20:
        if not has_broken_sma20:
            has_broken_sma20 = True
            break_price = close
            has_dropped_5_percent = False
            send_email("⚠️ 跌破20日均線", f"台積電收盤 {close:.2f} 跌破均線 {sma20:.2f}")
        else:
            drop_percent = (break_price - close) / break_price
            if drop_percent >= 0.05 and not has_dropped_5_percent:
                has_dropped_5_percent = True
                send_email("⚠️ 跌破後再跌5%", f"從 {break_price:.2f} 跌至 {close:.2f}，超過5%")
    else:
        if has_broken_sma20:
            print("✅ 回到均線上，重置狀態")
        has_broken_sma20 = False
        has_dropped_5_percent = False
        break_price = None

schedule.every(5).minutes.do(check_tsmc)

print("⏱️ 開始監控台積電")
while True:
    schedule.run_pending()
    time.sleep(30)
    import threading
import time
from flask import Flask

# 啟動 Flask 讓 Render 偵測到 port 開啟
app = Flask(__name__)

@app.route('/')
def home():
    return "TSMC Watcher is running."

def run_web():
    app.run(host='0.0.0.0', port=10000)

# 在背景執行 Flask
threading.Thread(target=run_web).start()
