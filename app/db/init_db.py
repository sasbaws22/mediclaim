from datetime import datetime
import os
from typing import Any, Dict, List, Optional

from alembic.config import Config
from alembic import command
from sqlalchemy.orm import Session 
from sqlmodel import SQLModel

from app.db.session import Base, async_engine
from app.core.config import settings
from app.models.models import User, UserRole
from app.core.security import get_password_hash


def ensure_directories():
    os.makedirs("migrations", exist_ok=True)
    os.makedirs("migrations/versions", exist_ok=True)
    with open("migrations/__init__.py", "w") as f:
        f.write("# Alembic migration package")


def write_env_py():
    env_py_content = """
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config
fileConfig(config.config_file_name)

from app.models.models import Base
target_metadata = Base.metadata

from app.core.config import settings

def run_migrations_offline():
    url = settings.SQLALCHEMY_DATABASE_URI
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.SQLALCHEMY_DATABASE_URI
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""
    with open("migrations/env.py", "w") as f:
        f.write(env_py_content)


def write_script_py_mako():
    script_mako_content = """\"\"\"${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

\"\"\"
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}
"""
    with open("migrations/script.py.mako", "w") as f:
        f.write(script_mako_content)


def setup_alembic():
    ensure_directories()
    write_env_py()
    write_script_py_mako()

async def init_db() -> None: 
     setup_alembic()
     async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all) 

        alembic_cfg = Config("alembic.ini")
        command.stamp(alembic_cfg, "head")


def create_initial_data(db: Session) -> None:
    admin = db.query(User).filter(User.email == "ssako@faabsystems.com").first()
    if not admin:
        admin_user = User(
            email="ssako@faabsystems.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Admin User",
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(admin_user)
        db.commit()
