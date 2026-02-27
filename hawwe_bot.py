# hawwe_bot.py

import telebot
import google.generativeai as genai
import os
from dotenv import load_dotenv

# تحميل المفاتيح من ملف .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# تشغيل البوتات
bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# تخزين مؤقت للمحادثات
user_sessions = {}

@bot.message_handler(commands=['start'])
def start(message):
    """رسالة الترحيب"""
    welcome_text = """
🤖 **مرحباً بك في حاوي!** ✨

أنا كاتبك التسويقي الذكي. أرسل لي أي منتج أو فكرة وسأكتب لك:

🔥 **3 عناوين جذابة**
📝 **وصف قصير مقنع**
📄 **وصف طويل احترافي**
🔑 **15 كلمة مفتاحية**
#️⃣ **10 هاشتاغات مناسبة**

**جرب الآن:** اكتب اسم المنتج أو فكرته
مثال: "قهوة سعودية عضوية"
    """
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def generate_content(message):
    """معالجة رسائل المستخدم"""
    try:
        # مؤشر الكتابة
        bot.send_chat_action(message.chat.id, 'typing')
        
        # بناء البرومبت الاحترافي
        prompt = f"""
أنت خبير تسويق عربي محترف اسمك "حاوي". مهمتك كتابة محتوى تسويقي للمنتجات.

المنتج: {message.text}

المطلوب بالضبط:
1. **3 عناوين جذابة** (كل عنوان مختلف في أسلوبه)
2. **وصف قصير** (40-50 كلمة) مقنع وسريع
3. **وصف طويل** (150-200 كلمة) احترافي للموقع
4. **15 كلمة مفتاحية** مناسبة لتحسين البحث SEO
5. **10 هاشتاغات** مناسبة للسوشيال ميديا

اكتب النتيجة بشكل منظم وجاهز للنسخ مع استخدام إيموجيات مناسبة.
"""
        
        # استدعاء Gemini
        response = model.generate_content(prompt)
        
        # أزرار تفاعلية
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🔄 إعادة بصيغة أخرى", callback_data=f"regenerate:{message.text}"),
            InlineKeyboardButton("📋 نسخ الكل", callback_data="copy")
        )
        
        bot.reply_to(message, response.text, reply_markup=markup, parse_mode="Markdown")
        
    except Exception as e:
        error_msg = f"❌ عذراً، حصل خطأ: {str(e)}\nحاول مرة أخرى."
        bot.reply_to(message, error_msg)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """معالجة الأزرار"""
    if call.data.startswith("regenerate:"):
        product = call.data.split(":", 1)[1]
        
        # إرسال رسالة "جاري إعادة الإنشاء"
        bot.edit_message_text(
            "🔄 جاري إعادة كتابة المحتوى بصيغة جديدة...",
            call.message.chat.id,
            call.message.message_id
        )
        
        # طلب إعادة الإنشاء (بنفس المنتج لكن بصيغة مختلفة)
        prompt = f"""
أنت خبير تسويق عربي. أعد كتابة محتوى تسويقي للمنتج التالي ولكن **بصيغة مختلفة تماماً** عن المرة السابقة.

المنتج: {product}

اكتب نفس العناصر لكن بأسلوب جديد كلياً.
"""
        response = model.generate_content(prompt)
        
        bot.edit_message_text(
            response.text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    
    elif call.data == "copy":
        bot.answer_callback_query(call.id, "📋 يمكنك نسخ النص يدوياً الآن", show_alert=True)

print("✅ بوت حاوي شغال الآن... جربه على تليغرام!")
bot.infinity_polling()
