"""Leaderboard service for gamification system."""

from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.gamification import LeaderboardEntry, UserPoints

logger = get_logger(__name__)

LeaderboardPeriod = Literal["daily", "weekly", "monthly", "all_time"]


class LeaderboardService:
    """Service for managing leaderboard rankings."""

    def __init__(self, db: Session, tenant_id: UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def get_leaderboard(
        self,
        period: LeaderboardPeriod = "all_time",
        limit: int = 10,
    ) -> list[LeaderboardEntry]:
        """Get top N users for a given period.

        Args:
            period: Time period for the leaderboard
            limit: Maximum number of entries to return

        Returns:
            List of LeaderboardEntry sorted by points descending
        """
        return (
            self.db.query(LeaderboardEntry)
            .filter(
                LeaderboardEntry.tenant_id == self.tenant_id,
                LeaderboardEntry.period == period,
            )
            .order_by(LeaderboardEntry.points.desc())
            .limit(limit)
            .all()
        )

    def get_user_rank(
        self,
        user_id: UUID,
        period: LeaderboardPeriod = "all_time",
    ) -> LeaderboardEntry | None:
        """Get a specific user's leaderboard entry."""
        return (
            self.db.query(LeaderboardEntry)
            .filter(
                LeaderboardEntry.tenant_id == self.tenant_id,
                LeaderboardEntry.user_id == user_id,
                LeaderboardEntry.period == period,
            )
            .first()
        )

    def update_user_score(
        self,
        user_id: UUID,
        period: LeaderboardPeriod = "all_time",
    ) -> LeaderboardEntry:
        """Update a user's leaderboard entry from their current points.

        Args:
            user_id: User to update
            period: Period to update

        Returns:
            Updated LeaderboardEntry
        """
        # Get user's total points
        user_points = (
            self.db.query(UserPoints)
            .filter(
                UserPoints.tenant_id == self.tenant_id,
                UserPoints.user_id == user_id,
            )
            .first()
        )

        points = user_points.total_points if user_points else 0

        # Upsert leaderboard entry
        entry = self.get_user_rank(user_id, period)
        if not entry:
            entry = LeaderboardEntry(
                tenant_id=self.tenant_id,
                user_id=user_id,
                period=period,
                points=points,
            )
            self.db.add(entry)
        else:
            entry.points = points

        self.db.flush()

        # Recalculate rank for this period
        self._recalculate_ranks(period)

        self.db.commit()
        self.db.refresh(entry)
        return entry

    def refresh_all_time_leaderboard(self) -> int:
        """Rebuild the all_time leaderboard from UserPoints.

        Returns:
            Number of entries updated
        """
        all_user_points = (
            self.db.query(UserPoints)
            .filter(UserPoints.tenant_id == self.tenant_id)
            .all()
        )

        count = 0
        for up in all_user_points:
            entry = self.get_user_rank(up.user_id, "all_time")
            if not entry:
                entry = LeaderboardEntry(
                    tenant_id=self.tenant_id,
                    user_id=up.user_id,
                    period="all_time",
                    points=up.total_points,
                )
                self.db.add(entry)
            else:
                entry.points = up.total_points
            count += 1

        if count > 0:
            self.db.flush()
            self._recalculate_ranks("all_time")
            self.db.commit()

        logger.info(f"Refreshed all_time leaderboard: {count} entries")
        return count

    def _recalculate_ranks(self, period: LeaderboardPeriod) -> None:
        """Recalculate rank positions for a period."""
        entries = (
            self.db.query(LeaderboardEntry)
            .filter(
                LeaderboardEntry.tenant_id == self.tenant_id,
                LeaderboardEntry.period == period,
            )
            .order_by(LeaderboardEntry.points.desc())
            .all()
        )

        for i, entry in enumerate(entries, start=1):
            entry.rank = i
