#!/usr/bin/env python
"""Script para depurar la consulta de comentarios."""

import os
import sys
from uuid import UUID

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import not_

from app.core.db.session import SessionLocal


def debug_comments():
    """Depurar comentarios en la base de datos."""
    db = SessionLocal()

    try:
        from app.models.comment import Comment

        task_id = UUID("53518d30-1816-428c-9295-9f69ca522d0a")
        tenant_id = UUID("36ea1fca-6b2b-46d4-84e1-1f3bdc13960e")

        print("\n" + "="*60)
        print(f"DEPURANDO COMENTARIOS PARA TASK ID: {task_id}")
        print("="*60 + "\n")

        # 1. Todos los comentarios en la tabla
        print("\n1️⃣ TODOS LOS COMENTARIOS EN LA TABLA:")
        all_comments = db.query(Comment).all()
        print(f"Total: {len(all_comments)}")
        for c in all_comments:
            print(f"  - ID: {c.id}")
            print(f"    entity_type: {c.entity_type}")
            print(f"    entity_id: {c.entity_id}")
            print(f"    tenant_id: {c.tenant_id}")
            print(f"    is_deleted: {c.is_deleted}")
            print(f"    content: {c.content[:50]}...")
            print()

        # 2. Comentarios del tenant
        print(f"\n2️⃣ COMENTARIOS DEL TENANT {tenant_id}:")
        tenant_comments = db.query(Comment).filter(
            Comment.tenant_id == tenant_id
        ).all()
        print(f"Total: {len(tenant_comments)}")
        for c in tenant_comments:
            print(f"  - ID: {c.id}, entity_type: {c.entity_type}, entity_id: {c.entity_id}")

        # 3. Comentarios de tipo "task"
        print("\n3️⃣ COMENTARIOS DE TIPO 'task':")
        task_type_comments = db.query(Comment).filter(
            Comment.entity_type == "task"
        ).all()
        print(f"Total: {len(task_type_comments)}")
        for c in task_type_comments:
            print(f"  - ID: {c.id}, entity_id: {c.entity_id}, tenant_id: {c.tenant_id}")

        # 4. Comentarios de esta tarea específica
        print(f"\n4️⃣ COMENTARIOS DE LA TAREA {task_id}:")
        task_comments = db.query(Comment).filter(
            Comment.entity_id == task_id
        ).all()
        print(f"Total: {len(task_comments)}")
        for c in task_comments:
            print(f"  - ID: {c.id}, entity_type: {c.entity_type}, tenant_id: {c.tenant_id}, is_deleted: {c.is_deleted}")

        # 5. La consulta completa (como en el servicio)
        print(f"\n5️⃣ CONSULTA COMPLETA (entity_type='task' AND entity_id={task_id} AND tenant_id={tenant_id} AND NOT is_deleted):")
        full_query_comments = db.query(Comment).filter(
            Comment.entity_type == "task",
            Comment.entity_id == task_id,
            Comment.tenant_id == tenant_id,
            not_(Comment.is_deleted),
        ).all()
        print(f"Total: {len(full_query_comments)}")
        for c in full_query_comments:
            print(f"  - ID: {c.id}, content: {c.content}")

        # 6. Verificar el tipo de datos de entity_id
        print("\n6️⃣ VERIFICACIÓN DE TIPOS DE DATOS:")
        if all_comments:
            first_comment = all_comments[0]
            print(f"  - entity_id type: {type(first_comment.entity_id)}")
            print(f"  - entity_id value: {first_comment.entity_id}")
            print(f"  - task_id type: {type(task_id)}")
            print(f"  - task_id value: {task_id}")
            print(f"  - ¿Son iguales? {first_comment.entity_id == task_id}")

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_comments()
