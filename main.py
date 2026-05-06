"""
نقطة البداية الرئيسية للبوت
"""
import os
import sys
import logging
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def check_configuration():
    """التحقق من الإعدادات"""
    required_keys = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID',
        'FINNHUB_API_KEY'
    ]

    missing_keys = []
    for key in required_keys:
        if not os.getenv(key):
            missing_keys.append(key)

    if missing_keys:
        print("\n❌ خطأ: البيانات المطلوبة مفقودة!\n")
        print("البيانات المفقودة:")
        for key in missing_keys:
            print(f"  • {key}")

        print("\nيرجى:")
        print("1. نسخ ملف .env.example إلى .env")
        print("2. ملء البيانات المطلوبة في ملف .env")
        print("3. إعادة تشغيل البوت\n")
        return False

    return True


def main():
    """الدالة الرئيسية"""
    print("\n" + "="*50)
    print("🤖 بوت تحليل الأسهم الإسلامي")
    print("="*50 + "\n")

    # التحقق من الإعدادات
    if not check_configuration():
        sys.exit(1)

    try:
        print("📥 جاري تحميل المكتبات...")
        from telegram_bot import StockBot

        print("✅ تم تحميل جميع المكتبات بنجاح\n")

        print("🤖 جاري إنشاء البوت...")
        bot = StockBot()

        print("✅ تم إنشاء البوت بنجاح\n")

        print("🚀 جاري تشغيل البوت...")
        print("-" * 50)
        print("البوت نشط وجاهز للعمل!")
        print("اضغط Ctrl+C لإيقاف البوت")
        print("-" * 50 + "\n")

        bot.run()

    except ImportError as e:
        print(f"\n❌ خطأ: مكتبة مفقودة")
        print(f"   {str(e)}\n")
        print("الرجاء تثبيت المتطلبات:")
        print("   pip install -r requirements.txt\n")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⏹️  تم إيقاف البوت")
        print("وداعاً! 👋\n")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ خطأ غير متوقع:")
        print(f"   {str(e)}\n")
        logger.exception("خطأ في البوت:")
        sys.exit(1)


if __name__ == '__main__':
    main()
