import telebot
import requests
import os
import threading
from flask import Flask

# 1. Cấu hình Token và Khởi tạo Bot, Flask
BOT_TOKEN = "8684661284:AAGN1g7lP-sNkUDYg54lvIsCTeBhW2F3fWw"
# Giả lập Database lưu số dư tạm thời (CẢNH BÁO: Render sẽ xóa dữ liệu này khi reset)
# Trong thực tế, bạn PHẢI dùng Database thật (MongoDB, PostgreSQL, MySQL...)
user_balances = {}

# 2. Các hàm gọi API ngoại vi
def check_payment_api(transaction_id):
    """
    Hàm này gọi API kiểm tra nạp tiền của bạn.
    """
    # api_url = f"https://api_kiem_tra_tien_cua_ban.com/check?trans={transaction_id}"
    # response = requests.get(api_url)
    # return response.json()
    
    # Giả lập trả về thành công với số tiền 50k
    return {"status": "success", "amount": 50000}

def topup_freefire_api(player_id, package_id):
    """
    Hàm này gọi API nạp Free Fire theo document bạn cung cấp.
    """
    api_url = "https://example-freefire-api.com/v1/topup" # Thay bằng URL thực tế từ Postman
    payload = {
        "playerId": player_id,
        "package": package_id
    }
    # Thêm headers nếu API yêu cầu Authorization/API Key
    # response = requests.post(api_url, json=payload)
    # return response.json()
    
    return {"status": "success", "message": "Nạp FF thành công!"}

# 3. Các lệnh của Telegram Bot
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "Xin chào! Đây là Bot Nạp Tiền & Nạp Free Fire.\n\n"
        "Các lệnh có sẵn:\n"
        "/naptien <Mã_Giao_Dịch> - Kiểm tra và cộng tiền vào tài khoản\n"
        "/napff <ID_Game> <Mã_Gói> - Nạp kim cương Free Fire\n"
        "/sodu - Xem số dư hiện tại"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['sodu'])
def check_balance(message):
    user_id = message.from_user.id
    balance = user_balances.get(user_id, 0)
    bot.reply_to(message, f"Số dư của bạn hiện tại là: {balance:,.0f} VNĐ")

@bot.message_handler(commands=['naptien'])
def handle_naptien(message):
    try:
        # Tách lấy mã giao dịch từ tin nhắn
        args = message.text.split()[1:]
        if not args:
            bot.reply_to(message, "Vui lòng nhập mã giao dịch. Ví dụ: /naptien ABC12345")
            return
        
        trans_id = args[0]
        bot.reply_to(message, "Đang kiểm tra giao dịch, vui lòng đợi...")
        
        # Gọi API kiểm tra tiền
        result = check_payment_api(trans_id)
        
        if result.get("status") == "success":
            user_id = message.from_user.id
            amount = result.get("amount", 0)
            
            # Cộng tiền vào "database"
            user_balances[user_id] = user_balances.get(user_id, 0) + amount
            bot.reply_to(message, f"✅ Nạp thành công {amount:,.0f} VNĐ. Dùng /sodu để kiểm tra.")
        else:
            bot.reply_to(message, "❌ Không tìm thấy giao dịch hoặc chưa được thanh toán.")
            
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")

@bot.message_handler(commands=['napff'])
def handle_napff(message):
    try:
        user_id = message.from_user.id
        args = message.text.split()[1:]
        
        if len(args) < 2:
            bot.reply_to(message, "Sai cú pháp! Ví dụ: /napff 123456789 GOI_1")
            return
            
        player_id = args[0]
        package_id = args[1]
        
        # Kiểm tra số dư (Giả sử GOI_1 giá 20k)
        price = 20000 
        current_balance = user_balances.get(user_id, 0)
        
        if current_balance < price:
            bot.reply_to(message, "❌ Số dư không đủ để nạp gói này. Vui lòng nạp thêm tiền!")
            return
            
        bot.reply_to(message, "Đang tiến hành nạp Free Fire...")
        
        # Gọi API nạp FF
        result = topup_freefire_api(player_id, package_id)
        
        if result.get("status") == "success":
            # Trừ tiền
            user_balances[user_id] -= price
            bot.reply_to(message, f"✅ Nạp Free Fire thành công cho ID {player_id}!")
        else:
            bot.reply_to(message, f"❌ Nạp thất bại: {result.get('message', 'Lỗi không xác định')}")
            
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")

# 4. Web server Flask để Render không tắt ứng dụng
@app.route('/')
def home():
    return "Bot đang hoạt động bình thường!"

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    # Chạy bot Telegram ở một luồng (thread) riêng biệt
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # Chạy Flask server trên cổng mà Render cấp phát
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)
