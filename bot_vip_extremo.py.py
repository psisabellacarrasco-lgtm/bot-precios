import os, time, re, sqlite3, requests
from bs4 import BeautifulSoup
from telegram import Bot
from datetime import datetime

# === CONFIGURACIÓN PERSONAL ===
TOKEN = os.environ.get("TOKEN", "8485073316:AAHKSizEFYtoc1CHkgIl-OEqZSPsw6iahdg")
CHAT_ID = int(os.environ.get("CHAT_ID", 1800215109))
CHECK_INTERVAL = 300   # cada 5 min
MIN_DISCOUNT = 90
URL = "https://www.ofertasshark.cl/offers?page=1"
TIENDAS = ["Falabella", "Ripley", "Paris", "Entel", "Movistar", "Lider"]

# === DB PARA NO REPETIR OFERTAS ===
conn = sqlite3.connect("seen.db")
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY)")
conn.commit()

bot = Bot(token=TOKEN)

def fetch():
    r = requests.get(URL, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
    r.raise_for_status()
    return r.text

def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    offers = []
    for item in soup.select(".offer-card, .offer, .card-offer, a.card"):
        try:
            title = item.get_text(" ", strip=True)
            link = item.get("href") or (item.select_one("a")["href"] if item.select_one("a") else None)
            url = "https://www.ofertasshark.cl" + link if link else None
            disc = None
            m = re.search(r"(\d+)%", item.get_text())
            if m: disc = int(m.group(1))
            tienda = next((t for t in TIENDAS if t.lower() in item.get_text().lower()), None)
            if url and title and disc and tienda:
                offers.append({"title": title, "url": url, "discount": disc, "tienda": tienda})
        except: pass
    return offers

def already_seen(oid):
    cur.execute("SELECT 1 FROM seen WHERE id=?", (oid,))
    return cur.fetchone() is not None

def mark_seen(oid):
    cur.execute("INSERT OR IGNORE INTO seen (id) VALUES (?)", (oid,))
    conn.commit()

def run_once():
    html = fetch()
    offers = parse(html)
    sent = 0
    for o in offers:
        if o["discount"] >= MIN_DISCOUNT:
            oid = str(hash(o["url"]))
            if not already_seen(oid):
                msg = f"🔥 {o['discount']}% OFF\n{o['title']}\nTienda: {o['tienda']}\n{o['url']}"
                bot.send_message(chat_id=CHAT_ID, text=msg)
                mark_seen(oid)
                sent += 1
    print(f"{datetime.now()} - enviadas {sent} nuevas ofertas.")

if __name__ == "__main__":
    while True:
        try:
            run_once()
        except Exception as e:
            print("Error:", e)
        time.sleep(CHECK_INTERVAL)
