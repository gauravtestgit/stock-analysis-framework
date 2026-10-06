"""API endpoints for the Current Portfolio page - lets a user create multiple
named portfolios of stock/ETF holdings (ticker + shares), see live market
value per holding, and (via the dashboard, not this router) push a
portfolio's tickers into the existing watchlist.

Deliberately does not touch strategy_models.py's Portfolio/Position (an
unrelated, unused "strategy backtester" object graph) - see
models/portfolio_models.py's module docstring.
"""

import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.database import SessionLocal
from ..models.portfolio_models import UserPortfolio, PortfolioHolding
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider

router = APIRouter()


class PortfolioCreateRequest(BaseModel):
    name: str
    owner_username: str = "demo"


class HoldingUpsertRequest(BaseModel):
    ticker: str
    shares: float


def _portfolio_to_dict(portfolio: UserPortfolio) -> dict:
    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "owner_username": portfolio.owner_username,
        "holding_count": len(portfolio.holdings),
        "created_at": portfolio.created_at.isoformat() if portfolio.created_at else None,
        "updated_at": portfolio.updated_at.isoformat() if portfolio.updated_at else None,
    }


def _holding_to_dict(holding: PortfolioHolding) -> dict:
    return {
        "id": holding.id,
        "ticker": holding.ticker,
        "shares": holding.shares,
    }


# Live price cache: ticker -> (price, fetched_at_epoch_seconds). Short TTL (not
# lru_cache, which never expires and would go stale) so repeated Streamlit reruns
# don't hammer Yahoo Finance on every unrelated widget interaction, while prices
# stay reasonably fresh within a session.
_PRICE_CACHE_TTL_SECONDS = 60
_price_cache: dict = {}


def _get_cached_price(provider: YahooFinanceProvider, ticker: str) -> tuple:
    """Returns (price, is_stale). is_stale=True means the live fetch failed and a
    previously-cached value was returned instead (or None if there was never one)."""
    now = time.time()
    cached = _price_cache.get(ticker)
    if cached and (now - cached[1]) < _PRICE_CACHE_TTL_SECONDS:
        return cached[0], False

    try:
        metrics = provider.get_financial_metrics(ticker)
        price = metrics.get('current_price') if 'error' not in metrics else None
    except Exception:
        price = None

    if price:
        _price_cache[ticker] = (price, now)
        return price, False

    # Live fetch failed - fall back to whatever's cached (even if past TTL) rather
    # than showing nothing.
    if cached:
        return cached[0], True
    return None, True


@router.get("/")
async def list_portfolios(owner_username: str):
    """Portfolios owned by owner_username, ordered by name."""
    db = SessionLocal()
    try:
        portfolios = (
            db.query(UserPortfolio)
            .filter(UserPortfolio.owner_username == owner_username)
            .order_by(UserPortfolio.name.asc())
            .all()
        )
        return {"portfolios": [_portfolio_to_dict(p) for p in portfolios]}
    finally:
        db.close()


@router.post("/")
async def create_portfolio(request: PortfolioCreateRequest):
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Portfolio name cannot be empty")

    db = SessionLocal()
    try:
        portfolio = UserPortfolio(owner_username=request.owner_username, name=name)
        db.add(portfolio)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Portfolio '{name}' already exists",
            )
        db.refresh(portfolio)
        return _portfolio_to_dict(portfolio)
    finally:
        db.close()


@router.delete("/{portfolio_id}")
async def delete_portfolio(portfolio_id: int):
    db = SessionLocal()
    try:
        portfolio = db.query(UserPortfolio).filter(UserPortfolio.id == portfolio_id).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        db.delete(portfolio)  # cascades to holdings via relationship + DB FK
        db.commit()
        return {"deleted": True, "portfolio_id": portfolio_id}
    finally:
        db.close()


@router.get("/{portfolio_id}/holdings")
async def list_holdings(portfolio_id: int):
    """Holdings for a portfolio without live price - fast path."""
    db = SessionLocal()
    try:
        portfolio = db.query(UserPortfolio).filter(UserPortfolio.id == portfolio_id).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        return {
            "portfolio_id": portfolio_id,
            "holdings": [_holding_to_dict(h) for h in portfolio.holdings],
        }
    finally:
        db.close()


@router.get("/{portfolio_id}/holdings/priced")
async def list_holdings_priced(portfolio_id: int):
    """Holdings with live current_price/market_value computed server-side - what the
    dashboard's main holdings table calls."""
    db = SessionLocal()
    try:
        portfolio = db.query(UserPortfolio).filter(UserPortfolio.id == portfolio_id).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        provider = YahooFinanceProvider()
        holdings = []
        total_market_value = 0.0
        for h in portfolio.holdings:
            price, is_stale = _get_cached_price(provider, h.ticker)
            market_value = (price * h.shares) if price is not None else None
            if market_value is not None:
                total_market_value += market_value
            holdings.append({
                "id": h.id,
                "ticker": h.ticker,
                "shares": h.shares,
                "current_price": price,
                "market_value": market_value,
                "price_stale": is_stale,
            })

        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.name,
            "holdings": holdings,
            "total_market_value": total_market_value,
            "priced_at": datetime.utcnow().isoformat(),
        }
    finally:
        db.close()


@router.post("/{portfolio_id}/holdings")
async def upsert_holding(portfolio_id: int, request: HoldingUpsertRequest):
    """Add a holding, or - if this ticker is already in the portfolio - add to its
    existing shares rather than creating a duplicate row (same dedupe philosophy as
    the watchlist's own add logic)."""
    if request.shares <= 0:
        raise HTTPException(status_code=400, detail="shares must be greater than 0")

    ticker = request.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker cannot be empty")

    db = SessionLocal()
    try:
        portfolio = db.query(UserPortfolio).filter(UserPortfolio.id == portfolio_id).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        holding = (
            db.query(PortfolioHolding)
            .filter(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.ticker == ticker)
            .first()
        )
        if holding:
            holding.shares += request.shares
        else:
            holding = PortfolioHolding(portfolio_id=portfolio_id, ticker=ticker, shares=request.shares)
            db.add(holding)

        db.commit()
        db.refresh(holding)
        return _holding_to_dict(holding)
    finally:
        db.close()


@router.delete("/{portfolio_id}/holdings/{holding_id}")
async def remove_holding(portfolio_id: int, holding_id: int):
    db = SessionLocal()
    try:
        holding = (
            db.query(PortfolioHolding)
            .filter(PortfolioHolding.id == holding_id, PortfolioHolding.portfolio_id == portfolio_id)
            .first()
        )
        if not holding:
            raise HTTPException(status_code=404, detail="Holding not found")
        db.delete(holding)
        db.commit()
        return {"deleted": True, "holding_id": holding_id}
    finally:
        db.close()
