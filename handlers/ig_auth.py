import asyncio

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from config import Config
from services.instagram import cl, login

router = Router(name="ig_auth")


class AuthState(StatesGroup):
    wait_2fa = State()


@router.message(Command("ig_login"))
async def cmd_ig_login(message: Message, config: Config, state: FSMContext):
    try:
        await message.answer("⏳ Проверяем сессию / Авторизуемся...")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, login, config)
        await message.answer(f"✅ Успешно залогинен как {cl.username}")

    except Exception as e:
        # Проверяем, содержит ли текст ошибки упоминание 2FA
        if "Two-factor authentication required" in str(e):
            await message.answer(
                "🔐 На аккаунте включена 2FA. Пожалуйста, **отправьте код безопасности** из SMS или приложения-аутентификатора:"
            )
            # Переводим пользователя в состояние ожидания кода
            await state.set_state(AuthState.wait_2fa)
        else:
            await message.answer(f"❌ Ошибка: {e}")


@router.message(AuthState.wait_2fa)
async def process_2fa_code(message: Message, state: FSMContext, config: Config):

    if message.text:
        code = message.text.strip().replace(" ", "")
    else:
        await message.answer(
            "❌ Пожалуйста, **отправьте код безопасности** из SMS или приложения-аутентификатора:"
        )
        return

    await message.answer("⏳ Отправляем код в Instagram...")

    try:
        loop = asyncio.get_running_loop()
        # Вызываем login повторно, но уже передаем введенный код
        await loop.run_in_executor(None, login, config, code)

        await message.answer(f"✅ Код принят! Залогинен как {cl.username}")
        await state.clear()  # Сбрасываем состояние FSM

    except Exception as e:
        await message.answer(
            f"❌ Не удалось войти с этим кодом: {e}\n\nПопробуйте ввести код еще раз или перезапустите процесс командой /ig_login."
        )
