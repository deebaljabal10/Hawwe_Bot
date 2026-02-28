# Hawwe_Bot

import telebot
import google.generativeai as genai
import os
from flask import Flask
from threading import Thread
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ===== Environment Variables =====
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    print("⚠️ تأكد من تعيين متغيرات البيئة!")
    TELEGRAM_TOKEN = "ضع_توكنك_مؤقتاً"  # مؤقتاً للاختبار
    GEMINI_API_KEY = "ضع_مفتاحك_مؤقتاً"

# ===== تشغيل البوتات =====
bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# ===== تخزين مؤقت للتحليلات (كل مستخدم) =====
user_analysis = {}

# ===== اختيار نموذج Gemini =====
def get_available_model():
    print("🔍 Searching for available Gemini models...")
    try:
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        print(f"📋 Available models: {available_models}")
        
        priority = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']
        for p in priority:
            if p in available_models:
                print(f"✅ Selecting: {p}")
                return genai.GenerativeModel(p)
        
        if available_models:
            print(f"✅ Selecting: {available_models[0]}")
            return genai.GenerativeModel(available_models[0])
            
    except Exception as e:
        print(f"❌ Error listing models: {e}")
    
    print("⚠️ Fallback to gemini-pro")
    return genai.GenerativeModel('gemini-pro')

model = get_available_model()

# ===== Flask للحفاظ على البوت =====
app = Flask(__name__)

@app.route('/')
def home():
    return "بوت حاوي التفاعلي شغال!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    try:
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"ℹ️ Flask port {port} error: {e}")

# ===== أزرار الاختيار =====
def get_choice_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔥 عناوين", callback_data="titles"),
        InlineKeyboardButton("📝 وصف قصير", callback_data="short_desc")
    )
    markup.row(
        InlineKeyboardButton("📄 وصف طويل", callback_data="long_desc"),
        InlineKeyboardButton("🔑 كلمات مفتاحية", callback_data="keywords")
    )
    markup.row(
        InlineKeyboardButton("#️⃣ هاشتاغات", callback_data="hashtags"),
        InlineKeyboardButton("🔄 منتج جديد", callback_data="new_product")
    )
    return markup

# ===== بداية المحادثة =====
@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = """
🤖 **مرحباً بك في حاوي التفاعلي!** ✨

أرسل لي **اسم المنتج** أو **فكرته**، ثم اختر ما تريد:

🔥 عناوين جذابة
📝 وصف قصير
📄 وصف طويل
🔑 كلمات مفتاحية
#️⃣ هاشتاغات

**جرب الآن:** اكتب اسم المنتج
مثال: "قهوة سعودية عضوية"
    """
    bot.reply_to(message, welcome_text)

# ===== استقبال المنتج =====
@bot.message_handler(func=lambda m: True)
def receive_product(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        # رسالة انتظار
        wait_msg = bot.reply_to(message, "⏳ جاري تحليل المنتج...")
        
        # تحليل المنتج بالكامل (مرة واحدة)
        prompt = f"""
أنت خبير تسويق عربي محترف اسمك "حاوي". قم بتحليل المنتج التالي وإنتاج محتوى تسويقي كامل.

المنتج: {message.text}

المطلوب تحليله:
1. TITLES: 3 عناوين جذابة (كل عنوان بسطر)
2. SHORT_DESC: وصف قصير 40-50 كلمة
3. LONG_DESC: وصف طويل 150-200 كلمة
4. KEYWORDS: 15 كلمة مفتاحية (مفصولة بفواصل)
5. HASHTAGS: 10 هاشتاغات (مفصولة بمسافات)

اكتب النتيجة بالتنسيق التالي بالضبط:
---TITLES---
[العناوين هنا]
---SHORT_DESC---
[الوصف القصير هنا]
---LONG_DESC---
[الوصف الطويل هنا]
---KEYWORDS---
[الكلمات المفتاحية هنا]
---HASHTAGS---
[الهاشتاغات هنا]
"""
        
        response = model.generate_content(prompt)
        result_text = response.text
        
        # حفظ التحليل للمستخدم
        user_analysis[message.chat.id] = {
            'product': message.text,
            'full_analysis': result_text,
            'timestamp': time.time()
        }
        
        # حذف رسالة الانتظار
        bot.delete_message(message.chat.id, wait_msg.message_id)
        
        # عرض أزرار الاختيار
        bot.send_message(
            message.chat.id,
            f"✅ تم تحليل المنتج: *{message.text}*\n\nاختر ما تريد من الأزرار 👇",
            reply_markup=get_choice_keyboard(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في تحليل المنتج: {str(e)}")

# ===== معالجة اختيارات الأزرار =====
@bot.callback_query_handler(func=lambda call: True)
def handle_choice(call):
    try:
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        
        # التحقق من وجود تحليل للمستخدم
        if chat_id not in user_analysis:
            bot.edit_message_text(
                "⚠️ الرجاء إرسال اسم المنتج أولاً",
                chat_id,
                message_id
            )
            return
        
        analysis = user_analysis[chat_id]['full_analysis']
        
        # استخراج الجزء المطلوب
        if call.data == "titles":
            section = extract_section(analysis, "---TITLES---")
            title = "🔥 **عناوين مقترحة:**\n\n" + section
        
        elif call.data == "short_desc":
            section = extract_section(analysis, "---SHORT_DESC---")
            title = "📝 **وصف قصير:**\n\n" + section
        
        elif call.data == "long_desc":
            section = extract_section(analysis, "---LONG_DESC---")
            title = "📄 **وصف طويل:**\n\n" + section
        
        elif call.data == "keywords":
            section = extract_section(analysis, "---KEYWORDS---")
            title = "🔑 **كلمات مفتاحية:**\n\n" + section
        
        elif call.data == "hashtags":
            section = extract_section(analysis, "---HASHTAGS---")
            title = "#️⃣ **هاشتاغات مقترحة:**\n\n" + section
        
        elif call.data == "new_product":
            bot.edit_message_text(
                "✏️ أرسل اسم المنتج الجديد",
                chat_id,
                message_id
            )
            return
        
        # إرسال الجزء المطلوب
        bot.edit_message_text(
            title,
            chat_id,
            message_id,
            parse_mode="Markdown"
        )
        
        # إعادة إظهار الأزرار أسفل الرسالة الجديدة
        bot.send_message(
            chat_id,
            f"🔄 لا تزال تتعامل مع منتج: *{user_analysis[chat_id]['product']}*",
            reply_markup=get_choice_keyboard(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ خطأ: {str(e)}")

# ===== دالة استخراج الأقسام =====
def extract_section(text, section_header):
    try:
        parts = text.split(section_header)
        if len(parts) > 1:
            section = parts[1].split("---")[0].strip()
            return section
        return "⚠️ هذا القسم غير متوفر"
    except:
        return "⚠️ خطأ في استخراج البيانات"

# ===== تشغيل البوت =====
if __name__ == "__main__":
    # تشغيل Flask في خيط منفصل
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("✅ بوت حاوي التفاعلي شغال...")
    
    # تشغيل البوت مع إعادة المحاولة
    while True:
        try:
            bot.polling(none_stop=True, timeout=20, interval=0)
        except Exception as e:
            print(f"⚠️ خطأ في polling: {e}")
            time.sleep(5)(call.id, "📋 
