"""
جلب البيانات من APIs والمصادر الخارجية
"""
import finnhub
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging
from config import (
    FINNHUB_API_KEY, NEWSAPI_KEY,
    WATCHLIST, EXCLUDED_SECTORS
)
from database import SessionLocal, Stock, PriceHistory, FundamentalData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# إعداد Finnhub
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)


class DataFetcher:
    """جلب بيانات الأسهم"""

    def __init__(self):
        self.db = SessionLocal()
        self.finnhub_client = finnhub_client

    def fetch_quote(self, symbol: str) -> Optional[Dict]:
        """جلب سعر السهم الحالي"""
        try:
            data = self.finnhub_client.quote(symbol)
            return {
                'symbol': symbol,
                'price': data.get('c'),
                'high': data.get('h'),
                'low': data.get('l'),
                'open': data.get('o'),
                'previous_close': data.get('pc'),
                'change': data.get('c') - data.get('pc') if data.get('c') and data.get('pc') else 0,
                'change_percent': ((data.get('c') - data.get('pc')) / data.get('pc') * 100) if data.get('pc') else 0,
                'timestamp': data.get('t')
            }
        except Exception as e:
            logger.error(f"خطأ في جلب سعر {symbol}: {e}")
            return None

    def fetch_company_profile(self, symbol: str) -> Optional[Dict]:
        """جلب ملف تعريف الشركة"""
        try:
            data = self.finnhub_client.company_profile2(symbol=symbol)
            return {
                'symbol': symbol,
                'name': data.get('name'),
                'industry': data.get('finnhubIndustry'),
                'website': data.get('weburl'),
                'market_cap': data.get('marketCapitalization'),
                'employees': data.get('employees'),
                'exchange': data.get('exchange'),
            }
        except Exception as e:
            logger.error(f"خطأ في جلب ملف الشركة {symbol}: {e}")
            return None

    def fetch_fundamental_data(self, symbol: str) -> Optional[Dict]:
        """جلب البيانات الأساسية (النسب المالية)"""
        try:
            metrics = self.finnhub_client.company_basic_financials(symbol, 'all')

            metric_data = metrics.get('metric', {})

            return {
                'symbol': symbol,
                'pe_ratio': metric_data.get('peBasicExclExtraTTM'),
                'ps_ratio': metric_data.get('psBasicExclExtraTTM'),
                'pb_ratio': metric_data.get('pbBasicExclExtraTTM'),
                'eps': metric_data.get('epsBasicExclExtraTTM'),
                'dividend_yield': metric_data.get('dividendYieldIndicatedAnnual'),
                'revenue_growth': metric_data.get('revenueCagr5Y'),
                'roe': metric_data.get('roe'),
                'roa': metric_data.get('roa'),
                'debt_to_equity': metric_data.get('totalDebt') / metric_data.get('totalEquity') if metric_data.get('totalEquity') else 0,
            }
        except Exception as e:
            logger.error(f"خطأ في جلب البيانات الأساسية {symbol}: {e}")
            return None

    def fetch_intraday_data(self, symbol: str) -> Optional[Dict]:
        """جلب بيانات اليوم (15 دقيقة)"""
        try:
            data = self.finnhub_client.quote(symbol)
            return {
                'symbol': symbol,
                'current_price': data.get('c'),
                'day_high': data.get('h'),
                'day_low': data.get('l'),
                'volume': data.get('v'),
                'volume_weighted_price': data.get('vw'),
            }
        except Exception as e:
            logger.error(f"خطأ في جلب بيانات اليوم {symbol}: {e}")
            return None

    def fetch_historical_data(self, symbol: str, days: int = 200) -> Optional[list]:
        """جلب البيانات التاريخية"""
        try:
            # نحسب التاريخ
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # جلب البيانات
            res = self.finnhub_client.stock_candles(
                symbol,
                'D',
                int(start_date.timestamp()),
                int(end_date.timestamp())
            )

            if res['s'] != 'ok':
                return None

            data = []
            for i in range(len(res['c'])):
                data.append({
                    'symbol': symbol,
                    'date': datetime.fromtimestamp(res['t'][i]),
                    'open': res['o'][i],
                    'high': res['h'][i],
                    'low': res['l'][i],
                    'close': res['c'][i],
                    'volume': res['v'][i],
                })
            return data
        except Exception as e:
            logger.error(f"خطأ في جلب البيانات التاريخية {symbol}: {e}")
            return None

    def fetch_news(self, symbol: str, limit: int = 5) -> Optional[list]:
        """جلب الأخبار الأخيرة"""
        try:
            news = self.finnhub_client.company_news(symbol, _from="2024-01-01", to="2024-12-31")

            articles = []
            for article in news[:limit]:
                articles.append({
                    'symbol': symbol,
                    'title': article.get('headline'),
                    'content': article.get('summary'),
                    'source': article.get('source'),
                    'url': article.get('url'),
                    'published_at': datetime.fromtimestamp(article.get('datetime')),
                })
            return articles
        except Exception as e:
            logger.error(f"خطأ في جلب الأخبار {symbol}: {e}")
            return None

    def get_earnings_dates(self, symbol: str) -> Optional[list]:
        """جلب تواريخ الأرباح القادمة"""
        try:
            earnings = self.finnhub_client.company_earnings(symbol)
            return [
                {
                    'date': e.get('date'),
                    'estimate': e.get('epsEstimate'),
                    'actual': e.get('epsActual'),
                    'surprise': e.get('surprise'),
                }
                for e in earnings
            ]
        except Exception as e:
            logger.error(f"خطأ في جلب تواريخ الأرباح {symbol}: {e}")
            return None

    def update_all_stocks(self):
        """تحديث بيانات جميع الأسهم"""
        logger.info("🔄 جاري تحديث بيانات الأسهم...")

        for symbol in WATCHLIST:
            try:
                # جلب البيانات
                quote = self.fetch_quote(symbol)
                profile = self.fetch_company_profile(symbol)
                fundamentals = self.fetch_fundamental_data(symbol)

                if not quote or not profile:
                    continue

                # حفظ بيانات السهم
                stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
                if not stock:
                    stock = Stock(symbol=symbol)

                stock.name = profile.get('name')
                stock.sector = profile.get('industry')
                stock.market_cap = profile.get('market_cap')
                stock.price = quote.get('price')
                stock.change_percent = quote.get('change_percent')
                stock.last_updated = datetime.utcnow()

                self.db.add(stock)

                # حفظ البيانات الأساسية
                if fundamentals:
                    fund_data = FundamentalData(
                        symbol=symbol,
                        date=datetime.utcnow(),
                        pe_ratio=fundamentals.get('pe_ratio'),
                        ps_ratio=fundamentals.get('ps_ratio'),
                        eps=fundamentals.get('eps'),
                        dividend_yield=fundamentals.get('dividend_yield'),
                        roe=fundamentals.get('roe'),
                        debt_to_equity=fundamentals.get('debt_to_equity'),
                    )
                    self.db.add(fund_data)

                self.db.commit()
                logger.info(f"✅ تم تحديث {symbol}")

            except Exception as e:
                logger.error(f"❌ خطأ في تحديث {symbol}: {e}")
                self.db.rollback()

    def close(self):
        """إغلاق الاتصال"""
        self.db.close()
