from flask import Flask
import yfinance as yf
import time
import threading
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)

# 狀態紀錄
is_below_ma = False
notified_below = False
notified_5_down = False
below_price = 0

# 設定
STOCK_SYMBOL = '2330.TW'
CHECK_INTERVAL = 300  # 每 5 分鐘檢查一次
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
TO_EMAIL = '你自己的email@gmail.com'
FROM_EMAIL = '你自己的email@gmail.com'

def send_email(subject, content):
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAIL,
        subject=subject,
        plain_text_content=content
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f">>> Email sent: {subject}")
    except Exception as e:
        print(f">>> Failed to send email: {e}")

def get_price_data():
    df = yf.download(STOCK_SYMBOL, period="30d", interval="1d")
    if len(df) < 20:
        return None, None
def get_price_data():
df = yf.download(STOCK_SYMBOL, period="30d", interval="1d")
if df.empty or "Close" not in df.columns:
    return None, None
current_price = df["Close"].iloc[-1]
ma20 = df["Close"].rolling(window=20).mean().iloc[-1]  # ← 這裡加 .iloc[-1]
def watch_stock():
    global is_below_ma, notified_below, notified_5_down, below_price
    while True:
        current_price, ma20 = get_price_data()
        if current_price is None:
            print(">>> 無法取得股價資料")
        else:
            print(f">>> 價格: {current_price}, MA20: {ma20}")
            if current_price < ma20:
                if not is_below_ma:
                    is_below_ma = True
                    below_price = current_price
                    notified_below = False
                    notified_5_down = False

                if not notified_below:
                    send_email("TSMC 跌破 20 日均線", f"股價 {current_price} 跌破 20 日均線 {ma20}")
                    notified_below = True

                drop_percent = (below_price - current_price) / below_price * 100
                if drop_percent >= 5 and not notified_5_down:
                    send_email("TSMC 跌破後又下跌超過 5%", f"目前股價：{current_price}，自跌破以來下跌 {drop_percent:.2f}%")
                    notified_5_down = True
            else:
                is_below_ma = False
                notified_below = False
                notified_5_down = False
        time.sleep(CHECK_INTERVAL)

@app.route('/')
def home():
    return 'TSMC Watcher is running.'

if __name__ == '__main__':
    # 啟動時寄一次通知
    threading.Thread(target=watch_stock, daemon=True).start()
    send_email("TSMC Watcher 啟動", "你的 Render 監控程式已經啟動並開始監控 TSMC")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
