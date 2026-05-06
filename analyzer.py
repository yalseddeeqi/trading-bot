"""
تحليل البيانات - المؤشرات الفنية والأساسية
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import logging
from ta import momentum, trend, volatility
from datetime import datetime, timedelta
from database import SessionLocal, TechnicalIndicator, FundamentalData, Stock
from config import (
    RSI_OVERSOLD, RSI_OVERBOUGHT, MACD_THRESHOLD,
    MA_SHORT_PERIOD, MA_LONG_PERIOD,
    PE_MAX, PE_MIN, DIVIDEND_YIELD_MIN,
    VOLUME_THRESHOLD
)

logger = logging.getLogger(__name__)


class StockAnalyzer:
    """محلل البيانات"""

    def __init__(self):
        self.db = SessionLocal()

    def calculate_technical_indicators(self, symbol: str, prices_df: pd.DataFrame) -> Optional[Dict]:
        """حساب المؤشرات الفنية"""
        try:
            if prices_df.empty or len(prices_df) < 50:
                return None

            close = prices_df['close'].values
            high = prices_df['high'].values
            low = prices_df['low'].values
            volume = prices_df['volume'].values

            # حساب المؤشرات
            rsi = momentum.rsi(pd.Series(close), window=14).iloc[-1]
            macd_line = trend.macd(pd.Series(close)).iloc[-1]
            macd_signal = trend.macd_signal(pd.Series(close)).iloc[-1]
            macd_histogram = trend.macd_diff(pd.Series(close)).iloc[-1]

            # Moving Averages
            sma_20 = trend.sma_indicator(pd.Series(close), window=20).iloc[-1]
            sma_50 = trend.sma_indicator(pd.Series(close), window=50).iloc[-1]
            sma_200 = trend.sma_indicator(pd.Series(close), window=200).iloc[-1] if len(close) > 200 else None

            # Bollinger Bands
            bb_high = volatility.bollinger_hband(pd.Series(close)).iloc[-1]
            bb_mid = volatility.bollinger_mavg(pd.Series(close)).iloc[-1]
            bb_low = volatility.bollinger_lband(pd.Series(close)).iloc[-1]

            return {
                'symbol': symbol,
                'date': datetime.utcnow(),
                'rsi': float(rsi) if not np.isnan(rsi) else None,
                'macd': float(macd_line) if not np.isnan(macd_line) else None,
                'macd_signal': float(macd_signal) if not np.isnan(macd_signal) else None,
                'macd_histogram': float(macd_histogram) if not np.isnan(macd_histogram) else None,
                'sma_20': float(sma_20) if not np.isnan(sma_20) else None,
                'sma_50': float(sma_50) if not np.isnan(sma_50) else None,
                'sma_200': float(sma_200) if sma_200 and not np.isnan(sma_200) else None,
                'bb_upper': float(bb_high) if not np.isnan(bb_high) else None,
                'bb_middle': float(bb_mid) if not np.isnan(bb_mid) else None,
                'bb_lower': float(bb_low) if not np.isnan(bb_low) else None,
            }

        except Exception as e:
            logger.error(f"خطأ في حساب المؤشرات الفنية {symbol}: {e}")
            return None

    def analyze_daily_trading(self, symbol: str, current_price: float, technical: Dict) -> Tuple[bool, float, str]:
        """
        تحليل فرص المضاربة اليومية
        Returns: (هل هناك فرصة، درجة الثقة، السبب)
        """
        try:
            if not technical:
                return False, 0.0, "لا توجد بيانات فنية كافية"

            rsi = technical.get('rsi')
            macd = technical.get('macd')
            macd_signal = technical.get('macd_signal')
            macd_hist = technical.get('macd_histogram')
            sma_20 = technical.get('sma_20')
            sma_50 = technical.get('sma_50')

            reasons = []
            confidence = 0.0
            max_confidence = 0.0

            # معايير الشراء
            buy_signals = 0
            total_signals = 0

            # 1. RSI - تجاوز الشراء الزائد
            if rsi and rsi < RSI_OVERSOLD:
                buy_signals += 1
                reasons.append(f"RSI منخفض جداً ({rsi:.1f})")
                confidence += 0.25
                total_signals += 1
            elif rsi and rsi < 40:
                reasons.append(f"RSI ضعيف ({rsi:.1f})")
                confidence += 0.15
                total_signals += 1

            # 2. MACD - تقاطع إيجابي
            if macd and macd_signal and macd_hist:
                if macd > macd_signal and macd_hist > 0:
                    buy_signals += 1
                    reasons.append("MACD فوق الإشارة - اتجاه صعودي")
                    confidence += 0.3
                    total_signals += 1
                elif macd < macd_signal:
                    reasons.append("MACD تحت الإشارة - اتجاه هابط")
                    confidence -= 0.15
                    total_signals += 1

            # 3. Moving Averages - الدعم والمقاومة
            if sma_20 and sma_50 and current_price:
                if current_price > sma_20 > sma_50:
                    reasons.append("السعر فوق المتوسطات - اتجاه صعودي قوي")
                    confidence += 0.25
                    total_signals += 1
                elif current_price < sma_20 < sma_50:
                    reasons.append("السعر تحت المتوسطات - اتجاه هابط")
                    confidence -= 0.2
                    total_signals += 1
                elif current_price < sma_20:
                    reasons.append("السعر اقترب من الدعم")
                    confidence += 0.1
                    total_signals += 1

            # حساب درجة الثقة النهائية
            if total_signals > 0:
                confidence = min(max(confidence / total_signals, 0.0), 1.0)

            has_opportunity = confidence > 0.5 and buy_signals >= 1
            reason = " | ".join(reasons) if reasons else "لا توجد إشارات شراء قوية"

            return has_opportunity, confidence, reason

        except Exception as e:
            logger.error(f"خطأ في تحليل المضاربة {symbol}: {e}")
            return False, 0.0, f"خطأ: {str(e)}"

    def analyze_long_term_investment(self, symbol: str, fundamental: Dict) -> Tuple[bool, float, str]:
        """
        تحليل فرص الاستثمار طويل الأجل
        Returns: (هل هناك فرصة، درجة الثقة، السبب)
        """
        try:
            if not fundamental:
                return False, 0.0, "لا توجد بيانات أساسية"

            reasons = []
            confidence = 0.0
            buy_signals = 0

            pe_ratio = fundamental.get('pe_ratio')
            ps_ratio = fundamental.get('ps_ratio')
            dividend_yield = fundamental.get('dividend_yield')
            roe = fundamental.get('roe')
            debt_to_equity = fundamental.get('debt_to_equity')

            # 1. نسبة P/E معقولة
            if pe_ratio and PE_MIN < pe_ratio < PE_MAX:
                buy_signals += 1
                reasons.append(f"P/E معقول ({pe_ratio:.1f})")
                confidence += 0.3
            elif pe_ratio and pe_ratio < PE_MIN:
                reasons.append(f"P/E منخفض جداً ({pe_ratio:.1f}) - قد يكون هناك مشكلة")
                confidence -= 0.1
            elif pe_ratio and pe_ratio > PE_MAX:
                reasons.append(f"P/E مرتفع جداً ({pe_ratio:.1f})")
                confidence -= 0.15

            # 2. عائد الأرباح
            if dividend_yield and dividend_yield >= DIVIDEND_YIELD_MIN:
                buy_signals += 1
                reasons.append(f"عائد أرباح جيد ({dividend_yield:.2%})")
                confidence += 0.25

            # 3. العائد على حقوق المساهمين
            if roe and roe > 0.15:
                buy_signals += 1
                reasons.append(f"ROE قوي ({roe:.1%})")
                confidence += 0.2
            elif roe and roe > 0.10:
                reasons.append(f"ROE جيد ({roe:.1%})")
                confidence += 0.1

            # 4. نسبة الدين
            if debt_to_equity and debt_to_equity < 1:
                buy_signals += 1
                reasons.append(f"نسبة ديون صحية ({debt_to_equity:.1f})")
                confidence += 0.15
            elif debt_to_equity and debt_to_equity > 2:
                reasons.append(f"نسبة ديون مرتفعة ({debt_to_equity:.1f})")
                confidence -= 0.15

            has_opportunity = confidence > 0.4 and buy_signals >= 2
            reason = " | ".join(reasons) if reasons else "البيانات الأساسية غير كافية"

            return has_opportunity, confidence, reason

        except Exception as e:
            logger.error(f"خطأ في تحليل الاستثمار طويل الأجل {symbol}: {e}")
            return False, 0.0, f"خطأ: {str(e)}"

    def close(self):
        """إغلاق الاتصال"""
        self.db.close()
