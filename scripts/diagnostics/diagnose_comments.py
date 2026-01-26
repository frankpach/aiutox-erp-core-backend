"""Script de diagnóstico para el problema de Comments en Tasks."""

from sqlalchemy import text

from app.core.db.session import SessionLocal
from app.models.comment import Comment
from app.models.task import Task


def diagnose_comments():
    """Diagnosticar el problema de comments."""
    db = SessionLocal()

    try:
        print("\n" + "="*80)
        print("DIAGNÓSTICO DE COMMENTS EN TASKS")
        print("="*80 + "\n")

        # 1. Verificar tasks existentes
        print("1. TASKS EN LA BASE DE DATOS:")
        print("-" * 80)
        tasks = db.query(Task).all()
        print(f"Total tasks: {len(tasks)}\n")

        for task in tasks[:5]:  # Mostrar primeros 5
            print(f"  Task ID: {task.id}")
            print(f"  Title: {task.title}")
            print(f"  Tenant ID: {task.tenant_id}")
            print(f"  Type of task.id: {type(task.id)}")
            print()

        # 2. Verificar comments existentes
        print("\n2. COMMENTS EN LA BASE DE DATOS:")
        print("-" * 80)
        comments = db.query(Comment).all()
        print(f"Total comments: {len(comments)}\n")

        for comment in comments:
            print(f"  Comment ID: {comment.id}")
            print(f"  Entity Type: {comment.entity_type}")
            print(f"  Entity ID: {comment.entity_id}")
            print(f"  Type of entity_id: {type(comment.entity_id)}")
            print(f"  Tenant ID: {comment.tenant_id}")
            print(f"  Content: {comment.content[:50]}...")
            print(f"  Is Deleted: {comment.is_deleted}")
            print()

        # 3. Buscar "Tarea 2"
        print("\n3. BUSCAR 'Tarea 2':")
        print("-" * 80)
        tarea2 = db.query(Task).filter(Task.title.like("%Tarea 2%")).first()

        if tarea2:
            print(f"✅ Encontrada 'Tarea 2':")
            print(f"  ID: {tarea2.id}")
            print(f"  Title: {tarea2.title}")
            print(f"  Tenant ID: {tarea2.tenant_id}")
            print(f"  Type: {type(tarea2.id)}")

            # 4. Buscar comments para Tarea 2
            print("\n4. COMMENTS PARA 'Tarea 2':")
            print("-" * 80)

            # Query directa
            task_comments = db.query(Comment).filter(
                Comment.entity_type == "task",
                Comment.entity_id == tarea2.id,
                Comment.tenant_id == tarea2.tenant_id,
                ~Comment.is_deleted,
            ).all()

            print(f"Comments encontrados con query: {len(task_comments)}")

            for comment in task_comments:
                print(f"  - Comment ID: {comment.id}")
                print(f"    Content: {comment.content}")
                print()

            # 5. Query SQL raw para verificar
            print("\n5. QUERY SQL RAW:")
            print("-" * 80)

            sql = text("""
                SELECT
                    id,
                    entity_type,
                    entity_id,
                    tenant_id,
                    content,
                    is_deleted,
                    pg_typeof(entity_id) as entity_id_type
                FROM comments
                WHERE entity_type = 'task'
                AND tenant_id = :tenant_id
            """)

            result = db.execute(sql, {"tenant_id": str(tarea2.tenant_id)})
            rows = result.fetchall()

            print(f"Total rows: {len(rows)}\n")
            for row in rows:
                print(f"  ID: {row[0]}")
                print(f"  Entity Type: {row[1]}")
                print(f"  Entity ID: {row[2]}")
                print(f"  Entity ID Type: {row[6]}")
                print(f"  Tenant ID: {row[3]}")
                print(f"  Content: {row[4][:50]}...")
                print(f"  Is Deleted: {row[5]}")
                print(f"  Match con Tarea 2: {str(row[2]) == str(tarea2.id)}")
                print()

            # 6. Comparación de UUIDs
            print("\n6. COMPARACIÓN DE UUIDs:")
            print("-" * 80)
            print(f"Tarea 2 ID: {tarea2.id}")
            print(f"Tipo: {type(tarea2.id)}")

            for comment in comments:
                if comment.entity_type == "task":
                    print(f"\nComment entity_id: {comment.entity_id}")
                    print(f"Tipo: {type(comment.entity_id)}")
                    print(f"Son iguales (==): {comment.entity_id == tarea2.id}")
                    print(f"Son iguales (str): {str(comment.entity_id) == str(tarea2.id)}")

        else:
            print("❌ No se encontró 'Tarea 2'")

        print("\n" + "="*80)
        print("FIN DEL DIAGNÓSTICO")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    diagnose_comments()
