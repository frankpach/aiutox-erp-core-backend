"""
Wrapper para imports con lazy loading para evitar dependencias circulares.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Estos imports solo se usan para type checking
    from app.schemas.contact import ContactCreate, ContactResponse
    from app.schemas.organization import OrganizationCreate, OrganizationResponse

def get_contact_schemas():
    """Importa schemas de contacto de forma lazy."""
    from app.schemas.contact import ContactCreate, ContactResponse
    return ContactCreate, ContactResponse

def get_organization_schemas():
    """Importa schemas de organización de forma lazy."""
    from app.schemas.organization import OrganizationCreate, OrganizationResponse
    return OrganizationCreate, OrganizationResponse
