"""Gamification API router.

Endpoints for points, badges, leaderboard, and analytics.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user, require_permission
from app.core.db.deps import get_db
from app.core.gamification.analytics_service import AnalyticsService
from app.core.gamification.badge_service import BadgeService
from app.core.gamification.leaderboard_service import LeaderboardService
from app.core.gamification.points_service import PointsService
from app.models.user import User
from app.modules.gamification.schemas import (
    AlertResponse,
    BadgeCreate,
    BadgeResponse,
    GamificationEventResponse,
    LeaderboardEntryResponse,
    TeamAnalyticsResponse,
    UserBadgeResponse,
    UserPointsResponse,
)
from app.schemas.common import StandardListResponse, StandardResponse

router = APIRouter()


# --- Dependencies ---

def _get_points_service(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PointsService:
    return PointsService(db, current_user.tenant_id)


def _get_badge_service(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BadgeService:
    return BadgeService(db, current_user.tenant_id)


def _get_leaderboard_service(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LeaderboardService:
    return LeaderboardService(db, current_user.tenant_id)


# --- User Points ---

@router.get(
    "/me/points",
    response_model=StandardResponse[UserPointsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get my points",
)
async def get_my_points(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PointsService, Depends(_get_points_service)],
) -> StandardResponse[UserPointsResponse]:
    """Get current user's points, level, and streak."""
    user_points = service.get_user_points(current_user.id)

    if not user_points:
        return StandardResponse(
            data=UserPointsResponse(
                id=current_user.id,
                user_id=current_user.id,
                total_points=0,
                level=1,
                current_streak=0,
                longest_streak=0,
                progress_to_next_level=0.0,
                points_to_next_level=100,
                updated_at=current_user.created_at,
            ),
            message="No points yet",
        )

    # Calculate progress
    current_level_min = service.points_for_level(user_points.level)
    next_level_min = service.points_for_level(user_points.level + 1)
    points_in_level = user_points.total_points - current_level_min
    points_needed = next_level_min - current_level_min
    progress = (points_in_level / points_needed * 100) if points_needed > 0 else 100.0

    response = UserPointsResponse(
        id=user_points.id,
        user_id=user_points.user_id,
        total_points=user_points.total_points,
        level=user_points.level,
        current_streak=user_points.current_streak,
        longest_streak=user_points.longest_streak,
        last_activity_date=(
            str(user_points.last_activity_date) if user_points.last_activity_date else None
        ),
        progress_to_next_level=round(progress, 1),
        points_to_next_level=max(0, next_level_min - user_points.total_points),
        updated_at=user_points.updated_at,
    )

    return StandardResponse(data=response, message="Points retrieved successfully")


# --- Points History ---

@router.get(
    "/me/history",
    response_model=StandardListResponse[GamificationEventResponse],
    status_code=status.HTTP_200_OK,
    summary="Get my points history",
)
async def get_my_history(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PointsService, Depends(_get_points_service)],
    limit: int = Query(default=50, ge=1, le=200, description="Max events to return"),
) -> StandardListResponse[GamificationEventResponse]:
    """Get current user's gamification event history."""
    events = service.get_user_events(current_user.id, limit=limit)
    total = len(events)

    return StandardListResponse(
        data=[GamificationEventResponse.model_validate(e) for e in events],
        meta={
            "total": total,
            "page": 1,
            "page_size": max(1, total) if total > 0 else limit,
            "total_pages": 1,
        },
        message="History retrieved successfully",
    )


# --- Badges ---

@router.get(
    "/me/badges",
    response_model=StandardListResponse[UserBadgeResponse],
    status_code=status.HTTP_200_OK,
    summary="Get my badges",
)
async def get_my_badges(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BadgeService, Depends(_get_badge_service)],
) -> StandardListResponse[UserBadgeResponse]:
    """Get badges earned by the current user."""
    user_badges = service.get_user_badges(current_user.id)
    total = len(user_badges)

    data = []
    for ub in user_badges:
        badge = ub.badge
        data.append(
            UserBadgeResponse(
                id=ub.id,
                badge_id=ub.badge_id,
                badge_name=badge.name if badge else "",
                badge_description=badge.description if badge else None,
                badge_icon=badge.icon if badge else "trophy",
                earned_at=ub.earned_at,
            )
        )

    return StandardListResponse(
        data=data,
        meta={
            "total": total,
            "page": 1,
            "page_size": max(1, total) if total > 0 else 20,
            "total_pages": 1,
        },
        message="Badges retrieved successfully",
    )


@router.get(
    "/badges",
    response_model=StandardListResponse[BadgeResponse],
    status_code=status.HTTP_200_OK,
    summary="List all badges",
)
async def list_badges(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BadgeService, Depends(_get_badge_service)],
    active_only: bool = Query(default=True, description="Only show active badges"),
) -> StandardListResponse[BadgeResponse]:
    """List all available badges for the tenant."""
    badges = service.list_badges(active_only=active_only)
    total = len(badges)

    return StandardListResponse(
        data=[BadgeResponse.model_validate(b) for b in badges],
        meta={
            "total": total,
            "page": 1,
            "page_size": max(1, total) if total > 0 else 20,
            "total_pages": 1,
        },
        message="Badges retrieved successfully",
    )


@router.post(
    "/badges",
    response_model=StandardResponse[BadgeResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create badge",
)
async def create_badge(
    badge_data: BadgeCreate,
    current_user: Annotated[User, Depends(require_permission("gamification.manage"))],
    service: Annotated[BadgeService, Depends(_get_badge_service)],
) -> StandardResponse[BadgeResponse]:
    """Create a new badge (admin only)."""
    badge = service.create_badge(badge_data.model_dump())

    return StandardResponse(
        data=BadgeResponse.model_validate(badge),
        message="Badge created successfully",
    )


# --- Leaderboard ---

@router.get(
    "/leaderboard",
    response_model=StandardListResponse[LeaderboardEntryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get leaderboard",
)
async def get_leaderboard(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[LeaderboardService, Depends(_get_leaderboard_service)],
    db: Annotated[Session, Depends(get_db)],
    period: str = Query(default="all_time", description="Period: daily, weekly, monthly, all_time"),
    limit: int = Query(default=10, ge=1, le=50, description="Max entries"),
) -> StandardListResponse[LeaderboardEntryResponse]:
    """Get leaderboard for a period. Only shows rank, not other users' points."""
    entries = service.get_leaderboard(period=period, limit=limit)
    total = len(entries)

    data = []
    for entry in entries:
        # Get user name
        user = db.query(User).filter(User.id == entry.user_id).first()
        user_name = f"{user.first_name} {user.last_name}" if user else "Unknown"

        data.append(
            LeaderboardEntryResponse(
                rank=entry.rank,
                user_id=entry.user_id,
                user_name=user_name,
                points=entry.points if entry.user_id == current_user.id else 0,
                is_current_user=entry.user_id == current_user.id,
            )
        )

    return StandardListResponse(
        data=data,
        meta={
            "total": total,
            "page": 1,
            "page_size": max(1, total) if total > 0 else limit,
            "total_pages": 1,
        },
        message="Leaderboard retrieved successfully",
    )


# --- Analytics (Manager) ---

def _get_analytics_service(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("gamification.manage"))],
) -> AnalyticsService:
    return AnalyticsService(db, current_user.tenant_id)


@router.get(
    "/analytics/team",
    response_model=StandardResponse[TeamAnalyticsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get team analytics",
)
async def get_team_analytics(
    current_user: Annotated[User, Depends(require_permission("gamification.manage"))],
    service: Annotated[AnalyticsService, Depends(_get_analytics_service)],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[TeamAnalyticsResponse]:
    """Get team gamification analytics (manager only)."""
    # Get all users in the same tenant
    team_users = db.query(User.id).filter(User.tenant_id == current_user.tenant_id).all()
    user_ids = [u.id for u in team_users]

    analytics = service.get_team_analytics(user_ids)

    return StandardResponse(
        data=TeamAnalyticsResponse(**analytics),
        message="Team analytics retrieved successfully",
    )


@router.get(
    "/analytics/alerts",
    response_model=StandardListResponse[AlertResponse],
    status_code=status.HTTP_200_OK,
    summary="Get predictive alerts",
)
async def get_alerts(
    current_user: Annotated[User, Depends(require_permission("gamification.manage"))],
    service: Annotated[AnalyticsService, Depends(_get_analytics_service)],
    db: Annotated[Session, Depends(get_db)],
) -> StandardListResponse[AlertResponse]:
    """Get predictive alerts for team members (manager only)."""
    team_users = db.query(User.id).filter(User.tenant_id == current_user.tenant_id).all()
    user_ids = [u.id for u in team_users]

    alerts = service.get_alerts(user_ids)
    total = len(alerts)

    return StandardListResponse(
        data=[AlertResponse(**a) for a in alerts],
        meta={
            "total": total,
            "page": 1,
            "page_size": max(1, total) if total > 0 else 20,
            "total_pages": 1,
        },
        message="Alerts retrieved successfully",
    )
