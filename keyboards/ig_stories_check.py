from aiogram import Router
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.state import StoryAction

router = Router(name="ig_stories_select")


def keyboard_ig_get_story(stories: list, current_index: int, selected_ids: set):
    """Генерирует клавиатуру для текущей истории."""
    builder = InlineKeyboardBuilder()
    story = stories[current_index]
    story_id = str(story["pk"])

    # 1. Кнопка-тоггл ✅/◻️
    is_chosen = story_id in selected_ids
    status_emoji = "✅ Выбрано" if is_chosen else "◻️ Отобрать"
    builder.button(
        text=status_emoji, callback_data=StoryAction(action="toggle", story_id=story_id)
    )

    # 2. Кнопки навигации (Назад / Вперед)
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(
            builder.button(
                text="⬅️ Пред.",
                callback_data=StoryAction(action="prev", story_id=story_id),
            )
        )
    if current_index < len(stories) - 1:
        nav_buttons.append(
            builder.button(
                text="След. ➡️",
                callback_data=StoryAction(action="next", story_id=story_id),
            )
        )

    # Корректно разбиваем ряды
    builder.adjust(1, len(nav_buttons), 2)

    # 3. Системные кнопки (публикация, отмена) — добавляем внизу
    builder.row(
        InlineKeyboardButton(
            text="🚀 Опубликовать выбранные",
            callback_data=StoryAction(action="pub_selected", story_id="0").pack(),
        ),
        InlineKeyboardButton(
            text="🔥 Все",
            callback_data=StoryAction(action="pub_all", story_id="0").pack(),
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=StoryAction(action="cancel", story_id="0").pack(),
        ),
    )
    return builder.as_markup()
