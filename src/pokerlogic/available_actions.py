import math

# Функция формирования возможных ответных действий
def get_available_actions(to_call: float = 0,
                          stack: float = 0,
                          bb: float = 1) -> dict[str, float]:
    '''
    Функция формирования возможных ответных действий в покере.
    Возвращает все возможные действия для текущей ситуации.
    :to_call: float - необходимая ставка для продолжения
    :stack: float - количество фишек у игрока
    :bb: float - размер большого блейнда
    :return: dict[str, None] - словарь, ключ - возможные действия с суммой ставки, значение - None (заполняется позже)
    '''

    actions = {}

    # Никто не поставил до нас (to_call == 0)
    if to_call == 0:
        actions['check_0'] = None
        actions[f'bet_{bb}'] = None
        actions[f'all-in_{stack}'] = None

    # Есть ставка перед нами (to_call > 0)
    else:
        # Cтек меньше ставки
        if to_call >= stack:
            actions['fold_0'] = None
            actions[f'all-in_{stack}'] = None

        # Cтек больше ставки
        else:
            actions['fold_0'] = None
            actions[f'call_{to_call}'] = None

            # raise x2 от to_call, округленный до BB
            raise_2x = math.ceil((to_call * 2) / bb) * bb
            if stack >= raise_2x:
                actions[f'raise_{raise_2x}'] = None

            # raise x3 от to_call, округленный до BB
            raise_3x = math.ceil((to_call * 3) / bb) * bb
            if stack >= raise_3x:
                actions[f'raise_{raise_3x}'] = None

            actions[f'all-in_{stack}'] = None

    return actions
