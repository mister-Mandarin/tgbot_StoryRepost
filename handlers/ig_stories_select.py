from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from database.queries import get_not_published_stories
from handlers.vk_stories_publish import vk_publish_stories
from keyboards.ig_stories_check import keyboard_ig_get_story
from services.state import StoryAction, StoryModeration

router = Router(name="ig_stories_select")


# --- ТРИГГЕР: Кнопка «Получить истории» ---
@router.message(Command("ig_get_stories"))
async def start_moderation(message: Message, state: FSMContext):
    # ТУТ вызывается ваш метод скачивания из Instagram (Этап 2)
    # await download_new_stories()

    stories = await get_not_published_stories()  # Получаем список из БД

    if not stories:
        await message.answer("Новых историй для публикации нет!")
        return

    # Инициализируем данные в FSM
    await state.set_state(StoryModeration.viewing)
    await state.update_data(stories=stories, current_index=0, selected_ids=list())

    first_story = stories[0]
    photo = FSInputFile(Path(first_story["thumb_path"]))

    await message.answer_photo(
        photo=photo,
        caption=f"История 1 из {len(stories)}\nТип: {'Видео' if first_story['media_type'] == 2 else 'Фото'}",
        reply_markup=keyboard_ig_get_story(stories, 0, set()),
    )


# --- ОБРАБОТКА НАВИГАЦИИ И ТОГГЛА ---
@router.callback_query(
    StoryModeration.viewing,
    StoryAction.filter(F.action.in_({"toggle", "next", "prev"})),
)
async def navigate_stories(
    callback: CallbackQuery, callback_data: StoryAction, state: FSMContext
):
    if not isinstance(callback.message, Message):
        return

    data = await state.get_data()
    stories = data["stories"]
    current_index = data["current_index"]
    selected_ids = data["selected_ids"]

    action = callback_data.action
    story_id = callback_data.story_id

    if action == "toggle":
        if story_id in selected_ids:
            selected_ids.remove(story_id)
        else:
            selected_ids.append(story_id)
        await state.update_data(selected_ids=selected_ids)

    elif action == "next":
        current_index += 1
        await state.update_data(current_index=current_index)

    elif action == "prev":
        current_index -= 1
        await state.update_data(current_index=current_index)

    # Обновляем сообщение (фото и клавиатуру)
    story = stories[current_index]
    photo = FSInputFile(Path(story["thumb_path"]))

    # Чтобы избежать мерцания, aiogram позволяет редактировать медиа
    from aiogram.types import InputMediaPhoto

    await callback.message.edit_media(
        media=InputMediaPhoto(
            media=photo,
            caption=f"История {current_index + 1} из {len(stories)}\nТип: {'Видео' if story['media_type'] == 2 else 'Фото'}",
        ),
        reply_markup=keyboard_ig_get_story(stories, current_index, selected_ids),
    )
    await callback.answer()


# --- ЗАВЕРШЕНИЕ: ПУБЛИКАЦИЯ ИЛИ ОТМЕНА ---
@router.callback_query(
    StoryModeration.viewing,
    StoryAction.filter(F.action.in_({"pub_selected", "pub_all", "cancel"})),
)
async def finish_moderation(
    callback: CallbackQuery, callback_data: StoryAction, state: FSMContext
):
    if not isinstance(callback.message, Message):
        return

    data = await state.get_data()
    action = callback_data.action

    if action == "cancel":
        await callback.message.delete()
        await callback.message.answer("Модерация отменена.")
        await state.clear()
        return

    stories = data["stories"]
    selected_ids = data["selected_ids"]

    # Определяем, какие истории публиковать
    to_publish = []
    if action == "pub_all":
        to_publish = stories
    elif action == "pub_selected":
        for chosen_id in selected_ids:
            for story in stories:
                if str(story["pk"]) == chosen_id:
                    to_publish.append(story)
                    break

    if not to_publish:
        await callback.answer("Ничего не выбрано!", show_alert=True)
        return

    # Удаляем предыдущее сообщение
    await callback.message.delete()

    await callback.message.answer("⏳ Публикация в процессе...")

    try:
        await vk_publish_stories(to_publish, state, callback)

        # Обновляем статусное сообщение на успех
        await callback.message.answer(
            f"🎉 Успешно опубликовано историй: {len(to_publish)}"
        )
    except Exception as e:
        # Если что-то пошло не так, пишем об ошибке
        await callback.message.answer(f"❌ Ошибка при публикации: {e}")
    finally:
        # Сбрасываем FSM состояние
        await state.clear()
