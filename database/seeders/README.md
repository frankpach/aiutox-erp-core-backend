# Database Seeders

Este directorio contiene los seeders (sembradores) de datos para la base de datos del sistema AiutoX ERP.

## 📋 Índice

- [Descripción General](#descripción-general)
- [Seeders Disponibles](#seeders-disponibles)
- [Uso](#uso)
- [Creación de Nuevos Seeders](#creación-de-nuevos-seeders)
- [Usuarios de Desarrollo](#usuarios-de-desarrollo)

## Descripción General

Los seeders son scripts que poblan la base de datos con datos iniciales necesarios para el funcionamiento del sistema. Son **idempotentes**, lo que significa que pueden ejecutarse múltiples veces sin crear datos duplicados.

### Principios

1. **Idempotencia**: Los seeders deben poder ejecutarse múltiples veces sin crear duplicados
2. **Seguridad**: Los seeders de producción solo crean datos esenciales
3. **Desarrollo**: Los seeders de desarrollo crean datos de prueba completos
4. **Verificación**: Siempre verifican si los datos ya existen antes de crearlos

## Seeders Disponibles

### `AdminUserSeeder` (Producción)

**Propósito**: Crea el usuario owner para entornos de producción.

**Crea**:
- `owner@aiutox.com` con rol `owner` (permiso `*` - acceso total)

**Cuándo usar**: En producción o cuando solo necesitas el usuario administrador principal.

**Ejecución**:
```bash
uv run aiutox db:seed --class=AdminUserSeeder
```

### `DevelopmentUsersSeeder` (Desarrollo)

**Propósito**: Crea múltiples usuarios con diferentes niveles de permisos para pruebas y desarrollo.

**Crea**:
- `owner@aiutox.com`: Rol `owner` (acceso total `*`)
- `admin@aiutox.com`: Rol `admin` (gestión de permisos globales)
- `supervisor@aiutox.com`: Rol `manager` + roles de módulo `internal.manager` en `inventory` y `products`
- `user@aiutox.com`: Sin roles (usuario básico para pruebas de delegación de permisos)

**Cuándo usar**: En desarrollo para probar diferentes niveles de permisos y la gestión de usuarios.

**Ejecución**:
```bash
uv run aiutox db:seed --class=DevelopmentUsersSeeder
```

### `DatabaseSeeder` (Principal)

**Propósito**: Seeder principal que ejecuta otros seeders según el entorno.

**Comportamiento**:
- **Producción** (`ENV=prod` o `ENV=production`): Ejecuta `AdminUserSeeder`
- **Desarrollo** (cualquier otro entorno): Ejecuta `DevelopmentUsersSeeder`

**Ejecución**:
```bash
uv run aiutox db:seed
```

## Uso

### Ejecutar Todos los Seeders Pendientes

```bash
# Desde el directorio backend
uv run aiutox db:seed
```

### Ejecutar un Seeder Específico

```bash
# Seeder de producción
uv run aiutox db:seed --class=AdminUserSeeder

# Seeder de desarrollo
uv run aiutox db:seed --class=DevelopmentUsersSeeder
```

### Usando el Script de Verificación

El script `ensure_admin_user.py` también puede crear/verificar usuarios:

```bash
# Auto-detecta el entorno
python ensure_admin_user.py

# Forzar modo desarrollo (crea todos los usuarios)
python ensure_admin_user.py --dev

# Forzar modo producción (solo owner)
python ensure_admin_user.py --prod
```

## Usuarios de Desarrollo

### Credenciales

Todos los usuarios de desarrollo tienen la contraseña: `password`

| Email | Rol | Permisos | Propósito |
|-------|-----|----------|-----------|
| `owner@aiutox.com` | `owner` | `*` (acceso total) | Verificar funcionamiento completo de módulos |
| `admin@aiutox.com` | `admin` | Globales: `auth.manage_users`, `auth.manage_roles`<br/>Wildcards: `*.*.view`, `*.*.edit`, `*.*.delete`, `*.*.manage_users` | Gestionar permisos generales y usuarios |
| `supervisor@aiutox.com` | `manager` + módulos | Global: `system.view_reports`<br/>Módulos: `inventory.manage_users`, `products.manage_users` | Gestionar permisos de módulos específicos |
| `user@aiutox.com` | Ninguno | Sin permisos | Usuario básico para pruebas de delegación |

### Casos de Uso

#### 1. Verificar Funcionamiento Completo (Owner)
- Login como `owner@aiutox.com`
- Verificar que tiene acceso a todos los módulos
- Verificar que puede realizar todas las acciones

#### 2. Gestionar Permisos Globales (Admin)
- Login como `admin@aiutox.com`
- Asignar roles globales a usuarios
- Gestionar usuarios del sistema
- Verificar que puede gestionar permisos en todos los módulos

#### 3. Gestionar Permisos de Módulos (Supervisor)
- Login como `supervisor@aiutox.com`
- Delegar permisos específicos de `inventory` y `products` a `user@aiutox.com`
- Verificar que NO puede delegar permisos de otros módulos
- Verificar que el frontend muestra/oculta opciones según permisos

#### 4. Probar Delegación de Permisos (User)
- Login como `user@aiutox.com` (inicialmente sin acceso)
- Como `supervisor@aiutox.com`, delegar `inventory.view` a `user@aiutox.com`
- Login nuevamente como `user@aiutox.com`
- Verificar que ahora puede ver el módulo de inventario
- Verificar que el frontend se adapta mostrando solo lo permitido

## Creación de Nuevos Seeders

### Estructura Base

```python
"""Description of the seeder."""

from sqlalchemy.orm import Session

from app.core.seeders.base import Seeder
from app.models.tenant import Tenant
from app.models.user import User


class MySeeder(Seeder):
    """Seeder description.

    This seeder is idempotent - it will not create duplicate data.
    """

    def run(self, db: Session) -> None:
        """Run the seeder.

        Args:
            db: Database session
        """
        # Get or create tenant
        tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not tenant:
            tenant = Tenant(name="Default Tenant", slug="default")
            db.add(tenant)
            db.commit()
            db.refresh(tenant)

        # Create data (always check if exists first)
        # ... your code here
```

### Buenas Prácticas

1. **Siempre verificar existencia**: Antes de crear, verificar si el dato ya existe
2. **Usar transacciones**: Agrupar operaciones relacionadas en commits
3. **Manejar errores**: Usar try/except y rollback cuando sea necesario
4. **Documentar**: Incluir docstrings claros sobre qué crea el seeder
5. **Idempotencia**: El seeder debe poder ejecutarse múltiples veces sin problemas

### Ejemplo: Crear un Seeder de Productos

```python
"""Product seeder for initial product data."""

from sqlalchemy.orm import Session

from app.core.seeders.base import Seeder
from app.models.product import Product
from app.models.tenant import Tenant


class ProductSeeder(Seeder):
    """Seeder for initial products.

    Creates sample products for testing.
    This seeder is idempotent - it will not create duplicate products.
    """

    def run(self, db: Session) -> None:
        """Run the seeder."""
        # Get tenant
        tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not tenant:
            return  # Tenant doesn't exist, skip

        # Create products (check if exists first)
        products_data = [
            {"name": "Product 1", "sku": "PROD-001"},
            {"name": "Product 2", "sku": "PROD-002"},
        ]

        for product_data in products_data:
            existing = (
                db.query(Product)
                .filter(Product.sku == product_data["sku"])
                .first()
            )
            if not existing:
                product = Product(
                    name=product_data["name"],
                    sku=product_data["sku"],
                    tenant_id=tenant.id,
                )
                db.add(product)
                db.commit()
```

## Integración con DatabaseSeeder

Para que un seeder se ejecute automáticamente, agrégalo a `DatabaseSeeder`:

```python
# En database_seeder.py
def run(self, db: Session) -> None:
    # ... existing code ...

    # Add your seeder
    from database.seeders.product_seeder import ProductSeeder
    ProductSeeder().run(db)
```

## Notas Importantes

1. **Contraseñas**: Todos los usuarios de desarrollo usan `password` como contraseña
2. **Producción**: En producción, solo se crea el usuario `owner`. Los demás usuarios deben crearse manualmente
3. **Seguridad**: Nunca hardcodees contraseñas reales en producción
4. **Tenants**: Los seeders asumen que existe un tenant con slug `"default"`. Si no existe, lo crean

## Referencias

- [Documentación de Seeders del Sistema](../docs/10-backend/migrations.md#seeders)
- [Sistema de Permisos](../docs/40-modules/auth.md)
- [CLI de Base de Datos](../../README.md#cli-unificado-aiutox)
















