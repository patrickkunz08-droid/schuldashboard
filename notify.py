"""Plant ntfy-Erinnerungen für Prüfungen (Zeitzone Europe/Zurich).

Läuft einmal täglich morgens (vor 07:00) und plant per ntfy-Verzögerung:
  - 07:00 heute      für Prüfungen von heute
  - 18:00 heute      für Prüfungen von morgen
Ohne NTFY_TOPIC wird nur ausgegeben (Trockenlauf).
"""
import json
import os
import re
import urllib.request
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Zurich")
EXAM_RE = re.compile(r"pr(ü|ue)fung|test|assessment|\bLK\b|klausur", re.I)
MORGEN_UM, VORTAG_UM = time(7, 0), time(18, 0)


def is_exam(e):
    return e.get("typ") == "pruefung" or (e.get("typ") != "normal" and EXAM_RE.search(e["titel"]))


def send(topic, title, message, when):
    body = {"topic": topic, "title": title, "message": message,
            "tags": ["warning"], "delay": str(int(when.timestamp()))}
    if not topic:
        print(f"[Trockenlauf] {when:%d.%m. %H:%M} | {title} | {message}")
        return
    req = urllib.request.Request("https://ntfy.sh", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=15).close()
    print(f"Geplant: {when:%d.%m. %H:%M} | {title}")


def main():
    now = datetime.now(TZ)
    today = now.date()
    topic = os.environ.get("NTFY_TOPIC", "")
    with open("termine.json", encoding="utf-8") as f:
        exams = [e for e in json.load(f) if is_exam(e)]

    jobs = [(today, MORGEN_UM, "Heute Prüfung"),
            (today + timedelta(days=1), VORTAG_UM, "Morgen Prüfung")]
    for day, at, title in jobs:
        # Bei Prüfungen von morgen: 18:00 heute; von heute: 07:00 heute
        when = datetime.combine(today, at, TZ)
        if when <= now + timedelta(seconds=30):  # ntfy braucht mind. 10 s Vorlauf
            continue
        for e in exams:
            if e["datum"] == day.isoformat():
                zeit = f" um {e['zeit']}" if e.get("zeit") else ""
                send(topic, f"{title}: {e['fach']}", f"{e['titel']}{zeit}", when)


if __name__ == "__main__":
    main()
