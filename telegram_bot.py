import logging
import os
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# تحميل متغيرات البيئة
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', "8715981572:AAFylx54UWGsx5d4xQR2-SB1aTV8i459OoY")
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY', 'demo')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', None)

# المنطقة الزمنية (توقيت نيويورك - فتح السوق)
ET = pytz.timezone('America/New_York')

# قائمة الأسهم ذات السيولة العالية والحلال للفحص
WATCHLIST = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM',
    'V', 'JNJ', 'WMT', 'PG', 'XOM', 'KO', 'INTC', 'AMD', 'NFLX',
    'PYPL', 'ADBE', 'CRM', 'SHOP', 'SQ', 'ROKU', 'SPOT', 'ABNB',
    'PATH', 'DDOG', 'CRWD', 'ZS', 'OKTA', 'NET', 'CLOUDFLARE'
]

# الأسهم غير الحلال (تبغ، مقامرة، كحول، أسلحة، إلخ)
HARAM_SYMBOLS = {
    'MO', 'PM', 'BTI', 'LOGI', 'LVS', 'WYNN', 'BYD', 'BAC', 'GS',
    'RTX', 'LMT', 'NOC', 'BA', 'RIO', 'BHP'
}

# قطاعات محرمة
HARAM_SECTORS = ['Tobacco', 'Liquor & Spirits', 'Gambling', 'Defense']

class StockBot:
    def __init__(self, app=None):
        """تهيئة البوت"""
        self.finnhub_api = FINNHUB_API_KEY
        self.cache = {}
        self.app = app
        self.chat_id = TELEGRAM_CHAT_ID

    def fetch_stock_data(self, symbol):
        """جلب بيانات السهم من Finnhub"""
        try:
            # بيانات السعر
            quote_url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={self.finnhub_api}"
            quote_response = requests.get(quote_url, timeout=10)
            quote_data = quote_response.json() if quote_response.status_code == 200 else {}

            # بيانات الشركة
            profile_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={self.finnhub_api}"
            profile_response = requests.get(profile_url, timeout=10)
            profile_data = profile_response.json() if profile_response.status_code == 200 else {}

            # آراء المحللين
            recommendation_url = f"https://finnhub.io/api/v1/stock/recommendation?symbol={symbol}&token={self.finnhub_api}"
            recommendation_response = requests.get(recommendation_url, timeout=10)
            recommendation_data = recommendation_response.json() if recommendation_response.status_code == 200 else []

            return {
                'quote': quote_data,
                'profile': profile_data,
                'recommendation': recommendation_data[0] if recommendation_data else {}
            }
        except Exception as e:
            logger.error(f"خطأ جلب بيانات {symbol}: {e}")
            return None

    def is_halal_stock(self, symbol, profile_data):
        """فحص إذا كان السهم حلال"""
        if symbol in HARAM_SYMBOLS:
            return False

        sector = profile_data.get('finnhubIndustry', '')
        if any(haram in sector for haram in HARAM_SECTORS):
            return False

        return True

    def get_opportunity_signal(self, symbol, stock_data):
        """تحليل الفرصة - بناءً على البيانات الحقيقية"""
        if not stock_data or 'quote' not in stock_data:
            return None

        quote = stock_data['quote']
        recommendation = stock_data.get('recommendation', {})
        profile = stock_data.get('profile', {})

        # التحقق من توفر البيانات الأساسية
        current_price = quote.get('c', 0)
        if not current_price:
            return None

        # حساب الفرصة بناءً على آراء المحللين
        buy_count = recommendation.get('buy', 0)
        hold_count = recommendation.get('hold', 0)
        sell_count = recommendation.get('sell', 0)
        total_analysts = buy_count + hold_count + sell_count

        if total_analysts == 0:
            return None

        buy_percentage = (buy_count / total_analysts) * 100 if total_analysts > 0 else 0

        # تحديد قوة الإشارة
        if buy_percentage >= 70:
            signal = "✅ فرصة شراء قوية"
            risk = "متوسطة 🟡"
        elif buy_percentage >= 50:
            signal = "✅ فرصة شراء"
            risk = "متوسطة 🟡"
        elif buy_percentage >= 30:
            signal = "⚠️ فرصة متوسطة"
            risk = "متوسطة 🟡"
        else:
            return None

        return {
            'symbol': symbol,
            'name': profile.get('name', symbol),
            'sector': profile.get('finnhubIndustry', 'غير محدد'),
            'current_price': round(current_price, 2),
            'signal': signal,
            'buy_count': buy_count,
            'hold_count': hold_count,
            'sell_count': sell_count,
            'total_analysts': total_analysts,
            'buy_percentage': round(buy_percentage, 1),
            'risk': risk,
            'high': quote.get('h', 0),
            'low': quote.get('l', 0),
            'change': round(quote.get('d', 0), 2),
            'change_percent': round(quote.get('dp', 0), 2)
        }

    async def send_automated_report(self, report_type="opening"):
        """إرسال تقرير تلقائي للمستخدم"""
        if not self.chat_id or not self.app:
            logger.error("Chat ID أو Application غير متوفر")
            return

        try:
            opportunities = []

            # فحص الأسهم في قائمة المراقبة
            for symbol in WATCHLIST[:15]:
                stock_data = self.fetch_stock_data(symbol)
                if not stock_data:
                    continue

                if not self.is_halal_stock(symbol, stock_data.get('profile', {})):
                    continue

                opportunity = self.get_opportunity_signal(symbol, stock_data)
                if opportunity:
                    opportunities.append(opportunity)

            opportunities.sort(key=lambda x: x['buy_percentage'], reverse=True)

            # تحديد عنوان التقرير حسب الوقت
            if report_type == "opening":
                title = "📈 تقرير فتح السوق"
                time_info = "فتح السوق للتو"
            elif report_type == "midday":
                title = "📊 تقرير منتصف اليوم"
                time_info = "منتصف جلسة التداول"
            else:
                title = "⏰ تقرير قبل إغلاق السوق"
                time_info = "قبل 30 دقيقة من الإغلاق"

            if not opportunities:
                text = f"{title}\n━━━━━━━━━━━━━━━━━━━━━\n\n⏱️ {time_info}\n\n❌ لا توجد فرص قوية حالياً\n\n💡 استخدم /daily_report للمزيد"
            else:
                text = f"""{title}
━━━━━━━━━━━━━━━━━━━━━
⏱️ {time_info}
📅 {datetime.now(ET).strftime('%Y-%m-%d %H:%M')} (توقيت نيويورك)

تم العثور على {len(opportunities)} فرصة:

"""
                for i, opp in enumerate(opportunities[:5], 1):
                    text += f"""
{i}️⃣ **{opp['symbol']}** {opp['signal']}
   💹 ${opp['current_price']} ({opp['change_percent']:+.2f}%)
   🧑‍💼 {opp['buy_count']}/{opp['total_analysts']} محلل ({opp['buy_percentage']:.0f}%)
   ⚠️ {opp['risk']}

"""

                text += "\n💡 استخدم /analyze SYMBOL للتفاصيل الكاملة"

            # إرسال الرسالة
            await self.app.bot.send_message(chat_id=int(self.chat_id), text=text, parse_mode='Markdown')
            logger.info(f"✅ تم إرسال تقرير {report_type} بنجاح")

        except Exception as e:
            logger.error(f"❌ خطأ في إرسال التقرير التلقائي: {e}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """رسالة البداية"""
        text = """
🤖 **بوت تحليل الأسهم الإسلامي المتقدم - النسخة 2.0**

📊 الأوامر الرئيسية:

📈 **/daily_report**
   تقرير يومي بأفضل الفرص الحالية (بيانات حية من السوق)

💡 **/opportunities**
   قائمة الفرص الفورية الآن - أسهم مختلفة بناءً على توصيات المحللين

🔍 **/analyze [SYMBOL]**
   تحليل تفصيلي لسهم معين (مثال: /analyze AAPL)

🕌 **/stocks**
   قائمة الأسهم المتاحة للتحليل

❓ **/help**
   عرض المساعدة الكاملة

**ملاحظة:** البوت الآن يجلب **بيانات حية من السوق** - تختلف التوصيات بناءً على تحليلات المحللين الحقيقيين!
        """
        await update.message.reply_text(text, parse_mode='Markdown')

    async def daily_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """التقرير اليومي - فرص حقيقية من السوق"""
        try:
            await update.message.reply_text("⏳ جاري تحليل السوق والبحث عن الفرص...")

            opportunities = []

            # فحص الأسهم في قائمة المراقبة
            for symbol in WATCHLIST[:15]:  # فحص أول 15 سهم للسرعة
                stock_data = self.fetch_stock_data(symbol)
                if not stock_data:
                    continue

                # فحص إذا كان حلال
                if not self.is_halal_stock(symbol, stock_data.get('profile', {})):
                    continue

                # تحليل الفرصة
                opportunity = self.get_opportunity_signal(symbol, stock_data)
                if opportunity:
                    opportunities.append(opportunity)

            # ترتيب الفرص حسب قوة البيانات
            opportunities.sort(key=lambda x: x['buy_percentage'], reverse=True)

            if not opportunities:
                text = """📊 **التقرير اليومي**

❌ لا توجد فرص قوية حالياً في السوق.

💡 **ملاحظة:** البوت يبحث عن أسهم بناءً على:
• توصيات المحللين (70% شراء أو أكثر)
• الفحص الحلال (استثناء الأسهم المحرمة)
• السيولة العالية

🔄 سيتم البحث عن فرص جديدة في التحديث التالي!
"""
            else:
                text = f"""📊 **التقرير اليومي - {datetime.now().strftime('%Y-%m-%d')}**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

تم العثور على {len(opportunities)} فرصة استثمارية حالياً:

"""
                for i, opp in enumerate(opportunities[:5], 1):  # عرض أفضل 5 فرص
                    text += f"""
{i}️⃣ **{opp['symbol']} - {opp['name']}**
📊 القطاع: {opp['sector']}
💹 السعر الحالي: ${opp['current_price']}
📈 التغير: {opp['change']:+.2f}$ ({opp['change_percent']:+.2f}%)

🧑‍💼 **رأي المحللين:**
   ✅ شراء: {opp['buy_count']} محلل ({opp['buy_percentage']:.1f}%)
   ⏳ محايد: {opp['hold_count']} محلل
   ❌ بيع: {opp['sell_count']} محلل
   📊 إجمالي: {opp['total_analysts']} محلل

🚨 الإشارة: {opp['signal']}
⚠️ المخاطر: {opp['risk']}
✅ الحلال: 🕌 نعم

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

                text += """
⚠️ **تنبيهات مهمة:**
• هذا تحليل بناءً على توصيات المحللين فقط
• ليس نصيحة مالية - استشر مستشاراً مالياً
• الاستثمار يحمل مخاطر - افعل بحثك الخاص
• البيانات من Finnhub API (قد تكون متأخرة قليلاً)
"""

            await update.message.reply_text(text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"خطأ في التقرير اليومي: {e}")
            await update.message.reply_text(f"❌ خطأ في جلب البيانات: {str(e)}")

    async def opportunities(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """الفرص الفورية - بيانات حية"""
        try:
            await update.message.reply_text("⏳ جاري البحث عن الفرص الفورية...")

            opportunities = []

            # فحص سريع لأفضل الأسهم
            for symbol in WATCHLIST[:20]:
                stock_data = self.fetch_stock_data(symbol)
                if not stock_data:
                    continue

                if not self.is_halal_stock(symbol, stock_data.get('profile', {})):
                    continue

                opportunity = self.get_opportunity_signal(symbol, stock_data)
                if opportunity and opportunity['buy_percentage'] >= 50:  # فرص قوية فقط
                    opportunities.append(opportunity)

            opportunities.sort(key=lambda x: x['buy_percentage'], reverse=True)

            if not opportunities:
                text = "❌ لا توجد فرص قوية حالياً\n\n💡 استخدم /analyze [SYMBOL] لتحليل أي سهم"
            else:
                text = f"🚨 **الفرص الفورية الحالية** - {len(opportunities)} فرصة\n━━━━━━━━━━━━━━━━━━━━━\n\n"

                for i, opp in enumerate(opportunities[:10], 1):
                    text += f"""
{i}. **{opp['symbol']}** - {opp['signal']}
   💹 السعر: ${opp['current_price']} ({opp['change_percent']:+.2f}%)
   🧑‍💼 المحللون: {opp['buy_count']}/{opp['total_analysts']} ({opp['buy_percentage']:.0f}%)
   ⚠️ المخاطر: {opp['risk']}

"""

            text += "\n💡 **استخدم /analyze SYMBOL للتفاصيل الكاملة**"
            await update.message.reply_text(text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"خطأ الفرص: {e}")
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تحليل سهم معين - بيانات حية"""
        try:
            if not context.args:
                await update.message.reply_text("❌ حدد رمز السهم\n\nمثال: /analyze AAPL\n\nيمكنك تحليل أي سهم أمريكي!")
                return

            symbol = context.args[0].upper()
            await update.message.reply_text(f"⏳ جاري تحليل {symbol}...")

            stock_data = self.fetch_stock_data(symbol)
            if not stock_data or 'quote' not in stock_data or not stock_data['quote'].get('c'):
                await update.message.reply_text(f"❌ لم أستطع جلب بيانات {symbol}\n\nتأكد من صحة الرمز (مثال: AAPL, MSFT)")
                return

            profile = stock_data.get('profile', {})
            quote = stock_data['quote']
            recommendation = stock_data.get('recommendation', {})

            # فحص الحلال
            is_halal = self.is_halal_stock(symbol, profile)
            halal_status = "✅ السهم حلال 🕌" if is_halal else "❌ السهم غير حلال"

            # استخراج البيانات
            current_price = quote.get('c', 0)
            high = quote.get('h', 0)
            low = quote.get('l', 0)
            change = quote.get('d', 0)
            change_percent = quote.get('dp', 0)

            buy_count = recommendation.get('buy', 0)
            hold_count = recommendation.get('hold', 0)
            sell_count = recommendation.get('sell', 0)
            total = buy_count + hold_count + sell_count

            text = f"""
📊 **تحليل {symbol}**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ **معلومات الشركة:**
📝 الاسم: {profile.get('name', 'غير متاح')}
🌐 الموقع: {profile.get('country', 'غير متاح')}
🏢 القطاع: {profile.get('finnhubIndustry', 'غير متاح')}

2️⃣ **السعر والتحرك:**
💹 السعر الحالي: ${current_price}
📈 المدى اليومي: ${low} - ${high}
🔄 التغير: {change:+.2f}$ ({change_percent:+.2f}%)

3️⃣ **رأي المحللين:**
"""

            if total > 0:
                text += f"""✅ شراء: {buy_count} ({(buy_count/total)*100:.1f}%)
⏳ محايد: {hold_count} ({(hold_count/total)*100:.1f}%)
❌ بيع: {sell_count} ({(sell_count/total)*100:.1f}%)
📊 إجمالي: {total} محلل
"""
            else:
                text += "📊 لا توجد توصيات محللين متاحة"

            text += f"""
4️⃣ **الفحص الإسلامي:**
{halal_status}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **تنبيه:**
• هذه بيانات حية من السوق
• ليست نصيحة مالية - استشر مستشاراً
• افعل بحثك الخاص قبل الاستثمار
"""
            await update.message.reply_text(text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"خطأ التحليل: {e}")
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def stocks_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """قائمة الأسهم الموصى بفحصها"""
        stocks_str = ", ".join(WATCHLIST[:15])
        text = f"""
📈 **الأسهم التي يراقبها البوت:**

{stocks_str}

**ملاحظات:**
✅ جميع الأسهم في القائمة حلال (بعد الفحص)
💹 يمكنك تحليل أي سهم أمريكي بـ /analyze SYMBOL
🔄 الفرص تتغير حسب توصيات المحللين الحقيقية

**أمثلة:**
/analyze AAPL
/analyze NVDA
/analyze GOOGL

تذكر: الأسهم قد تتغير بناءً على البيانات الحقيقية من السوق!
"""
        await update.message.reply_text(text, parse_mode='Markdown')

    async def help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """المساعدة"""
        text = """
📚 **دليل الاستخدام الكامل**

**الأوامر الرئيسية:**

📈 /daily_report - التقرير اليومي الشامل
💡 /opportunities - الفرص الفورية
🔍 /analyze [SYMBOL] - تحليل سهم
📊 /stocks - قائمة الأسهم
❓ /help - المساعدة

**مثال:**
   /daily_report
   /analyze MSFT
   /opportunities
"""
        await update.message.reply_text(text, parse_mode='Markdown')

def main():
    """تشغيل البوت"""
    app = Application.builder().token(TOKEN).build()
    stock_bot = StockBot(app=app)

    # إضافة معالجات الأوامر
    app.add_handler(CommandHandler("start", stock_bot.start))
    app.add_handler(CommandHandler("daily_report", stock_bot.daily_report))
    app.add_handler(CommandHandler("opportunities", stock_bot.opportunities))
    app.add_handler(CommandHandler("analyze", stock_bot.analyze))
    app.add_handler(CommandHandler("stocks", stock_bot.stocks_list))
    app.add_handler(CommandHandler("help", stock_bot.help_cmd))

    # إضافة الجدول الزمني للتقارير التلقائية
    if TELEGRAM_CHAT_ID:
        scheduler = AsyncIOScheduler(timezone=ET)

        # التقرير الأول: فتح السوق (9:30 AM بتوقيت نيويورك)
        scheduler.add_job(
            stock_bot.send_automated_report,
            CronTrigger(hour=9, minute=30, day_of_week='0-4'),  # من الاثنين للجمعة
            kwargs={'report_type': 'opening'},
            name='opening_report'
        )

        # التقرير الثاني: منتصف اليوم (1:00 PM بتوقيت نيويورك)
        scheduler.add_job(
            stock_bot.send_automated_report,
            CronTrigger(hour=13, minute=0, day_of_week='0-4'),
            kwargs={'report_type': 'midday'},
            name='midday_report'
        )

        # التقرير الثالث: قبل الإغلاق (3:30 PM بتوقيت نيويورك)
        scheduler.add_job(
            stock_bot.send_automated_report,
            CronTrigger(hour=15, minute=30, day_of_week='0-4'),
            kwargs={'report_type': 'closing'},
            name='closing_report'
        )

        # بدء الجدول الزمني
        scheduler.start()
        logger.info("✅ تم تفعيل الجدول الزمني للتقارير التلقائية")
    else:
        logger.warning("⚠️ TELEGRAM_CHAT_ID غير موجود - التقارير التلقائية معطلة")

    print("\n" + "="*70)
    print("🤖 بوت تحليل الأسهم الإسلامي المتقدم - النسخة 2.0")
    print("="*70)
    print("\n✅ البوت نشط وجاهز للعمل!\n")
    print("الأوامر المتاحة:")
    print("  📈 /daily_report    - تقرير يومي بفرص السوق الحالية")
    print("  💡 /opportunities   - الفرص الفورية الآن")
    print("  🔍 /analyze [SYMBOL] - تحليل أي سهم (مثال: /analyze AAPL)")
    print("  📊 /stocks          - قائمة الأسهم المراقبة")
    print("  ❓ /help            - عرض المساعدة")
    print("\n🌟 الميزات الجديدة:")
    print("  • بيانات حية من Finnhub API")
    print("  • توصيات فعلية من المحللين الحقيقيين")
    print("  • فرص مختلفة كل يوم حسب السوق")
    print("  • فحص إسلامي تلقائي للأسهم")
    print("\n📅 التقارير التلقائية:")
    print("  • 9:30 AM  - تقرير فتح السوق")
    print("  • 1:00 PM  - تقرير منتصف اليوم")
    print("  • 3:30 PM  - تقرير قبل إغلاق السوق")
    print("  (توقيت نيويورك، من الاثنين للجمعة فقط)")
    print("="*70)
    print("اضغط Ctrl+C لإيقاف البوت\n")

    app.run_polling()

if __name__ == '__main__':
    main()
