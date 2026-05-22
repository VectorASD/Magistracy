from des import EventEngine
from rnd import exponential, uniform

from collections import defaultdict, deque, Counter
from typing import Any, Optional
import statistics



def ascii_histogram(data, bins=60, width=30):
    """
    Строит текстовую гистограмму в рамке.
    data  — список чисел
    bins  — количество столбцов
    width — максимальная высота столбца в символах
    """

    if not data:
        print("Нет данных для гистограммы.")
        return

    mn, mx = min(data), max(data)
    step = (mx - mn) / bins if bins > 0 else 1

    hist = [0] * bins  # Разбиваем на корзины
    for x in data:
        idx = int((x - mn) / step)
        if idx == bins:  # правый край
            idx -= 1
        hist[idx] += 1
    print("- hist:", hist)

    # Нормируем высоту
    max_h = max(hist)
    scale = width / max_h if max_h > 0 else 1
    scaled = [int(h * scale) for h in hist]

    # Целевой рендер
    print(f"┌{'─' * (bins)}┐")
    for level in range(width, 0, -1):
        heights = ''.join("•" if h >= level else " " for h in scaled)
        print(f"│{heights}│{level:>3}")
    print(f"└{'─' * bins}┘")
    min_s = f"{mn:.5f}"
    max_s = f"{mx:.5f}"
    pad = bins + 2 - len(min_s) - len(max_s)
    print(f"{min_s}{' ' * pad}{max_s}")



class Job:
    __slots__ = ("payload",)

    def __init__(self, *payload):
        payload = tuple(item.payload[0] if isinstance(item, Job) and len(item.payload) == 1 else item for item in payload)
        self.payload = payload

    def __repr__(self):
        body = ", ".join(map(str, self.payload))
        return f"<{body}>"


class Sensor:
    # Откуда берём людей/детали/сырьё
    __slots__ = ("engine", "lmbd", "outputs", "idx", "runs")
    groups = defaultdict(list)
    count = 0

    def __init__(self, engine: EventEngine, tau: float, group: Any=None) -> None:
        self.engine = engine
        self.lmbd = 1 / tau
        self.outputs = []
        self.idx = Sensor.count
        self.runs = 0
        Sensor.count += 1

        autostart = group is None
        if autostart:
            self.schedule_next()
        else:
            Sensor.groups[group].append(self)

    @staticmethod
    def start(group):
        for sensor in Sensor.groups[group]:
            sensor.schedule_next()
        del Sensor.groups[group]

    def schedule_next(self):
        dt = exponential(self.lmbd)
        self.engine.next(dt, self.emit)

    def emit(self):
        job = Job(self.idx)
        for input_f in self.outputs:
            input_f(job)
        self.schedule_next()
        self.runs += 1

    def stats(self):
        print(f"- index: {self.idx}   sensors: {Sensor.count}")
        print(f"- τ: {1 / self.lmbd:.5f}   λ: {self.lmbd:.5f}")
        print(f"- jobs emited: {self.runs}")


def _connect(input, output):
    """Просто подсоединяем вход к выходу"""
    if hasattr(output, "accept_from"):
        if hasattr(output, "accept"):
            raise ValueError("класс не может одновременно содержать и 'accept', и 'accept_from'")
        if not callable(output.accept_from):
            raise ValueError("'accept_from' ожидается, как функция")
        if not hasattr(output, "inputs"):
            raise ValueError("Класс с функцией 'accept_from' должен содержать в себе счётчик 'inputs'")

        f = output.accept_from
        idx = output.inputs
        output.inputs += 1
        input.outputs.append(lambda *payload: f(idx, *payload))
    elif not hasattr(output, "accept"):
        raise ValueError("в классе нет ни 'accept', ни 'accept_from'")
    else:
        if not callable(output.accept):
            raise ValueError("'accept' ожидается, как функция")

        input.outputs.append(output.accept)

def connect(*chain):
    """Вместо написания: connect(a, b); connect(b, c); ..., проще писать: connect(a, b, c, ...)"""
    pairs = len(chain) - 1
    assert pairs, "Должно быть минимум два блока в цепочке"
    for i in range(pairs):
        input = chain[i]
        output = chain[i+1]
        _connect(input, output)


class ServiceDevice:
    # Кружки с сигмами - обслуживающие приборы
    __slots__ = ("engine", "generator", "Es", "a_b_info", "queue", "busy", "outputs", "accepted", "finished")

    def __init__(self, engine: EventEngine, a: float, b: Optional[float] = None, *, uniform_mode: bool = True) -> None:
        self.engine = engine
      # self.a = a
      # self.b = b
        if uniform_mode:
            assert b is not None
            G = {"u": uniform}
            self.generator = eval(f"lambda: u({a}, {b})", G)
            self.Es = (a + b) / 2  # среднее обслуживание
            self.a_b_info  = f"- interval: {a} .. {b}"
        else:
            if b is None: b = a
            self.Es = (a + b) / 2  # среднее обслуживание
            G = {"e": exponential}
            self.generator = eval(f"lambda: e({1 / self.Es})", G)
            self.a_b_info  = f"- interval: exp(1 / {self.Es})"
        self.queue    = []
        self.busy     = False
        self.outputs  = []
        self.accepted = self.finished = 0

    def accept(self, job):
      # print("accepted:", job)
        self.accepted += 1
        self.queue.append(job)
        if not self.busy:
            self.start_service()

    def start_service(self):
        if not self.queue:
            self.busy = False
            return

        self.busy = True
        job = self.queue.pop(0)
        dt = self.generator()
        self.engine.next(dt, self.finish, job)

    def finish(self, job):
        self.finished += 1
        for input_f in self.outputs:
            input_f(job)
        self.start_service()

    def stats(self):
        print(self.a_b_info)
        print(f"- accepted: {self.accepted}   finished: {self.finished}")
        print(f"- busy? {('no', 'yes')[self.busy]}")
        print(f"- |queue|: {len(self.queue)}")

        Es = self.Es
        mu = 1 / Es
        lmbd = self.accepted / self.engine.time
        print(f"- 𝐸[𝑆]: {Es:.5f} s.   (среднее обслуживание)")
        print(f"- 𝜇:    {mu:.5f} /s.  (пропускная способность)")
        print(f"- 𝜆:    {lmbd:.5f}      (поток на входе)")
        print(f"- ρ = 𝜆/𝜇: {lmbd/mu:.5f}   (загруженность)")

        assert self.accepted == self.queue_length + self.finished, "invalid params"

    @property
    def queue_length(self):
        """Текущее число требований в системе (очередь + на обслуживании)."""
        return len(self.queue) + self.busy


class TupleCombiner:
    # Что-то, что требует "детали" нескольких типов
    __slots__ = ("buffers", "need_buffers", "inputs", "outputs", "accepted", "combined")

    def __init__(self, count: int) -> None:
        self.buffers = tuple(deque() for i in range(count))
        self.need_buffers = count
        self.inputs = 0
        self.outputs = []
        self.accepted = [0] * count
        self.combined = 0

    def accept_from(self, input_id, job):
      # print("accepted_from:", input_id, job)
        self.accepted[input_id] += 1
        buffer = self.buffers[input_id]
        if not buffer:
            self.need_buffers -= 1
        buffer.append(job)
      # print(tuple(map(len, self.buffers)), self.need_buffers)
        if not self.need_buffers:
            self.emit()

    def emit(self):
        combination = tuple(buffer.popleft() for buffer in self.buffers)
        self.need_buffers = len(self.buffers) - sum(map(bool, self.buffers))
      # print("new:", self.need_buffers)
        self.combined += 1
        job = Job(*combination)
        for input_f in self.outputs:
            input_f(job)

    def stats(self):
        print(f"- accepted: {self.accepted}   combined: {self.combined}")
        print(f"- |buffers|: {tuple(map(len, self.buffers))}")
        print(f"- void buffers: {self.need_buffers}")

        assert self.combined == min(self.accepted), "invalid params"


class Sink:
    """
    Все синонимы Sink по мнению словаря яндекса:
    -   washbasin (раковина, умывальник), washing (мойка);
    -   radiator (радиатор), heatsink (теплоотвод);
    -   absorber (поглодитель);
    -   receiver (приёмник);
    -   drain (сток).
    А раз то, что планируется как выходом из модели к анализатору,
        может оказаться чем угодно из этого, значит так и оставим!
    """
    __slots__ = ("engine", "times")

    def __init__(self, engine: EventEngine) -> None:
        self.engine = engine
        self.times = []

    def accept(self, job):
      # print("sink:", job, self.engine.time)
        self.times.append(self.engine.time)

    def stats(self):
        deltas_n = len(self.times) - 1
        deltas = tuple(self.times[i + 1] - self.times[i] for i in range(deltas_n))
        n = len(deltas)

        print(f"- received: {len(self.times)}   intervals: {n}")

        if n == 0:
            print("- not enough data")
            return

        # Базовые параметры
        mean = statistics.mean(deltas)
        median = statistics.median(deltas)
        variance = statistics.variance(deltas) if n > 1 else 0.0
        stdev = statistics.stdev(deltas) if n > 1 else 0.0
        min_v = min(deltas)
        max_v = max(deltas)

        # Мода (может не существовать)
        try:
            mode = statistics.mode(deltas)
        except statistics.StatisticsError:
            # Если мод несколько — берём самую частую вручную
            c = Counter(deltas)
            mode = c.most_common(1)[0][0]

        print(f"- mean:     {mean:.5f}")      # среднее время между выходами — оценка интенсивности потока
        print(f"- median:   {median:.5f}")    # медиана — устойчивая к выбросам центральная тенденция
        print(f"- mode:     {mode:.5f}")      # мода — наиболее частый интервал, форма распределения
        print(f"- variance: {variance:.5f}")  # дисперсия — разброс интервалов, степень неравномерности
        print(f"- stdev:    {stdev:.5f}")     # стандартное отклонение — корень из дисперсии, удобная мера разброса
        print(f"- min:      {min_v:.5f}")     # минимальный интервал — нижняя граница, редкие быстрые выходы
        print(f"- max:      {max_v:.5f}")     # максимальный интервал — верхняя граница, редкие задержки
        print(f"- cv:       {stdev/mean:.5f}")# коэффициент вариации — относительная вариабельность потока
        ascii_histogram(deltas)



class Builder:
    __slots__ = ("engine", "buildings", "names")

    def __init__(self) -> None:
        self.engine = EventEngine()
        self.buildings = []
        self.names = defaultdict(int)

    def _add(self, name, building):
        self.names[name] += 1
        name = f"{name}{self.names[name]}"
        self.buildings.append((name, building))
        return building

    def Sensor(self, tau: float, group: Any=None) -> Sensor:
        return self._add("s", Sensor(self.engine, tau, group))

    def ServiceDevice(self, a: float, b: float) -> ServiceDevice:
        return self._add("sd", ServiceDevice(self.engine, a, b))

    def TupleCombiner(self, count: int) -> TupleCombiner:
        return self._add("tc", TupleCombiner(count))

    def Sink(self) -> Sink:
        return self._add("si", Sink(self.engine))

    def stats(self) -> None:
        for name, building in self.buildings:
            print(f"~~~ {name} ~~~")
            building.stats()

    def run(self, until: int) -> None:
        self.engine.run(until)
        self.stats()



def test_scheme():
    engine = EventEngine()

    s1 = Sensor(engine, 1.0)
    s2 = Sensor(engine, 0.8)
    sd1 = ServiceDevice(engine, 0.5, 1.4)
    sd2 = ServiceDevice(engine, 0.7, 1.4)
    t1 = TupleCombiner(2)
    si1 = Sink(engine)

  # connect(s1, sd1); connect(sd1, t1)
  # connect(s2, sd2); connect(sd2, t1)
  # connect(t1, si1)
    connect(s1, sd1, t1)
    connect(s2, sd2, t1, si1)

    engine.run(100)

def test_scheme_v2():
    b = Builder()

    s1 = b.Sensor(1.0)
    s2 = b.Sensor(0.8)
    sd1 = b.ServiceDevice(0.5, 1.4)
    sd2 = b.ServiceDevice(0.7, 1.4)
    tc1 = b.TupleCombiner(2)
    si1 = b.Sink()

    connect(s1, sd1, tc1)
    connect(s2, sd2, tc1, si1)

    b.run(10000)

if __name__ == "__main__":
    test_scheme_v2()
