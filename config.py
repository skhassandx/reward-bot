"""
কনফিগারেশন — এখানে আপনার বটের সব সেটিংস।
.env ফাইল বানিয়ে এগুলো সেট করবেন (নিচে .env.example দেখুন)।
"""
import os


class Config:
    # টেলিগ্রাম বট টোকেন (BotFather থেকে পাবেন)
    BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")

    # অ্যাডমিনের টেলিগ্রাম ইউজার আইডি (কমা দিয়ে একাধিক)
    ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "123456789").split(",")]

    DB_PATH = os.getenv("DB_PATH", "bot.db")

    # মিনিমাম উত্তোলন (USD-তে) — ফি বাদে যেন ইউজার লসে না পড়ে
    MIN_WITHDRAW_USD = float(os.getenv("MIN_WITHDRAW_USD", "1.0"))

    # রেফারেল কমিশন (%) — ইউজারের টাস্ক আয় থেকে
    REF_COMMISSION_PCT = float(os.getenv("REF_COMMISSION_PCT", "10"))

    # দৈনিক বোনাস (USD, মাইক্রো)
    DAILY_BONUS_USD = float(os.getenv("DAILY_BONUS_USD", "0.002"))

    # টাস্কের রিওয়ার্ড (USD) — অ্যাড নেটওয়ার্কের আপনার আয়ের 50-70% ইউজারকে দিন
    TASK_REWARD_AD_USD = float(os.getenv("TASK_REWARD_AD_USD", "0.001"))

    # টাস্ক কুলডাউন (সেকেন্ড) — স্প্যাম ঠেকাতে
    TASK_COOLDOWN_SEC = int(os.getenv("TASK_COOLDOWN_SEC", "600"))

    # FaucetPay পেআউট (ঐচ্ছিক — না থাকলে ম্যানুয়াল পেআউট)
    FAUCETPAY_API_KEY = os.getenv("FAUCETPAY_API_KEY", "")

    # সমর্থিত টোকেন (উত্তোলনের জন্য) — FaucetPay-এ যেগুলো আছে
    SUPPORTED_TOKENS = ["BTC", "ETH", "USDT", "LTC", "TRX", "DOGE", "TON", "SOL"]
