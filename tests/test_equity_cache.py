import pickle
import os

if os.path.exists('src/pokerlogic/equity_cache.pickle'):
    with open('src/pokerlogic/equity_cache.pickle', 'rb') as f:
        cache = pickle.load(f)
    print(f'Размер кэша: {len(cache)} записей')
    for i, (key, value) in enumerate(list(cache.items())):
        print(f'{i+1}. {key[:10]}... = {value:.3f}')

else:
    print('Файл кэша не найден')
