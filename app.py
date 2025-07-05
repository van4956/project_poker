import tkinter as tk          # Основной модуль tkinter (базовые виджеты)
from tkinter import ttk       # Подмодуль ttk (современные themed виджеты)
import sys
import os
import logging
from datetime import datetime

# Добавляем текущую директорию в sys.path для корректной работы импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
def setup_logging():
    """Настройка системы логирования"""
    # Создаем папку для логов если её нет
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Имя файла лога с текущей датой
    log_filename = os.path.join(log_dir, f"poker_calculator_{datetime.now().strftime('%Y%m%d')}.log")

    # Настройка форматирования
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Настройка корневого логгера
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Очищаем существующие обработчики
    logger.handlers.clear()

    # Обработчик для записи в файл
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# Инициализируем логгер
logger = setup_logging()

from src.gui.gui import PokerCalculatorGUI


def main():
    '''
    Главная функция для запуска приложения
    :return: None
    '''
    logger.info("Запуск приложения Poker Calculator")

    try:
        root = tk.Tk()
        PokerCalculatorGUI(root)
        logger.info("GUI успешно инициализирован")
        root.mainloop()
    except Exception as e:
        logger.error("Критическая ошибка при запуске приложения: %s", e)
        raise
    finally:
        logger.info("Завершение работы приложения")


if __name__ == "__main__":
    main()
