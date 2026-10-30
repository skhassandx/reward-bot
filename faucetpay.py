"""FaucetPay মাইক্রো-পেআউট — API কল।
FaucetPay-তে একাউন্ট বানিয়ে Merchant API key নিন:
https://faucetpay.io/page/api
"""
import aiohttp


async def send(token: str, address: str, amount: float, api_key: str) -> dict:
    """টোকেন পাঠায়। সফল হলে {'status': 200, ...} ফেরত দেয়।"""
    url = "https://faucetpay.io/api/v1/send"
    data = {
        "api_key": api_key,
        "amount": round(amount, 8),
        "to": address,
        "currency": token.upper(),
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as resp:
            return await resp.json()


async def get_balance(api_key: str) -> dict:
    url = "https://faucetpay.io/api/v1/balance"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data={"api_key": api_key}) as resp:
            return await resp.json()


async def exchange_rates():
    """USD রেট CoinGecko থেকে — টোকেন ↔ USD রূপান্তরের জন্য।"""
    ids = {
        "BTC": "bitcoin", "ETH": "ethereum", "USDT": "tether",
        "LTC": "litecoin", "TRX": "tron", "DOGE": "dogecoin",
        "TON": "the-open-network", "SOL": "solana",
    }
    url = ("https://api.coingecko.com/api/v3/simple/price"
           "?ids=" + ",".join(ids.values()) + "&vs_currencies=usd")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                data = await resp.json()
        rates = {sym: float(data[cid]["usd"]) for sym, cid in ids.items()
                 if cid in data}
        return rates or _fallback()
    except Exception:
        return _fallback()


def _fallback():
    # CoinGecko না পেলে কাছাকাছি স্ট্যাটিক রেট (শুধু ব্যাকআপ)
    return {"BTC": 100000, "ETH": 3500, "USDT": 1, "LTC": 90,
            "TRX": 0.25, "DOGE": 0.1, "TON": 5, "SOL": 150}
