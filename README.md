# 🪙 RewardBot — টেলিগ্রাম অ্যাড-রিওয়ার্ড বট

ইউজার টাস্ক/বিজ্ঞাপন দেখে আয় করবে, আর ব্যালান্স **যেকোনো সমর্থিত টোকেনে**
(BTC, ETH, USDT, LTC, TRX, DOGE, TON, SOL) উত্তোলন করতে পারবে।

> ⚠️ সৎ নোট: এটা "মাইনিং" না — এটা অ্যাড/টাস্ক রিওয়ার্ড ফকেট।
> ইউজারের আয় ছোট হবে ($0.001–0.01/দিন) — এটাই রিয়ালিস্টিক।

## 📁 ফাইলসমূহ
- `config.py` — সব সেটিংস
- `db.py` — ডেটাবেজ (SQLite)
- `faucetpay.py` — পেআউট API + রেট
- `bot.py` — মেইন বট লজিক
- `requirements.txt` — প্যাকেজ লিস্ট

## 🚀 সেটআপ (৫ মিনিট)

1. **BotFather** থেকে বট বানান → টোকেন কপি করুন
2. আপনার টেলিগ্রাম user ID জানুন (@userinfobot)
3. `.env` ফাইল বানান (`.env.example` দেখুন):
   ```
   BOT_TOKEN=123:abc
   ADMIN_IDS=123456789
   FAUCETPAY_API_KEY=your_key
   ```
4. ডিপেন্ডেন্সি: `pip install -r requirements.txt`
5. চালান: `python bot.py`

## 💸 অ্যাড ইন্টিগ্রেশন
বটে এখন placeholder টাস্ক আছে। রিয়েল অ্যাডের জন্য:
- **AdsGram** (Mini App হলে rewarded video) — USDT on TON-এ পেআউট
- **CPX Research Offerwall** — বটেই সার্ভে/অফার ওয়াল চলে
- **Shortlink** (HilltopAds DirectLink) — বটের জন্য সবচেয়ে সহজ

`bot.py`-এর `show_ad_task` ফাংশনে আপনার অ্যাড URL/API বসান।

## 🛡️ ফি সতর্কতা
মাইক্রো উত্তোলনে চেইন ফি সব খেয়ে ফেলতে পারে। তাই:
- মিনিমাম উত্তোলন $1+ রাখুন
- FaucetPay ব্যবহার করুন (ফি নেগ্লিজিবল)
