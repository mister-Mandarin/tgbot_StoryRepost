import asyncio
import logging
from datetime import timedelta
from pathlib import Path

from instagrapi import Client

from config import Config
from database.queries import insert_story

logger = logging.getLogger(__name__)
cl = Client()


def login(config: Config, verification_code: str = ""):
    session_file = config.sessions_dir / "instagram.json"

    if session_file.exists():
        try:
            cl.load_settings(session_file)
            if cl.user_id:
                print("Сессия успешно загружена из файла, повторный логин не требуется.")
                return  # Выходим, всё готово
        except Exception:
            print("Старая сессия недействительна, выполняем вход по паролю...")
            # Если сессия устарела — сбрасываем настройки перед новым логином
            cl.set_settings({})

    if verification_code:
        cl.login(
            config.ig_username, config.ig_password, verification_code=verification_code
        )
    else:
        cl.login(config.ig_username, config.ig_password)

    cl.dump_settings(session_file)
    cl.account_info()
    print("Выполнен вход по паролю, сессия сохранена.")


def get_and_download_my_stories(config: Config) -> list[dict]:
    stories = cl.user_stories(str(cl.user_id))

    result = []

    for story in stories:
        pk = str(story.pk)
        media_type = story.media_type
        taken_at = story.taken_at
        expires_at = taken_at + timedelta(hours=24)

        # Пути к файлам
        thumb_path = config.stories_dir / f"story_{pk}_thumb.jpg"
        if media_type == 2:
            local_path = config.stories_dir / f"story_{pk}.mp4"
        else:
            local_path = config.stories_dir / f"story_{pk}.jpg"

        # Проверка дубликата по наличию файла
        if local_path.exists():
            result.append(
                {
                    "pk": pk,
                    "status": "already_downloaded",
                    "local_path": str(local_path),
                }
            )
            continue

        _download_file(str(story.thumbnail_url), thumb_path, is_video=False)
        if media_type == 2 and story.video_url:
            _download_file(str(story.video_url), local_path, is_video=True)
        else:
            local_path = thumb_path

        # Пишем в БД
        asyncio.run(
            insert_story(
                {
                    "pk": pk,
                    "media_type": media_type,
                    "taken_at": str(taken_at),
                    "expires_at": str(expires_at),
                    "thumb_path": str(thumb_path),
                    "local_path": str(local_path),
                },
            )
        )

        result.append(
            {
                "pk": pk,
                "status": "new_downloaded",
                "local_path": str(local_path),
            }
        )

    return result


def _download_file(url: str, dest: Path, is_video: bool) -> None:
    """Скачивает файл по URL в зависимости от его типа."""
    if is_video:
        cl.video_download_by_url(url, dest.stem, dest.parent)
    else:
        cl.photo_download_by_url(url, dest.stem, dest.parent)
