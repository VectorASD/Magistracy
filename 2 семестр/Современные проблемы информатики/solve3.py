"""
Эта лабораторная работа — своего рода «симулятор планировщика» в миниатюре. Её главная цель
— не научиться писать код ради кода, а понять, как операционная система управляет
параллельными задачами, которые борются за общий ресурс, и как приоритеты и случайность
влияют на производительность и справедливость.

Зачем это моделировать?

В реальной системе (Windows, Linux) ядро постоянно решает, кому дать процессор, кого пустить к
файлу, а кого заставить подождать. Вы же не видите этих «пружин», а просто пользуетесь
приложениями. Модель, которую вы строите, позволяет:
-   Увидеть скрытую борьбу за ресурс: несколько читателей могут читать файл одновременно, но
    писатель требует эксклюзивного доступа. Вам нужно корректно разруливать конфликты — это
    классическая задача «читатели-писатели», один из краеугольных камней параллельного
    программирования.
-   Прочувствовать влияние приоритетов: чем выше приоритет писателя, тем чаще он будет
    вытеснять читателей. В результате одни процессы могут прочитать много символов, а другие
    почти ничего — возникает «голодание». Графики зависимости числа считанных символов от
    приоритета записи наглядно покажут, насколько несправедливой может быть система, если
    приоритеты расставлены неудачно.
-   Осознать вероятностный характер переключений: передача управления случайна
    (пропорциональна приоритетам). Это отражает реальность: события в ОС приходят в
    непредсказуемые моменты. Модель показывает, как стохастичность влияет на среднюю
    пропускную способность.

Методическая и практическая ценность

    На методическом уровне вы знакомитесь с фундаментальными понятиями: процессы, потоки,
разделяемые ресурсы, критические секции (неявно), типы многозадачности, приоритетное
планирование.
    На практике — разрабатываете упрощённый аналог планировщика ввода-вывода или менеджера
блокировок. Это помогает понять, почему в реальных ОС вводят сложные механизмы
синхронизации (мьютексы, семафоры) и как выбор стратегии влияет на производительность и
отзывчивость системы.
"""



import matplotlib.pyplot as plt  # pip install matplotlib

import random
from random import randint



class Process:
    """Базовый класс процесса."""
    def __init__(self, pid, priority):
        self.pid      = pid      # идентификатор
        self.priority = priority # приоритет (целое число > 0)

    def action(self, file_state):
        """Действие процесса. Возвращает True, если действие выполнено."""
        raise NotImplementedError

class Writer(Process):
    """Процесс записи: увеличивает счётчик символов в файле."""
    def action(self, file_state):
        file_state['written'] += 1
        return True

class Reader(Process):
    """Процесс чтения: читает один символ, если есть что читать."""
    def __init__(self, pid, priority):
        super().__init__(pid, priority)
        self.read_count = 0   # сколько символов прочитано этим процессом

    def action(self, file_state):
        if file_state['written'] > 0:
            self.read_count += 1
            return True
        return False  # нечего читать – теряет квант времени



def simulate(num_readers, writer_priority, reader_priority=1,
             steps=10000, seed=None):
    """
    Запустить симуляцию на заданное число шагов.
    Возвращает список прочитанных символов каждым читателем.
    """
    if seed is not None:
        random.seed(seed)

    processes = []
    for i in range(num_readers):
        processes.append(Reader(pid=f'R{i}', priority=reader_priority))
    writer = Writer(pid='W', priority=writer_priority)
    processes.append(writer)

    total_priority = sum(p.priority for p in processes)
    file_state = {'written': 0}

    for _ in range(steps):
        # Случайный выбор процесса с учётом приоритетов
        r = randint(1, total_priority)
        acc = 0
        chosen = None
        for p in processes:
            acc += p.priority
            if r <= acc:
                chosen = p
                break
        # Выполняем действие
        chosen.action(file_state)

    # Собираем статистику чтения
    read_counts = [p.read_count for p in processes if isinstance(p, Reader)]
    return read_counts



def main():
    NUM_READERS = 3          # число процессов чтения
    READER_PRIORITY = 1      # одинаковый приоритет читателей
    STEPS = 10000            # сколько квантов симулируется
    RUNS_PER_POINT = 5       # количество повторов для усреднения

    writer_priorities = list(range(1, 16))  # от 1 до 15
    avg_reads = {i: [] for i in range(NUM_READERS)}

    for wp in writer_priorities:
        # Несколько запусков для сглаживания
        all_runs = []
        for _ in range(RUNS_PER_POINT):
            counts = simulate(NUM_READERS, wp, READER_PRIORITY, STEPS)
            all_runs.append(counts)
        # Усредняем по каждому читателю
        for i in range(NUM_READERS):
            avg = sum(run[i] for run in all_runs) / RUNS_PER_POINT
            avg_reads[i].append(avg)
        print(f"Приоритет писателя {wp:2d}: средние чтения {[f'{avg_reads[i][-1]:.1f}' for i in range(NUM_READERS)]}")

    plt.figure(figsize=(10, 6))
    for i in range(NUM_READERS):
        plt.plot(writer_priorities, avg_reads[i], 'o-', label=f'Читатель {i}')
    plt.xlabel('Приоритет процесса записи')
    plt.ylabel('Среднее число считанных символов')
    plt.title('Зависимость числа считанных символов от приоритета писателя')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('lab3_plot_v1.png', dpi=200)
    plt.show()



if __name__ == "__main__":
    main()
