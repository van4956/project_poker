import tkinter as tk          # Основной модуль tkinter (базовые виджеты)
from tkinter import ttk       # Подмодуль ttk (современные themed виджеты)
import sys
import os

# Добавляем текущую директорию в sys.path для корректной работы импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.gui.gui import PokerCalculatorGUI


def main():
    '''
    Главная функция для запуска приложения
    :return: None
    '''
    root = tk.Tk()
    PokerCalculatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
