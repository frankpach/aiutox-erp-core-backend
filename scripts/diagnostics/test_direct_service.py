"""Test directo del servicio de comments sin pasar por el endpoint."""

from uuid import UUID
from app.core.db.session import SessionLocal
from app.core.tasks.comment_service import TaskCommentService

# IDs conocidos
task_id = UUID("53518d30-1816-428c-9295-9f69ca522d0a")
tenant_id = UUID("36ea1fca-6b2b-46d4-84e1-1f3bdc13960e")

print("\n" + "="*80)
print("TEST DIRECTO DEL SERVICIO DE COMMENTS")
print("="*80 + "\n")

db = SessionLocal()

try:
    print(f"1. Creando servicio con sesión: {db}")
    service = TaskCommentService(db)

    print(f"\n2. Llamando list_comments:")
    print(f"   task_id: {task_id}")
    print(f"   tenant_id: {tenant_id}\n")

    comments = service.list_comments(
        task_id=task_id,
        tenant_id=tenant_id,
    )

    print(f"\n3. Resultado:")
    print(f"   Total comentarios: {len(comments)}")
    print(f"   Comentarios: {comments}\n")

    if len(comments) > 0:
        print("✅ El servicio FUNCIONA correctamente")
        print("❌ El problema está en el ENDPOINT o en las DEPENDENCIAS")
    else:
        print("❌ El servicio NO encuentra comentarios")
        print("⚠️  Verificar query SQL o datos en BD")

finally:
    db.close()

print("\n" + "="*80)
print("FIN DEL TEST")
print("="*80 + "\n")
