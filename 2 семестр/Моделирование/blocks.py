from des import EventEngine
from rnd import exponential, uniform

from collections import defaultdict, deque



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
    __slots__ = ("engine", "lmbd", "outputs", "idx")
    groups = defaultdict(list)
    count = 0

    def __init__(self, engine, tau, group=None):
        self.engine = engine
        self.lmbd = 1 / tau
        self.outputs = []
        self.idx = Sensor.count
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
    __slots__ = ("engine", "a", "b", "queue", "busy", "outputs")

    def __init__(self, engine, a, b):
        self.engine = engine
        self.a = a
        self.b = b
        self.queue = []
        self.busy = False
        self.outputs = []

    def accept(self, job):
      # print("accepted:", job)
        self.queue.append(job)
        if not self.busy:
            self.start_service()

    def start_service(self):
        if not self.queue:
            self.busy = False
            return

        self.busy = True
        job = self.queue.pop(0)
        dt = uniform(self.a, self.b)
        self.engine.next(dt, self.finish, job)

    def finish(self, job):
        for input_f in self.outputs:
            input_f(job)
        self.start_service()


class TupleCombiner:
    # Что-то, что требует "детали" нескольких типов
    __slots__ = ("buffers", "need_buffers", "inputs", "outputs")

    def __init__(self, count):
        self.buffers = tuple(deque() for i in range(count))
        self.need_buffers = count
        self.inputs = 0
        self.outputs = []

    def accept_from(self, input_id, job):
      # print("accepted_from:", input_id, job)
        buffer = self.buffers[input_id]
        if not buffer:
            self.need_buffers -= 1
        buffer.append(job)
        print(tuple(map(len, self.buffers)), self.need_buffers)
        if not self.need_buffers:
            self.emit()

    def emit(self):
        combination = tuple(buffer.popleft() for buffer in self.buffers)
        self.need_buffers = len(self.buffers) - sum(map(bool, self.buffers))
      # print("new:", self.need_buffers)
        job = Job(*combination)
        for input_f in self.outputs:
            input_f(job)


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
    __slots__ = ("engine", "count")

    def __init__(self, engine):
        self.engine = engine
        self.count = 0

    def accept(self, job):
        print("sink:", job, self.engine.time)
        self.count += 1



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

if __name__ == "__main__":
    test_scheme()
