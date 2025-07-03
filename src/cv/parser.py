# общий парсинг, сбор и вывод всей необходимой информации для best_action

from .detect import detect_image, detect_cards
from .ocr import ocr_text
from fuzzywuzzy import fuzz

import sys
import os
import cv2
import math

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



def dist_points(a, b) -> float:
    '''
    Функция для расчета расстояния между двумя точками
    :param a: координаты точки 1
    :param b: координаты точки 2
    :return: расстояние между двумя точками
    '''
    return (a[0]-b[0])**2 + (a[1]-b[1])**2

def extract_number(text: str) -> float:
    '''
    Функция для извлечения числа из текста. Поиск с конца строки.
    :param text: текст для поиска числа
    :return: найденное число, либо 0.0 если не найдено
    '''
    words = text.split()

    for word in reversed(words):
        clean_word = word.replace('BB', '').replace('$', '').replace(',', '.')

        try:
            number = float(clean_word)
            # Исключаем 66, возможная ошибка OCR для BB
            if number != 66:
                return number
        except ValueError:
            continue

    return 0.0

def understand_button(text: str) -> str | None:
    '''
    Функция возвращает название кнопки, по обнаруженному через OCR тексту с помощью нечеткого сравнения
    :param text: строчка текста полученная через OCR
    :return: название кнопки или 'None' если не распознана
    '''
    text_lower = text.lower().strip()

    # Словарь кнопок и их возможных вариантов OCR
    button_variants = {
        'Call': ['call', 'кол', 'колл', 'уравнять', 'уравнять ставку'],
        'Raise': ['raise', 'рейз', 'поднять', 'поднять ставку'],
        'Bet': ['бет', 'bet', 'ставка', 'делать ставку'],
        'Fold': ['fold', 'фолд', 'сбросить', 'сброс'],
        'All-In': ['all-in', 'all in', 'олл-ин', 'олл ин', 'все в'],
        'Check': ['check', 'чек', 'пас', 'пропустить'],
        'Check / Fold': ['чек / фолд', 'чек фолд', 'чек фолд', 'check / fold', 'check fold', 'checkfold']
    }

    # Проверяем каждую кнопку
    for button_name, variants in button_variants.items():
        for variant in variants:
            # Точное вхождение подстроки
            if variant in text_lower:
                return button_name

            # Нечеткое сравнение (дополнительная проверка)
            if fuzz.ratio(text_lower, variant) > 70:
                return button_name

    return None

# Самая главная функция обработки изображения
def parse_image(image_path: str, conf: float = 0.3) -> dict:
    '''
    Общий парсинг скриншота, вывод всей возможной информации.
    :param image_path: путь к изображению
    :param conf: базовое пороговое значение уверенности для фильтрации (по дефолту 0.3)
    :return: словарь со всеми данными полученными из изображения
    '''
    # список обнаруженных объектов
    list_detect_images = detect_image(image_path=image_path,
                                                            conf=0.4,
                                                            save_img=True)

    # если нет обнаруженных объектов, то возвращаем None
    if len(list_detect_images) == 0:
        return {}

    # словарь результатов
    dict_result = {
                   'size': 0,
                   'active': 0,
                   'pot': 0,
                   'action_buttons': {},
                   'player_panels': [],
                   'to_call': 0,
                   'board_cards': [],
                   'hero_cards': [],
                   'hero_pos': None,
                   'hero_stack': 0,
                   'street': 'None',
                   }

    # размеры и центр изображения
    img = cv2.imread(image_path)
    img_h, img_w = img.shape[:2]
    center_img = (img_w // 2, img_h // 2)

    list_psm = ["--psm 6", "--psm 7", "--psm 8", "--psm 13"]
    list_lang = ['eng', 'rus']
    total_users = 0
    active_users = 0
    dict_active_buttons = {}
    list_player_panels = []
    pot, pot_conf = 0, 0
    dealer_coor, dealer_conf = (0, 0), 0
    hero_coor, hero_card_conf = (0, 0), 0
    hero_card = []


    # делаем первый цикл - уточнение параметров
    for det in list_detect_images:

        # уточняем размер банка - pot
        # если обнаружено несколько банков, то берется максимальный по уверенности
        if det['name'] == 'pot_box' and pot_conf < det['conf']:
            # проверяем все конфигурации PSM
            for psm in list_psm:
                pot_text = ocr_text(image_path, det['bbox'], config=psm, preprocess=False)
                pot, pot_conf = extract_number(pot_text), det['conf']
                if pot != 0:
                    break

        # уточняем координаты фишки дилера - dealer
        # если обнаружено несколько фишек дилера, то берется максимальная по уверенности
        if det['name'] == 'dealer_button' and dealer_conf < det['conf']:
            x1, y1, x2, y2 = det['bbox']
            dealer_coor = (x1 + x2) // 2, (y1 + y2) // 2
            dealer_conf = det['conf']

        # уточняем координаты героя - hero
        if det['name'] == 'hero_card' and hero_card_conf < det['conf']:
            x1, y1, x2, y2 = det['bbox']
            hero_coor = (x1 + x2) // 2, (y1 + y2) // 2
            hero_card_conf = det['conf']
            hero_card = detect_cards(image_path=image_path,
                                                bbox=det['bbox'],
                                                conf=conf,
                                                save_img=True)

        # уточняем общее количество игроков - total_users
        if det['name'] == 'player_panel':
            total_users += 1
            name_user = f'user_{total_users}'
            x1, y1, x2, y2 = det['bbox']
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            for psm in list_psm:
                ocr_text_ = ocr_text(image_path, det['bbox'], lang='eng', config=psm)
                stack = extract_number(ocr_text_)
                if stack != 0:
                    break
            dict_player_panels = {
                'name': name_user,
                'bbox': det['bbox'],
                'pos': None,
                'angle': 0,
                'center': center,
                'stack': stack
            }
            list_player_panels.append(dict_player_panels)

        # уточняем количество активных игроков (противников) - active_users
        if det['name'] == 'back_card':
            active_users += 1

        # уточняем активные кнопки - action_button
        if det['name'] == 'action_button':
            # проверяем все конфигурации PSM
            for psm in list_psm:
                for lang in list_lang:
                    ocr_button = ocr_text(image_path,
                                                det['bbox'],
                                                lang=lang,
                                                config=psm,
                                                preprocess=False)
                    action_button = understand_button(ocr_button)
                    if action_button:
                        dict_active_buttons[action_button] = det['bbox']
                        if action_button == 'Call':
                            to_call = extract_number(ocr_button)
                            dict_result['to_call'] = to_call
                        break

        # уточняем карты стола
        if det['name'] == 'board_card':
            board_card = detect_cards(image_path=image_path,
                                                bbox=det['bbox'],
                                                conf=conf,
                                                save_img=True)
            dict_result['board_cards'] = list(set(board_card))

    # если нет игроков, то возвращаем пустой словарь
    # это значит что у нас не покерная сессия
    if total_users == 0:
        return {}


    dict_result['active'] = active_users
    dict_result['pot'] = pot
    dict_result['action_buttons'] = dict_active_buttons
    dict_result['hero_cards'] = list(set(hero_card))

    # Уточняем карты доски
    board_card = set(dict_result['board_cards']) - set(dict_result['hero_cards'])
    dict_result['board_cards'] = list(board_card)

    # Фильтруем дубли player_panel (по близости центров)
    filtered_panels = []
    used = set()
    min_dist = 100  # минимальное расстояние между центрами для уникальных игроков
    for i, panel_i in enumerate(list_player_panels):
        if i in used:
            continue
        best_panel = panel_i
        for j, panel_j in enumerate(list_player_panels):
            if i != j and j not in used:
                dist = dist_points(panel_i['center'], panel_j['center']) ** 0.5
                if dist < min_dist:
                    best_panel = panel_i
                    used.add(j)
                    total_users -= 1
        filtered_panels.append(best_panel)
        used.add(i)
    list_player_panels = filtered_panels

    # Считаем углы относительно центра картинки (по часовой стрелке)
    for panel in list_player_panels:
        dx = panel['center'][0] - center_img[0]  # смещение по x
        dy = panel['center'][1] - center_img[1]  # смещение по y
        angle = math.atan2(dy, dx)             # угол в радианах
        panel['angle'] = round(angle, 2)

    # Сортируем по углу (по часовой стрелке)
    list_player_panels.sort(key=lambda p: p['angle'])

    # Находим индекс игрока BTN (дилера)
    distances = list(map(lambda panel: dist_points(panel['center'], dealer_coor), list_player_panels))
    btn_idx = distances.index(min(distances))

    # Сдвигаем список, чтобы BTN был первым
    list_player_panels = list_player_panels[btn_idx:] + list_player_panels[:btn_idx]

    # Назначаем позиции
    pos_names = ['BTN', 'SB', 'BB']
    for i, panel in enumerate(list_player_panels):
        panel['pos'] = pos_names[i] if i < len(pos_names) else f'M{i-2}'
        panel['name'] = f'user_{i+1}'

    # Находим героя
    for panel in list_player_panels:
        x1_p, y1_p, x2_p, y2_p = panel['bbox']
        x, y = hero_coor
        if x1_p <= x <= x2_p and y1_p <= y <= y2_p:
            panel['name'] = 'hero'
            dict_result['hero_pos'] = panel['pos']
            dict_result['hero_stack'] = panel['stack']
            break


    dict_result['size'] = total_users
    dict_result['player_panels'] = list_player_panels

    if len(dict_result['board_cards']) == 0:
        dict_result['street'] = "Preflop"
    elif len(dict_result['board_cards']) < 3:
        dict_result['street'] = "Flop"
    elif len(dict_result['board_cards']) == 4:
        dict_result['street'] = "Turn"
    elif len(dict_result['board_cards']) >= 5:
        dict_result['street'] = "River"


    return dict_result
