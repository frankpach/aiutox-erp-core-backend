"""Analytics service for gamification manager dashboard."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.gamification import GamificationEvent, UserPoints

logger = get_logger(__name__)


class AnalyticsService:
    """Service for team gamification analytics and predictive alerts."""

    def __init__(self, db: Session, tenant_id: UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def get_team_analytics(self, user_ids: list[UUID]) -> dict[str, Any]:
        """Get aggregated team analytics.

        Args:
            user_ids: List of team member user IDs

        Returns:
            Dict with team velocity, trend, top performers, needs attention
        """
        if not user_ids:
            return {
                "team_velocity": 0,
                "trend": "+0%",
                "total_points": 0,
                "active_users": 0,
                "top_performers": [],
                "needs_attention": [],
            }

        # Get all user points for team
        team_points = (
            self.db.query(UserPoints)
            .filter(
                UserPoints.tenant_id == self.tenant_id,
                UserPoints.user_id.in_(user_ids),
            )
            .all()
        )

        total_points = sum(up.total_points for up in team_points)
        active_users = len([up for up in team_points if up.current_streak > 0])

        # Top performers (sorted by points desc)
        sorted_points = sorted(team_points, key=lambda x: x.total_points, reverse=True)
        top_performers = [
            {
                "user_id": str(up.user_id),
                "points": up.total_points,
                "level": up.level,
                "streak": up.current_streak,
            }
            for up in sorted_points[:5]
        ]

        # Needs attention (low activity or broken streaks)
        needs_attention = [
            {
                "user_id": str(up.user_id),
                "points": up.total_points,
                "streak": up.current_streak,
                "reason": "low_activity" if up.current_streak == 0 else "declining",
            }
            for up in team_points
            if up.current_streak == 0 or up.total_points < 50
        ]

        # Calculate trend (compare last 7 days vs previous 7 days)
        trend = self._calculate_trend(user_ids)

        return {
            "team_velocity": total_points // max(len(user_ids), 1),
            "trend": trend,
            "total_points": total_points,
            "active_users": active_users,
            "top_performers": top_performers,
            "needs_attention": needs_attention[:5],
        }

    def get_alerts(self, user_ids: list[UUID]) -> list[dict[str, Any]]:
        """Get predictive alerts for team members.

        Args:
            user_ids: List of team member user IDs

        Returns:
            List of alert dicts
        """
        alerts: list[dict[str, Any]] = []

        team_points = (
            self.db.query(UserPoints)
            .filter(
                UserPoints.tenant_id == self.tenant_id,
                UserPoints.user_id.in_(user_ids),
            )
            .all()
        )

        for up in team_points:
            # Burnout risk: very high activity (streak > 14 and high points)
            if up.current_streak > 14 and up.total_points > 500:
                alerts.append(
                    {
                        "type": "burnout_risk",
                        "employee_id": str(up.user_id),
                        "employee_name": "",
                        "severity": "medium",
                        "recommendation": "Consider encouraging a break or varied tasks",
                        "data": {
                            "streak": up.current_streak,
                            "points": up.total_points,
                        },
                    }
                )

            # Disengagement: no activity for 3+ days
            if up.last_activity_date:
                days_inactive = (datetime.now(UTC).date() - up.last_activity_date).days
                if days_inactive >= 3:
                    severity = "high" if days_inactive >= 7 else "medium"
                    alerts.append(
                        {
                            "type": "disengagement",
                            "employee_id": str(up.user_id),
                            "employee_name": "",
                            "severity": severity,
                            "recommendation": "Check in with this team member",
                            "data": {
                                "days_inactive": days_inactive,
                                "last_activity": str(up.last_activity_date),
                            },
                        }
                    )

        return alerts

    def _calculate_trend(self, user_ids: list[UUID]) -> str:
        """Calculate points trend comparing last 7 days vs previous 7 days."""
        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)

        recent_points = (
            self.db.query(func.coalesce(func.sum(GamificationEvent.points_earned), 0))
            .filter(
                GamificationEvent.tenant_id == self.tenant_id,
                GamificationEvent.user_id.in_(user_ids),
                GamificationEvent.created_at >= week_ago,
            )
            .scalar()
        ) or 0

        previous_points = (
            self.db.query(func.coalesce(func.sum(GamificationEvent.points_earned), 0))
            .filter(
                GamificationEvent.tenant_id == self.tenant_id,
                GamificationEvent.user_id.in_(user_ids),
                GamificationEvent.created_at >= two_weeks_ago,
                GamificationEvent.created_at < week_ago,
            )
            .scalar()
        ) or 0

        if previous_points == 0:
            return "+100%" if recent_points > 0 else "+0%"

        change = ((recent_points - previous_points) / previous_points) * 100
        sign = "+" if change >= 0 else ""
        return f"{sign}{int(change)}%"
