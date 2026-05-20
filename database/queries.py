from database.db import get_db


async def story_exists(pk: str) -> bool:
    connection = await get_db()
    cursor = await connection.execute("SELECT 1 FROM stories WHERE pk = ?", (pk,))
    return await cursor.fetchone() is not None


async def insert_story(story_data: dict) -> None:
    connection = await get_db()
    await connection.execute(
        """
        INSERT OR IGNORE INTO stories

            (pk, media_type, taken_at, expires_at, thumb_path, local_path)
        VALUES
            (:pk, :media_type, :taken_at, :expires_at, :thumb_path, :local_path)
    """,
        story_data,
    )
    await connection.commit()


async def get_active_stories():
    """Истории у которых не истёк срок и есть локальный файл."""
    connection = await get_db()
    cursor = await connection.execute("""
        SELECT * FROM stories
        WHERE expires_at > datetime('now')
            AND local_path IS NOT NULL
            AND published_at IS NULL
        ORDER BY taken_at DESC
    """)
    return await cursor.fetchall()


async def get_not_published_stories():
    connection = await get_db()
    cursor = await connection.execute("""
        SELECT * FROM stories
        WHERE published_at IS NULL
        ORDER BY taken_at DESC
    """)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def mark_published(pk: str, vk_story_id: str) -> None:
    connection = await get_db()
    await connection.execute(
        """
            UPDATE stories
            SET vk_story_id = ?, published_at = datetime('now')
            WHERE pk = ?
        """,
        (vk_story_id, pk),
    )
    await connection.commit()


async def mark_story_as_published(pk: str) -> None:
    connection = await get_db()
    await connection.execute(
        """
            UPDATE stories
            SET published_at = datetime('now')
            WHERE pk = ?
        """,
        (pk,),
    )
    await connection.commit()
