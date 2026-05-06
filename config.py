"""
ملف التكوين الرئيسي للبوت
"""
import os
from dotenv import load_dotenv

load_dotenv()

# معلومات التلجرام
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')  # للقنوات/المجموعات

# مفاتيح APIs
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY', '')  # اختياري

# قاعدة البيانات
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///stocks_bot.db')

# المراقبة والجدولة
CHECK_INTERVAL_MINUTES = 30  # فحص الأسهم كل 30 دقيقة
DAILY_SUMMARY_HOUR = 9  # ملخص يومي في الساعة 9 صباحاً
WEEKLY_SUMMARY_DAY = 'sunday'  # ملخص أسبوعي يوم الأحد

# معايير التحليل الفني
RSI_OVERSOLD = 30  # مؤشر RSI للشراء
RSI_OVERBOUGHT = 70
MACD_THRESHOLD = 0.5
MA_SHORT_PERIOD = 20
MA_LONG_PERIOD = 50

# معايير التحليل الأساسي - للاستثمار طويل الأجل
PE_MAX = 25  # نسبة السعر إلى الربح القصوى
PE_MIN = 5
PS_MAX = 2  # نسبة السعر إلى المبيعات
DIVIDEND_YIELD_MIN = 0.02  # العائد الأدنى 2%

# معايير حجم التداول
VOLUME_THRESHOLD = 1000000  # حد أدنى لمتوسط التداول اليومي

# الأسهم المراقبة (قائمة أولية)
WATCHLIST = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA',
    'META', 'TSLA', 'JPM', 'V', 'WMT',
    'JNJ', 'PG', 'KO', 'XOM', 'MCD'
]

# الأسهم المستثناة (غير إسلامية)
EXCLUDED_SECTORS = [
    'Financial Services',  # البنوك والخدمات المالية بفائدة
    'Tobacco',  # التبغ
    'Gambling',  # المقامرة
    'Weapons & Defense',  # الأسلحة
]

# معايير الشريعة الإسلامية
ISLAMIC_SCREENING_RULES = {
    'interest_bearing_debt_ratio': 0.3,  # نسبة الديون التي تترتب عليها فائدة
    'haram_revenue_ratio': 0.05,  # نسبة الدخل من مصادر حرام
    'cash_to_market_cap_ratio': 0.5,  # النقد إلى القيمة السوقية
}

# رسائل النوتيفيكشن
NOTIFICATION_SETTINGS = {
    'daily_trading': True,  # تنبيهات المضاربة اليومية
    'long_term': True,  # تنبيهات الاستثمار طويل الأجل
    'urgent_alerts': True,  # تنبيهات عاجلة فورية
    'summary_reports': True,  # التقارير الملخصة
}
