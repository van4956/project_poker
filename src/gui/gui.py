# Настройка DPI awareness ДО импорта tkinter
import ctypes
import os
import sys
import time
import logging

# Настройка логгера для этого модуля
logger = logging.getLogger(__name__)

# Настраиваем DPI awareness ДО импорта tkinter, для корректного отображения
try:
    # Правильная настройка DPI awareness
    from ctypes import windll, wintypes

    # Делаем приложение DPI aware
    windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    logger.info("DPI awareness установлен: PROCESS_PER_MONITOR_DPI_AWARE")

except Exception as e:
    try:
        # Fallback для старых версий Windows
        ctypes.windll.user32.SetProcessDPIAware()
        logger.info("DPI awareness установлен: SetProcessDPIAware (fallback)")
    except Exception as e2:
        logger.error("Не удалось установить DPI awareness: %s, %s", e, e2)

import tkinter as tk               # Основной модуль tkinter (базовые виджеты)
from tkinter import ttk            # Подмодуль ttk (современные themed виджеты)
import PIL.ImageGrab as ImageGrab  # Для создания скриншотов
import PIL
import threading                   # Для асинхронных операций
import queue                       # Для безопасной передачи данных между потоками
import glob                        # Для поиска файлов по маске

from src.cv.parser import parse_image
from src.pokerlogic.best_action import best_action

n_simulations = 10000


class PokerCalculatorGUI:
    '''Класс для создания и управления графическим интерфейсом приложения'''

    def __init__(self, root):
        '''
        Инициализация графического интерфейса
        :root: основное окно приложения
        '''
        self.root = root
        self.root.title("Poker Bot")
        self.root.geometry("1200x600")
        self.root.resizable(False, False)  # Запрет изменения размеров окна
        self.root.configure(bg='#2c3e50')  # Темно-синий фон окна

        # Диагностика системы при запуске
        self.log_system_info()

        # Получаем информацию о DPI (для отладки)
        self.get_dpi_info()

        # Переменные для хранения координат выделенной области
        self.selection_coords = None
        self.overlay_window = None
        self.start_x = None
        self.start_y = None
        self.rect_id = None

        # Асинхронные переменные
        self.analysis_thread = None
        self.is_analyzing = False
        self.continuous_analysis = False
        self.result_queue = queue.Queue()
        self.last_analysis_result = None

        # Установка иконки (если файл существует)
        try:
            self.root.iconbitmap('poker.ico')
        except:
            logger.warning("Иконка poker.ico не найдена")

        # Основной фрейм
        main_frame = tk.Frame(root, bg='#34495e')
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Настройка растягивания строк и столбцов (ОБЯЗАТЕЛЬНО для sticky!)
        root.grid_rowconfigure(0, weight=1)          # Строка 0 окна растягивается
        root.grid_columnconfigure(0, weight=1)       # Столбец 0 окна растягивается
        main_frame.grid_rowconfigure(2, weight=1)    # Строка 2 фрейма растягивается (для результатов)
        main_frame.grid_columnconfigure(0, weight=1) # Столбец 0 фрейма растягивается
        main_frame.grid_columnconfigure(1, weight=1) # Столбец 1 фрейма растягивается
        main_frame.grid_columnconfigure(2, weight=1) # Столбец 2 фрейма растягивается

        # Фрейм для кнопок в верхней строке
        self.buttons_frame = tk.Frame(main_frame, bg='#34495e')
        self.buttons_frame.grid(row=0, column=0, columnspan=3, sticky="nw", padx=10, pady=10)

        # Кнопка "Область" (всегда видна)
        self.select_button = ttk.Button(self.buttons_frame,
                                       text="Область",
                                       command=self.start_area_selection,
                                       width=20)
        self.select_button.grid(row=0, column=0, padx=(0, 5))

        # Кнопки "Стоп", "Анализ" и "Авто анализ" (изначально скрыты)
        self.stop_button = ttk.Button(self.buttons_frame,
                                     text="Стоп",
                                     command=self.stop_analysis,
                                     width=15)

        self.analysis_button = ttk.Button(self.buttons_frame,
                                         text="Анализ",
                                         command=self.start_analysis,
                                         width=15)

        self.continuous_button = ttk.Button(self.buttons_frame,
                                           text="Авто анализ",
                                           command=self.toggle_continuous_analysis,
                                           width=15)

        # Статус фрейм - это область в верхней части окна ПОД кнопками
        self.status_frame = tk.Frame(main_frame, bg='#34495e')
        self.status_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=5)

        # Статус строка - это строка в верхней части окна ПОД кнопками (тоже самое что и в status_frame)
        self.status_label = tk.Label(self.status_frame,
                                   text="Готов к работе",
                                   bg='#34495e',
                                   fg='#ecf0f1',
                                   font=('Arial', 9))
        self.status_label.grid(row=0, column=0, sticky="w")

        # Область для результатов анализа, это область в средней части окна со скроллом
        self.results_frame = tk.Frame(main_frame, bg='#34495e')
        self.results_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=10, pady=5)

        # Текст для результатов анализа, это область в средней части окна со скроллом
        self.results_text = tk.Text(self.results_frame,
                                  height=6,
                                  bg='#2c3e50',
                                  fg='#ecf0f1',
                                  font=('Arial', 9),
                                  state='disabled')
        self.results_text.grid(row=0, column=0, sticky="nsew")

        # Scrollbar для результатов анализа, это область в средней части окна со скроллом
        scrollbar = ttk.Scrollbar(self.results_frame, orient="vertical", command=self.results_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.results_text.configure(yscrollcommand=scrollbar.set)

        self.results_frame.grid_rowconfigure(0, weight=1)
        self.results_frame.grid_columnconfigure(0, weight=1)

        # Кнопка завершения
        exit_button = ttk.Button(main_frame,
                                 text="Завершить",
                                 command=self.exit_app,
                                 width=20)
        exit_button.grid(row=3,  # размещаем в последней строке
                         column=0,
                         columnspan=3,
                         sticky="se", # se = south-east (нижний правый)
                         padx=10,
                         pady=10)

        # Запуск проверки очереди результатов
        self.check_result_queue()

    def show_additional_buttons(self):
        '''Показывает кнопки "Стоп", "Анализ" и "Авто анализ" справа от "Область"'''
        self.stop_button.grid(row=0, column=1, padx=(5, 5))
        self.analysis_button.grid(row=0, column=2, padx=(5, 5))
        self.continuous_button.grid(row=0, column=3, padx=(5, 0))

    def hide_additional_buttons(self):
        '''Скрывает кнопки "Стоп", "Анализ" и "Авто анализ"'''
        self.stop_button.grid_remove()
        self.analysis_button.grid_remove()
        self.continuous_button.grid_remove()

    def start_area_selection(self):
        '''Начинает процесс выделения области экрана. Скрываем основное окно'''
        self.root.withdraw()

        # Создаем временное окно для получения точных размеров экрана
        temp_window = tk.Toplevel()
        temp_window.withdraw()  # Сразу скрываем
        temp_window.update()  # Обновляем для получения корректных размеров

        # Получаем размеры всех мониторов
        screen_width = temp_window.winfo_screenwidth()
        screen_height = temp_window.winfo_screenheight()
        temp_window.destroy()  # Удаляем временное окно

        # Создаем полноэкранное overlay окно
        self.overlay_window = tk.Toplevel()

        # Устанавливаем размеры и позицию overlay окна
        self.overlay_window.geometry(f"{screen_width}x{screen_height}+0+0")
        self.overlay_window.attributes('-alpha', 0.3)  # Полупрозрачность
        self.overlay_window.configure(bg='black')  # Черный фон
        self.overlay_window.attributes('-topmost', True)  # Помещаем на верх
        self.overlay_window.overrideredirect(True)  # Убираем рамку окна

        # Принудительно делаем окно полноэкранным
        self.overlay_window.state('zoomed')  # Максимизируем окно
        self.overlay_window.update()  # Обновляем окно

        # Создаем canvas для рисования прямоугольника
        self.canvas = tk.Canvas(self.overlay_window,
                               highlightthickness=0,
                               bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Изменяем курсор на крестик
        self.overlay_window.configure(cursor='crosshair')

        # Привязываем события мыши
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)

        # Привязываем Escape для отмены
        self.overlay_window.bind('<Escape>', self.cancel_selection)
        self.overlay_window.focus_set()

    def on_mouse_down(self, event):
        '''Обработка нажатия мыши - начало выделения'''
        self.start_x = event.x_root
        self.start_y = event.y_root

    def on_mouse_drag(self, event):
        '''Обработка перетаскивания мыши - рисование прямоугольника'''
        if self.start_x is not None and self.start_y is not None:
            # Удаляем предыдущий прямоугольник
            if self.rect_id:
                self.canvas.delete(self.rect_id)

            # Используем глобальные координаты для всех расчетов
            # Преобразуем текущие координаты мыши в глобальные
            current_x_global = event.x_root
            current_y_global = event.y_root

            # Преобразуем глобальные координаты в локальные для canvas
            overlay_x = self.overlay_window.winfo_rootx()
            overlay_y = self.overlay_window.winfo_rooty()

            x1_canvas = self.start_x - overlay_x
            y1_canvas = self.start_y - overlay_y
            x2_canvas = current_x_global - overlay_x
            y2_canvas = current_y_global - overlay_y

            self.rect_id = self.canvas.create_rectangle(x1_canvas, y1_canvas, x2_canvas, y2_canvas,
                                                       outline='red',
                                                       width=2,
                                                       fill='')

    def on_mouse_up(self, event):
        '''Обработка отпускания мыши - завершение выделения'''
        if self.start_x is not None and self.start_y is not None:
            # Сохраняем координаты области (все в глобальных координатах)
            x1 = min(self.start_x, event.x_root)
            y1 = min(self.start_y, event.y_root)
            x2 = max(self.start_x, event.x_root)
            y2 = max(self.start_y, event.y_root)

            self.selection_coords = (x1, y1, x2, y2)

        # Закрываем overlay и показываем дополнительные кнопки
        self.close_overlay()
        self.show_additional_buttons()

    def stop_analysis(self):
        '''Остановка анализа и очистка координат'''
        self.continuous_analysis = False
        self.is_analyzing = False

        # Обновляем кнопку авто анализа
        self.continuous_button.config(text="Авто анализ")

        self.selection_coords = None
        self.hide_additional_buttons()
        # Обновляем статус через специальное сообщение
        self.result_queue.put(('status', "Анализ остановлен"))

    def start_analysis(self):
        '''Запуск анализа в отдельном потоке'''
        if not self.selection_coords:
            self.result_queue.put(('status', "Область не выбрана"))
            return

        if self.is_analyzing:
            self.result_queue.put(('status', "Анализ уже выполняется ..."))
            return

        # Обновляем интерфейс для непрерывного анализа
        if self.continuous_analysis:
            self.continuous_button.config(text="Стоп авто")

        self.is_analyzing = True

        # Запускаем анализ в отдельном потоке
        self.analysis_thread = threading.Thread(target=self.analysis_worker, daemon=True)
        self.analysis_thread.start()

    def analysis_worker(self):
        '''Анализ изображения покера'''
        # пока если нет координат, то ничего не делаем
        while self.is_analyzing and self.selection_coords:
            try:
                # Получаем координаты БЕЗ масштабирования - Tkinter уже учел DPI
                x1, y1, x2, y2 = self.selection_coords

                # Создаем скриншот БЕЗ дополнительного масштабирования
                screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))

                # Проверяем размер полученного изображения
                img_width, img_height = screenshot.size

                # Генерируем имя файла с временной меткой
                timestamp = int(time.time())
                filename = f"screenshot_{timestamp}.png"
                filepath = os.path.join(os.getcwd(), filename)

                # Сохраняем скриншот
                screenshot.save(filepath)

                # Очищаем старые скриншоты, оставляя только 10 последних
                self.cleanup_old_screenshots(max_screenshots=10)

                # Начало анализа изображения
                start_time = time.time()
                self.result_queue.put('--------------------------------------------------------')

                status_message = f"{filename}, {img_width}x{img_height}"
                self.result_queue.put(status_message)

                message = "Анализ: ⌛️"
                self.result_queue.put(message)

                # Парсинг изображения
                dict_image = parse_image(image_path=filepath, conf=0.4)

                if len(dict_image) > 0:
                    text_game = f"Игра: {dict_image['street']} - {dict_image['hero_pos']} - Pot {dict_image['pot']} - Stack {dict_image['hero_stack']}"
                    if dict_image['to_call'] > 0:
                        text_game += f" - To Call {dict_image['to_call']}"
                    self.result_queue.put(text_game)

                    text_card = "Карты:  "
                    text_card += ' '.join(dict_image['hero_cards'])
                    if len(dict_image['board_cards']) > 0:
                        text_card += "     "
                        text_card += ' '.join(dict_image['board_cards'])
                    self.result_queue.put(text_card)

                    # Расчет оптимального действия
                    to_call = dict_image['to_call'] if dict_image['to_call'] else 0
                    dict_action = best_action(size=dict_image['size'],
                                                                active=dict_image['active'],
                                                                hero_pos=dict_image['hero_pos'],
                                                                hero_cards=dict_image['hero_cards'],
                                                                range_hands=[],
                                                                board_cards=dict_image['board_cards'],
                                                                pot=dict_image['pot'],
                                                                bb=1,
                                                                hero_stack=dict_image['hero_stack'],
                                                                to_call=to_call,
                                                                n_simulations=n_simulations)
                    text_actions = "Действия: "
                    for action, value in dict_action.items():
                        action_name, action_amount = action.split('_')
                        action_ = action_name.capitalize() + '(' + str(action_amount) + ')'
                        text_actions += f"{action_} {value} "

                    # Отправляем действия как специальное сообщение для статуса
                    self.result_queue.put(('status', text_actions))
                    # И также в общий поток результатов
                    self.result_queue.put(text_actions)

                else:
                    error_msg = "Ошибка: это не покерная сессия"
                    self.result_queue.put(('status', error_msg))
                    self.result_queue.put(error_msg)

                end_time = time.time()
                self.result_queue.put(f"Время: {end_time - start_time:.3f} секунд")

                # Если не непрерывный режим - останавливаемся
                if not self.continuous_analysis:
                    self.is_analyzing = False
                    break

                # Пауза между анализами в непрерывном режиме (2 секунды)
                time.sleep(2.0)

            except Exception as e:
                error_msg = f"Ошибка: {str(e)}"
                self.result_queue.put(('status', error_msg))
                self.result_queue.put(error_msg)
                logger.error("Ошибка в analysis_worker: %s", e)
                self.is_analyzing = False
                break

        self.is_analyzing = False

    def cancel_selection(self, event=None):
        '''Отмена выделения области'''
        self.close_overlay()

    def close_overlay(self):
        '''Закрытие overlay окна и возврат к основному'''
        if self.overlay_window:
            self.overlay_window.destroy()
            self.overlay_window = None

        # Сбрасываем переменные
        self.start_x = None
        self.start_y = None
        self.rect_id = None

        # Возвращаем основное окно
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def exit_app(self):
        '''
        Закрывает приложение. Остановить анализ. Очистить скриншоты.
        :return: None
        '''
        # Останавливаем анализ
        self.continuous_analysis = False
        self.is_analyzing = False

        # Закрываем overlay окно если открыто
        if self.overlay_window:
            self.overlay_window.destroy()

        # Очищаем все скриншоты при выходе
        self.cleanup_old_screenshots(max_screenshots=0)

        self.root.quit()
        self.root.destroy()

    def toggle_continuous_analysis(self):
        '''Переключает режим непрерывного анализа'''
        if not self.selection_coords:
            self.result_queue.put(('status', "Сначала выберите область"))
            return

        self.continuous_analysis = not self.continuous_analysis

        if self.continuous_analysis:
            self.continuous_button.config(text="Стоп авто")
            self.start_analysis()
        else:
            self.continuous_button.config(text="Авто анализ")
            self.stop_analysis()

    def check_result_queue(self):
        '''Проверяет очередь результатов и обновляет интерфейс'''
        try:
            while not self.result_queue.empty():
                result = self.result_queue.get_nowait()

                # Проверяем, является ли результат специальным сообщением для статуса
                if isinstance(result, tuple) and result[0] == 'status':
                    # Обновляем только статус (без времени)
                    self.status_label.config(text=result[1])
                else:
                    # Обычное сообщение - добавляем в результаты с временем
                    self.results_text.config(state='normal')
                    self.results_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {result}\n")
                    self.results_text.see(tk.END)
                    self.results_text.config(state='disabled')

        except queue.Empty:
            pass

        # Планируем следующую проверку
        self.root.after(100, self.check_result_queue)

    def cleanup_old_screenshots(self, max_screenshots=10):
        '''Удаляет старые скриншоты, оставляя только указанное количество последних'''
        try:
            # Ищем все файлы скриншотов по паттерну
            screenshot_pattern = "*.png"
            screenshot_files = glob.glob(screenshot_pattern)

            # Если max_screenshots = 0, удаляем все файлы
            if max_screenshots == 0:
                files_to_delete = screenshot_files
            else:
                # Если файлов меньше чем лимит - ничего не делаем
                if len(screenshot_files) <= max_screenshots:
                    return

                # Сортируем файлы по времени создания (самые новые в конце)
                screenshot_files.sort(key=lambda x: os.path.getctime(x))

                # Удаляем самые старые файлы, оставляя только max_screenshots
                files_to_delete = screenshot_files[:-max_screenshots]

            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    logger.info("Удален старый скриншот: %s", file_path)
                except OSError as e:
                    logger.error("Ошибка удаления файла %s: %s", file_path, e)

        except Exception as e:
            logger.error("Ошибка очистки скриншотов: %s", e)

    def log_system_info(self):
        '''Выводит информацию о системе'''
        logger.info("Операционная система: %s", os.name)
        logger.info("Имя пользователя: %s", os.getlogin())
        logger.info("Текущая рабочая директория: %s", os.getcwd())
        logger.info("Версия Python: %s", sys.version)
        logger.info("Версия PIL: %s", PIL.__version__)

    def get_dpi_scale(self):
        '''Получает коэффициент DPI масштабирования Windows'''
        try:
            # Делаем процесс DPI-aware
            ctypes.windll.shcore.SetProcessDpiAwareness(1)

            # Получаем DPI
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
            ctypes.windll.user32.ReleaseDC(0, hdc)

            # Стандартный DPI = 96, вычисляем коэффициент
            scale_factor = dpi / 96.0
            logger.info("DPI: %s, Коэффициент масштабирования: %s", dpi, scale_factor)
            return scale_factor

        except Exception as e:
            logger.error("Ошибка получения DPI: %s", e)
            return 1.0  # По умолчанию без масштабирования

    def get_dpi_info(self):
        '''Получает информацию о DPI для отладки'''
        try:
            # Получаем DPI
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
            ctypes.windll.user32.ReleaseDC(0, hdc)

            # Стандартный DPI = 96, вычисляем коэффициент
            scale_factor = dpi / 96.0
            logger.info("DPI информация: %s, Коэффициент: %s", dpi, scale_factor)

        except Exception as e:
            logger.error("Ошибка получения DPI: %s", e)
