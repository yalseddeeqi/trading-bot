"""
فحص التوافق مع الشريعة الإسلامية
"""
import logging
from typing import Tuple, Dict
from config import (
    EXCLUDED_SECTORS,
    ISLAMIC_SCREENING_RULES
)

logger = logging.getLogger(__name__)


class IslamicScreening:
    """فحص التوافق الإسلامي للأسهم"""

    # قائمة الشركات الموثوقة الحلال
    KNOWN_HALAL_STOCKS = {
        'AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA',
        'V', 'MA', 'JNJ', 'PG', 'KO',
        'MCD', 'SBUX', 'AMZN', 'WMT', 'XOM',
        'JPM', 'BA', 'CAT', 'GE', 'IBM',
        'INTC', 'AMD', 'QCOM', 'CISCO', 'DELL',
    }

    # القطاعات المستبعدة
    FORBIDDEN_SECTORS = EXCLUDED_SECTORS

    # الشركات المعروفة غير الحلال
    HARAM_STOCKS = {
        'MO',  # Philip Morris (تبغ)
        'PM',  # Philip Morris (تبغ)
        'LVS',  # Las Vegas Sands (قمار)
        'WYNN',  # Wynn Resorts (قمار)
        'MGM',  # MGM Resorts (قمار)
        'DNKN',  # Dunkin (نقاش حول التحليل)
        'CRUS',  # Cirrus Logic (أجهزة قمار)
    }

    @staticmethod
    def check_sector(sector: str) -> Tuple[bool, str]:
        """
        فحص القطاع
        Returns: (هل القطاع حلال، الملاحظة)
        """
        if not sector:
            return True, "لا توجد معلومات قطاع"

        sector_lower = sector.lower()

        # فحص القطاعات المحرمة
        for forbidden in IslamicScreening.FORBIDDEN_SECTORS:
            if forbidden.lower() in sector_lower:
                return False, f"❌ القطاع '{sector}' غير حلال (مستبعد)"

        return True, f"✅ القطاع '{sector}' مقبول"

    @staticmethod
    def check_debt_ratio(debt_to_equity: float) -> Tuple[bool, str]:
        """
        فحص نسبة الديون (المقاولة المكرومة)
        وفقاً لمعايير الشريعة الإسلامية
        """
        if debt_to_equity is None:
            return True, "لا توجد بيانات الديون"

        max_debt_ratio = ISLAMIC_SCREENING_RULES['interest_bearing_debt_ratio']

        if debt_to_equity < max_debt_ratio:
            return True, f"✅ نسبة الديون منخفضة ({debt_to_equity:.1%})"
        elif debt_to_equity < max_debt_ratio * 1.5:
            return True, f"⚠️ نسبة الديون مرتفعة نسبياً ({debt_to_equity:.1%}) - مقبول"
        else:
            return False, f"❌ نسبة الديون مرتفعة جداً ({debt_to_equity:.1%}) - غير مقبول"

    @staticmethod
    def check_haram_revenue(haram_revenue_ratio: float) -> Tuple[bool, str]:
        """
        فحص نسبة الدخل من مصادر حرام
        """
        if haram_revenue_ratio is None:
            return True, "لا توجد بيانات عن مصادر الدخل"

        max_haram = ISLAMIC_SCREENING_RULES['haram_revenue_ratio']

        if haram_revenue_ratio < max_haram:
            return True, f"✅ الدخل من مصادر حلال ({(1-haram_revenue_ratio):.1%})"
        elif haram_revenue_ratio < max_haram * 2:
            return True, f"⚠️ جزء من الدخل من مصادر ثانوية ({haram_revenue_ratio:.1%})"
        else:
            return False, f"❌ الدخل من مصادر حرام كبيرة ({haram_revenue_ratio:.1%})"

    @staticmethod
    def check_cash_ratio(cash: float, market_cap: float) -> Tuple[bool, str]:
        """
        فحص نسبة النقد إلى القيمة السوقية
        (معيار السيولة)
        """
        if not cash or not market_cap or market_cap == 0:
            return True, "لا توجد بيانات سيولة"

        cash_ratio = cash / market_cap
        min_cash = ISLAMIC_SCREENING_RULES['cash_to_market_cap_ratio']

        if cash_ratio > min_cash * 0.5:
            return True, f"✅ السيولة كافية ({cash_ratio:.1%})"
        else:
            return False, f"❌ السيولة منخفضة جداً ({cash_ratio:.1%})"

    @staticmethod
    def screen_stock(
        symbol: str,
        sector: str = None,
        profile: Dict = None,
        fundamentals: Dict = None
    ) -> Tuple[bool, float, str]:
        """
        فحص شامل لتوافق السهم مع الشريعة الإسلامية
        Returns: (هل السهم حلال، درجة الثقة، الملاحظات)
        """

        try:
            notes = []
            confidence = 0.5
            is_compliant = True

            # 1. فحص إذا كان من الأسهم المعروفة
            if symbol in IslamicScreening.HARAM_STOCKS:
                return False, 0.0, f"❌ {symbol} معروف أنه غير حلال"

            if symbol in IslamicScreening.KNOWN_HALAL_STOCKS:
                return True, 1.0, f"✅ {symbol} من قائمة الأسهم الحلال المعروفة"

            # 2. فحص القطاع
            if sector:
                sector_ok, sector_note = IslamicScreening.check_sector(sector)
                notes.append(sector_note)
                if not sector_ok:
                    is_compliant = False
                    confidence = 0.2
            else:
                notes.append("⚠️ لا توجد معلومات قطاع")

            # 3. فحص نسبة الديون
            if fundamentals and 'debt_to_equity' in fundamentals:
                debt_ok, debt_note = IslamicScreening.check_debt_ratio(
                    fundamentals.get('debt_to_equity')
                )
                notes.append(debt_note)
                if not debt_ok:
                    is_compliant = False
                    confidence = max(confidence - 0.3, 0.0)
                else:
                    confidence = min(confidence + 0.2, 1.0)

            # 4. فحص مصادر الدخل
            if fundamentals and 'haram_revenue_ratio' in fundamentals:
                revenue_ok, revenue_note = IslamicScreening.check_haram_revenue(
                    fundamentals.get('haram_revenue_ratio')
                )
                notes.append(revenue_note)
                if not revenue_ok:
                    is_compliant = False

            # 5. فحص السيولة
            if profile and 'cash' in profile and profile.get('market_cap'):
                cash_ok, cash_note = IslamicScreening.check_cash_ratio(
                    profile.get('cash'),
                    profile.get('market_cap')
                )
                notes.append(cash_note)

            # النتيجة النهائية
            final_note = "\n".join(notes)

            if is_compliant:
                emoji = "✅" if confidence > 0.8 else "⚠️"
                final_note = f"{emoji} السهم متوافق مع الشريعة الإسلامية\n{final_note}"
            else:
                final_note = f"❌ السهم غير متوافق مع الشريعة الإسلامية\n{final_note}"

            return is_compliant, confidence, final_note

        except Exception as e:
            logger.error(f"خطأ في فحص التوافق الإسلامي {symbol}: {e}")
            return True, 0.5, f"⚠️ خطأ في الفحص: {str(e)}"

    @staticmethod
    def get_zakat_information(symbol: str, price: float, quantity: int) -> Dict:
        """
        معلومات عن الزكاة على الأسهم
        """
        total_value = price * quantity

        return {
            'symbol': symbol,
            'shares': quantity,
            'price_per_share': price,
            'total_value': total_value,
            'zakat_2_5_percent': total_value * 0.025,
            'note': 'الزكاة على الأسهم 2.5% من قيمتها السوقية إذا كانت للتجارة'
        }
