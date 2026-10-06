"""Models for the Current Portfolio feature - named ticker+shares holdings
lists owned by a dashboard username. Deliberately separate from
strategy_models.py's Portfolio/Position, which are part of an unrelated
"strategy backtester" object graph (mandatory Strategy FK, cash-balance/
rebalancing semantics, no owner column) used only by a standalone test
script - nothing in the live app touches those."""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class UserPortfolio(Base):
    """A named collection of stock/ETF holdings owned by a dashboard username.
    owner_username follows the same plain-string-no-FK pattern as
    BatchJob.created_by (strategy_models.py) - there is no users table in this app."""
    __tablename__ = "user_portfolios"

    id = Column(Integer, primary_key=True, index=True)
    owner_username = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('owner_username', 'name', name='uq_user_portfolios_owner_name'),
    )

    holdings = relationship(
        "PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan"
    )


class PortfolioHolding(Base):
    """A ticker + shares row within a UserPortfolio. Unique on (portfolio_id, ticker) -
    adding the same ticker again is an upsert (shares updated), not a duplicate row."""
    __tablename__ = "portfolio_holdings"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("user_portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False)
    shares = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('portfolio_id', 'ticker', name='uq_portfolio_holdings_portfolio_ticker'),
    )

    portfolio = relationship("UserPortfolio", back_populates="holdings")
