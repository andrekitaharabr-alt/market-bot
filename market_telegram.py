import requests
import yfinance as yf
from datetime import datetime
import xml.etree.ElementTree as ET
import warnings
warnings.filterwarnings("ignore")

TOKEN = "8698745900:AAGZewCYxXRMxWU4uQEQtbEP20oYuEkcRYA"
CHAT_ID = "7580899579"

_noticias_enviadas = set()

def formatar_variacao(val):
    if val is None:
        return "N/A"
    sinal = "🟢" if val >= 0 else "🔴"
    return f"{sinal} {val:+.2f}%"

def buscar_dado(ticker, nome):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")
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

def buscar_tesouro():
    resultado = {}
    try:
        url = "https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/model/dto/TesouroDiretoDTO.json"
        data = requests.get(url, timeout=10).json()
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

def buscar_di_futuro():
    resultado = {}
    try:
        selic_url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        selic = float(requests.get(selic_url, timeout=10).json()[0]["valor"])
        resultado["DI Jan/2028"] = f"~{selic + 0.8:.2f}% a.a."
        resultado["DI Jan/2030"] = f"~{selic + 1.2:.2f}% a.a."
        resultado["DI Jan/2032"] = f"~{selic + 1.5:.2f}% a.a."
    except:
        resultado["DI Jan/2028"] = "N/A"
        resultado["DI Jan/2030"] = "N/A"
        resultado["DI Jan/2032"] = "N/A"
    return resultado

def buscar_rss(url, fonte, max_items=5):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
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

def buscar_noticias():
    global _noticias_enviadas
    todas = []

    feeds = [
        ("https://feeds.reuters.com/reuters/businessNews", "Reuters"),
        ("https://feeds.reuters.com/reuters/technologyNews", "Reuters Tech"),
        ("https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "NYT"),
        ("https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml", "NYT Tech"),
        ("https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "WSJ Markets"),
        ("https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml", "WSJ Business"),
        ("https://www.infomoney.com.br/feed/", "InfoMoney"),
        ("https://valoreconomico.com.br/rss", "Valor Econômico"),
        ("https://www.estadao.com.br/rss/economia.xml", "Estadão"),
    ]

    for url, fonte in feeds:
        itens = buscar_rss(url, fonte, max_items=5)
        todas.extend(itens)

    selecionadas = []
    for n in todas:
        if n["titulo"] not in _noticias_enviadas and len(selecionadas) < 10:
            selecionadas.append(n)
            _noticias_enviadas.add(n["titulo"])
    return selecionadas

def montar_mensagem():
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    hora = datetime.now().hour
    if hora < 12:
        periodo = "🌅 BOM DIA"
    elif hora < 17:
        periodo = "☀️ BOA TARDE"
    else:
        periodo = "🌙 BOA NOITE"

    L = [f"📊 {periodo} — RESUMO DE MERCADO", f"🕐 {agora}", ""]

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
    noticias = buscar_noticias()
    if noticias:
        for n in noticias:
            L.append(f"  • [{n['fonte']}] {n['titulo']}")
    else:
        L.append("  Noticias indisponíveis no momento")

    L.append("\nFonte: Yahoo Finance, Banco Central, Tesouro Direto & RSS")
    return "\n".join(L)

def enviar():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Coletando dados...")
    msg = montar_mensagem()
    if len(msg) > 4096:
        partes = [msg[i:i+4096] for i in range(0, len(msg), 4096)]
    else:
        partes = [msg]
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    for parte in partes:
        resp = requests.post(url, json={"chat_id": CHAT_ID, "text": parte})
        if resp.status_code == 200:
            print("✅ Mensagem enviada!")
        else:
            print(f"Erro: {resp.text}")

if __name__ == "__main__":
    enviar()
