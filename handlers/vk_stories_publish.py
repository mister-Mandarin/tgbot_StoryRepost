from pathlib import Path

from database.queries import mark_story_as_published
from services.vk import publish_story


async def vk_publish_stories(to_publish, state, callback):

    success_count = 0
    failed_count = 0

    try:
        # Проходим циклом по выбранным историям
        for story in to_publish:
            # Определяем, какой файл отправлять: для видео — mp4 (local_path), для фото — jpg (thumb_path)
            media_type = story["media_type"]
            file_to_send = (
                Path(story["local_path"])
                if media_type == 2
                else Path(story["thumb_path"])
            )

            # Отправляем в ВК
            is_success = await publish_story(file_to_send, media_type)

            if is_success:
                # Помечаем в базе данных, используя ID истории
                await mark_story_as_published(str(story["id"]))
                success_count += 1
            else:
                failed_count += 1

        # Формируем итоговый текст отчета
        report_text = f"🎉 Публикация завершена!\n\nУспешно добавлено: {success_count}"
        if failed_count > 0:
            report_text += f"\n❌ Ошибок при отправке: {failed_count}"

        await callback.message.answer(report_text)

    except Exception as e:
        await callback.message.answer(f"❌ Критическая ошибка при публикации: {e}")
    finally:
        await state.clear()
