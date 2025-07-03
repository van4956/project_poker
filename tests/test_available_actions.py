import sys
import os
# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pokerlogic.available_actions import get_available_actions

args1 = {
    'to_call': 100,
    'stack': 90,
    'bb': 1
}

args2 = {
    'to_call': 100,
    'stack': 1000,
    'bb': 1
}

args3 = {
    'to_call': 105,
    'stack': 300,
    'bb': 1
}

args4 = {
    'to_call': 0,
    'stack': 300,
    'bb': 1
}

print(f'args1: {get_available_actions(**args1)}')
print(f'args2: {get_available_actions(**args2)}')
print(f'args3: {get_available_actions(**args3)}')
print(f'args4: {get_available_actions(**args4)}')
