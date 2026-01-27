"""Sistema de paginación optimizado para endpoints de listado."""

from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, validator

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Parámetros de paginación optimizados."""
    
    page: int = Field(default=1, ge=1, description="Número de página (empezando en 1)")
    page_size: int = Field(
        default=20, 
        ge=1, 
        le=100, 
        description="Elementos por página (1-100)"
    )
    sort_by: str | None = Field(default=None, description="Campo para ordenar")
    sort_order: str = Field(default="desc", regex="^(asc|desc)$", description="Orden (asc/desc)")
    search: str | None = Field(default=None, description="Término de búsqueda")
    
    @validator("page_size")
    def validate_page_size(cls, v):
        """Validar tamaño de página según contexto."""
        # Para endpoints móviles, limitar a 20 por defecto
        # Para endpoints web, permitir hasta 100
        return min(v, 100)
    
    @property
    def offset(self) -> int:
        """Calcular offset para base de datos."""
        return (self.page - 1) * self.page_size


class PaginationMeta(BaseModel):
    """Metadatos de paginación."""
    
    total: int = Field(..., description="Total de elementos")
    page: int = Field(..., description="Página actual")
    page_size: int = Field(..., description="Elementos por página")
    total_pages: int = Field(..., description="Total de páginas")
    has_next: bool = Field(..., description="Hay página siguiente")
    has_prev: bool = Field(..., description="Hay página anterior")
    next_page: int | None = Field(default=None, description="Siguiente página")
    prev_page: int | None = Field(default=None, description="Página anterior")
    
    @classmethod
    def create(
        cls,
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginationMeta":
        """Crear metadatos de paginación."""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        has_next = page < total_pages
        has_prev = page > 1
        
        return cls(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
            next_page=page + 1 if has_next else None,
            prev_page=page - 1 if has_prev else None,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Respuesta paginada optimizada."""
    
    data: list[T] = Field(..., description="Datos de la página")
    meta: PaginationMeta = Field(..., description="Metadatos de paginación")
    links: dict[str, str | None] = Field(default_factory=dict, description="Links de navegación")
    
    @classmethod
    def create(
        cls,
        data: list[T],
        total: int,
        page: int,
        page_size: int,
        base_url: str = "",
        additional_params: dict[str, Any] | None = None,
    ) -> "PaginatedResponse[T]":
        """Crear respuesta paginada con links."""
        meta = PaginationMeta.create(total, page, page_size)
        
        # Generar links de navegación
        links = {}
        if base_url:
            params = additional_params or {}
            
            # Link actual
            current_params = {**params, "page": page, "page_size": page_size}
            links["self"] = f"{base_url}?{_build_query_string(current_params)}"
            
            # Link primera página
            if page > 1:
                first_params = {**params, "page": 1, "page_size": page_size}
                links["first"] = f"{base_url}?{_build_query_string(first_params)}"
            
            # Link última página
            if meta.total_pages > 0:
                last_params = {**params, "page": meta.total_pages, "page_size": page_size}
                links["last"] = f"{base_url}?{_build_query_string(last_params)}"
            
            # Link siguiente
            if meta.has_next:
                next_params = {**params, "page": meta.next_page, "page_size": page_size}
                links["next"] = f"{base_url}?{_build_query_string(next_params)}"
            
            # Link anterior
            if meta.has_prev:
                prev_params = {**params, "page": meta.prev_page, "page_size": page_size}
                links["prev"] = f"{base_url}?{_build_query_string(prev_params)}"
        
        return cls(data=data, meta=meta, links=links)


def _build_query_string(params: dict[str, Any]) -> str:
    """Construir query string desde diccionario."""
    from urllib.parse import urlencode
    
    # Filtrar valores None y vacíos
    filtered_params = {k: v for k, v in params.items() if v is not None and v != ""}
    
    return urlencode(filtered_params)


class CursorPaginationParams(BaseModel):
    """Parámetros de paginación por cursor (para datasets grandes)."""
    
    cursor: str | None = Field(default=None, description="Cursor de posición")
    limit: int = Field(default=20, ge=1, le=100, description="Límite de elementos")
    sort_by: str = Field(default="created_at", description="Campo para ordenar")
    sort_order: str = Field(default="desc", regex="^(asc|desc)$", description="Orden")


class CursorPaginationMeta(BaseModel):
    """Metadatos de paginación por cursor."""
    
    has_next: bool = Field(..., description="Hay más elementos")
    next_cursor: str | None = Field(default=None, description="Cursor siguiente")
    limit: int = Field(..., description="Límite aplicado")


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Respuesta paginada por cursor."""
    
    data: list[T] = Field(..., description="Datos de la página")
    meta: CursorPaginationMeta = Field(..., description="Metadatos de paginación")


class OptimizedQueryBuilder:
    """Constructor de consultas optimizado para paginación."""
    
    def __init__(self, query, default_sort: str = "created_at", default_order: str = "desc"):
        """Inicializar constructor de consultas."""
        self.query = query
        self.default_sort = default_sort
        self.default_order = default_order
    
    def apply_pagination(
        self,
        params: PaginationParams,
        searchable_fields: list[str] | None = None,
        filterable_fields: dict[str, Any] | None = None,
    ):
        """Aplicar paginación y filtros a la consulta."""
        from sqlalchemy import or_, and_
        
        # Aplicar búsqueda si se proporciona
        if params.search and searchable_fields:
            search_conditions = []
            for field in searchable_fields:
                if hasattr(self.query.column_descriptions[0]["type"], field):
                    field_attr = getattr(self.query.column_descriptions[0]["type"], field)
                    search_conditions.append(field_attr.ilike(f"%{params.search}%"))
            
            if search_conditions:
                self.query = self.query.filter(or_(*search_conditions))
        
        # Aplicar filtros adicionales
        if filterable_fields:
            filter_conditions = []
            for field, value in filterable_fields.items():
                if value is not None and hasattr(self.query.column_descriptions[0]["type"], field):
                    field_attr = getattr(self.query.column_descriptions[0]["type"], field)
                    if isinstance(value, list):
                        filter_conditions.append(field_attr.in_(value))
                    else:
                        filter_conditions.append(field_attr == value)
            
            if filter_conditions:
                self.query = self.query.filter(and_(*filter_conditions))
        
        # Aplicar ordenamiento
        sort_field = params.sort_by or self.default_sort
        sort_order = params.sort_order or self.default_order
        
        if hasattr(self.query.column_descriptions[0]["type"], sort_field):
            sort_attr = getattr(self.query.column_descriptions[0]["type"], sort_field)
            if sort_order == "desc":
                self.query = self.query.order_by(sort_attr.desc())
            else:
                self.query = self.query.order_by(sort_attr.asc())
        
        # Aplicar paginación
        self.query = self.query.offset(params.offset).limit(params.page_size)
        
        return self.query


class TaskQueryOptimizer:
    """Optimizador específico para consultas de tareas."""
    
    @staticmethod
    def optimize_task_list_query(
        db_query,
        tenant_id: UUID,
        params: PaginationParams,
        user_id: UUID | None = None,
        user_group_ids: list[UUID] | None = None,
        status_filter: str | None = None,
        priority_filter: str | None = None,
        assigned_to_filter: UUID | None = None,
    ):
        """Optimizar consulta de listado de tareas."""
        from sqlalchemy import or_, exists
        
        query = db_query.filter(tenant_id=tenant_id)
        
        # Aplicar filtros básicos
        if status_filter:
            query = query.filter(status=status_filter)
        if priority_filter:
            query = query.filter(priority=priority_filter)
        if assigned_to_filter:
            query = query.filter(assigned_to_id=assigned_to_filter)
        
        # Aplicar visibilidad si se proporciona user_id
        if user_id and user_group_ids is not None:
            visibility_conditions = [
                created_by_id == user_id,
                assigned_to_id == user_id,
                exists().where(
                    TaskAssignment.task_id == Task.id,
                    TaskAssignment.tenant_id == tenant_id,
                    TaskAssignment.assigned_to_id == user_id
                ),
            ]
            
            if user_group_ids:
                visibility_conditions.append(
                    exists().where(
                        TaskAssignment.task_id == Task.id,
                        TaskAssignment.tenant_id == tenant_id,
                        TaskAssignment.assigned_to_group_id.in_(user_group_ids)
                    )
                )
            
            query = query.filter(or_(*visibility_conditions))
        
        # Aplicar búsqueda
        if params.search:
            search_conditions = [
                Task.title.ilike(f"%{params.search}%"),
                Task.description.ilike(f"%{params.search}%"),
            ]
            query = query.filter(or_(*search_conditions))
        
        # Aplicar ordenamiento
        sort_field = params.sort_by or "created_at"
        if hasattr(Task, sort_field):
            sort_attr = getattr(Task, sort_field)
            if params.sort_order == "desc":
                query = query.order_by(sort_attr.desc())
            else:
                query = query.order_by(sort_attr.asc())
        
        # Aplicar paginación
        query = query.offset(params.offset).limit(params.page_size)
        
        return query


class PaginationCacheManager:
    """Gestor de caché para resultados paginados."""
    
    def __init__(self, cache_client):
        """Inicializar gestor con cliente de caché."""
        self.cache = cache_client
    
    async def get_cached_page(
        self,
        cache_key: str,
    ) -> dict[str, Any] | None:
        """Obtener página cachéada."""
        return await self.cache.get(cache_key)
    
    async def cache_page(
        self,
        cache_key: str,
        data: dict[str, Any],
        ttl: int = 120,
    ) -> None:
        """Cachear página de resultados."""
        await self.cache.set(cache_key, data, ttl)
    
    async def invalidate_pages(
        self,
        pattern: str,
    ) -> int:
        """Invalidar páginas por patrón."""
        return await self.cache.delete_pattern(pattern)
    
    def generate_cache_key(
        self,
        base_key: str,
        params: PaginationParams,
        filters: dict[str, Any] | None = None,
    ) -> str:
        """Generar clave de caché única."""
        import hashlib
        
        # Crear string representativo de los parámetros
        param_parts = [
            f"page:{params.page}",
            f"size:{params.page_size}",
            f"sort:{params.sort_by or 'default'}",
            f"order:{params.sort_order}",
        ]
        
        if params.search:
            param_parts.append(f"search:{params.search}")
        
        if filters:
            for k, v in sorted(filters.items()):
                if v is not None:
                    param_parts.append(f"{k}:{v}")
        
        param_string = "|".join(param_parts)
        param_hash = hashlib.md5(param_string.encode()).hexdigest()
        
        return f"{base_key}:{param_hash}"


# Decorador para endpoints paginados
def paginated_response(
    default_page_size: int = 20,
    max_page_size: int = 100,
    searchable_fields: list[str] | None = None,
):
    """Decorador para endpoints con respuesta paginada optimizada."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extraer parámetros de paginación
            page = kwargs.pop("page", 1)
            page_size = kwargs.pop("page_size", default_page_size)
            sort_by = kwargs.pop("sort_by", None)
            sort_order = kwargs.pop("sort_order", "desc")
            search = kwargs.pop("search", None)
            
            # Validar y crear parámetros
            params = PaginationParams(
                page=page,
                page_size=min(page_size, max_page_size),
                sort_by=sort_by,
                sort_order=sort_order,
                search=search,
            )
            
            # Ejecutar función original con parámetros optimizados
            result = await func(*args, **kwargs, pagination_params=params)
            
            return result
        
        return wrapper
    return decorator


# Helper functions para FastAPI
def get_pagination_params(
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_order: str = "desc",
    search: str | None = None,
) -> PaginationParams:
    """Obtener parámetros de paginación desde query params."""
    return PaginationParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
    )
