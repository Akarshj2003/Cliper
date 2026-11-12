import urllib.request
import json

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/ingest/url",
    data=json.dumps({"url": "https://youtu.be/ijCrXHI1g2k?si=MVm2xAPFixER1ALW"}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req) as response:
        print("STATUS:", response.status)
        print("BODY:", response.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code)
    print("BODY:", e.read().decode("utf-8"))
