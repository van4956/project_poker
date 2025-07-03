import sys
import os
# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pokerlogic.best_action import best_action

args1 = {
    'size': 9,
    'active': 3,
    'hero_pos': 'UTG',
    'hero_cards': ['2s', '3h'],
    'board_cards': [],
    'range_hands': [],
    'pot': 3,
    'bb': 1,
    'hero_stack': 100,
    'to_call': 1
}

print(best_action(**args1))
