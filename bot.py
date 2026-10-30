"""RewardBot — টেলিগ্রাম অ্যাড-রিওয়ার্ড বট (aiogram 3.x)
ইউজার টাস্ক করে আয় করে, যেকোনো সমর্থিত টোকেনে উত্তোলন করে।
"""
import asyncio
import time
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, \
    InlineKeyboardMarkup, InlineKeyboardButton

from config import Config
import db
import faucetpay

router = Router()
TOKENS = Config.SUPPORTED_TOKENS


# ---------- FSM স্টেট ----------
class Withdraw(StatesGroup):
    token = State()
    address = State()
    amount = State()


# ---------- হেল্পার ----------
def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 টাস্ক করুন", callback_data="tasks"),
         InlineKeyboardButton(text="💰 ব্যালান্স", callback_data="balance")],
        [InlineKeyboardButton(text="💸 উত্তোলন", callback_data="withdraw"),
         InlineKeyboardButton(text="👥 রেফারেল", callback_data="ref")],
    ])


def tasks_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 দৈনিক বোনাস", callback_data="task_daily")],
        [InlineKeyboardButton(text="📺 বিজ্ঞাপন দেখুন", callback_data="task_ad")],
        [InlineKeyboardButton(text="🔗 লিংক ভিজিট", callback_data="task_link")],
        [InlineKeyboardButton(text="⬅️ ফিরে যান", callback_data="main")],
    ])


async def credit_with_referral(user_id: int, usd: float):
    """ইউজারকে ক্রেডিট + রেফারারকে কমিশন।"""
    await db.credit(user_id, usd)
    ref = await db.get_ref_by(user_id)
    if ref:
        await db.credit(ref, usd * Config.REF_COMMISSION_PCT / 100)


# ---------- /start ----------
@router.message(CommandStart())
async def cmd_start(m: Message):
    ref_by = 0
    if m.text and len(m.text.split()) > 1:
        try:
            ref_by = int(m.text.split()[1])
            if ref_by == m.from_user.id:
                ref_by = 0
        except ValueError:
            pass
    await db.add_user(m.from_user.id, ref_by)
    await m.answer(
        "🪙 <b>RewardBot</b>-এ স্বাগতম!\n\n"
        "📋 টাস্ক করে আয় করুন\n"
        "💸 BTC, ETH, USDT, LTC, TRX, DOGE, TON, SOL-এ উত্তোলন\n"
        "👥 বন্ধুদের রেফার করে ১০% কমিশন\n\n"
        "নিচের মেনু থেকে শুরু করুন 👇",
        parse_mode="HTML", reply_markup=main_menu())


@router.callback_query(F.data == "main")
async def back_main(c: CallbackQuery):
    await c.message.edit_text("মেইন মেনু 👇", reply_markup=main_menu())


# ---------- ব্যালান্স ----------
@router.callback_query(F.data == "balance")
@router.message(Command("balance"))
async def show_balance(event):
    user_id = event.from_user.id
    bal = await db.get_balance(user_id)
    text = (f"💰 আপনার ব্যালান্স: <b>${bal:.6f}</b>\n"
            f"মিনিমাম উত্তোলন: ${Config.MIN_WITHDRAW_USD}")
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML",
                                      reply_markup=main_menu())
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


# ---------- রেফারেল ----------
@router.callback_query(F.data == "ref")
@router.message(Command("ref"))
async def show_ref(event):
    user_id = event.from_user.id
    count = await db.get_ref_count(user_id)
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={user_id}"
    text = (f"👥 আপনার রেফারেল লিংক:\n<code>{link}</code>\n\n"
            f"মোট রেফারেল: {count} জন\n"
            f"প্রতিটি টাস্ক আয় থেকে {Config.REF_COMMISSION_PCT}% কমিশন")
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML",
                                      reply_markup=main_menu())
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


# ---------- টাস্ক মেনু ----------
@router.callback_query(F.data == "tasks")
async def open_tasks(c: CallbackQuery):
    await c.message.edit_text("📋 টাস্ক বেছে নিন:", reply_markup=tasks_menu())
    await c.answer()


@router.callback_query(F.data == "task_daily")
async def task_daily(c: CallbackQuery):
    last = await db.last_task_ts(c.from_user.id, "daily")
    if time.time() - last < 86400:
        left = int(86400 - (time.time() - last))
        await c.answer(f"⏳ আবার {left//3600}ঘ {left%3600//60}মি পরে আসুন",
                       show_alert=True)
        return
    await db.log_task(c.from_user.id, "daily", Config.DAILY_BONUS_USD)
    await credit_with_referral(c.from_user.id, Config.DAILY_BONUS_USD)
    await c.answer(f"🎁 দৈনিক বোনাস ${Config.DAILY_BONUS_USD} জমা হয়েছে!",
                   show_alert=True)
    await show_balance(c)


@router.callback_query(F.data == "task_ad")
async def task_ad(c: CallbackQuery):
    last = await db.last_task_ts(c.from_user.id, "ad")
    if time.time() - last < Config.TASK_COOLDOWN_SEC:
        left = int(Config.TASK_COOLDOWN_SEC - (time.time() - last))
        await c.answer(f"⏳ {left//60} মিনিট পরে আবার চেষ্টা করুন",
                       show_alert=True)
        return
    # 🔧 এখানে আপনার অ্যাড নেটওয়ার্কের রিয়েল ইন্টিগ্রেশন বসাবেন:
    # AdsGram Mini App SDK / CPX offerwall / shortlink ইত্যাদি।
    url = "https://example.com/your-ad"   # ← আপনার অ্যাড লিংক দিন
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📺 বিজ্ঞাপন দেখুন (৩০ সেকেন্ড)", url=url)],
        [InlineKeyboardButton(text="✅ দেখা শেষ", callback_data="ad_done")]])
    await c.message.edit_text(
        "📺 নিচের বিজ্ঞাপনটি দেখুন, তারপর 'দেখা শেষ' চাপুন।",
        reply_markup=kb)
    await c.answer()


@router.callback_query(F.data == "ad_done")
async def ad_done(c: CallbackQuery):
    last = await db.last_task_ts(c.from_user.id, "ad")
    if time.time() - last < Config.TASK_COOLDOWN_SEC:
        await c.answer("⚠️ ভুয়া নিশ্চিতকরণ ধরা পড়েছে!", show_alert=True)
        return
    await db.log_task(c.from_user.id, "ad", Config.TASK_REWARD_AD_USD)
    await credit_with_referral(c.from_user.id, Config.TASK_REWARD_AD_USD)
    await c.answer(f"✅ +${Config.TASK_REWARD_AD_USD} জমা হয়েছে!", show_alert=True)
    await c.message.edit_text("📋 টাস্ক বেছে নিন:", reply_markup=tasks_menu())


@router.callback_query(F.data == "task_link")
async def task_link(c: CallbackQuery):
    last = await db.last_task_ts(c.from_user.id, "link")
    if time.time() - last < Config.TASK_COOLDOWN_SEC:
        left = int(Config.TASK_COOLDOWN_SEC - (time.time() - last))
        await c.answer(f"⏳ {left//60} মিনিট পরে আসুন", show_alert=True)
        return
    url = "https://example.com/shortlink"  # ← HilltopAds DirectLink বসান
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 লিংকে যান", url=url)],
        [InlineKeyboardButton(text="✅ ভিজিট সম্পন্ন", callback_data="link_done")]])
    await c.message.edit_text("🔗 লিংকে গিয়ে ১৫ সেকেন্ড থাকুন:", reply_markup=kb)
    await c.answer()


@router.callback_query(F.data == "link_done")
async def link_done(c: CallbackQuery):
    await db.log_task(c.from_user.id, "link", Config.TASK_REWARD_AD_USD)
    await credit_with_referral(c.from_user.id, Config.TASK_REWARD_AD_USD)
    await c.answer(f"✅ +${Config.TASK_REWARD_AD_USD} জমা হয়েছে!", show_alert=True)
    await c.message.edit_text("📋 টাস্ক বেছে নিন:", reply_markup=tasks_menu())


# ---------- উত্তোলন (FSM) ----------
@router.callback_query(F.data == "withdraw")
async def wd_start(c: CallbackQuery, state: FSMContext):
    bal = await db.get_balance(c.from_user.id)
    if bal < Config.MIN_WITHDRAW_USD:
        await c.answer(
            f"❌ মিনিমাম ${Config.MIN_WITHDRAW_USD} লাগবে। "
            f"আপনার ব্যালান্স ${bal:.6f}", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=f"wdtok_{t}")
         for t in TOKENS[i:i+4]]
        for i in range(0, len(TOKENS), 4)])
    await state.set_state(Withdraw.token)
    await c.message.edit_text("কোন টোকেনে নিতে চান?", reply_markup=kb)
    await c.answer()


@router.callback_query(Withdraw.token, F.data.startswith("wdtok_"))
async def wd_token(c: CallbackQuery, state: FSMContext):
    await state.update_data(token=c.data.split("_")[1])
    await state.set_state(Withdraw.address)
    await c.message.edit_text("আপনার ওয়ালেট ঠিকানা পাঠান:")
    await c.answer()


@router.message(Withdraw.address)
async def wd_address(m: Message, state: FSMContext):
    await state.update_data(address=m.text.strip())
    await state.set_state(Withdraw.amount)
    bal = await db.get_balance(m.from_user.id)
    rates = await faucetpay.exchange_rates()
    await state.update_data(rates=rates)
    data = await state.get_data()
    tok = data["token"]
    per = rates.get(tok, 0)
    await m.answer(
        f"💰 ব্যালান্স: ${bal:.6f}\n"
        f"📈 ১ {tok} = ${per:.4f}\n"
        f"কত {tok} চান? (সংখ্যায় লিখুন, যেমন 0.0001)")


@router.message(Withdraw.amount)
async def wd_amount(m: Message, state: FSMContext):
    try:
        amt = float(m.text.strip())
        assert amt > 0
    except (ValueError, AssertionError):
        await m.answer("❌ সঠিক সংখ্যা লিখুন।")
        return
    data = await state.get_data()
    rates = data.get("rates", {})
    usd_val = amt * rates.get(data["token"], 0)
    bal = await db.get_balance(m.from_user.id)
    if usd_val > bal:
        await m.answer(f"❌ পর্যাপ্ত ব্যালান্স নেই (দরকার ${usd_val:.6f}, "
                       f"আছে ${bal:.6f})")
        return
    if usd_val < Config.MIN_WITHDRAW_USD:
        await m.answer(f"❌ মিনিমাম ${Config.MIN_WITHDRAW_USD} লাগবে "
                       f"(এই লেনদেন ${usd_val:.6f})")
        return
    wid = await db.create_withdrawal(m.from_user.id, data["token"],
                                     data["address"], amt)
    await db.deduct_balance(m.from_user.id, usd_val)
    await state.clear()
    await m.answer(
        f"✅ উত্তোলনের অনুরোধ গৃহীত হয়েছে!\n\n"
        f"ID: <code>#{wid}</code>\nটোকেন: {data['token']}\nপরিমাণ: {amt}\n"
        f"মূল্য: ${usd_val:.6f}\n\n"
        "অ্যাডমিন অনুমোদনের পর ২৪-৪৮ ঘণ্টার মধ্যে পেমেন্ট হবে।",
        parse_mode="HTML", reply_markup=main_menu())
    for aid in Config.ADMIN_IDS:
        try:
            await bot.send_message(
                aid,
                f"🆕 নতুন উত্তোলন #{wid}\nইউজার: {m.from_user.id}\n"
                f"{amt} {data['token']} → <code>{data['address']}</code>\n"
                f"/approve_{wid} /reject_{wid}", parse_mode="HTML")
        except Exception:
            pass


# ---------- অ্যাডমিন ----------
@router.message(Command("stats"))
async def admin_stats(m: Message):
    if m.from_user.id not in Config.ADMIN_IDS:
        return
    users, bal, paid = await db.stats()
    await m.answer(f"📊 স্ট্যাটস\nইউজার: {users}\nমোট ব্যালান্স: ${bal:.4f}\n"
                   f"পেইড: ${paid:.4f}")


@router.message(Command("pending"))
async def admin_pending(m: Message):
    if m.from_user.id not in Config.ADMIN_IDS:
        return
    rows = await db.get_pending_withdrawals()
    if not rows:
        await m.answer("কোনো pending উত্তোলন নেই।")
        return
    for wid, uid, tok, addr, amt in rows:
        await m.answer(f"#{wid} | user:{uid} | {amt} {tok}\n<code>{addr}</code>\n"
                       f"/approve_{wid} /reject_{wid}", parse_mode="HTML")


@router.message(F.text.startswith("/approve_"))
async def admin_approve(m: Message):
    if m.from_user.id not in Config.ADMIN_IDS:
        return
    wid = int(m.text.split("_")[1])
    import aiosqlite
    async with aiosqlite.connect(Config.DB_PATH) as con:
        cur = await con.execute(
            "SELECT user_id, token, address, amount FROM withdrawals WHERE id=?",
            (wid,))
        row = await cur.fetchone()
    if not row:
        await m.answer("পাওয়া যায়নি।")
        return
    uid, tok, addr, amt = row
    if Config.FAUCETPAY_API_KEY:
        res = await faucetpay.send(tok, addr, amt, Config.FAUCETPAY_API_KEY)
        if res.get("status") == 200:
            await db.set_withdrawal_status(wid, "paid")
            await m.answer(f"✅ #{wid} পেইড। Payout ID: {res.get('payout_id')}")
            await bot.send_message(uid, f"💸 আপনার {amt} {tok} পাঠানো হয়েছে!")
        else:
            await m.answer(f"❌ FaucetPay এরর: {res}")
    else:
        await m.answer("⚠️ FAUCETPAY_API_KEY সেট নেই — ম্যানুয়ালি পাঠিয়ে "
                       f"/paid_{wid} চাপুন।")


@router.message(F.text.startswith("/reject_"))
async def admin_reject(m: Message):
    if m.from_user.id not in Config.ADMIN_IDS:
        return
    wid = int(m.text.split("_")[1])
    import aiosqlite
    async with aiosqlite.connect(Config.DB_PATH) as con:
        cur = await con.execute(
            "SELECT user_id, token, amount FROM withdrawals WHERE id=?", (wid,))
        row = await cur.fetchone()
        await con.execute("UPDATE withdrawals SET status='rejected' WHERE id=?",
                          (wid,))
        await con.commit()
    if row:
        rates = await faucetpay.exchange_rates()
        usd_val = row[2] * rates.get(row[1], 0)
        await db.credit(row[0], usd_val)
        await bot.send_message(row[0], f"❌ উত্তোলন #{wid} বাতিল হয়েছে। "
                                       "ব্যালান্স ফেরত দেওয়া হয়েছে।")
    await m.answer(f"#{wid} rejected।")


@router.message(F.text.startswith("/paid_"))
async def admin_paid_manual(m: Message):
    if m.from_user.id not in Config.ADMIN_IDS:
        return
    wid = int(m.text.split("_")[1])
    await db.set_withdrawal_status(wid, "paid")
    await m.answer(f"#{wid} paid হিসেবে চিহ্নিত।")


@router.message(Command("addbal"))
async def admin_addbal(m: Message):
    if m.from_user.id not in Config.ADMIN_IDS:
        return
    try:
        _, uid, usd = m.text.split()
        await db.credit(int(uid), float(usd))
        await m.answer(f"✅ {uid}-কে ${usd} দেওয়া হয়েছে।")
    except ValueError:
        await m.answer("ব্যবহার: /addbal user_id amount")


# ---------- মেইন ----------
bot = Bot(token=Config.BOT_TOKEN)


async def run_health_server():
    """Koyeb/Render-এ বটকে healthy দেখানোর জন্য ছোট HTTP সার্ভার।"""
    import os
    from aiohttp import web

    async def health(request):
        return web.Response(text="RewardBot is running")

    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "8000"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Health server: port {port}")


async def main():
    await db.init_db()
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    me = await bot.get_me()
    print(f"✅ বট চলছে: @{me.username}")
    # পোলিং আর health server একসাথে চালানো
    await asyncio.gather(run_health_server(), dp.start_polling(bot))


if __name__ == "__main__":
    asyncio.run(main())
