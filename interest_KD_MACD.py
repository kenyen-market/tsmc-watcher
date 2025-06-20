import yfinance as yf
import pandas as pd
from ta.momentum import StochasticOscillator
from ta.trend import MACD
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
import pytz

def is_check_time():
    tz = pytz.timezone("Asia/Taipei")
    now = datetime.now(tz)
    hour = now.hour
    minute = now.minute

    # 只在 10:00 與 13:00 當下執行
    return (hour == 10 and minute == 0) or (hour == 13 and minute == 0)

# === 設定 ===
STOCKS = {
    "2330.TW": "台積電",
    "2891.TW": "中信金",
    "1216.tw": "統一",
    "2327.tw": "國巨",
    "00878.TW": "國泰永續高股息",
    "00919.tw": "群益台灣精選高息"
}

# === 狀態追蹤（每支股票獨立）===
notified = {symbol: False for symbol in STOCKS}

# === 寄 Email ===
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASS = os.environ.get("GMAIL_PASS")
TO_EMAIL = os.environ.get("TO_EMAIL")

def send_email(subject, content):
    try:
        msg = EmailMessage()
        msg.set_content(content)
        msg["Subject"] = subject
        msg["From"] = GMAIL_USER
        msg["To"] = TO_EMAIL

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASS)
            smtp.send_message(msg)
        print(f">>> Email sent: {subject}")
    except Exception as e:
        print(f">>> Email failed: {e}")
def calculate_kd(df, n=9):
    df = df.copy()
    df['lowest_low'] = df['Low'].rolling(window=n).min()
    df['highest_high'] = df['High'].rolling(window=n).max()
    df['RSV'] = (df['Close'] - df['lowest_low']) / (df['highest_high'] - df['lowest_low']) * 100

    # 初始 K 與 D 值為 50
    k_list = [50]
    d_list = [50]

    for rsv in df['RSV']:
        if pd.isna(rsv):
            k_prev = k_list[-1]
            d_prev = d_list[-1]
            continue
        k = 2/3 * k_prev + 1/3 * rsv
        d = 2/3 * d_prev + 1/3 * k
        k_list.append(k)
        d_list.append(d)

    df = df.copy()
    df['K'] = pd.Series(k_list, index=df.index[-len(k_list):])
    df['D'] = pd.Series(d_list, index=df.index[-len(d_list):])
    return df

# === 技術指標取得 ===
def get_ta_data(symbol):
    try:
        df = yf.download(symbol, period="90d", interval="1d", progress=False)
        if df.empty or "Close" not in df.columns:
            print(f">>> 抓取 {symbol} 資料失敗")
            return None

        df.dropna(inplace=True)
        if len(df) < 30:  # 根據你用的技術指標所需天數調整
            print(f">>> 資料量不足，只有 {len(df)} 筆")
            return None
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]

        current_price = close.iloc[-1]
        
        df["Close"] = close
        df = calculate_kd(df)
        k = df["K"].iloc[-1]
        d = df["D"].iloc[-1]
        if pd.isna(k) or pd.isna(d):
            print(">>> 最新一筆 K 或 D 是 NaN，略過")
            return None
        
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
    if now.weekday() >= 5:
        print(">>> 週末不執行，略過")
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

        if k < 30 and d < 30 and macd_diff < 0:
            if not notified[symbol]:
                send_email(
                    f" 嗨，這是自動提醒系統："
                    f"【{name} 警示】KD<30 且 MACD差值<0",
                    f"{name}（{symbol}）\n股價: {current_price:.2f}\nK: {k:.2f}, D: {d:.2f}, MACD差值: {macd_diff:.4f}"
                    f" 請留意市場波動。 "
                )
                notified[symbol] = True
        else:
            notified[symbol] = False

# === 主程式 ===
if __name__ == "__main__":
    print(">>> 系統啟動中...")
    watch_stock()
