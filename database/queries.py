"""
Все запросы к БД сосредоточены здесь.
Каждая функция принимает соединение явно — удобно тестировать.
"""

import time
from dataclasses import dataclass
from typing import Optional

import aiosqlite

# ---------------------------------------------------------------------------
# Модель строки таблицы stories
# ---------------------------------------------------------------------------


@dataclass
class Story:
    id: int
    ig_story_id: str
    media_type: str  # 'video' | 'photo'
    local_path: Optional[str]
    thumb_path: Optional[str]
    expires_at: int  # unix timestamp
    downloaded_at: int  # unix timestamp
    vk_story_id: Optional[str]
    published_at: Optional[int]
    is_deleted: bool

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "Story":
        return cls(
            id=row["id"],
            ig_story_id=row["ig_story_id"],
            media_type=row["media_type"],
            local_path=row["local_path"],
            thumb_path=row["thumb_path"],
            expires_at=row["expires_at"],
            downloaded_at=row["downloaded_at"],
            vk_story_id=row["vk_story_id"],
            published_at=row["published_at"],
            is_deleted=bool(row["is_deleted"]),
        )

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def is_published(self) -> bool:
        return self.vk_story_id is not None


# ---------------------------------------------------------------------------
# INSERT
# ---------------------------------------------------------------------------


async def insert_story(
    conn: aiosqlite.Connection,
    *,
    ig_story_id: str,
    media_type: str,
    local_path: str,
    thumb_path: str | None,
    expires_at: int,
) -> int:
    cursor = await conn.execute(
        """
        INSERT INTO stories
            (ig_story_id, media_type, local_path, thumb_path, expires_at, downloaded_at)
        VALUES
            (?, ?, ?, ?, ?, ?)
        ON CONFLICT(ig_story_id) DO NOTHING
        """,
        (ig_story_id, media_type, local_path, thumb_path, expires_at, int(time.time())),
    )
    await conn.commit()

    if cursor.rowcount == 1:
        return cursor.lastrowid or 0

    cursor = await conn.execute(
        "SELECT rowid FROM stories WHERE ig_story_id = ?",
        (ig_story_id,),
    )
    row = await cursor.fetchone()
    return row[0] if row else 0


# ---------------------------------------------------------------------------
# SELECT
# ---------------------------------------------------------------------------


async def get_story_by_ig_id(
    conn: aiosqlite.Connection,
    ig_story_id: str,
) -> Optional[Story]:
    """Возвращает историю по ig_story_id или None."""
    async with conn.execute(
        "SELECT * FROM stories WHERE ig_story_id = ?", (ig_story_id,)
    ) as cursor:
        row = await cursor.fetchone()
        return Story.from_row(row) if row else None


async def get_all_active_stories(conn: aiosqlite.Connection) -> list[Story]:
    """
    Скачанные истории, которые ещё не истекли и не удалены.
    Используется для отображения в боте.
    """
    async with conn.execute(
        """
        SELECT * FROM stories
        WHERE is_deleted = 0
          AND expires_at > ?
        ORDER BY downloaded_at DESC
        """,
        (int(time.time()),),
    ) as cursor:
        rows = await cursor.fetchall()
        return [Story.from_row(r) for r in rows]


async def get_unpublished_stories(conn: aiosqlite.Connection) -> list[Story]:
    """Активные истории, которые ещё не были опубликованы в VK."""
    async with conn.execute(
        """
        SELECT * FROM stories
        WHERE is_deleted = 0
          AND expires_at > ?
          AND published_at IS NULL
        ORDER BY downloaded_at DESC
        """,
        (int(time.time()),),
    ) as cursor:
        rows = await cursor.fetchall()
        return [Story.from_row(r) for r in rows]


async def get_expired_not_deleted(conn: aiosqlite.Connection) -> list[Story]:
    """Истории, у которых истёк срок, но файлы ещё не удалены. Для автоочистки."""
    async with conn.execute(
        """
        SELECT * FROM stories
        WHERE is_deleted = 0
          AND expires_at <= ?
        """,
        (int(time.time()),),
    ) as cursor:
        rows = await cursor.fetchall()
        return [Story.from_row(r) for r in rows]


async def story_exists(conn: aiosqlite.Connection, ig_story_id: str) -> bool:
    """Быстрая проверка — уже скачивали эту историю?"""
    async with conn.execute(
        "SELECT 1 FROM stories WHERE ig_story_id = ?", (ig_story_id,)
    ) as cursor:
        return await cursor.fetchone() is not None


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------


async def mark_published(
    conn: aiosqlite.Connection,
    *,
    ig_story_id: str,
    vk_story_id: str,
) -> None:
    """Помечает историю как опубликованную в VK."""
    await conn.execute(
        """
        UPDATE stories
        SET vk_story_id = ?,
            published_at = ?
        WHERE ig_story_id = ?
        """,
        (vk_story_id, int(time.time()), ig_story_id),
    )
    await conn.commit()


async def mark_deleted(
    conn: aiosqlite.Connection,
    ig_story_id: str,
) -> None:
    """Помечает историю как удалённую (файл уже удалён с диска)."""
    await conn.execute(
        "UPDATE stories SET is_deleted = 1 WHERE ig_story_id = ?",
        (ig_story_id,),
    )
    await conn.commit()


async def mark_deleted_batch(
    conn: aiosqlite.Connection,
    ig_story_ids: list[str],
) -> None:
    """Пакетная пометка удалённых — для автоочистки."""
    if not ig_story_ids:
        return
    placeholders = ",".join("?" * len(ig_story_ids))
    await conn.execute(
        f"UPDATE stories SET is_deleted = 1 WHERE ig_story_id IN ({placeholders})",
        ig_story_ids,
    )
    await conn.commit()
