from aiogram.fsm.state import State, StatesGroup

class sign(StatesGroup):
    login = State()
    password = State()


class TaskSolve(StatesGroup):
    waiting_answer = State()
