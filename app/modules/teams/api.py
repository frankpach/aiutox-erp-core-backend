"""Teams router for team and member management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.common import PaginationMeta, StandardListResponse, StandardResponse
from app.schemas.team import (
    TeamCreate,
    TeamMemberCreate,
    TeamMemberResponse,
    TeamResponse,
    TeamUpdate,
)
from app.services.team_service import TeamService

router = APIRouter()


def get_team_service(db: Annotated[Session, Depends(get_db)]) -> TeamService:
    """Dependency to get TeamService."""
    return TeamService(db)


# Team CRUD Endpoints

@router.post(
    "",
    response_model=StandardResponse[TeamResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create team",
    description="Create a new team. Requires teams.manage permission.",
)
async def create_team(
    team_data: TeamCreate,
    current_user: Annotated[User, Depends(require_permission("teams.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[TeamResponse]:
    """Create a new team."""
    team = Team(
        tenant_id=current_user.tenant_id,
        name=team_data.name,
        description=team_data.description,
        parent_team_id=team_data.parent_team_id,
        color=team_data.color,
        is_active=team_data.is_active,
    )

    db.add(team)
    db.commit()
    db.refresh(team)

    return StandardResponse(
        data=TeamResponse.model_validate(team),
        message="Team created successfully",
    )


@router.get(
    "",
    response_model=StandardListResponse[TeamResponse],
    summary="List teams",
    description="Get all teams for the current tenant. Requires teams.view permission.",
)
async def list_teams(
    current_user: Annotated[User, Depends(require_permission("teams.view"))],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    is_active: bool | None = Query(None, description="Filter by active status"),
) -> StandardListResponse[TeamResponse]:
    """List all teams."""
    query = db.query(Team).filter(Team.tenant_id == current_user.tenant_id)

    if is_active is not None:
        query = query.filter(Team.is_active == is_active)

    total = query.count()
    teams = query.order_by(Team.name).offset((page - 1) * page_size).limit(page_size).all()

    return StandardListResponse(
        data=[TeamResponse.model_validate(team) for team in teams],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=(total + page_size - 1) // page_size,
        ),
        message="Teams retrieved successfully",
    )


@router.get(
    "/{team_id}",
    response_model=StandardResponse[TeamResponse],
    summary="Get team",
    description="Get a specific team by ID. Requires teams.view permission.",
)
async def get_team(
    team_id: Annotated[UUID, Path(description="Team ID")],
    current_user: Annotated[User, Depends(require_permission("teams.view"))],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> StandardResponse[TeamResponse]:
    """Get a team by ID."""
    team = service.get_team_by_id(current_user.tenant_id, team_id)

    if not team:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Team not found",
        )

    return StandardResponse(
        data=TeamResponse.model_validate(team),
        message="Team retrieved successfully",
    )


@router.put(
    "/{team_id}",
    response_model=StandardResponse[TeamResponse],
    summary="Update team",
    description="Update a team. Requires teams.manage permission.",
)
async def update_team(
    team_id: Annotated[UUID, Path(description="Team ID")],
    team_data: TeamUpdate,
    current_user: Annotated[User, Depends(require_permission("teams.manage"))],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> StandardResponse[TeamResponse]:
    """Update a team."""
    team = service.get_team_by_id(current_user.tenant_id, team_id)

    if not team:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Team not found",
        )

    # Update fields
    update_data = team_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)

    db.commit()
    db.refresh(team)

    return StandardResponse(
        data=TeamResponse.model_validate(team),
        message="Team updated successfully",
    )


@router.delete(
    "/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete team",
    description="Delete a team. Requires teams.manage permission.",
)
async def delete_team(
    team_id: Annotated[UUID, Path(description="Team ID")],
    current_user: Annotated[User, Depends(require_permission("teams.manage"))],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> None:
    """Delete a team."""
    team = service.get_team_by_id(current_user.tenant_id, team_id)

    if not team:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Team not found",
        )

    db.delete(team)
    db.commit()


# Team Member Endpoints

@router.post(
    "/{team_id}/members",
    response_model=StandardResponse[TeamMemberResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add team member",
    description="Add a member to a team. Requires teams.manage permission.",
)
async def add_team_member(
    team_id: Annotated[UUID, Path(description="Team ID")],
    member_data: TeamMemberCreate,
    current_user: Annotated[User, Depends(require_permission("teams.manage"))],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> StandardResponse[TeamMemberResponse]:
    """Add a member to a team."""
    # Verify team exists
    team = service.get_team_by_id(current_user.tenant_id, team_id)
    if not team:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Team not found",
        )

    # Verify team_id matches
    if member_data.team_id != team_id:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Team ID in path and body must match",
        )

    # Add member
    member = service.add_team_member(
        tenant_id=current_user.tenant_id,
        team_id=team_id,
        user_id=member_data.user_id,
        added_by=current_user.id,
        role=member_data.role,
    )

    return StandardResponse(
        data=TeamMemberResponse.model_validate(member),
        message="Team member added successfully",
    )


@router.get(
    "/{team_id}/members",
    response_model=StandardListResponse[TeamMemberResponse],
    summary="List team members",
    description="Get all members of a team. Requires teams.view permission.",
)
async def list_team_members(
    team_id: Annotated[UUID, Path(description="Team ID")],
    current_user: Annotated[User, Depends(require_permission("teams.view"))],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> StandardListResponse[TeamMemberResponse]:
    """List all members of a team."""
    # Verify team exists
    team = service.get_team_by_id(current_user.tenant_id, team_id)
    if not team:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Team not found",
        )

    members = db.query(TeamMember).filter(
        TeamMember.tenant_id == current_user.tenant_id,
        TeamMember.team_id == team_id,
    ).all()

    return StandardListResponse(
        data=[TeamMemberResponse.model_validate(member) for member in members],
        meta=PaginationMeta(
            page=1,
            page_size=len(members),
            total_items=len(members),
            total_pages=1,
        ),
        message="Team members retrieved successfully",
    )


@router.delete(
    "/{team_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove team member",
    description="Remove a member from a team. Requires teams.manage permission.",
)
async def remove_team_member(
    team_id: Annotated[UUID, Path(description="Team ID")],
    user_id: Annotated[UUID, Path(description="User ID")],
    current_user: Annotated[User, Depends(require_permission("teams.manage"))],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> None:
    """Remove a member from a team."""
    # Verify team exists
    team = service.get_team_by_id(current_user.tenant_id, team_id)
    if not team:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Team not found",
        )

    # Remove member
    removed = service.remove_team_member(
        tenant_id=current_user.tenant_id,
        team_id=team_id,
        user_id=user_id,
    )

    if not removed:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Team member not found",
        )


@router.get(
    "/{team_id}/members/resolved",
    response_model=StandardResponse[list[UUID]],
    summary="Get resolved team members",
    description="Get all user IDs that are members of this team (including nested teams). Requires teams.view permission.",
)
async def get_resolved_team_members(
    team_id: Annotated[UUID, Path(description="Team ID")],
    current_user: Annotated[User, Depends(require_permission("teams.view"))],
    service: Annotated[TeamService, Depends(get_team_service)],
    include_nested: bool = Query(False, description="Include members from child teams"),
) -> StandardResponse[list[UUID]]:
    """Get all resolved member IDs for a team."""
    # Verify team exists
    team = service.get_team_by_id(current_user.tenant_id, team_id)
    if not team:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Team not found",
        )

    member_ids = service.get_group_members(
        tenant_id=current_user.tenant_id,
        group_id=team_id,
        include_nested=include_nested,
    )

    return StandardResponse(
        data=member_ids,
        message=f"Found {len(member_ids)} members",
    )
