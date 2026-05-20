from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import State, StatesGroup


class StoryModeration(StatesGroup):
    viewing = State()  # Просмотр и выбор историй


class StoryAction(CallbackData, prefix="story"):
    action: str # "toggle", "next", "prev", "pub_selected", "pub_all", "cancel"
    story_id: str  # ID истории из базы данных
