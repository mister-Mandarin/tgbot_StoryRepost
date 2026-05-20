import logging
from pathlib import Path

import httpx
from aiogram import Router
from aiogram.filters import Command

from config import app_config

router = Router(name="vk_stories")
logger = logging.getLogger(__name__)


@router.message(Command("vk_get_stories"))
async def publish_story(file_path: Path, media_type: int) -> bool:
    """
    Публикует историю в ВК.
    media_type: 1 для фото, 2 для видео.
    """
    if not file_path.exists():
        logger.error(f"Файл не найден для публикации в ВК: {file_path}")
        return False

    async with httpx.AsyncClient() as client:
        try:
            # Шаг 1: Получаем URL сервера для загрузки
            if media_type == 2:
                method = "stories.getVideoUploadServer"
                params = {
                    "add_to_news": 1,
                    "link_text": "open",
                    "access_token": app_config.vk_user_token,
                    "v": app_config.vk_api_version,
                }
            else:
                method = "stories.getPhotoUploadServer"
                params = {
                    "add_to_news": 1,
                    "access_token": app_config.vk_user_token,
                    "v": app_config.vk_api_version,
                }

            response = await client.get(
                f"{app_config.vk_api_url}/method/{method}", params=params
            )
            res_data = response.json()

            if "error" in res_data:
                logger.error(f"Ошибка получения сервера ВК: {res_data['error']}")
                return False

            upload_url = res_data["response"]["upload_url"]

            # Шаг 2: Загружаем файл на полученный сервер
            field_name = "video_file" if media_type == 2 else "file"
            with open(file_path, "rb") as f:
                files = {field_name: (file_path.name, f)}
                upload_response = await client.post(upload_url, files=files)
                upload_data = upload_response.json()
                # Шаг 3: Сохраняем историю в ВК (Обязательно для всех типов!)
            save_params = {
                "access_token": app_config.vk_user_token,
                "v": str(app_config.vk_api_version),
            }

            if media_type == 2:
                # Видео-сервер возвращает строку в upload_result
                if "upload_result" in upload_data:
                    save_params["upload_results"] = upload_data["upload_result"]
                # Если видео-сервер вернул структуру (в зависимости от подсети ВК)
                elif (
                    "response" in upload_data
                    and "upload_result" in upload_data["response"]
                ):
                    save_params["upload_results"] = upload_data["response"][
                        "upload_result"
                    ]
                else:
                    logger.error(
                        f"Неизвестный формат ответа видео-сервера ВК: {upload_data}"
                    )
                    return False
            else:
                # Фото-сервер возвращает параметры внутри upload_url_params
                if (
                    "response" in upload_data
                    and "upload_url_params" in upload_data["response"]
                ):
                    save_params["upload_results"] = upload_data["response"][
                        "upload_url_params"
                    ]
                else:
                    # Прямой ответ без ключа response
                    save_params["upload_results"] = upload_data.get("upload_url_params")

            if not save_params.get("upload_results"):
                logger.error(
                    f"Не удалось вытащить результаты загрузки из ответа: {upload_data}"
                )
                return False

                # Отправляем финальный запрос на сохранение
            save_response = await client.get(
                f"{app_config.vk_api_url}/method/stories.save", params=save_params
            )
            save_data = save_response.json()

            if "error" in save_data:
                logger.error(f"Ошибка сохранения истории ВК: {save_data['error']}")
                return False

            logger.info("История успешно опубликована в ВК!")
            return True

        except Exception as e:
            logger.error(f"Исключение при публикации в ВК: {e}")
            return False
