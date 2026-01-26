#!/usr/bin/env python
"""Obtener el user ID real de owner@aiutox.com."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.user import User

# Conectar a la BD
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aiutox:aiutox123@localhost:5432/aiutox_erp")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Buscar el usuario owner@aiutox.com
    owner = db.query(User).filter(User.email == "owner@aiutox.com").first()

    if owner:
        print("✅ Usuario encontrado:")
        print(f"   ID: {owner.id}")
        print(f"   Email: {owner.email}")
        print(f"   Tenant ID: {owner.tenant_id}")
        print(f"   Full Name: {owner.full_name}")
        print(f"   Is Active: {owner.is_active}")
    else:
        print("❌ Usuario owner@aiutox.com no encontrado")

finally:
    db.close()
