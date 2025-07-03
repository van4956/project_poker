import sys
import os
from treys import Card
# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cv.parser import parse_image


path = "test.png"

result = parse_image(path)

# print(*result.items(), sep='\n')
print(result['hero_cards'])
int_cards = map(Card.new, result['hero_cards'])
pretty_cards = map(lambda x: Card.int_to_pretty_str(x)[1:3], int_cards)
print(list(pretty_cards))

print(result['board_cards'])
int_cards = map(Card.new, result['board_cards'])
pretty_cards = map(lambda x: Card.int_to_pretty_str(x)[1:3], int_cards)
print(list(pretty_cards))
