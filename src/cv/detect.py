# определяем по картинке объекты: стол, карты, стек, pot, кнопки

from ultralytics import YOLO
import ultralytics
import cv2
import numpy as np
import os
import sys
import logging
from pathlib import Path

# Настройка логгера для этого модуля
logger = logging.getLogger(__name__)

def get_model_path(model_name):
    """Получает путь к модели в зависимости от способа запуска"""
    if getattr(sys, 'frozen', False):
        # Запуск из .exe файла
        base_path = Path(sys._MEIPASS)
        return str(base_path / "models" / model_name)
    else:
        # Обычный запуск
        return f"models/{model_name}"

# Загружаем общую модель детекции всего стола
TOTAL_MODEL_PATH = get_model_path("totalpoker_yolo11n_200_768_40_0005.pt")
total_model = YOLO(TOTAL_MODEL_PATH, verbose=True)

# Загружаем модель для детекции карт
CARDS_MODEL_PATH = get_model_path("pokercard_yolo11n_7598_768_80_001.pt")
cards_model = YOLO(CARDS_MODEL_PATH, verbose=True)


def detect_image(image_path: str, conf: float = 0.3, save_img: bool = False) -> list[dict]:
    '''
    Функция для детектирования визуальных объектов на изображении.
    :param image_path: путь к PNG картинке
    :param conf: пороговое значение для фильтрации детекций (default=0.3)
    :param save_img: флаг для сохранения изображения с детекциями (default=False)
    :return: список словарей [{'name': 'card', 'bbox': (x1, y1, x2, y2), 'conf': 0.93}, ...]
    '''

    results = total_model(image_path, conf=conf, imgsz=768)[0]
    detections = []

    if save_img:
        image_path = image_path.replace('.png', '_table.png')
        cv2.imwrite(image_path, results.plot())

    for box in results.boxes.data.tolist():
        x1, y1, x2, y2, conf, cls = box
        name = total_model.names[int(cls)]
        detections.append({
            'name': name,
            'bbox': [int(x1), int(y1), int(x2), int(y2)],
            'conf': float(conf)
        })

    return detections


def detect_cards(image_path: str, bbox: tuple[int, int, int, int], conf: float = 0.3, save_img: bool = False) -> list:
    '''
    Функция детектирует все карты на изображении.
    :param image_path: путь к PNG картинке
    :param bbox: координаты бокса (x1, y1, x2, y2)
    :param conf: пороговое значение для фильтрации (default=0.3)
    :param save_img: флаг для сохранения изображения с детекциями (default=False)
    :return: возвращает список карт только тех, что пересекаются с bbox.
    '''

    results = cards_model(image_path, conf=conf, imgsz=768)[0]

    if save_img:
        image_path = image_path.replace('.png', '_cards.png')
        cv2.imwrite(image_path, results.plot())

    x1, y1, x2, y2 = bbox
    detections = []

    def intersects(boxA, boxB):
        # Проверка пересечения двух прямоугольников
        ax1, ay1, ax2, ay2 = boxA
        bx1, by1, bx2, by2 = boxB
        return not (ax2 < bx1 or ax1 > bx2 or ay2 < by1 or ay1 > by2)

    for box in results.boxes.data.tolist():
        xx1, yy1, xx2, yy2, _, cls = box
        if intersects((x1, y1, x2, y2), (xx1, yy1, xx2, yy2)):
            name = cards_model.names[int(cls)]
            detections.append(name)

    return detections


if __name__ == "__main__":
    path = "test.png"

    # только детекции
    # detections_result_1 = detect_image(path)
    # logger.info("Детекции:", detections_result_1)


    # детекция карт
    cards_result = detect_cards(image_path=path, bbox=(725, 859, 958, 1113), conf=0.3)
    logger.info("Карты: %s", cards_result)
