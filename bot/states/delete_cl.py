from aiogram.fsm.state import State, StatesGroup

class DeleteClient(StatesGroup):
    number = State()
