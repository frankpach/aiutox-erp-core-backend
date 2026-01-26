# Scripts de Utilidad

Scripts de utilidad para desarrollo y mantenimiento.

## Scripts Disponibles

### `create_test_admin.py`
Crea un usuario admin para pruebas en la base de datos.

**Uso:**
```bash
uv run python scripts/utils/create_test_admin.py
```

### `ensure_admin_user.py` / `ensure-admin-user.ps1`
Verifica o crea usuarios admin/owner en la base de datos.

**Uso:**
```bash
uv run python scripts/utils/ensure_admin_user.py --dev
```

### `fix_env_encoding.py`
Script para diagnosticar y corregir problemas de encoding en archivos `.env`.

**Uso:**
```bash
uv run python scripts/utils/fix_env_encoding.py
```

### `generate_token.py`
Genera tokens para pruebas rápidas.

**Uso:**
```bash
uv run python scripts/utils/generate_token.py
```

### `get_token.py`
Obtiene un token de autenticación desde el backend.

**Uso:**
```bash
uv run python scripts/utils/get_token.py
```

### `get_user_id.py`
Obtiene el ID de usuario para pruebas o diagnósticos.

**Uso:**
```bash
uv run python scripts/utils/get_user_id.py
```

### `start-dev.ps1`
Script de arranque rápido del backend en Windows.

**Uso:**
```powershell
.\scripts\utils\start-dev.ps1
```

## Nota

Estos scripts son herramientas de desarrollo. No deben ejecutarse en producción.

