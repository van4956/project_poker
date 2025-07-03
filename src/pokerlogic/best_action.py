import hashlib
import pickle
import os
from functools import lru_cache
from math import comb
import numpy as np

from treys import Evaluator, Deck, Card
import random

try:
    from .available_actions import get_available_actions
except ImportError:
    from available_actions import get_available_actions

# Глобальный evaluator для переиспользования
EVALUATOR = Evaluator()

# Кэш для equity расчетов
EQUITY_CACHE = {}
CACHE_FILE = "equity_cache.pickle"

def load_equity_cache():
    """Загружает кэш equity из файла"""
    global EQUITY_CACHE
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'rb') as f:
                EQUITY_CACHE = pickle.load(f)
            print(f"Загружен кэш equity: {len(EQUITY_CACHE)} записей")
        except Exception as e:
            print(f"Ошибка загрузки кэша: {e}")
            EQUITY_CACHE = {}

def save_equity_cache():
    """Сохраняет кэш equity в файл"""
    try:
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(EQUITY_CACHE, f)
    except Exception as e:
        print(f"Ошибка сохранения кэша: {e}")

def get_cache_key(hero_cards: list, board_cards: list, active: int) -> str:
    """
    Создает ключ для кэширования equity. Сортируем руку и доску для консистентности
    :param hero_cards: рука игрока
    :param board: доска
    :param active: количество активных игроков
    :return: ключ для кэширования equity
    """
    sorted_hand = sorted(hero_cards)
    sorted_board = sorted(board_cards)
    key_data = f"{sorted_hand}_{sorted_board}_{active}"

    return hashlib.md5(key_data.encode()).hexdigest()

def calculate_equity_fast(hero_cards: list, board_cards: list, active: int, n_simulations: int) -> float:
    """
    Быстрый расчет equity с оптимизациями
    :param hero_cards: рука игрока
    :param board_cards: доска
    :param active: количество активных игроков
    :param n_simulations: количество симуляций
    :return: equity
    """
    # Проверяем кэш
    cache_key = get_cache_key([str(c) for c in hero_cards], [str(c) for c in board_cards], active)
    if cache_key in EQUITY_CACHE:
        return EQUITY_CACHE[cache_key]

    # Создаем одну колоду и убираем известные карты
    remaining_cards = []
    deck = Deck()
    used_cards = set(hero_cards + board_cards)
    remaining_cards = [c for c in deck.cards if c not in used_cards]

    wins = ties = losses = 0

    # Оптимизированный цикл симуляций
    for _ in range(n_simulations):
        # Перемешиваем оставшиеся карты
        random.shuffle(remaining_cards)

        # Раздаем карты противникам
        card_index = 0
        villains = []
        for _ in range(active - 1):
            villain = remaining_cards[card_index:card_index + 2]
            villains.append(villain)
            card_index += 2

        # Добираем доску до 5 карт, если нужно
        sim_board = board_cards[:]
        cards_needed = 5 - len(sim_board)
        if cards_needed > 0:
            sim_board.extend(remaining_cards[card_index:card_index + cards_needed])

        # Оценка рук
        hero_score = EVALUATOR.evaluate(sim_board, hero_cards)

        # Находим лучшего противника
        best_villain_score = float('inf')
        for villain in villains:
            villain_score = EVALUATOR.evaluate(sim_board, villain)
            if villain_score < best_villain_score:
                best_villain_score = villain_score

        # Подсчет результатов (в treys меньше = лучше)
        if hero_score < best_villain_score:
            wins += 1
        elif hero_score == best_villain_score:
            ties += 1
        else:
            losses += 1

    equity = (wins + 0.5 * ties) / n_simulations

    # Кэшируем результат
    EQUITY_CACHE[cache_key] = equity

    return equity


# Основная функция расчета оптимального действия в покере
def best_action(size: int,
                active: int,
                hero_pos: str,
                hero_cards: list,
                range_hands: list,
                board_cards: list,
                pot: float,
                hero_stack: float,
                to_call: float = 0,
                bb: float = 1,
                n_simulations: int = 10000,
                fold_equity: float = 0.5) -> dict[str,float]:
  '''
  Функция расчета оптимального действия в покере.
  Возвращает все возможные действия для конкретной позиции, с их EV.
  :size: int - общее количество мест за столом
  :active: int - количество участвующих (те кто еще не сбросил, с кем делим банк)
  :hero_pos: str - позиция игрока
  :hero_cards: list - рука игрока
  :range_hands: list - диапазон рук противников (может быть пустым)
  :board_cards: list - доска (может быть пустой, тогда это прифлоп)
  :pot: float - банк
  :bb: float - размер большого блейнда
  :hero_stack: float - количество фишек у игрока
  :to_call: float - необходимая ставка для продолжения
  :n_simulations: int - количество симуляций (по умолчанию 10000)
  :fold_equity: float - вероятность фолда оппонента (по умолчанию 0.5)
  :return: dict[str,float] - словарь, ключ - возможные действия, значение - EV
  '''
  # Проверяем количесвто карт в руке
  if len(hero_cards) != 2:
      raise ValueError("ошибка детекции карт в руке")

  # Преобразуем карты в объекты treys
  hero_cards = [Card.new(c) for c in hero_cards]
  board_cards = [Card.new(c) for c in board_cards]

  # Быстрый расчет equity
  equity = calculate_equity_fast(hero_cards, board_cards, active, n_simulations)

  # формируем возможные действия игрока
  available_actions = get_available_actions(to_call, hero_stack, bb)

  # рассчитываем EV для каждого действия
  for action, _ in available_actions.items():
      action_name, action_amount = action.split('_')
      action_amount = float(action_amount)

      if action_name == 'fold':
          # EV = 0
          available_actions[action] = 0

      elif action_name == 'check':
          # EV = E × Y
          available_actions[action] = round(equity * pot, 2)

      elif action_name == 'call':
          # EV = E × (Y + X) – (1 – E) × X
          X = action_amount  # наша ставка
          Y = pot           # текущий банк
          E = equity        # наша equity
          available_actions[action] = round(E * (Y + X) - (1 - E) * X, 2)

      elif action_name in ['bet', 'raise', 'all-in']:
          # EV = FE × Y + (1 – FE) × (E × (Y + X) – (1 – E) × X)
          X = action_amount  # наша ставка
          Y = pot           # текущий банк
          E = equity        # наша equity
          FE = fold_equity  # вероятность фолда оппонента
          available_actions[action] = round(FE * Y + (1 - FE) * (E * (Y + X) - (1 - E) * X), 2)

  return available_actions

# Загружаем кэш при импорте модуля
load_equity_cache()

# ... existing code ...

if __name__ == "__main__":
    args1 = {
        'size': 9,
        'active': 5,
        'hero_pos': 'UTG',
        'hero_cards': ['3s', 'Kh'],
        'board_cards': [],
        'range_hands': [],
        'pot': 3,
        'bb': 1,
        'hero_stack': 9,
        'to_call': 2,
        'n_simulations': 10000  # Теперь можно настраивать
    }

    print("Запуск оптимизированной версии...")
    import time
    start = time.time()
    result = best_action(**args1)
    end = time.time()

    print(f"Результат: {result}")
    print(f"Время выполнения: {end - start:.3f} секунд")

    # Сохраняем кэш при завершении
    save_equity_cache()
