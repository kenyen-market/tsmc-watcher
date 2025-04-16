import yfinance as yf
import time
import threading
import os
from flask import Flask
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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
def watch_stock():
    print(">>> 開始執行 watch_stock()")
    try:
        df = yf.download(STOCK_SYMBOL, period="30d", interval="1d", progress=False)
        if df.empty or "Close" not in df.columns:
            print(">>> 資料抓取失敗或缺少欄位")
            return None

        current_price = (df["Close"].iloc[-1]).item()
        ma20 = df["Close"].rolling(window=20).mean().iloc[-1].item()

        if pd.isna(ma20):
            print(">>> MA20 資料不足")
            return None

        ma20 = float(ma20)
        return current_price, ma20
    except Exception as e:
        print(f">>> 取得資料錯誤：{e}")
        return None
# === 狀態紀錄 ===
is_below_ma = False
notified_below = False
notified_5_down = False
notified_10_down = False
below_price = 0

# === 監控邏輯 ===
def watch_stock():
    global is_below_ma, notified_below, notified_5_down, notified_10_down, below_price
    while True:
        try:
            result = get_price_data()
            if not result:
                print(">>> 股價資料抓取失敗，略過")
                time.sleep(CHECK_INTERVAL)
                continue

            current_price, ma20 = result
            print(f">>> 現價：{current_price:.2f} / MA20：{ma20:.2f}")

            if current_price < ma20:
                if not is_below_ma:
                    is_below_ma = True
                    below_price = current_price
                    notified_below = False
                    notified_5_down = False
                    notified_10_down = False
                    print(f">>> 首次跌破 MA20，紀錄起跌價格：{below_price:.2f}")

                drop_pct = (below_price - current_price) / below_price * 100
                print(f">>> 跌幅：{drop_pct:.2f}%")

                if not notified_below:
                    send_email("【TSMC 警示】跌破 20 日均線", f"目前股價 {current_price:.2f}，已跌破均線 {ma20:.2f}")
                    notified_below = True

                if drop_pct >= 5 and not notified_5_down:
                    send_email("【TSMC 警示】跌破後再跌 5%", f"股價已跌至 {current_price:.2f}，下跌 {drop_pct:.2f}%")
                    notified_5_down = True

                if drop_pct >= 10 and not notified_10_down:
                    send_email("【TSMC 警示】跌破後再跌 10%", f"股價已跌至 {current_price:.2f}，下跌 {drop_pct:.2f}%")
                    notified_10_down = True

            else:
                # 如果價格回到 MA20 以上，重置狀態
                print(">>> 現價回到 MA20 以上，重置狀態")
                is_below_ma = False
                notified_below = False
                notified_5_down = False
                notified_10_down = False
                below_price = 0

        except Exception as e:
            print(f">>> [ERROR] 在監控過程中發生錯誤：{e}")

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

    # 啟動監控背景執行緒
    threading.Thread(target=watch_stock, daemon=True).start()

    # 啟動 Flask Web Server
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
