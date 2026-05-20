import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.methods import DeleteWebhook

from config import app_config
from database.db import close_db, init_db
from handlers import ig_auth, ig_stories, ig_stories_select
from services.middleware import OwnerOnlyMiddleware

logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db(app_config.db_path)

    bot = Bot(
        token=app_config.tg_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await bot(DeleteWebhook(drop_pending_updates=True))

    dp = Dispatcher()
    # Передаём config во все хэндлеры через workflow_data
    dp["config"] = app_config

    dp.message.middleware(OwnerOnlyMiddleware())
    dp.include_router(ig_auth.router)
    dp.include_router(ig_stories.router)
    dp.include_router(ig_stories_select.router)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await close_db()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        if app_config.app_env == "dev":
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            logging.basicConfig(level=logging.ERROR)
        print("Bot started...")
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
