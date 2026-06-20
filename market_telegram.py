import yfinance as yf
import requests
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

TOKEN = "8698745900:AAGZewCYxXRMxWU4uQEQtbEP20oYuEkcRYA"
CHAT_ID = "7580899579"

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
            return {"nome": nome, "preco": None, "variacao": None}
        return {"nome": nome, "preco": atual, "variacao": var_pct}
    except:
        return {"nome": nome, "preco": None, "variacao": None}

def buscar_cambio():
    try:
        url = "https://economia.awesomeapi.com.br/json/last/USD-BRL,EUR-BRL"
        data = requests.get(url, timeout=10).json()
        return (float(data["USDBRL"]["bid"]), float(data["USDBRL"]["pctChange"]),
                float(data["EURBRL"]["bid"]), float(data["EURBRL"]["pctChange"]))
    except:
        return None, None, None, None

def buscar_selic():
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        return f"{float(requests.get(url, timeout=10).json()[0]['valor']):.2f}%"
    except:
        return "N/A"

def montar_mensagem():
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    L = [f"📊 RESUMO DE MERCADO", f"🕐 {agora}", ""]

    L.append("🇧🇷 BRASIL (B3)")
    for tk, nm in [("^BVSP","Ibovespa"),("PETR4.SA","Petrobras PN"),("VALE3.SA","Vale ON"),
                   ("ITUB4.SA","Itaú PN"),("BBDC4.SA","Bradesco PN"),("ABEV3.SA","Ambev"),("WEGE3.SA","WEG")]:
        d = buscar_dado(tk, nm)
        p = f"R$ {d['preco']:,.2f}" if d["preco"] else "N/A"
        L.append(f"  {nm}: {p}  {formatar_variacao(d['variacao'])}")

    L.append("\n💵 CÂMBIO")
    usd, uv, eur, ev = buscar_cambio()
    if usd:
        L.append(f"  USD/BRL: R$ {usd:.4f}  {formatar_variacao(uv)}")
        L.append(f"  EUR/BRL: R$ {eur:.4f}  {formatar_variacao(ev)}")

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

    L.append("\n📈 JUROS & MACRO")
    for tk, nm in [("^TNX","Treasury 10Y"),("^IRX","Treasury 3M"),("^TYX","Treasury 30Y")]:
        d = buscar_dado(tk, nm)
        p = f"{d['preco']:.2f}%" if d["preco"] else "N/A"
        L.append(f"  {nm}: {p}  {formatar_variacao(d['variacao'])}")
    L.append(f"  SELIC: {buscar_selic()} a.a.")

    L.append("\n💳 CRÉDITO PRIVADO")
    for tk, nm in [("HYG","High Yield EUA"),("LQD","Grau Invest. EUA"),("EMB","Mercados Emergentes")]:
        d = buscar_dado(tk, nm)
        p = f"US$ {d['preco']:.2f}" if d["preco"] else "N/A"
        L.append(f"  {nm}: {p}  {formatar_variacao(d['variacao'])}")

    L.append("\nFonte: Yahoo Finance & Banco Central")
    return "\n".join(L)

def enviar():
    msg = montar_mensagem()
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    resp = requests.post(url, json={"chat_id": CHAT_ID, "text": msg})
    if resp.status_code == 200:
        print("✅ Enviado!")
    else:
        print(f"Erro: {resp.text}")

if __name__ == "__main__":
    enviar()
