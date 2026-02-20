"""Team service for team and group management."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.team import Team, TeamMember

logger = logging.getLogger(__name__)


class TeamService:
    """Service for team business logic."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db

    def get_group_members(
        self, tenant_id: UUID, group_id: UUID, include_nested: bool = False
    ) -> list[UUID]:
        """
        Obtiene IDs de todos los miembros de un grupo.

        Args:
            tenant_id: ID del tenant
            group_id: ID del grupo
            include_nested: Si incluir miembros de subgrupos

        Returns:
            Lista de user_ids
        """
        # Obtener miembros directos
        members = (
            self.db.query(TeamMember.user_id)
            .filter(TeamMember.tenant_id == tenant_id, TeamMember.team_id == group_id)
            .all()
        )

        user_ids = [member.user_id for member in members]

        # Si incluye anidados, obtener recursivamente
        if include_nested:
            child_teams = (
                self.db.query(Team.id)
                .filter(
                    Team.tenant_id == tenant_id,
                    Team.parent_team_id == group_id,
                    Team.is_active.is_(True),
                )
                .all()
            )

            for child_team in child_teams:
                child_members = self.get_group_members(
                    tenant_id, child_team.id, include_nested=True
                )
                user_ids.extend(child_members)

        # Eliminar duplicados
        return list(set(user_ids))

    def get_user_groups(
        self, tenant_id: UUID, user_id: UUID, include_parent_groups: bool = False
    ) -> list[UUID]:
        """
        Obtiene IDs de todos los grupos a los que pertenece un usuario.

        Args:
            tenant_id: ID del tenant
            user_id: ID del usuario
            include_parent_groups: Si incluir grupos padres

        Returns:
            Lista de group_ids
        """
        # Obtener grupos directos
        memberships = (
            self.db.query(TeamMember.team_id)
            .filter(TeamMember.tenant_id == tenant_id, TeamMember.user_id == user_id)
            .all()
        )

        group_ids = [membership.team_id for membership in memberships]

        # Si incluye padres, obtener recursivamente
        if include_parent_groups:
            for group_id in list(group_ids):
                parent_teams = self._get_parent_teams(tenant_id, group_id)
                group_ids.extend([team.id for team in parent_teams])

        # Eliminar duplicados
        return list(set(group_ids))

    def _get_parent_teams(self, tenant_id: UUID, team_id: UUID) -> list[Team]:
        """
        Obtiene todos los equipos padres de un equipo de forma recursiva.

        Args:
            tenant_id: ID del tenant
            team_id: ID del equipo

        Returns:
            Lista de equipos padres
        """
        team = (
            self.db.query(Team)
            .filter(Team.id == team_id, Team.tenant_id == tenant_id)
            .first()
        )

        if not team or not team.parent_team_id:
            return []

        parent = (
            self.db.query(Team)
            .filter(Team.id == team.parent_team_id, Team.tenant_id == tenant_id)
            .first()
        )

        if not parent:
            return []

        # Recursivamente obtener padres del padre
        grandparents = self._get_parent_teams(tenant_id, parent.id)
        return [parent] + grandparents

    def get_team_by_id(self, tenant_id: UUID, team_id: UUID) -> Team | None:
        """
        Obtiene un equipo por ID.

        Args:
            tenant_id: ID del tenant
            team_id: ID del equipo

        Returns:
            Team o None si no existe
        """
        return (
            self.db.query(Team)
            .filter(Team.id == team_id, Team.tenant_id == tenant_id)
            .first()
        )

    def is_user_in_group(
        self,
        tenant_id: UUID,
        user_id: UUID,
        group_id: UUID,
        include_nested: bool = False,
    ) -> bool:
        """
        Verifica si un usuario pertenece a un grupo.

        Args:
            tenant_id: ID del tenant
            user_id: ID del usuario
            group_id: ID del grupo
            include_nested: Si considerar subgrupos

        Returns:
            True si el usuario pertenece al grupo
        """
        # Verificar membresía directa
        direct_member = (
            self.db.query(TeamMember)
            .filter(
                TeamMember.tenant_id == tenant_id,
                TeamMember.user_id == user_id,
                TeamMember.team_id == group_id,
            )
            .first()
        )

        if direct_member:
            return True

        # Si incluye anidados, verificar en subgrupos
        if include_nested:
            child_teams = (
                self.db.query(Team.id)
                .filter(
                    Team.tenant_id == tenant_id,
                    Team.parent_team_id == group_id,
                    Team.is_active.is_(True),
                )
                .all()
            )

            for child_team in child_teams:
                if self.is_user_in_group(
                    tenant_id, user_id, child_team.id, include_nested=True
                ):
                    return True

        return False

    def add_team_member(
        self,
        tenant_id: UUID,
        team_id: UUID,
        user_id: UUID,
        added_by: UUID,
        role: str | None = None,
    ) -> TeamMember:
        """
        Agrega un miembro a un equipo.

        Args:
            tenant_id: ID del tenant
            team_id: ID del equipo
            user_id: ID del usuario
            added_by: ID del usuario que agrega
            role: Rol del miembro (opcional)

        Returns:
            TeamMember creado
        """
        # Verificar si ya existe
        existing = (
            self.db.query(TeamMember)
            .filter(
                TeamMember.tenant_id == tenant_id,
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
            .first()
        )

        if existing:
            logger.warning(f"User {user_id} already member of team {team_id}")
            return existing

        # Crear nuevo miembro
        member = TeamMember(
            tenant_id=tenant_id,
            team_id=team_id,
            user_id=user_id,
            added_by=added_by,
            role=role,
        )

        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)

        logger.info(f"Added user {user_id} to team {team_id}")
        return member

    def remove_team_member(self, tenant_id: UUID, team_id: UUID, user_id: UUID) -> bool:
        """
        Remueve un miembro de un equipo.

        Args:
            tenant_id: ID del tenant
            team_id: ID del equipo
            user_id: ID del usuario

        Returns:
            True si se removió, False si no existía
        """
        member = (
            self.db.query(TeamMember)
            .filter(
                TeamMember.tenant_id == tenant_id,
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
            .first()
        )

        if not member:
            return False

        self.db.delete(member)
        self.db.commit()

        logger.info(f"Removed user {user_id} from team {team_id}")
        return True
