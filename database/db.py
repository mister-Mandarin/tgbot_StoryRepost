from pathlib import Path

import aiosqlite

_connection: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    if _connection is None:
        raise RuntimeError("БД не инициализирована. Вызови init_db() при старте.")
    return _connection


async def init_db(db_path: Path) -> None:
    global _connection
    _connection = await aiosqlite.connect(db_path)
    _connection.row_factory = aiosqlite.Row
    # запись и чтение без блокировки базы
    await _connection.execute("PRAGMA journal_mode=WAL")
    await _connection.execute("PRAGMA foreign_keys=ON")
    await _create_tables(_connection)
    await _connection.commit()


async def close_db() -> None:
    global _connection
    if _connection:
        await _connection.close()
        _connection = None


async def _create_tables(conn: aiosqlite.Connection) -> None:
    await conn.executescript("""
        CREATE TABLE IF NOT EXISTS stories (
            pk           TEXT PRIMARY KEY,
            media_type   INTEGER NOT NULL,  -- 1=фото, 2=видео
            taken_at     TEXT NOT NULL,
            expires_at   TEXT NOT NULL,     -- taken_at + 24h
            thumb_path   TEXT,
            local_path   TEXT,
            vk_story_id  TEXT,
            published_at TEXT
        );
    """)
