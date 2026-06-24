from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import json, os, re
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import asyncio

# ========== پورت ساختگی برای Render ==========
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_dummy():
    try:
        HTTPServer(('0.0.0.0', 10000), DummyHandler).serve_forever()
    except: pass

Thread(target=run_dummy, daemon=True).start()

# ========== تنظیمات ==========
TOKEN = "8846132875:AAF9n8bTYMF_xOKgJcXbgjdHRPkACyNvWyY"
ADMIN_ID = 6106477309
CHANNEL_ID = -1004298773614
DATA_FILE = "bot_data.json"
MAX_WARNINGS = 5
app = None

# ========== دیتابیس ==========
def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "warnings": {}, "banned": [], "last_statement": {}}

def save():
    with open(DATA_FILE, "w") as f:
        json.dump({"users": users, "warnings": warnings, "banned": banned, "last_statement": last_statement}, f, ensure_ascii=False, indent=2)

data = load()
users = data.get("users", {})
warnings = data.get("warnings", {})
banned = data.get("banned", [])
last_statement = data.get("last_statement", {})

def get_user_country(uid):
    return users.get(str(uid))

def get_warnings(uid):
    return warnings.get(str(uid), 0)

def is_admin(uid):
    return uid == ADMIN_ID

def is_banned(uid):
    return int(uid) in banned

# ========== دستورات ادمین ==========
async def set_country(update, context):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ شما اجازه این کار را ندارید.")
    
    try:
        args = context.args
        if len(args) < 2:
            return await update.message.reply_text("فرمت: /set [user_id] [نام کشور]")
        
        uid = args[0]
        country = " ".join(args[1:])
        users[uid] = country
        warnings[str(uid)] = 0
        last_statement[str(uid)] = datetime.now().isoformat()
        save()
        await update.message.reply_text(f"✅ کاربر {uid} با کشور {country} ثبت شد.")
        try:
            await app.bot.send_message(int(uid), f"✅ شما به عنوان {country} ثبت شدید.")
        except:
            pass
    except:
        await update.message.reply_text("خطا! فرمت: /set [user_id] [نام کشور]")

async def remove_user(update, context):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ شما اجازه این کار را ندارید.")
    
    try:
        uid = context.args[0]
        if uid not in users:
            return await update.message.reply_text(f"کاربر {uid} ثبت نشده.")
        del users[uid]
        if str(uid) in warnings:
            del warnings[str(uid)]
        if str(uid) in last_statement:
            del last_statement[str(uid)]
        if int(uid) in banned:
            banned.remove(int(uid))
        save()
        await update.message.reply_text(f"✅ کاربر {uid} حذف شد.")
        try:
            await app.bot.send_message(int(uid), "❌ شما از ربات حذف شدید.")
        except:
            pass
    except:
        await update.message.reply_text("فرمت: /remove [user_id]")

async def warn_user(update, context):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ شما اجازه این کار را ندارید.")
    
    try:
        uid = str(context.args[0])
        if uid not in users:
            return await update.message.reply_text(f"کاربر {uid} ثبت نشده.")
        
        warnings[uid] = get_warnings(uid) + 1
        save()
        await update.message.reply_text(f"⚠️ کاربر {uid} اخطار گرفت. (تعداد اخطار: {warnings[uid]}/{MAX_WARNINGS})")
        try:
            await app.bot.send_message(int(uid), f"⚠️ شما یک اخطار دریافت کردید. (تعداد اخطار: {warnings[uid]}/{MAX_WARNINGS})")
        except:
            pass
    except:
        await update.message.reply_text("فرمت: /warn [user_id]")

async def list_users(update, context):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ شما اجازه این کار را ندارید.")
    if not users:
        return await update.message.reply_text("هیچ کاربری ثبت نشده.")
    msg = "📋 لیست کاربران:\n\n"
    for uid, country in users.items():
        warn_count = get_warnings(uid)
        ban_status = "🔴 بن" if is_banned(int(uid)) else "🟢 فعال"
        last = "ندارد"
        if str(uid) in last_statement:
            last_date = datetime.fromisoformat(last_statement[str(uid)])
            if (datetime.now() - last_date).days >= 1:
                last = "⚠️ بیش از ۱ روز"
            else:
                last = "✅ امروز"
        msg += f"🆔 {uid} → {country} (اخطار: {warn_count}/{MAX_WARNINGS}) {ban_status} | آخرین: {last}\n"
    await update.message.reply_text(msg)

# ========== بن و آنبن ==========
async def ban_user(update, context):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ شما اجازه این کار را ندارید.")
    
    try:
        uid = int(context.args[0])
        if uid in banned:
            return await update.message.reply_text(f"کاربر {uid} قبلاً بن شده.")
        banned.append(uid)
        save()
        await update.message.reply_text(f"✅ کاربر {uid} بن شد.")
        try:
            await app.bot.send_message(uid, "⛔ شما توسط ادمین بن شدید.")
        except:
            pass
    except:
        await update.message.reply_text("فرمت: /ban [user_id]")

async def unban_user(update, context):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ شما اجازه این کار را ندارید.")
    
    try:
        uid = int(context.args[0])
        if uid not in banned:
            return await update.message.reply_text(f"کاربر {uid} بن نیست.")
        banned.remove(uid)
        save()
        await update.message.reply_text(f"✅ بن کاربر {uid} برداشته شد.")
        try:
            await app.bot.send_message(uid, "✅ بن شما توسط ادمین برداشته شد.")
        except:
            pass
    except:
        await update.message.reply_text("فرمت: /unban [user_id]")

# ========== بررسی فعالیت روزانه ==========
async def check_daily_activity():
    try:
        now = datetime.now()
        for uid, country in users.items():
            if is_banned(int(uid)):
                continue
            if str(uid) in last_statement:
                last_date = datetime.fromisoformat(last_statement[str(uid)])
                if (now - last_date).days >= 1:
                    await app.bot.send_message(
                        ADMIN_ID,
                        f"⚠️ کاربر {uid} ({country}) بیش از ۱ روز بیانیه نفرستاده است."
                    )
                    try:
                        await app.bot.send_message(
                            int(uid),
                            f"⚠️ شما بیش از ۱ روز است که بیانیه نفرستاده‌اید. لطفاً فعالیت کنید."
                        )
                    except:
                        pass
    except Exception as e:
        print(f"خطا در بررسی فعالیت: {e}")

async def scheduled_check():
    while True:
        await asyncio.sleep(3600)
        await check_daily_activity()

# ========== خوش‌آمدگویی ==========
async def start(update, context):
    uid = str(update.effective_user.id)
    
    if is_banned(int(uid)):
        return await update.message.reply_text("⛔ شما بن هستید و نمی‌توانید از ربات استفاده کنید.")
    
    country = get_user_country(uid)
    first_name = update.effective_user.first_name
    
    welcome_text = (
        f"🌟 **به ربات رسمی بیانیه‌ها خوش آمدید، {first_name}!** 🌟\n\n"
        f"🇺🇳 این ربات برای ارسال بیانیه‌های رسمی مقامات کشورها طراحی شده است.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📜 **قوانین و مقررات:**\n\n"
        f"1️⃣ **بیانیه‌ها باید رسمی و محترمانه باشند.**\n"
        f"2️⃣ **از فحش و توهین جدا خودداری کنید.**\n"
        f"   • پس از {MAX_WARNINGS} اخطار، از ربات حذف می‌شوید.\n"
        f"3️⃣ **عکس بیانیه باید از رئیس‌جمهور یا مقام رسمی کشور باشد.**\n"
        f"4️⃣ **بیانیه باید حداقل ۵ خط یا ۵ جمله باشد.**\n"
        f"5️⃣ **عکس و متن باید مرتبط باشند.**\n"
        f"6️⃣ **حداقل روزانه ۱ بیانیه ارسال کنید.**\n"
        f"   • در غیر این صورت اخطار دریافت می‌کنید.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 **نحوه ارسال بیانیه:**\n"
        f"• یک عکس از رئیس‌جمهور انتخاب کنید.\n"
        f"• در بخش کپشن، متن بیانیه را بنویسید.\n"
        f"• حداقل ۵ خط یا ۵ جمله بنویسید.\n"
        f"• ارسال کنید.\n"
    )
    
    if country:
        welcome_text += (
            f"\n━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌍 **کشور شما:** {country}\n"
            f"✅ شما به عنوان مقام این کشور ثبت شده‌اید.\n"
            f"📊 تعداد اخطارها: {get_warnings(uid)}/{MAX_WARNINGS}\n"
        )
    else:
        welcome_text += (
            f"\n━━━━━━━━━━━━━━━━━━━━━\n"
            f"❌ **شما هنوز ثبت نام نکرده‌اید.**\n"
            f"لطفاً با ادمین تماس بگیرید.\n"
        )
    
    await update.message.reply_text(welcome_text, parse_mode="HTML")

# ========== دریافت بیانیه ==========
async def handle_statement(update, context):
    uid = str(update.effective_user.id)
    
    if is_banned(int(uid)):
        return await update.message.reply_text("⛔ شما بن هستید.")
    
    country = get_user_country(uid)
    
    if not country:
        return await update.message.reply_text("❌ شما ثبت نیستید. لطفاً با ادمین تماس بگیرید.")
    
    if get_warnings(uid) >= MAX_WARNINGS:
        return await update.message.reply_text(f"⛔ شما {MAX_WARNINGS} اخطار دریافت کرده‌اید.")
    
    photo = update.message.photo[-1] if update.message.photo else None
    caption = update.message.caption or ""
    
    if not photo:
        await update.message.reply_text("❌ لطفاً یک عکس از رئیس‌جمهور همراه با متن ارسال کنید.")
        return
    
    if not caption:
        await update.message.reply_text("❌ لطفاً متن بیانیه را در کپشن عکس بنویسید.")
        return
    
    lines_enter = [line for line in caption.split('\n') if line.strip()]
    sentences = re.split(r'[.؟!]\s*', caption)
    sentences = [s for s in sentences if len(s.strip()) > 5]
    line_count = max(len(lines_enter), len(sentences))
    
    if line_count < 5:
        await update.message.reply_text(
            f"❌ بیانیه باید حداقل **۵ خط** یا **۵ جمله** داشته باشد.\n"
            f"تعداد خطوط: {len(lines_enter)}\n"
            f"تعداد جملات: {len(sentences)}\n"
            f"لطفاً دوباره تلاش کنید."
        )
        return
    
    last_statement[uid] = datetime.now().isoformat()
    save()
    
    photo_file = await photo.get_file()
    path = f"statement_{uid}.jpg"
    await photo_file.download_to_drive(path)
    
    # ========== فرمت نهایی با فونت هر دو کلمه ==========
    header = (
        f"<b>【 𝐑𝐞𝐮𝐭𝐞𝐫𝐬 | 𝗢𝗳𝗳𝗶𝗰𝗶𝗮𝗹 𝗡𝗲𝘄𝘀 】</b>\n\n"
        f"<b>📢- بیانیه رسمی مقام کشور {country}</b>\n\n"
        f"{caption}"
    )
    
    try:
        await app.bot.send_photo(
            CHANNEL_ID,
            photo=open(path, "rb"),
            caption=header,
            parse_mode="HTML"
        )
        
        await update.message.reply_text(
            f"✅ بیانیه شما با موفقیت در کانال منتشر شد!\n"
            f"🌍 کشور: {country}\n"
            f"📊 تعداد خطوط/جملات: {line_count}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال به کانال: {e}")
    
    try:
        os.remove(path)
    except:
        pass

# ========== راه‌اندازی ==========
def main():
    global app
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("set", set_country))
    app.add_handler(CommandHandler("remove", remove_user))
    app.add_handler(CommandHandler("warn", warn_user))
    app.add_handler(CommandHandler("list_users", list_users))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_statement))
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(scheduled_check())
    
    print("✅ ربات بیانیه با فونت دقیق روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
