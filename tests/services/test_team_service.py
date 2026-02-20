"""Tests for TeamService."""

from uuid import uuid4

import pytest

from app.models.team import Team
from app.models.tenant import Tenant
from app.services.team_service import TeamService


@pytest.fixture
def team_service(db_session):
    """Create TeamService instance."""
    return TeamService(db_session)


@pytest.fixture
def sample_tenant(db_session):
    """Create a sample tenant."""
    tenant = Tenant(
        id=uuid4(),
        name="Tenant Test",
        slug=f"tenant-test-{uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def sample_team(db_session, sample_tenant):
    """Create a sample team."""
    team = Team(
        tenant_id=sample_tenant.id,
        name="Test Team",
        description="Test team description",
        is_active=True,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


@pytest.fixture
def sample_users(db_session, sample_tenant):
    """Create sample users."""
    from app.models.user import User

    users = []
    for i in range(3):
        unique_suffix = uuid4().hex[:8]
        user = User(
            tenant_id=sample_tenant.id,
            email=f"user{i}-{unique_suffix}@test.com",
            password_hash="hashed",
        )
        db_session.add(user)
        users.append(user)

    db_session.commit()
    for user in users:
        db_session.refresh(user)

    return users


class TestTeamService:
    """Test TeamService methods."""

    def test_add_team_member(
        self, team_service, sample_team, sample_users, sample_tenant
    ):
        """Test adding a member to a team."""
        user = sample_users[0]

        member = team_service.add_team_member(
            tenant_id=sample_tenant.id,
            team_id=sample_team.id,
            user_id=user.id,
            added_by=user.id,
            role="member",
        )

        assert member is not None
        assert member.team_id == sample_team.id
        assert member.user_id == user.id
        assert member.role == "member"

    def test_add_duplicate_member(
        self, team_service, sample_team, sample_users, sample_tenant
    ):
        """Test adding a duplicate member returns existing member."""
        user = sample_users[0]

        # Add first time
        member1 = team_service.add_team_member(
            tenant_id=sample_tenant.id,
            team_id=sample_team.id,
            user_id=user.id,
            added_by=user.id,
        )

        # Add second time
        member2 = team_service.add_team_member(
            tenant_id=sample_tenant.id,
            team_id=sample_team.id,
            user_id=user.id,
            added_by=user.id,
        )

        assert member1.id == member2.id

    def test_get_group_members(
        self, team_service, sample_team, sample_users, sample_tenant
    ):
        """Test getting all members of a group."""
        # Add multiple members
        for user in sample_users:
            team_service.add_team_member(
                tenant_id=sample_tenant.id,
                team_id=sample_team.id,
                user_id=user.id,
                added_by=user.id,
            )

        members = team_service.get_group_members(sample_tenant.id, sample_team.id)

        assert len(members) == 3
        assert all(user.id in members for user in sample_users)

    def test_get_group_members_with_nested(
        self, team_service, db_session, sample_team, sample_users, sample_tenant
    ):
        """Test getting members including nested teams."""
        # Create child team
        child_team = Team(
            tenant_id=sample_tenant.id,
            name="Child Team",
            parent_team_id=sample_team.id,
            is_active=True,
        )
        db_session.add(child_team)
        db_session.commit()
        db_session.refresh(child_team)

        # Add members to parent
        team_service.add_team_member(
            tenant_id=sample_tenant.id,
            team_id=sample_team.id,
            user_id=sample_users[0].id,
            added_by=sample_users[0].id,
        )

        # Add members to child
        team_service.add_team_member(
            tenant_id=sample_tenant.id,
            team_id=child_team.id,
            user_id=sample_users[1].id,
            added_by=sample_users[1].id,
        )

        # Get without nested
        members_flat = team_service.get_group_members(
            sample_tenant.id, sample_team.id, include_nested=False
        )
        assert len(members_flat) == 1

        # Get with nested
        members_nested = team_service.get_group_members(
            sample_tenant.id, sample_team.id, include_nested=True
        )
        assert len(members_nested) == 2

    def test_get_user_groups(
        self, team_service, sample_team, sample_users, sample_tenant
    ):
        """Test getting all groups a user belongs to."""
        user = sample_users[0]

        # Add user to team
        team_service.add_team_member(
            tenant_id=sample_tenant.id,
            team_id=sample_team.id,
            user_id=user.id,
            added_by=user.id,
        )

        groups = team_service.get_user_groups(sample_tenant.id, user.id)

        assert len(groups) == 1
        assert sample_team.id in groups

    def test_is_user_in_group(
        self, team_service, sample_team, sample_users, sample_tenant
    ):
        """Test checking if user is in group."""
        user = sample_users[0]

        # User not in group yet
        assert not team_service.is_user_in_group(
            sample_tenant.id, user.id, sample_team.id
        )

        # Add user to group
        team_service.add_team_member(
            tenant_id=sample_tenant.id,
            team_id=sample_team.id,
            user_id=user.id,
            added_by=user.id,
        )

        # User now in group
        assert team_service.is_user_in_group(sample_tenant.id, user.id, sample_team.id)

    def test_remove_team_member(
        self, team_service, sample_team, sample_users, sample_tenant
    ):
        """Test removing a member from a team."""
        user = sample_users[0]

        # Add member
        team_service.add_team_member(
            tenant_id=sample_tenant.id,
            team_id=sample_team.id,
            user_id=user.id,
            added_by=user.id,
        )

        # Remove member
        removed = team_service.remove_team_member(
            tenant_id=sample_tenant.id,
            team_id=sample_team.id,
            user_id=user.id,
        )

        assert removed is True

        # Verify removed
        members = team_service.get_group_members(sample_tenant.id, sample_team.id)
        assert user.id not in members

    def test_remove_nonexistent_member(
        self, team_service, sample_team, sample_users, sample_tenant
    ):
        """Test removing a member that doesn't exist."""
        user = sample_users[0]

        removed = team_service.remove_team_member(
            tenant_id=sample_tenant.id,
            team_id=sample_team.id,
            user_id=user.id,
        )

        assert removed is False
