import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Обязательная переменная окружения не задана: {key}")
    return value


@dataclass(frozen=True)
class Config:
    # Режим работы
    app_env: str

    # Telegram
    tg_bot_token: str
    tg_owner_id: int

    # Пути
    data_dir: Path
    sessions_dir: Path
    db_path: Path
    stories_dir: Path

    # Instagram
    ig_username: str
    ig_password: str

    # VK
    vk_user_token: str = ""


def load_config() -> Config:
    data_dir = Path("data")

    cfg = Config(
        # Режим работы
        app_env=_require("APP_ENV"),
        # Telegram
        tg_bot_token=_require("TG_BOT_TOKEN"),
        tg_owner_id=int(_require("TG_OWNER_ID")),
        # Пути
        data_dir=data_dir,
        sessions_dir=data_dir / "sessions",
        db_path=Path(data_dir / "db.sqlite3"),
        stories_dir=data_dir / "stories",
        # Instagram
        ig_username=_require("IG_USERNAME"),
        ig_password=_require("IG_PASSWORD"),
        # VK
        vk_user_token=_require("VK_USER_TOKEN"),
    )

    # Создаём директории при необходимости
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.sessions_dir.mkdir(parents=True, exist_ok=True)
    cfg.stories_dir.mkdir(parents=True, exist_ok=True)

    return cfg
