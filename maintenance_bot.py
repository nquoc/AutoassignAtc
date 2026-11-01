import sys
import json
import telebot

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

bot = telebot.TeleBot(config["bot_token"])

msg_text = (
    "⚠️ **THÔNG BÁO TẠM DỪNG BOT** ⚠️\n\n"
    "Anh Quốc đẹp trai đang code thêm 1 số tính năng để chia data tự động mỗi ngày. AE SC cần chuyển ATC thì **ĐỪNG liên hệ Quốc** =))"
)

@bot.message_handler(func=lambda message: True)
def notify_maintenance(message):
    bot.reply_to(message, msg_text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def notify_callback(call):
    bot.answer_callback_query(call.id, "⚠️ Anh Quốc đẹp trai đang code thêm tính năng...")
    bot.send_message(call.message.chat.id, msg_text, parse_mode="Markdown")

if __name__ == "__main__":
    print("Bot Maintenance Mode started with custom funny text...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
