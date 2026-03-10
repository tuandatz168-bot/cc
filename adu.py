import telebot
import requests
import os
import threading
import hashlib
import time
from flask import Flask, request, jsonify

# ==========================================
# 1. CẤU HÌNH CƠ BẢN (ĐIỀN THÔNG TIN CỦA BẠN)
# ==========================================
# Khai báo Bot ngay từ đầu để không bị lỗi NameError
BOT_TOKEN = "8684661284:AAGN1g7lP-sNkUDYg54lvIsCTeBhW2F3fWw" # Nhớ thay token mới sau khi test xong nhé!
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Cấu hình API Gạch Thẻ (Lấy trên web gạch thẻ của bạn)
PARTNER_ID = "3959777132"
PARTNER_KEY = "9305c7f4506f607f0cb348a2a78fe320"
URL_GACH_THE = "https://thesieure.com/chargingws/v2" # Thay bằng link API chuẩn của web bạn dùng

# Dữ liệu lưu trữ tạm thời (Sẽ mất khi Render reset)
user_balances = {}
pending_transactions = {} # Lưu mã giao dịch để biết thẻ của ai khi Webhook gọi về

# ==========================================
# 2. XỬ LÝ API GẠCH THẺ VÀ FREE FIRE
# ==========================================
def create_signature(partner_key, ma_the, seri):
    """Tạo chữ ký bảo mật MD5 (Tùy web gạch thẻ yêu cầu cấu trúc khác nhau)"""
    # Đa số các web dùng: MD5(partner_key + pin + serial)
    sign_str = partner_key + ma_the + seri
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest()

def send_card_to_api(telco, amount, seri, pin, request_id):
    """Gửi thẻ lên hệ thống gạch thẻ"""
    sign = create_signature(PARTNER_KEY, pin, seri)
    payload = {
        "telco": telco,
        "code": pin,
        "serial": seri,
        "amount": amount,
        "request_id": request_id,
        "partner_id": PARTNER_ID,
        "sign": sign,
        "command": "charging"
    }
    # Tùy web yêu cầu gửi GET hay POST, ở đây ví dụ POST json
    try:
        response = requests.post(URL_GACH_THE, json=payload)
        return response.json()
    except Exception as e:
        return {"status": 99, "message": f"Lỗi kết nối: {str(e)}"}

def topup_freefire_api(player_id, package_id):
    """API Nạp Free Fire"""
    # Thay bằng URL thật từ Postman của bạn
    api_url = "https://example-freefire-api.com/v1/topup" 
    payload = {"playerId": player_id, "package": package_id}
    # Gửi request nạp FF (Đang giả lập thành công)
    return {"status": "success", "message": "Nạp thành công!"}

# ==========================================
# 3. CÁC LỆNH CỦA TELEGRAM BOT
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "🤖 **BOT TỰ ĐỘNG NẠP THẺ & FREE FIRE** 🤖\n\n"
        "💰 /napthe <LoạiThẻ> <MệnhGiá> <Seri> <MãThẻ>\n"
        "VD: `/napthe VIETTEL 20000 1000xxxx 5321xxxx`\n\n"
        "💎 /napff <ID_Game> <Mã_Gói>\n"
        "VD: `/napff 123456789 GOI_1`\n\n"
        "💳 /sodu - Xem số dư hiện tại"
    )
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['sodu'])
def check_balance(message):
    user_id = message.from_user.id
    balance = user_balances.get(user_id, 0)
    bot.reply_to(message, f"💳 Số dư của bạn là: {balance:,.0f} VNĐ")

@bot.message_handler(commands=['napthe'])
def handle_napthe(message):
    try:
        user_id = message.from_user.id
        args = message.text.split()[1:]
        
        # Kiểm tra cú pháp
        if len(args) != 4:
            bot.reply_to(message, "❌ Sai cú pháp!\nChuẩn: /napthe <Loại> <Giá> <Seri> <Mã>\nVí dụ: /napthe VIETTEL 20000 12345 67890")
            return
            
        telco = args[0].upper()
        amount = args[1]
        seri = args[2]
        pin = args[3]
        
        # Tạo mã giao dịch duy nhất
        request_id = f"R_{user_id}_{int(time.time())}"
        
        bot.reply_to(message, "⏳ Đang gửi thẻ lên hệ thống kiểm tra, vui lòng đợi 10-30 giây...")
        
        # Gửi thẻ đi
        result = send_card_to_api(telco, amount, seri, pin, request_id)
        
        # Xử lý kết quả trả về bước đầu (1: Thành công, 99: Chờ xử lý...)
        # Lưu ý: Các web gạch thẻ thường trả về trạng thái "Chờ xử lý" (Pending)
        status = result.get('status')
        if status in [1, 99]: # Tùy web, thường 99 là pending
            # Lưu giao dịch lại để chờ Webhook gọi về
            pending_transactions[request_id] = {
                "user_id": user_id,
                "amount": int(amount)
            }
            bot.send_message(user_id, f"📝 Đã tiếp nhận thẻ (Mã GD: {request_id}). Đang chờ hệ thống gạch thẻ...")
        else:
            msg = result.get('message', 'Lỗi không xác định')
            bot.reply_to(message, f"❌ Thẻ bị từ chối ngay lập tức: {msg}")
            
    except Exception as e:
        bot.reply_to(message, f"Lỗi: {str(e)}")

@bot.message_handler(commands=['napff'])
def handle_napff(message):
    # (Phần này giữ nguyên như cũ của bạn)
    try:
        user_id = message.from_user.id
        args = message.text.split()[1:]
        if len(args) < 2:
            bot.reply_to(message, "❌ Sai cú pháp! VD: /napff 123456789 GOI_1")
            return
            
        player_id = args[0]
        package_id = args[1]
        price = 20000 # Giả sử gói giá 20k
        current_balance = user_balances.get(user_id, 0)
        
        if current_balance < price:
            bot.reply_to(message, "❌ Bạn không đủ tiền. Vui lòng nạp thêm!")
            return
            
        bot.reply_to(message, "⏳ Đang nạp Free Fire...")
        result = topup_freefire_api(player_id, package_id)
        
        if result.get("status") == "success":
            user_balances[user_id] -= price
            bot.reply_to(message, f"✅ Nạp thành công cho ID {player_id}! Trừ {price}đ. Số dư: {user_balances[user_id]:,.0f}đ")
        else:
            bot.reply_to(message, "❌ Nạp thất bại!")
    except Exception as e:
        bot.reply_to(message, f"Lỗi: {str(e)}")

# ==========================================
# 4. FLASK WEB SERVER & WEBHOOK TỰ ĐỘNG
# ==========================================
@app.route('/')
def home():
    return "Bot Gạch Thẻ Auto 100% đang chạy!"

# ĐÂY LÀ NƠI WEB GẠCH THẺ SẼ GỌI VỀ ĐỂ BÁO KẾT QUẢ
@app.route('/webhook', methods=['POST', 'GET'])
def webhook_gachthe():
    # Web gạch thẻ có thể gửi GET hoặc POST, ta lấy dữ liệu ra
    data = request.args if request.method == 'GET' else request.json
    if not data:
        data = request.form

    try:
        status = int(data.get('status', 0)) # Trạng thái thẻ (1: Thành công, 2: Sai mệnh giá, 3: Thẻ lỗi, v.v.)
        request_id = data.get('request_id')
        amount = int(data.get('amount', 0)) # Số tiền thực nhận

        # Kiểm tra xem mã giao dịch này có tồn tại trong hệ thống bot không
        if request_id in pending_transactions:
            trans_info = pending_transactions[request_id]
            user_id = trans_info['user_id']
            
            if status == 1: # Thẻ đúng 100%
                user_balances[user_id] = user_balances.get(user_id, 0) + amount
                bot.send_message(user_id, f"✅ NẠP THẺ THÀNH CÔNG!\nCộng {amount:,.0f} VNĐ vào tài khoản.\nMã GD: {request_id}")
            
            elif status == 2: # Sai mệnh giá
                bot.send_message(user_id, f"⚠️ Thẻ đúng nhưng sai mệnh giá. Bạn nhận được {amount:,.0f} VNĐ.\nMã GD: {request_id}")
                user_balances[user_id] = user_balances.get(user_id, 0) + amount
                
            elif status == 3 or status == 4: # Thẻ lỗi / Đã sử dụng
                bot.send_message(user_id, f"❌ THẺ LỖI HOẶC ĐÃ SỬ DỤNG!\nMã GD: {request_id}")
            
            # Xóa giao dịch khỏi hàng đợi
            del pending_transactions[request_id]
            
        return jsonify({"status": "success"}) # Báo cho web gạch thẻ biết bot đã nhận được thông báo
        
    except Exception as e:
        print("Webhook Error:", e)
        return jsonify({"status": "error"}), 500

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    # Chạy Bot ở luồng phụ
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # Chạy Flask ở luồng chính (Render cấp Port tự động)
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)
