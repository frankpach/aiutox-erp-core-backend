"""Script para corregir la URL de Redis en el archivo .env."""

import os
import re
from pathlib import Path

def fix_redis_url():
    """Corregir la URL de Redis en el archivo .env."""
    # Buscar el archivo .env en el directorio raíz del proyecto
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"

    if not env_file.exists():
        print(f"[ERROR] No se encontro el archivo .env en: {env_file}")
        print("[AYUDA] Crea un archivo .env en la raiz del proyecto")
        return False

    print(f"[INFO] Leyendo archivo .env: {env_file}")

    # Leer el archivo
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"[ERROR] No se pudo leer el archivo .env: {e}")
        return False

    # Buscar REDIS_URL
    redis_url_pattern = r'^REDIS_URL\s*=\s*(.+)$'
    lines = content.split('\n')
    modified = False
    new_lines = []

    for line in lines:
        match = re.match(redis_url_pattern, line.strip())
        if match:
            current_url = match.group(1).strip().strip('"').strip("'")

            # Verificar si necesita corrección
            if not current_url.startswith(('redis://', 'rediss://', 'unix://')):
                # Corregir la URL
                if ':' in current_url:
                    # Si tiene formato host:port, agregar esquema
                    if current_url.startswith('localhost') or current_url.startswith('127.0.0.1'):
                        new_url = f"redis://{current_url}/0"
                    else:
                        new_url = f"redis://{current_url}/0"
                else:
                    # Si solo tiene el host, agregar puerto y esquema
                    new_url = f"redis://{current_url}:6379/0"

                print(f"[CORRECCION] REDIS_URL cambiado de: {current_url}")
                print(f"            a: {new_url}")
                new_lines.append(f"REDIS_URL={new_url}\n")
                modified = True
            else:
                print(f"[OK] REDIS_URL ya tiene el formato correcto: {current_url}")
                new_lines.append(line + '\n')
        else:
            new_lines.append(line + '\n')

    # Si no se encontró REDIS_URL, agregarlo
    if not any('REDIS_URL' in line for line in lines):
        print("[INFO] REDIS_URL no encontrado, agregando...")
        new_lines.append("REDIS_URL=redis://localhost:6379/0\n")
        modified = True

    # Escribir el archivo si hubo cambios
    if modified:
        try:
            # Crear backup
            backup_file = env_file.with_suffix('.env.backup')
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[INFO] Backup creado: {backup_file}")

            # Escribir archivo corregido
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(''.join(new_lines))
            print(f"[OK] Archivo .env actualizado correctamente")
            return True
        except Exception as e:
            print(f"[ERROR] No se pudo escribir el archivo .env: {e}")
            return False
    else:
        print("[INFO] No se requirieron cambios")
        return True

if __name__ == "__main__":
    print("=" * 70)
    print("[CORRECCION] Correccion de URL de Redis en .env")
    print("=" * 70)
    print()

    success = fix_redis_url()

    print()
    if success:
        print("=" * 70)
        print("[OK] Proceso completado")
        print("=" * 70)
        print()
        print("[SIGUIENTE] Ejecuta nuevamente: uv run python scripts\\test_redis_connection.py")
    else:
        print("=" * 70)
        print("[ERROR] Hubo problemas al corregir el archivo")
        print("=" * 70)









