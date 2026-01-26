"""
Script para probar si los endpoints de archivos y comentarios funcionan para eventos
"""

import asyncio
import sys
import os

# Agregar el path del backend al sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.db.session import SessionLocal
from app.models.user import User
from app.models.calendar import CalendarEvent

async def test_event_files_comments():
    """Probar si los endpoints de archivos y comentarios funcionan para eventos"""

    async with SessionLocal() as db:
        # Buscar un usuario para pruebas
        user = db.query(User).first()
        if not user:
            print("❌ No se encontró usuario para pruebas")
            return

        # Buscar un evento para pruebas
        event = db.query(CalendarEvent).filter(CalendarEvent.tenant_id == user.tenant_id).first()
        if not event:
            print("❌ No se encontró evento para pruebas")
            return

        print(f"✅ Usuario encontrado: {user.email}")
        print(f"✅ Evento encontrado: {event.title}")
        print(f"📝 Event ID: {event.id}")
        print(f"📝 Tenant ID: {event.tenant_id}")

        # Aquí podríamos probar los endpoints pero necesitamos que el backend esté corriendo
        print("\n📋 Para probar los endpoints:")
        print(f"   1. GET /api/v1/events/{event.id}/files - Listar archivos del evento")
        print(f"   2. POST /api/v1/files/upload?entity_type=event&entity_id={event.id} - Subir archivo al evento")
        print(f"   3. GET /api/v1/events/{event.id}/comments - Listar comentarios del evento")
        print(f"   4. POST /api/v1/events/{event.id}/comments - Agregar comentario al evento")

if __name__ == "__main__":
    asyncio.run(test_event_files_comments())
