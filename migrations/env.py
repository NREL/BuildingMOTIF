from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from buildingmotif.database.tables import Base
from buildingmotif.database.utils import (
    _custom_json_deserializer,
    _custom_json_serializer,
)

# If config doesn't exist, this is considered a third party import and module cant be found.
import configs as building_motif_configs  # type: ignore # isort:skip

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# custom url from configs.
config.set_main_option("sqlalchemy.url", building_motif_configs.DB_URI)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Do not autogenerate migrations for rdflib sqlalchemy tables
sqlalchemy_rdflib_table_base_names = [
    "asserted_statements",
    "literal_statements",
    "namespace_binds",
    "quoted_statements",
    "type_statements",
]


def include_name(name, type_, parent_names):
    if name is None:
        return True
    else:
        return not any(n in name for n in sqlalchemy_rdflib_table_base_names)


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_name=include_name,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_engine(
        config.get_section(config.config_ini_section)["sqlalchemy.url"],
        poolclass=pool.NullPool,
        json_serializer=_custom_json_serializer,
        json_deserializer=_custom_json_deserializer,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
