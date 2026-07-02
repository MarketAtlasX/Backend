"""Global globe-data routes at the root level (outside /countries prefix).

Frontend calls these without a country code prefix:
  GET /api/relations/trade    →  /relations/trade
  GET /api/relations/military →  /relations/military
  GET /api/ports              →  /ports
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.military_relation_repository import MilitaryRelationRepository
from app.repositories.port_repository import PortRepository
from app.repositories.trade_route_repository import TradeRouteRepository
from app.serializers import _military_relation_to_dict, _port_to_dict, _trade_route_to_dict

router = APIRouter(tags=["globe"])


@router.get("/relations/trade")
async def get_all_trade_routes(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get all trade routes for the globe visualization."""
    repo = TradeRouteRepository(db)
    routes = await repo.get_all()
    return [_trade_route_to_dict(r) for r in routes]


@router.get("/relations/military")
async def get_all_military_relations(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get all military relations for the globe visualization."""
    repo = MilitaryRelationRepository(db)
    relations = await repo.get_all()
    return [_military_relation_to_dict(r) for r in relations]


@router.get("/ports")
async def get_all_ports(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get all ports for the globe visualization."""
    repo = PortRepository(db)
    ports = await repo.get_all()
    return [_port_to_dict(p) for p in ports]
