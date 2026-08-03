from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.portfolio import (
    PortfolioCreate,
    PortfolioRead,
    PortfolioUpdate,
    build_allocation_payload,
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post("", response_model=PortfolioRead, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    body: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioRead:
    portfolio = Portfolio(
        user_id=current_user.id,
        name=body.name,
        allocation=build_allocation_payload(body.allocation),
    )
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return PortfolioRead.model_validate(portfolio)


@router.get("", response_model=list[PortfolioRead])
async def list_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PortfolioRead]:
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.user_id == current_user.id)
        .order_by(Portfolio.created_at.desc())
    )
    return [PortfolioRead.model_validate(p) for p in result.scalars().all()]


@router.get("/{portfolio_id}", response_model=PortfolioRead)
async def get_portfolio(
    portfolio_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioRead:
    portfolio = await _owned_portfolio(db, portfolio_id, current_user.id)
    return PortfolioRead.model_validate(portfolio)


@router.patch("/{portfolio_id}", response_model=PortfolioRead)
async def update_portfolio(
    portfolio_id: str,
    body: PortfolioUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioRead:
    portfolio = await _owned_portfolio(db, portfolio_id, current_user.id)
    if body.name is not None:
        portfolio.name = body.name
    if body.allocation is not None:
        portfolio.allocation = build_allocation_payload(body.allocation)
    await db.commit()
    await db.refresh(portfolio)
    return PortfolioRead.model_validate(portfolio)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    portfolio = await _owned_portfolio(db, portfolio_id, current_user.id)
    await db.delete(portfolio)
    await db.commit()


async def _owned_portfolio(db: AsyncSession, portfolio_id: str, user_id: int) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio
