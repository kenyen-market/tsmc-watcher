from flask import Flask
import os
import sendgrid
from sendgrid.helpers.mail import Mail

app = Flask(__name__)

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
FROM_EMAIL = os.environ.get("FROM_EMAIL")      # 你的 gmail
TO_EMAIL = os.environ.get("TO_EMAIL")          # 要通知的收件人

@app.route("/")
def home():
    return "TSMC Watcher Service is running."

@app.route("/notify")
def notify():
    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAIL,
        subject="TSMC Watcher 啟動成功",
        html_content="<strong>你的 Web Service 已啟動，可以開始追蹤台積電啦！</strong>"
    )
    try:
        sg.send(message)
        return "Notification sent!"
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    app.run()
