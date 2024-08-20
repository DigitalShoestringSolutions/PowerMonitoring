from aiohttp import web
import aiosqlite
import logging

logger = logging.getLogger("stats_collector.db")


def get_db_path():
    # todo maybe from config or command line in future
    return "/app/data/db.sqlite3"


async def init(app: web.Application):
    sqlite_db = get_db_path()
    db = await aiosqlite.connect(sqlite_db)
    db.row_factory = aiosqlite.Row
    await check_exists(db)
    app["DB"] = db
    yield
    await db.close()


async def check_exists(db):
    # Check if the "usage_records" table exists
    async with db.execute(
        "SELECT name FROM sqlite_schema WHERE type='table' AND name='usage_records'"
    ) as cursor:
        exists = await cursor.fetchone() is not None

    if exists:
        # If it exists continue
        logger.info("Database found.")
    else:
        # If it doesn't - create it
        logger.info("Database does not exist - creating.")
        await db.execute(
            """
            CREATE TABLE usage_records (
                id INTEGER PRIMARY KEY,
                stat TEXT NOT NULL,
                value INTEGER NOT NULL,
                timestamp INTEGER NOT NULL
            );
            """
        )

        await db.execute(
            """
            CREATE TABLE usage_aggregated (
                id INTEGER PRIMARY KEY,
                stat TEXT NOT NULL,
                total INTEGER NOT NULL,
                hour_bucket_ts INTEGER NOT NULL,
 				UNIQUE(stat,hour_bucket_ts)
            )
            """
        )
        # Add an index on the "stat" column to speed up queries that filter on "stat"
        await db.execute(
            """
            CREATE INDEX idx_stat on usage_records (stat)
            """
        )

        await db.commit()
