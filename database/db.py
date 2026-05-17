import aiosqlite
from pathlib import Path


# Один экземпляр соединения на всё время жизни бота
_connection: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """Возвращает активное соединение с БД."""
    if _connection is None:
        raise RuntimeError("БД не инициализирована. Вызови init_db() при старте.")
    return _connection


async def init_db(db_path: Path) -> None:
    """Открывает соединение и создаёт таблицы, если их ещё нет."""
    global _connection

    _connection = await aiosqlite.connect(db_path)
    # Возвращать строки как dict-подобные объекты
    _connection.row_factory = aiosqlite.Row
    # WAL-режим: лучше для конкурентного чтения
    await _connection.execute("PRAGMA journal_mode=WAL")
    await _connection.execute("PRAGMA foreign_keys=ON")

    await _create_tables(_connection)
    await _connection.commit()


async def close_db() -> None:
    """Закрывает соединение при остановке бота."""
    global _connection
    if _connection:
        await _connection.close()
        _connection = None


async def _create_tables(conn: aiosqlite.Connection) -> None:
    await conn.executescript("""
        CREATE TABLE IF NOT EXISTS stories (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Идентификатор истории в Instagram (уникален)
            ig_story_id     TEXT    NOT NULL UNIQUE,

            -- 'video' или 'photo'
            media_type      TEXT    NOT NULL,

            -- Абсолютный путь к скачанному файлу (NULL пока не скачан)
            local_path      TEXT,

            -- Абсолютный путь к превью (NULL для фото — используется local_path)
            thumb_path      TEXT,

            -- Когда история исчезнет из Instagram (unix timestamp)
            -- Instagram хранит истории 24 часа с момента публикации
            expires_at      INTEGER NOT NULL,

            -- Когда мы скачали историю (unix timestamp)
            downloaded_at   INTEGER NOT NULL,

            -- ID истории в VK после публикации (NULL = не опубликована)
            vk_story_id     TEXT,

            -- Когда опубликовали в VK (unix timestamp, NULL = не публиковалось)
            published_at    INTEGER,

            -- 1 = файл удалён с диска (история истекла или вручную удалена)
            is_deleted      INTEGER NOT NULL DEFAULT 0
        );

        -- Быстрый поиск по истёкшим и неудалённым историям (для автоочистки)
        CREATE INDEX IF NOT EXISTS idx_stories_cleanup
            ON stories (expires_at, is_deleted);

        -- Быстрый поиск неопубликованных скачанных историй
        CREATE INDEX IF NOT EXISTS idx_stories_unpublished
            ON stories (published_at, is_deleted);
    """)
