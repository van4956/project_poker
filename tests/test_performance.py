import time
import sys
import os

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pokerlogic.best_action import best_action, save_equity_cache

def test_performance():
    """Тестирует производительность оптимизированной версии"""

    test_cases = [
        # Тест 1: Преflop
        {
            'name': 'Preflop - AA vs random',
            'args': {
                'size': 9,
                'active': 3,
                'pos': 'UTG',
                'hand': ['As', 'Ad'],
                'board': [],
                'range_hands': [],
                'pot': 150,
                'bb': 50,
                'stack': 2000,
                'to_call': 100,
                'n_simulations': 5000  # Быстрый тест
            }
        },

        # Тест 2: Flop
        {
            'name': 'Flop - Flush draw',
            'args': {
                'size': 6,
                'active': 2,
                'pos': 'BB',
                'hand': ['3s', '5s'],
                'board': ['Kd', '9h', '2s'],
                'range_hands': [],
                'pot': 350,
                'bb': 100,
                'stack': 900,
                'to_call': 315,
                'n_simulations': 5000
            }
        },

        # Тест 3: Turn
        {
            'name': 'Turn - Top pair',
            'args': {
                'size': 9,
                'active': 4,
                'pos': 'BTN',
                'hand': ['Kh', 'Qd'],
                'board': ['Ks', '9c', '2h', '7d'],
                'range_hands': [],
                'pot': 800,
                'bb': 50,
                'stack': 1500,
                'to_call': 200,
                'n_simulations': 3000
            }
        },

        # Тест 4:
        {
            'name': 'Turn - Top pair',
            'args': {
                'size': 9,
                'active': 4,
                'pos': 'BTN',
                'hand': ['Kh', 'Qd'],
                'board': ['Ks', '9c', '2h', '7d', '3s'],
                'range_hands': [],
                'pot': 800,
                'bb': 50,
                'stack': 1500,
                'to_call': 200,
                'n_simulations': 3000
            }
        }
    ]

    print("=" * 60)
    print("ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ ОПТИМИЗИРОВАННОЙ best_action()")
    print("=" * 60)

    total_time = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nТест {i}: {test_case['name']}")
        print("-" * 40)

        start_time = time.time()
        result = best_action(**test_case['args'])
        end_time = time.time()

        execution_time = end_time - start_time
        total_time += execution_time

        print(f"Время выполнения: {execution_time:.3f} секунд")
        print(f"Симуляций: {test_case['args']['n_simulations']:,}")
        print(f"Скорость: {test_case['args']['n_simulations']/execution_time:.0f} сим/сек")

        # Показываем топ-3 действия по EV
        sorted_actions = sorted(result.items(), key=lambda x: x[1], reverse=True)
        print("Топ-3 действия:")
        for j, (action, ev) in enumerate(sorted_actions[:3], 1):
            print(f"  {j}. {action}: {ev:.0f} EV")

    print("\n" + "=" * 60)
    print(f"ОБЩЕЕ ВРЕМЯ: {total_time:.3f} секунд")
    print(f"СРЕДНЕЕ ВРЕМЯ НА РАСЧЕТ: {total_time/len(test_cases):.3f} сек")

    # Сохраняем кэш после тестов
    save_equity_cache()
    print("Кэш equity сохранен в equity_cache.pickle")

    # Проверяем кэш
    print(f"\nРекомендации:")
    if total_time/len(test_cases) < 0.1:
        print("✅ Отлично! Время < 0.1 сек - подходит для real-time")
    elif total_time/len(test_cases) < 0.2:
        print("⚠️  Хорошо, но можно еще ускорить (уменьшить симуляции)")
    else:
        print("❌ Медленно для real-time. Нужны дополнительные оптимизации")

if __name__ == "__main__":
    test_performance()
