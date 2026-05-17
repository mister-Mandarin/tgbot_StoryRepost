import json

from instagrapi import Client

from config import Config

cl = Client()


def login(config: Config, verification_code: str = ""):
    session_file = config.sessions_dir / "instagram.json"

    if session_file.exists():
        try:
            cl.load_settings(session_file)
            # Проверяем, работает ли загруженная сессия
            cl.get_timeline_feed()
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

    # апрашиваем список своих активных историй
    stories = cl.user_stories(str(cl.user_id))

    saved_stories_info = []

    for story in stories:
        # Уникальный первичный ключ истории
        story_id = story.pk

        # Формируем базовое имя файла на основе ID истории
        base_filename = f"story_{story_id}"
        json_path = config.stories_dir / f"{base_filename}.json"

        # Собираем максимум метаданных, включая ссылки на превью
        # instagrapi отдает сущности в виде Pydantic-моделей или объектов, переводим в dict
        metadata = {
            "id": story.id,
            "pk": story.pk,
            "code": story.code,
            "taken_at": str(story.taken_at),  # Время публикации
            "media_type": story.media_type,  # 1 — фото, 2 — видео
            "product_type": story.product_type,
            "thumbnail_url": str(story.thumbnail_url) if story.thumbnail_url else None,
            # Видео содержит список доступных версий превью разного качества
            # "video_dash_manifest": story.video_dash_manifest
            # if hasattr(story, "video_dash_manifest")
            # else None,
            "video_duration": story.video_duration
            if hasattr(story, "video_duration")
            else 0,
            "mentions": [m.user.username for m in story.mentions]
            if story.mentions
            else [],
            "medias": [str(url) for url in story.medias] if story.medias else [],
        }

        # 3. Проверка на дубликаты: если JSON уже есть, значит история скачана
        if json_path.exists():
            metadata["status"] = "already_downloaded"
            saved_stories_info.append(metadata)
            continue  # Пропускаем скачивание самого медиафайла

        if story.media_type == 2 and story.video_url:
            cl.story_download_by_url(
                url=str(story.video_url),
                filename=base_filename,
                folder=config.stories_dir,
            )
        else:
            cl.story_download(
                story_pk=story.pk, filename=base_filename, folder=config.stories_dir
            )

        # 5. Сохраняем метаданные в JSON файл рядом с картинкой/видео
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)

        metadata["status"] = "new_downloaded"
        saved_stories_info.append(metadata)

    return saved_stories_info
