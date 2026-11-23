import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import inspect, pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from app.core.config import settings
import app.models  # noqa: F401  Ensures every table is registered in metadata.


config = context.config
config.set_main_option("sqlalchemy.url", settings.async_database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def include_name(name: str | None, type_: str, parent_names: dict[str, str | None]) -> bool:
    """Limit autogeneration to AnkiBook's public schema."""
    if type_ == "schema":
        return name in (None, settings.DB_SCHEMA)
    return True


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_schemas=True,
        include_name=include_name,
    )

    with context.begin_transaction():
        context.run_migrations()


def _equivalent_foreign_key_names(connection: object) -> set[str]:
    """Match FKs while treating the default schema and ``public`` equally."""
    inspector = inspect(connection)
    database_fks: dict[str, tuple[object, ...]] = {}
    metadata_fks: dict[str, tuple[object, ...]] = {}

    for table in target_metadata.tables.values():
        table_schema = table.schema or settings.DB_SCHEMA
        # Tables created by a pending migration don't exist yet: nothing to compare.
        if not inspector.has_table(table.name, schema=table.schema):
            continue
        for foreign_key in inspector.get_foreign_keys(table.name, schema=table.schema):
            name = foreign_key.get("name")
            if name:
                options = foreign_key.get("options") or {}
                database_fks[name] = (
                    table_schema,
                    table.name,
                    tuple(foreign_key["constrained_columns"]),
                    foreign_key.get("referred_schema") or settings.DB_SCHEMA,
                    foreign_key["referred_table"],
                    tuple(foreign_key["referred_columns"]),
                    (options.get("ondelete") or "").upper(),
                )

        for foreign_key in table.foreign_key_constraints:
            if foreign_key.name:
                referred_table = foreign_key.referred_table
                metadata_fks[foreign_key.name] = (
                    table_schema,
                    table.name,
                    tuple(foreign_key.column_keys),
                    referred_table.schema or settings.DB_SCHEMA,
                    referred_table.name,
                    tuple(element.column.name for element in foreign_key.elements),
                    (foreign_key.ondelete or "").upper(),
                )

    return {
        name
        for name, definition in metadata_fks.items()
        if database_fks.get(name) == definition
    }


def do_run_migrations(connection: object) -> None:
    equivalent_fks = _equivalent_foreign_key_names(connection)
    # SQLAlchemy 2 starts a transaction for the reflection queries above.
    # End it so Alembic owns and commits the migration transaction itself.
    if connection.in_transaction():
        connection.commit()

    def include_object(
        object_: object,
        name: str | None,
        type_: str,
        reflected: bool,
        compare_to: object | None,
    ) -> bool:
        # Alembic otherwise sees public.foo and default-schema foo as distinct.
        if type_ == "foreign_key_constraint" and name in equivalent_fks:
            return False
        return True

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_schemas=True,
        include_name=include_name,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations through its sync bridge."""
    connect_args: dict[str, int] = {}
    if "asyncpg" in settings.async_database_url:
        connect_args["statement_cache_size"] = 0

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
