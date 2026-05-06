"""
قاعدة البيانات والنماذج
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Stock(Base):
    """نموذج السهم المراقب"""
    __tablename__ = "stocks"

    symbol = Column(String, primary_key=True)
    name = Column(String)
    sector = Column(String)
    industry = Column(String)
    market_cap = Column(Float)

    # معايير إسلامية
    is_islamic_compliant = Column(Boolean, default=False)
    haram_revenue_ratio = Column(Float)
    interest_bearing_debt_ratio = Column(Float)

    # آخر تحديث
    last_updated = Column(DateTime, default=datetime.utcnow)

    # إحصائيات
    price = Column(Float)
    change_percent = Column(Float)
    volume = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)


class PriceHistory(Base):
    """السجل التاريخي للأسعار"""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    date = Column(DateTime)
    open_price = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)


class TechnicalIndicator(Base):
    """المؤشرات الفنية"""
    __tablename__ = "technical_indicators"

    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    date = Column(DateTime)

    # المؤشرات الفنية
    rsi = Column(Float)  # Relative Strength Index
    macd = Column(Float)  # MACD
    macd_signal = Column(Float)
    macd_histogram = Column(Float)
    sma_20 = Column(Float)  # Simple Moving Average 20
    sma_50 = Column(Float)
    sma_200 = Column(Float)
    bb_upper = Column(Float)  # Bollinger Bands
    bb_middle = Column(Float)
    bb_lower = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)


class FundamentalData(Base):
    """البيانات الأساسية"""
    __tablename__ = "fundamental_data"

    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    date = Column(DateTime)

    # النسب المالية
    pe_ratio = Column(Float)  # Price to Earnings
    ps_ratio = Column(Float)  # Price to Sales
    pb_ratio = Column(Float)  # Price to Book
    peg_ratio = Column(Float)  # PEG Ratio

    # العائدات والأرباح
    eps = Column(Float)  # Earnings Per Share
    dividend_yield = Column(Float)
    revenue_growth = Column(Float)
    earnings_growth = Column(Float)

    # الصحة المالية
    current_ratio = Column(Float)
    debt_to_equity = Column(Float)
    roe = Column(Float)  # Return on Equity
    roa = Column(Float)  # Return on Assets

    created_at = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    """الفرص والتنبيهات"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    alert_type = Column(String)  # 'daily_trading', 'long_term', 'urgent'
    reason = Column(String)  # سبب التنبيه

    # البيانات
    current_price = Column(Float)
    target_price = Column(Float)
    confidence_score = Column(Float)  # ثقة التنبيه من 0-1

    # الحالة
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NewsArticle(Base):
    """مقالات الأخبار"""
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    title = Column(String)
    content = Column(String)
    source = Column(String)
    url = Column(String)

    # التحليل
    sentiment = Column(String)  # 'positive', 'negative', 'neutral'
    importance = Column(Integer)  # 1-5

    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# إنشاء الجداول
Base.metadata.create_all(bind=engine)


def get_db():
    """الحصول على جلسة قاعدة البيانات"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
