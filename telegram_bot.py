"""
SS EMPIRE - Telegram Payment Bot
Generates real UPI QR codes directly inside Telegram chat with instant payment detection.
"""

import io
import json
import os
import sys
import threading
import time
import qrcode
import requests
import telebot
from telebot import types

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


cfg = load_config()
GATEWAY_URL = os.environ.get('GATEWAY_URL') or cfg.get('gateway_url') or "https://ssempire-paymentgateway.vercel.app"
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN') or cfg.get('telegram_bot_token') or ""

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    print("=" * 65)
    print(" [!] TELEGRAM BOT TOKEN MISSING")
    print(" 1. Telegram par @BotFather ke paas jao aur /newbot banake token lo")
    print(" 2. Us token ko config.json mein 'telegram_bot_token' mein daal do")
    print("=" * 65)
    # Ask interactively if running in terminal
    try:
        user_input = input("Paste your Telegram Bot Token here (or press Enter to exit): ").strip()
        if user_input:
            BOT_TOKEN = user_input
            cfg['telegram_bot_token'] = BOT_TOKEN
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2)
            print("Token saved successfully in config.json!\n")
        else:
            sys.exit(1)
    except Exception:
        sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


def generate_qr_buffer(upi_string):
    """Generate high quality QR code as in-memory PNG buffer"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(upi_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "⚡ <b>Welcome to SS EMPIRE Payment Bot!</b>\n\n"
        "Aap kisi bhi amount ka instant UPI QR code yahi generate kar sakte hain.\n\n"
        "<b>Commands:</b>\n"
        "👉 <code>/pay &lt;amount&gt;</code> (Jaise: <code>/pay 50</code> ya <code>/pay 100</code>)\n"
        "👉 Ya fir direct koi bhi number bhejo (Jaise: <code>20</code>, <code>500</code>)\n\n"
        "Payment complete hote hi real Bank UTR automatically detect ho jayega!"
    )
    bot.reply_to(message, text)


@bot.message_handler(commands=['pay', 'qr', 'deposit'])
def handle_pay_command(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ <b>Amount enter karo!</b>\nExample: <code>/pay 50</code> ya <code>/pay 100</code>")
        return
    
    amount_str = parts[1].replace('₹', '').replace(',', '').strip()
    create_and_send_qr(message, amount_str)


@bot.message_handler(func=lambda msg: msg.text and msg.text.isdigit())
def handle_direct_number(message):
    create_and_send_qr(message, message.text.strip())


def create_and_send_qr(message, amount_str):
    try:
        amt = float(amount_str)
        if amt < 1:
            bot.reply_to(message, "❌ Minimum payment amount ₹1 hona chahiye.")
            return
        amt_formatted = f"{amt:.2f}"
    except ValueError:
        bot.reply_to(message, "❌ Invalid amount. Please enter a valid number (e.g. 50).")
        return

    cust_name = message.from_user.first_name or "Telegram User"
    loading_msg = bot.reply_to(message, f"⏳ Generating real UPI QR for <b>₹{amt_formatted}</b>...")

    # 1. Create order on local SS EMPIRE backend (which talks to TerminalX live)
    try:
        resp = requests.post(f"{GATEWAY_URL}/api/create-order", json={
            "amount": str(int(amt) if amt.is_integer() else amt),
            "customer_name": cust_name,
            "customer_mobile": "7579923536",
            "remark": f"TG_{message.from_user.id}"
        }, timeout=10)
        data = resp.json()
    except Exception as e:
        bot.edit_message_text(f"❌ Error connecting to payment gateway: {str(e)}", chat_id=message.chat.id, message_id=loading_msg.message_id)
        return

    if not data.get('success'):
        bot.edit_message_text(f"❌ Payment order creation failed: {data.get('message', 'Unknown error')}", chat_id=message.chat.id, message_id=loading_msg.message_id)
        return

    order_id = data.get('order_id')
    merchant_name = data.get('merchant_name', 'SS EMPIRE')
    upi_intent = data.get('upi_intent') or data.get('qr_data')

    # 2. Generate QR code in memory
    qr_buf = generate_qr_buffer(upi_intent)

    # 3. Create inline buttons
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_check = types.InlineKeyboardButton("🔄 Check Payment Status", callback_data=f"chk_{order_id}")
    markup.add(btn_check)

    caption = (
        f"⚡ <b>{merchant_name} — UPI PAYMENT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Amount to Pay:</b> ₹{amt_formatted}\n"
        f"🆔 <b>Order ID:</b> <code>{order_id}</code>\n"
        f"👤 <b>Payee:</b> {merchant_name} (<code>paytm.s3tuyo9@pty</code>)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📲 <b>Kese Pay Karein:</b>\n"
        f"1. Is QR Code ko apne <b>PhonePe, Paytm ya GPay</b> se scan karein.\n"
        f"2. Normal <b>Bank Savings Account</b> se pay karein.\n\n"
        f"⏳ <i>Awaiting payment confirmation...</i>"
    )

    try:
        bot.delete_message(chat_id=message.chat.id, message_id=loading_msg.message_id)
    except Exception:
        pass

    sent_photo = bot.send_photo(
        chat_id=message.chat.id,
        photo=qr_buf,
        caption=caption,
        reply_markup=markup
    )

    # 4. Start automatic background polling thread for this order
    threading.Thread(
        target=poll_order_status,
        args=(message.chat.id, sent_photo.message_id, order_id, amt_formatted, merchant_name),
        daemon=True
    ).start()


def poll_order_status(chat_id, message_id, order_id, amount_str, merchant_name):
    """Polls the gateway every 3 seconds for 3 minutes until paid"""
    start_time = time.time()
    while time.time() - start_time < 180:  # Poll for 3 minutes
        time.sleep(3)
        try:
            resp = requests.post(f"{GATEWAY_URL}/api/check-status", json={"order_id": order_id}, timeout=5)
            d = resp.json()
            if d.get('status') in ['SUCCESS', 'COMPLETED']:
                utr = d.get('utr') or 'VERIFIED'
                success_caption = (
                    f"✅ <b>PAYMENT SUCCESSFUL!</b> 🎉\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"💰 <b>Amount Paid:</b> ₹{amount_str}\n"
                    f"🆔 <b>Order ID:</b> <code>{order_id}</code>\n"
                    f"🏦 <b>Bank UTR:</b> <code>{utr}</code>\n"
                    f"👤 <b>Merchant:</b> {merchant_name}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"✨ <i>Payment verified directly with bank!</i>"
                )
                try:
                    bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=message_id,
                        caption=success_caption,
                        reply_markup=None
                    )
                    bot.send_message(
                        chat_id=chat_id,
                        text=f"🔔 <b>Payment Received!</b>\nOrder <code>{order_id}</code> (₹{amount_str}) has been confirmed. Bank UTR: <code>{utr}</code>"
                    )
                except Exception:
                    pass
                return
        except Exception:
            pass


@bot.callback_query_handler(func=lambda call: call.data.startswith('chk_'))
def handle_check_callback(call):
    order_id = call.data.replace('chk_', '')
    try:
        resp = requests.post(f"{GATEWAY_URL}/api/check-status", json={"order_id": order_id}, timeout=5)
        d = resp.json()
        if d.get('status') in ['SUCCESS', 'COMPLETED']:
            utr = d.get('utr') or 'VERIFIED'
            bot.answer_callback_query(call.id, "✅ Payment Verified!", show_alert=True)
            success_caption = (
                f"✅ <b>PAYMENT SUCCESSFUL!</b> 🎉\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>Amount Paid:</b> ₹{d.get('amount', '')}\n"
                f"🆔 <b>Order ID:</b> <code>{order_id}</code>\n"
                f"🏦 <b>Bank UTR:</b> <code>{utr}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✨ <i>Verified directly with Bank!</i>"
            )
            bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=success_caption, reply_markup=None)
        else:
            bot.answer_callback_query(call.id, "⏳ Payment not detected yet. Please scan and pay first!", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error checking: {str(e)}", show_alert=True)


if __name__ == '__main__':
    print("=" * 55)
    print("  🚀 SS EMPIRE TELEGRAM BOT RUNNING...")
    print("  Send /pay <amount> or any number to your bot!")
    print("=" * 55)
    bot.infinity_polling()
