import pytesseract
import cv2
import numpy as np
import logging

# Настройка логгера для этого модуля
logger = logging.getLogger(__name__)

# Указываем путь к исполняемому файлу Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def ocr_text(image_path, bbox, lang="rus", config="--psm 6", preprocess=True) -> str:
    '''
    Функция для распознавания текста внутри заданного bbox
    :param image_path: путь к изображению
    :param bbox: [x1, y1, x2, y2]
    :param config: конфигурация для Tesseract, по дефолту config="--psm 6", режим распознавания текста
    :param preprocess: флаг для предварительной обработки изображения, по дефолту preprocess=True
    :return: строка текста
    '''
    img = cv2.imread(image_path)
    if img is None:
        logger.error("Не удалось загрузить изображение %s", image_path)
        return ""

    # Получаем размеры изображения
    img_height, img_width = img.shape[:2]
    x1, y1, x2, y2 = bbox

    # Проверяем корректность координат bbox
    if x1 >= x2 or y1 >= y2:
        logger.error("Некорректные координаты bbox %s", bbox)
        return ""

    # Ограничиваем координаты границами изображения с отступами
    margin = 10
    x1_safe = max(0, x1 - margin)      # Расширяем влево
    y1_safe = max(0, y1 - margin)      # Расширяем вверх
    x2_safe = min(img_width, x2 + margin)   # Расширяем вправо
    y2_safe = min(img_height, y2 + margin)

    # Проверяем, что после коррекции область не пустая
    if x1_safe >= x2_safe or y1_safe >= y2_safe:
        logger.error("Область ROI пуста после коррекции. Исходный bbox: %s, размер изображения: %sx%s", bbox, img_width, img_height)
        return ""

    # Извлекаем ROI
    roi = img[y1_safe:y2_safe, x1_safe:x2_safe]

    # Дополнительная проверка размера ROI
    if roi.size == 0 or roi.shape[0] == 0 or roi.shape[1] == 0:
        logger.error("Пустая область ROI. Размер: %s, bbox: %s", roi.shape, bbox)
        return ""

    if preprocess:
        # Увеличиваем изображение для лучшего OCR
        scale = 2
        try:
            roi = cv2.resize(roi, (roi.shape[1]*scale, roi.shape[0]*scale), interpolation=cv2.INTER_CUBIC)
        except Exception as e:
            logger.error("Ошибка изменения размера ROI: %s, размер ROI: %s", e, roi.shape)
            return ""

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # Повышаем контраст с помощью CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        # Удаляем шум медианным блюром
        gray = cv2.medianBlur(gray, 3)
        # Бинаризация
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # cv2.imwrite(f'debug_roi_{x1}.png', roi)
        # cv2.imwrite(f'debug_bw_{x1}.png', bw)

        text = pytesseract.image_to_string(bw, lang=lang, config=config)

    else:
        text = pytesseract.image_to_string(roi, lang=lang, config=config)

    return text.strip()
