import requests
from pywebpush import webpush, WebPushException
from datetime import datetime

VAPID_PRIVATE_KEY = "DGezJqZaqCCVbYRljEmAfpMTnzR40hoBqJRlD-Z779A"
VAPID_CLAIMS = {"sub": "mailto:medazizlahmar@naxxum.fr"}

reminders = requests.get("https://apex.oracle.com/pls/apex/naxxum/reminders/").json()["items"]
now = datetime.utcnow()

for r in reminders:
    reminder_time = datetime.strptime(r["REMINDER_TIME"], "%Y-%m-%dT%H:%M:%S.%fZ")
    if r["STATUS"] == "active" and reminder_time <= now:
        subscription_info = {
            "endpoint": r["PUSH_ENDPOINT"],
            "keys": {"p256dh": r["PUSH_P256DH"], "auth": r["PUSH_AUTH"]}
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=f"Votre session live '{r['SESSION_ID']}' commence bientôt !",
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )
            requests.put(f"https://apex.oracle.com/pls/apex/naxxum/reminders/{r['ID']}", json={"STATUS": "sent"})
        except WebPushException as ex:
            print("Erreur WebPush:", ex)