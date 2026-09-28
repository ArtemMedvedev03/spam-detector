"""Окно приложения. Запуск: python main.py."""
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import sqlite3
from train import load_model, classify
from database import init_db, save_prediction, run_queries

EXAMPLES = {
    'Пример спама': 'Поздравляем! Вы выиграли миллион рублей! Для получения приза срочно переведите комиссию по ссылке. Предложение действует только сегодня!',
    'Обычное письмо': 'Здравствуйте! Напоминаю, что завтра в 10:00 состоится встреча по проекту. Пожалуйста, подготовьте отчёт и список вопросов. С уважением, коллега.',
}


class SpamApp:
    """Класс объединяет элементы окна и обработчики кнопок."""
    def __init__(self, root, model, metrics):
        self.root, self.model, self.metrics = root, model, metrics
        self.model_id = init_db(metrics)
        root.title('Определитель спама — русская версия 2.1')
        root.geometry('860x690')
        root.minsize(730, 610)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=('Segoe UI', 11), padding=8)
        style.configure('TLabel', font=('Segoe UI', 11))
        frame = ttk.Frame(root, padding=22)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Определитель спама', font=('Segoe UI', 23, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Анализ русскоязычных писем и сообщений',
                  foreground='#526071').pack(anchor='w', pady=(6, 18))
        ttk.Label(frame, text='Вставьте тему и текст письма:').pack(anchor='w')
        self.text = ScrolledText(frame, height=12, wrap='word', font=('Segoe UI', 12),
                                padx=12, pady=12, undo=True)
        self.text.pack(fill='both', expand=True, pady=8)
        self.setup_editing()
        examples = ttk.Frame(frame)
        examples.pack(fill='x')
        ttk.Button(examples, text='Вставить текст', command=self.paste_text).pack(side='left', padx=(0, 8))
        for name, body in EXAMPLES.items():
            ttk.Button(examples, text=name, command=lambda value=body: self.set_text(value)).pack(side='left', padx=(0, 8))
        ttk.Button(examples, text='Очистить', command=lambda: self.set_text('')).pack(side='right')
        ttk.Button(frame, text='Проверить письмо', command=self.check).pack(fill='x', pady=15)
        self.result = ttk.Label(frame, text='Введите письмо и нажмите «Проверить».',
                                font=('Segoe UI', 16, 'bold'))
        self.result.pack(anchor='w')
        self.score = ttk.Label(frame, text='')
        self.score.pack(anchor='w', pady=5)
        self.notice = ttk.Label(frame, text='', foreground='#975800', wraplength=760)
        self.notice.pack(anchor='w')
        ttk.Label(frame, text='Оценка модели не гарантирует правильность результата.\n'
                  'История с текстами писем сохраняется локально в spam_history_ru.db.',
                  foreground='#526071', wraplength=760).pack(anchor='w', pady=8)
        bottom = ttk.Frame(frame)
        bottom.pack(fill='x', pady=(8, 0))
        ttk.Button(bottom, text='История и статистика', command=self.history).pack(side='left')
        ttk.Button(bottom, text='Результаты тестирования', command=self.show_metrics).pack(side='right')
        self.text.focus_set()

    def setup_editing(self):
        """Вставка кнопкой, контекстное меню и горячие клавиши в любой раскладке Windows."""
        self.window_system = self.root.tk.call('tk', 'windowingsystem')
        self.text.bind('<<Paste>>', self.paste_text)
        self.text.bind('<Control-KeyPress>', self.edit_shortcut)
        self.text.bind('<Shift-Insert>', self.paste_text)
        self.edit_menu = tk.Menu(self.root, tearoff=False)
        self.edit_menu.add_command(label='Вставить', command=self.paste_text)
        self.edit_menu.add_command(label='Копировать', command=lambda: self.text.event_generate('<<Copy>>'))
        self.edit_menu.add_command(label='Вырезать', command=lambda: self.text.event_generate('<<Cut>>'))
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label='Выделить всё', command=self.select_all)
        self.text.bind('<Button-3>', self.show_edit_menu)
        self.text.edit_modified(False)
        self.text.bind('<<Modified>>', self.text_changed)

    def paste_text(self, event=None):
        """Читает текст прямо из буфера, независимо от раскладки клавиатуры."""
        try:
            content = self.root.clipboard_get()
        except tk.TclError:
            messagebox.showinfo('Вставка текста',
                                'В буфере обмена нет доступного текста. Сначала скопируйте письмо.')
            return 'break'
        if not content:
            return 'break'
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        self.text.edit_separator()
        if self.text.tag_ranges('sel'):
            self.text.delete('sel.first', 'sel.last')
        self.text.insert('insert', content)
        self.text.edit_separator()
        self.text.see('insert')
        self.text.focus_set()
        return 'break'  # Не даём стандартному обработчику вставить текст второй раз.

    def select_all(self):
        self.text.tag_add('sel', '1.0', 'end-1c')
        self.text.mark_set('insert', 'end-1c')
        self.text.focus_set()
        return 'break'

    def edit_shortcut(self, event):
        # В Windows keycode — код физической клавиши: V=86 и при русской раскладке.
        keys = {86: 'v', 67: 'c', 88: 'x', 65: 'a', 90: 'z', 89: 'y'}
        key = keys.get(event.keycode) if self.window_system == 'win32' else event.keysym.lower()
        if key == 'v':
            return self.paste_text()
        if key == 'a':
            return self.select_all()
        if key in ('c', 'x'):
            self.text.event_generate('<<Copy>>' if key == 'c' else '<<Cut>>')
            return 'break'
        if key in ('z', 'y'):
            try:
                if key == 'y' or (key == 'z' and event.state & 1):
                    self.text.edit_redo()
                else:
                    self.text.edit_undo()
            except tk.TclError:
                pass  # В истории редактирования пока нечего отменять.
            return 'break'
        return None  # Другие сочетания продолжают обрабатываться самим Tkinter.

    def show_edit_menu(self, event):
        self.text.focus_set()
        try:
            self.edit_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.edit_menu.grab_release()
        return 'break'

    def text_changed(self, event=None):
        if self.text.edit_modified():
            self.result.configure(text='Текст изменён. Нажмите «Проверить».', foreground='#182333')
            self.score.configure(text='')
            self.notice.configure(text='')
            self.text.edit_modified(False)

    def set_text(self, text):
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', text)
        self.result.configure(text='Нажмите «Проверить».', foreground='#182333')
        self.score.configure(text='')
        self.notice.configure(text='')

    def check(self):
        text = self.text.get('1.0', 'end').strip()
        try:
            label, score = classify(self.model, text)
        except ValueError as error:
            self.result.configure(text='Проверка не выполнена', foreground='#975800')
            self.score.configure(text='')
            self.notice.configure(text='')
            messagebox.showwarning('Проверьте ввод', str(error))
            return
        self.result.configure(text='СПАМ' if label else 'НЕ СПАМ',
                              foreground='#b32432' if label else '#167047')
        self.score.configure(text=f'Оценка класса «спам» моделью: {score:.1%}')
        self.notice.configure(text=('Пограничная оценка — проверьте письмо вручную.'
                                    if 0.35 <= score <= 0.65 else ''))
        try:
            save_prediction(text, label, score, self.model_id)
        except sqlite3.Error as error:
            messagebox.showwarning('История', f'Результат получен, но не сохранён: {error}')

    def show_metrics(self):
        m = self.metrics
        tn, fp = m['confusion_matrix'][0]
        fn, tp = m['confusion_matrix'][1]
        messagebox.showinfo('Тестирование модели',
            f"Набор: {m['dataset']}\nОбучение: {m['train_count']} писем\n"
            f"Тест: {m['test_count']} писем\n\n"
            f"Accuracy (доля верных ответов): {m['accuracy']:.2%}\n"
            f"Precision (точность для спама): {m['precision']:.2%}\n"
            f"Recall (полнота для спама): {m['recall']:.2%}\nF1: {m['f1']:.4f}\n\n"
            f"Обычные письма распознаны верно: {tn}\nЛожные тревоги: {fp}\n"
            f"Пропущенный спам: {fn}\nСпам распознан верно: {tp}\n\n"
            'Метрики рассчитаны на сообщениях из чата.\nДля электронной почты качество отдельно не установлено.')

    def history(self):
        try:
            results = run_queries()
        except sqlite3.Error as error:
            messagebox.showerror('База данных', str(error))
            return
        window = tk.Toplevel(self.root)
        window.title('История проверок и статистика')
        window.geometry('950x540')
        notebook = ttk.Notebook(window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        names = ['Последние проверки', 'Спам', 'По результатам', 'По дням', 'Модели']
        for name, (columns, rows) in zip(names, results):
            tab = ttk.Frame(notebook)
            notebook.add(tab, text=name)
            text = ScrolledText(tab, wrap='word', font=('Consolas', 10))
            text.pack(fill='both', expand=True)
            if not rows:
                text.insert('end', 'Пока нет проверок. Проверьте несколько писем.\n')
            for row in rows:
                for column, value in zip(columns, row):
                    text.insert('end', f'{column}: {value}\n')
                text.insert('end', '\n' + '─' * 55 + '\n\n')
            text.configure(state='disabled')


def main():
    print('Загрузка модели. При первом запуске выполняется обучение...', flush=True)
    model, metrics = load_model()
    root = tk.Tk()
    SpamApp(root, model, metrics)
    root.mainloop()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        input('\nОшибка запуска. Скопируйте сообщение выше. Нажмите Enter...')
        raise SystemExit(1)
