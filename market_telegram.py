import requests
import yfinance as yf
from datetime import datetime
import pytz
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings("ignore")

TOKEN = "8698745900:AAGZewCYxXRMxWU4uQEQtbEP20oYuEkcRYA"
CHAT_ID = "7580899579"

def horario_brasilia():
    tz = pytz.timezone("America/Sao_Paulo")
    return datetime.now(tz)

def formatar_variacao(val):
    if val is None:
        return "N/A"
    sinal = "🟢" if val >= 0 else "🔴"
    return f"{sinal} {val:+.2f}%"

def buscar_dado(ticker, nome):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d", interval="1d")
        if len(hist) >= 2:
            anterior = float(hist["Close"].iloc[-2])
            atual = float(hist["Close"].iloc[-1])
            var_pct = ((atual - anterior) / anterior) * 100
        elif len(hist) == 1:
            atual = float(hist["Close"].iloc[-1])
            var_pct = None
        else:
            return {"preco": None, "variacao": None}
        return {"preco": atual, "variacao": var_pct}
    except:
        return {"preco": None, "variacao": None}

def buscar_cambio():
    try:
        url = "https://economia.awesomeapi.com.br/json/last/USD-BRL,EUR-BRL,GBP-BRL"
        data = requests.get(url, timeout=10).json()
        return {
            "usd": float(data["USDBRL"]["bid"]), "usd_var": float(data["USDBRL"]["pctChange"]),
            "eur": float(data["EURBRL"]["bid"]), "eur_var": float(data["EURBRL"]["pctChange"]),
            "gbp": float(data["GBPBRL"]["bid"]), "gbp_var": float(data["GBPBRL"]["pctChange"]),
        }
    except:
        return None

def buscar_selic():
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        return f"{float(requests.get(url, timeout=10).json()[0]['valor']):.2f}%"
    except:
        return "N/A"

def buscar_di_futuro():
    resultado = {}
    contratos = [
        ("DI1F28", "DI Jan/2028"),
        ("DI1F30", "DI Jan/2030"),
        ("DI1F32", "DI Jan/2032"),
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for codigo, nome in contratos:
        try:
            url = f"https://br.advfn.com/bolsa-de-valores/bmf/{codigo}/cotacao"
            resp = requests.get(url, timeout=10, headers=headers)
            soup = BeautifulSoup(resp.text, "html.parser")
            preco = None
            for tag in soup.find_all(["span", "div", "td"]):
                texto = tag.get_text(strip=True).replace(",", ".")
                try:
                    val = float(texto)
                    if 8 < val < 25:
                        preco = val
                        break
                except:
                    continue
            resultado[nome] = f"{preco:.3f}% a.a." if preco else "N/A"
        except:
            resultado[nome] = "N/A"
    return resultado

def buscar_tesouro():
    resultado = {}
    try:
        url = "https://www.anbima.com.br/pt_br/informar/taxas-de-titulos-publicos.htm"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, timeout=15, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 3:
                nome = cols[0].get_text(strip=True)
                taxa = cols[2].get_text(strip=True)
                if "NTN-B" in nome and taxa:
                    resultado[nome] = taxa
    except:
        pass
    if not resultado:
        try:
            url = "https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/model/dto/TesouroDiretoDTO.json"
            headers = {"User-Agent": "Mozilla/5.0"}
            data = requests.get(url, timeout=10, headers=headers).json()
            titulos = data["response"]["TrsrBdTradgList"]
            for t in titulos:
                nome = t["TrsrBd"]["nm"]
                taxa = t["TrsrBd"]["anulInvstmtRate"]
                venc = t["TrsrBd"]["mtrtyDt"][:10]
                if "IPCA+" in nome:
                    resultado[f"NTN-B {venc}"] = f"{taxa:.2f}%"
        except:
            pass
    return resultado

def buscar_rss(url, fonte, max_items=4):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, timeout=10, headers=headers)
        root = ET.fromstring(resp.content)
        itens = []
        for item in root.findall(".//item")[:max_items]:
            titulo = item.findtext("title", "").strip()
            if titulo and "[Removed]" not in titulo:
                itens.append({"titulo": titulo, "fonte": fonte})
        return itens
    except:
        return []

def buscar_noticias(periodo):
    todas = []
    feeds = [
        ("https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "NYT Business"),
        ("https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml", "NYT Tech"),
        ("https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml", "NYT Economy"),
        ("https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml", "NYT Politics"),
        ("https://feeds.bbci.co.uk/news/business/rss.xml", "BBC Business"),
        ("https://feeds.bbci.co.uk/news/technology/rss.xml", "BBC Tech"),
        ("https://braziljournal.com/feed/", "Brazil Journal"),
        ("https://apnews.com/rss/business", "AP Business"),
        ("https://apnews.com/rss/technology", "AP Tech"),
    ]
    for url, fonte in feeds:
        itens = buscar_rss(url, fonte, max_items=6)
        todas.extend(itens)

    offset = {"manha": 0, "tarde": 8, "noite": 16}.get(periodo, 0)
    unicas = []
    vistos = set()
    for n in todas:
        if n["titulo"] not in vistos:
            vistos.add(n["titulo"])
            unicas.append(n)
    return unicas[offset:offset+8]

def montar_mensagem():
    agora = horario_brasilia()
    hora = agora.hour
    data_str = agora.strftime("%d/%m/%Y %H:%M")

    if hora < 12:
        periodo = "manha"
        periodo_label = "🌅 BOM DIA"
    elif hora < 17:
        periodo = "tarde"
        periodo_label = "☀️ BOA TARDE"
    else:
        periodo = "noite"
        periodo_label = "🌙 BOA NOITE"

    L = [f"📊 {periodo_label} — RESUMO DE MERCADO", f"🕐 {data_str} (Brasília)", ""]

    L.append("🇧🇷 BRASIL (B3)")
    for tk, nm in [("^BVSP","Ibovespa"),("PETR4.SA","Petrobras PN"),("VALE3.SA","Vale ON"),
                   ("ITUB4.SA","Itaú PN"),("BBDC4.SA","Bradesco PN"),("ABEV3.SA","Ambev"),("WEGE3.SA","WEG")]:
        d = buscar_dado(tk, nm)
        p = f"R$ {d['preco']:,.2f}" if d["preco"] else "N/A"
        L.append(f"  {nm}: {p}  {formatar_variacao(d['variacao'])}")

    L.append("\n💵 CÂMBIO")
    c = buscar_cambio()
    if c:
        L.append(f"  USD/BRL: R$ {c['usd']:.4f}  {formatar_variacao(c['usd_var'])}")
        L.append(f"  EUR/BRL: R$ {c['eur']:.4f}  {formatar_variacao(c['eur_var'])}")
        L.append(f"  GBP/BRL: R$ {c['gbp']:.4f}  {formatar_variacao(c['gbp_var'])}")

    L.append("\n₿ CRIPTOMOEDAS")
    for tk, nm in [("BTC-USD","Bitcoin"),("ETH-USD","Ethereum"),("SOL-USD","Solana")]:
        d = buscar_dado(tk, nm)
        p = f"US$ {d['preco']:,.2f}" if d["preco"] else "N/A"
        L.append(f"  {nm}: {p}  {formatar_variacao(d['variacao'])}")

    L.append("\n🌍 AÇÕES GLOBAIS / TECH / AI")
    for tk, nm in [("^GSPC","S&P 500"),("^NDX","Nasdaq 100"),("^DJI","Dow Jones"),
                   ("AAPL","Apple"),("MSFT","Microsoft"),("NVDA","Nvidia"),
                   ("GOOGL","Alphabet"),("META","Meta"),("AMZN","Amazon"),
                   ("TSLA","Tesla"),("PLTR","Palantir"),("AI","C3.ai")]:
        d = buscar_dado(tk, nm)
        p = f"US$ {d['preco']:,.2f}" if d["preco"] else "N/A"
        L.append(f"  {nm}: {p}  {formatar_variacao(d['variacao'])}")

    L.append("\n🛢️ COMMODITIES")
    for tk, nm in [("CL=F","Petróleo WTI"),("GC=F","Ouro"),("SI=F","Prata"),
                   ("ZC=F","Milho"),("ZS=F","Soja"),("NG=F","Gás Natural")]:
        d = buscar_dado(tk, nm)
        p = f"US$ {d['preco']:,.2f}" if d["preco"] else "N/A"
        L.append(f"  {nm}: {p}  {formatar_variacao(d['variacao'])}")

    L.append("\n📈 JUROS GLOBAIS & MACRO")
    for tk, nm in [("^TNX","Treasury 10Y (EUA)"),("^IRX","Treasury 3M (EUA)"),("^TYX","Treasury 30Y (EUA)")]:
        d = buscar_dado(tk, nm)
        p = f"{d['preco']:.2f}%" if d["preco"] else "N/A"
        L.append(f"  {nm}: {p}  {formatar_variacao(d['variacao'])}")
    L.append(f"  SELIC: {buscar_selic()} a.a.")

    L.append("\n📉 DI FUTURO (B3)")
    for nome, taxa in buscar_di_futuro().items():
        L.append(f"  {nome}: {taxa}")

    L.append("\n🏦 TESOURO DIRETO (NTN-B / IPCA+)")
    td = buscar_tesouro()
    if td:
        for nome, taxa in list(td.items())[:5]:
            L.append(f"  {nome}: {taxa}")
    else:
        L.append("  Dados indisponíveis no momento")

    L.append("\n💳 CRÉDITO PRIVADO (ETFs)")
    for tk, nm in [("HYG","High Yield EUA"),("LQD","Grau Invest. EUA"),("EMB","Mercados Emergentes")]:
        d = buscar_dado(tk, nm)
        p = f"US$ {d['preco']:.2f}" if d["preco"] else "N/A"
        L.append(f"  {nm}: {p}  {formatar_variacao(d['variacao'])}")

    L.append("\n📰 MANCHETES DO MOMENTO")
    noticias = buscar_noticias(periodo)
    if noticias:
        for n in noticias:
            L.append(f"  • [{n['fonte']}] {n['titulo']}")
    else:
        L.append("  Noticias indisponíveis no momento")

    L.append("\nFonte: Yahoo Finance, Banco Central, ANBIMA, ADVFN & RSS")
    return "\n".join(L)

def enviar():
    print(f"Coletando dados...")
    msg = montar_mensagem()
    if len(msg) > 4096:
        partes = [msg[i:i+4096] for i in range(0, len(msg), 4096)]
    else:
        partes = [msg]
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    for parte in partes:
        resp = requests.post(url, json={"chat_id": CHAT_ID, "text": parte})
        if resp.status_code == 200:
            print("✅ Enviado!")
        else:
            print(f"Erro: {resp.text}")

if __name__ == "__main__":
    enviar()
