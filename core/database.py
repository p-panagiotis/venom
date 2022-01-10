import logging
import os

from alembic.config import Config
from alembic.runtime import migration
from alembic.runtime.environment import EnvironmentContext
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, exc, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker

from fastapi import Request

logger = logging.getLogger(__name__)
logging.getLogger("alembic").setLevel(logging.ERROR)
# logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

ALEMBIC_TABLE_PREFIX = "alembic_"


class Database(object):

    def __init__(self, url, pool_size=5, max_overflow=10):
        """ Construct a new :class: `Database`

        :param url: The database url to create the database engine
        :param pool_size: The number of connections to keep open inside the connection pool
        :param max_overflow: The number of connections to allow in connection pool "overflow",
                             that is connections that can be opened above and beyond the pool_size setting
        """
        self.url = url
        self.pool_size = pool_size
        self.max_overflow = max_overflow

        logger.info("Initializing database engine...")
        try:
            self.engine = create_engine(self.url, pool_size=pool_size, max_overflow=max_overflow)
        except TypeError:
            self.engine = create_engine(self.url)

        self.Session = scoped_session(sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            enable_baked_queries=False
        ))

        try:
            logger.info("Initializing database connection...")
            self.engine.execute("SELECT 1")
        except (exc.OperationalError, exc.ProgrammingError) as e:
            raise SystemExit(e)

    def apply_migrations(self):
        migrations_folder = os.path.join("core", "api", "migrations")
        if os.path.exists(migrations_folder):
            self.migrate(repository=migrations_folder, version_table=ALEMBIC_TABLE_PREFIX + "venom")

        for root_package, dirs, files in os.walk("api"):
            for dir_name in dirs:
                migrations_folder = root_package + os.path.sep + dir_name + os.path.sep + "migrations"
                if os.path.exists(migrations_folder):
                    self.migrate(repository=migrations_folder, version_table=ALEMBIC_TABLE_PREFIX + dir_name)

    def migrate(self, repository, version_table):
        config = Config()
        config.set_main_option("script_location", repository)
        config.set_main_option("url", self.url)

        with self.engine.connect() as connection:
            migration_context = MigrationContext.configure(connection, opts=dict(version_table=version_table))
            current_revision = migration_context.get_current_revision()
            script = ScriptDirectory.from_config(config)
            current_head = script.get_current_head()

            def upgrade(rev, ctx):
                logger.info(f"Applying database migrations of repository \"{repository}\"")
                with script._catch_revision_errors(
                        ancestor="Destination %(end)s is not a valid upgrade target from current head(s)",
                        end="head"
                ):
                    revs = list(script.revision_map.iterate_revisions("head", rev, implicit_base=True))
                    upgraded_revisions = []
                    for sc in reversed(revs):
                        down_revision = sc.down_revision if sc.down_revision else "000"
                        logger.info(f"Migrating revision {down_revision} -> {sc.revision} {sc.doc}")
                        upgraded_revision = migration.MigrationStep.upgrade_from_script(script.revision_map, sc)
                        upgraded_revisions.append(upgraded_revision)
                    return upgraded_revisions

            if current_head != current_revision:
                try:
                    with EnvironmentContext(config=config,
                                            script=script,
                                            fn=upgrade,
                                            as_sql=False,
                                            starting_rev=None,
                                            destination_rev="head") as context:

                        context.configure(connection=connection, version_table=version_table)

                        with context.begin_transaction():
                            context.run_migrations()

                    logger.info(f"Database migrations of repository \"{repository}\" migrated")
                except Exception as e:
                    raise SystemExit(e)
            else:
                logger.info(f"Repository \"{repository}\" migrations on version {current_head}")

    def truncate_tables(self):
        with self.engine.connect() as session:
            sorted_tables = self.get_sorted_tables()
            for table in reversed(sorted_tables):
                table_name = table.name
                # disable table foreign key checks
                session.execute(f"ALTER TABLE {table_name} DISABLE TRIGGER ALL")
                # process table data deletion
                session.execute(table.delete())
                # reset table id counter to 1
                session.execute(f"ALTER SEQUENCE {table_name}_id_seq RESTART WITH 1;")
                # enable table triggers e.g. foreign key checks
                session.execute(f"ALTER TABLE {table_name} ENABLE TRIGGER ALL;")
        return self

    def get_sorted_tables(self):
        sorted_tables = []
        meta = MetaData(bind=self.engine)
        meta.reflect(self.engine)
        for table in meta.sorted_tables:
            if table.name.startswith(ALEMBIC_TABLE_PREFIX):
                continue
            sorted_tables.append(table)
        return sorted_tables


def get_db(request: Request):
    """ Returns current session database object per request """
    return request.state.session
