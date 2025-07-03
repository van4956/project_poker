import pytesseract
import cv2
import numpy as np

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
        return ""
    x1, y1, x2, y2 = bbox
    roi = img[y1+10:y2-10, x1-10:x2+10]

    if preprocess:
        # Увеличиваем изображение для лучшего OCR
        scale = 2
        roi = cv2.resize(roi, (roi.shape[1]*scale, roi.shape[0]*scale), interpolation=cv2.INTER_CUBIC)

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
