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
from random import choice, sample



class FileState:
    __slots__ = ("written",)

    def __init__(self):
        self.written = 0

class Process:
    """Базовый класс процесса."""

    __slots__ = ("pid", "priority")

    def __init__(self, pid, priority):
        self.pid      = pid      # идентификатор
        self.priority = priority # приоритет (целое число > 0)

    def action(self, file_state: FileState):
        """Действие процесса. Возвращает True, если действие выполнено."""
        raise NotImplementedError

    def __repr__(self):
        return f"<proc: {self.pid}:{self.priority}>"

class Writer(Process):
    """Процесс записи: увеличивает счётчик символов в файле."""

    __slots__ = ()

    def action(self, file_state: FileState):
        file_state.written += 1
        return True

class Reader(Process):
    """Процесс чтения: читает один символ, если есть что читать."""

    __slots__ = ("read_count",)

    def __init__(self, pid, priority):
        super().__init__(pid, priority)
        self.read_count = 0  # сколько символов прочитано этим процессом

    def action(self, file_state: FileState):
        if file_state.written > self.read_count:
            self.read_count += 1
            return True
        return False  # нечего читать – теряет квант времени



class Weights:
    __slots__ = ("total_w", "pool", "counts")

    def __init__(self, weights):
        for w in weights:
            assert isinstance(w, int) and w > 0

        self.total_w = sum(weights)
        self.pool = []
        for idx, p in enumerate(weights):
            self.pool += [idx] * p
        self.counts = list(weights)

    def choose_one(self) -> int:
        return choice(self.pool)
    
    def choose_k_without_replacement(self, k: int) -> list[int]:
        # выбираем k уникальных индексов
        if k <= 0:
            return []
      # return sample(self.pool, k=k)  # оказывается есть ещё аргумент counts, что, в точности, соответствует weights
        n = len(self.counts)
        return sample(range(n), k=min(k, n), counts=self.counts)

    def __repr__(self):
        return f"<W: {self.pool}>"



def simulate(writer_priority, reader_priorities,
             steps=10000, num_cores=1, seed=None):
    if seed is not None:
        random.seed(seed)

    num_readers = len(reader_priorities)
    processes = (
        *(
            Reader(pid=f'R{i}', priority=reader_priorities[i])
            for i in range(num_readers)
        ),
        Writer(pid='W', priority=writer_priority),
    )
    print("processes:", processes)

    writer_index = tuple(idx for idx, proc in enumerate(processes) if isinstance(proc, Writer))
    assert len(writer_index) == 1
    writer_index = writer_index[0]
    writer       = processes[writer_index]

    all_weights    = Weights([p.priority for p in processes])
    reader_weights = Weights([p.priority for p in processes if isinstance(p, Reader)])
    print("weights:", all_weights)
    file_state = FileState()

    k = min(num_cores, num_readers)
    for _ in range(steps):
        if all_weights.choose_one() == writer_index:
            writer.action(file_state)
        else:
            chosen = reader_weights.choose_k_without_replacement(k)
            for idx in chosen:
                processes[idx].action(file_state)

    return [p.read_count for p in processes if isinstance(p, Reader)]



def main():
    READER_PRIORITIES = (1, 3, 2) # приоритеты читателей
    STEPS = 10000                 # сколько квантов симулируется
    RUNS_PER_POINT = 5            # количество повторов для усреднения
    CORES_W = 3
    CORES_H = 2
    WRITER_PRIORITY_SCALE = 2

    writer_priorities = tuple(range(1, 16))  # от 1 до 15
    writer_priorities = tuple(p * WRITER_PRIORITY_SCALE for p in writer_priorities)  # от 2 до 30 без нечётных при скаляре в 2

    num_readers = len(READER_PRIORITIES)
    CORES = range(1, 1+CORES_W*CORES_H)
  # CORES = (4,)

    plt.figure(figsize=(6*CORES_W, 4*CORES_H))
  # plt.title('Зависимость числа считанных символов от приоритета писателя и числа ядер', fontsize=14)
    for cores in CORES:
        avg_reads = {i: [] for i in range(num_readers)}
        for wp in writer_priorities:
            print()
            # Несколько запусков для сглаживания
            all_runs = [
                simulate(wp, READER_PRIORITIES, steps=STEPS, num_cores=cores)
                for _ in range(RUNS_PER_POINT)
            ]
            # Усредняем по каждому читателю
            for i in range(num_readers):
                avg = sum(run[i] for run in all_runs) / RUNS_PER_POINT
                avg_reads[i].append(avg)
            print(f"Приоритет писателя {wp:2d}: средние чтения {[f'{avg_reads[i][-1]:.1f}' for i in range(num_readers)]}")

        plt.subplot(CORES_H, CORES_W, cores)
        for r in range(num_readers):
            plt.plot(writer_priorities, avg_reads[r], 'o-', label=f'Читатель {r}')
        a, b = cores // 10 % 10, cores % 10
        ender = "ро" if a != 1 and b == 1 else "ра" if b > 0 and b < 5 else "ер"
        plt.title(f'{cores} яд{ender}')
        plt.xlabel('Приоритет писателя')
        plt.ylabel('Прочитано символов')
        plt.legend()
        plt.grid(True)

    plt.tight_layout()
    plt.savefig('lab3_plot_v3_p132.png', dpi=200)
    plt.show()



if __name__ == "__main__":
    main()
