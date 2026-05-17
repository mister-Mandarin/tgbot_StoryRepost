import asyncio

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import Config
from services.instagram import get_and_download_my_stories

router = Router(name="ig_stories")


@router.message(Command("ig_sync_stories"))
async def cmd_sync_stories(message: Message, config: Config):
    await message.answer("🔄 Проверяю ваши истории в Instagram и загружаю новые...")

    try:
        loop = asyncio.get_running_loop()
        # Запускаем тяжелую функцию скачивания в отдельном потоке
        stories_report = await loop.run_in_executor(
            None, get_and_download_my_stories, config
        )

        if not stories_report:
            await message.answer("📭 У вас сейчас нет активных историй в профиле.")
            return

        # Считаем результаты для отчета пользователю
        new_count = sum(1 for s in stories_report if s["status"] == "new_downloaded")
        skipped_count = sum(
            1 for s in stories_report if s["status"] == "already_downloaded"
        )

        report_text = (
            f"✅ **Синхронизация завершена!**\n\n"
            f"📥 Скачано новых: `{new_count}`\n"
            f"⏭ Пропущено дубликатов: `{skipped_count}`\n\n"
            f"Файлы сохранены в вашу директорию историй."
        )
        await message.answer(report_text, parse_mode="Markdown")

    except Exception as e:
        await message.answer(f"❌ Ошибка при скачивании историй: {e}")
