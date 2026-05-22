# DES - Discrete‑Event Simulation
# (дискретно‑событийное моделирование)

from sortedcontainers import SortedList  # v2.4.0

from typing import Callable, Any, Tuple, Dict
from collections import defaultdict

Callback = Callable[..., None]
Events = SortedList[Tuple[float, int, Callback, Tuple[Any, ...]]]



class EventEngine:
    def __init__(self) -> None:
        self.time: float = 0.0
        self.events: Events = SortedList()  # А вот и расписание
        self.counter: int = 0   # Для событий с одинаковым временем, чтобы tuple-компаратор не добрался до callback

    def schedule(self, time: float, callback: Callback, *payload: Any) -> None:
        self.counter += 1
        self.events.add((time, self.counter, callback, payload))  # Runtime complexity: `O(log(n))` -- approximate.

    def next(self, delta: float, callback: Callback, *payload: Any) -> None:
        self.schedule(self.time + delta, callback, *payload)

    def run(self, until: float) -> None:
        while self.events:
            time, _, callback, payload = e = self.events.pop(0)  # Runtime complexity: `O(log(n))` -- approximate.
            if time > until:
                self.events.add(e)  # возврат для переиспользования run
                self.time = until  # багофикс: сломанное расписание, если последнее событие меньше шага съёма логов
                break
            self.time = time
            callback(*payload)

    def run_next(self, delta: float):
        self.run(self.time + delta)

    def run_with_logging(self,
                         buildings: Tuple[Tuple[str, Any], ...],
                         property_names: Tuple[str, ...] = ("queue_length",)
                        ) -> Tuple[Callable[[float], None], Dict[str, list]]:
        def runner(delta: float):
            self.run_next(delta)
            log_it()

        code = ["def L():"]
        history = defaultdict(dict)
        extends = {}
        en = 0
        for attr in property_names:
            for i, (_, block) in enumerate(buildings):
                if hasattr(block, attr):
                    history[block][attr] = arr = []
                    code.append(f"  a{en}(b{i}.{attr})")
                    extends[f"a{en}"] = arr.append
                    en += 1
        G = {
            **{f"b{i}": block for i, (_, block) in enumerate(buildings)},
            **extends,
        }
        if len(code) == 1:
            code.append("  pass")
            print("[warning] Нечего логировать! Используйте обычный run/run_next")
        exec('\n'.join(code), G)
        log_it = G["L"]

        return runner, history



if __name__ == "__main__":
    events = EventEngine()
    events.schedule(0.5, lambda des: print("event A:", des.time), events)
    events.schedule(0.8, lambda des: print("event B:", des.time), events)
    events.next    (0.5, lambda des: print("event C:", des.time), events)
    events.schedule(0.3, lambda des: print("event D:", des.time), events)

    events.run(0.5)  # Сработают события: 'D' -> 'A' -> 'C'
  # events.run(0.49) # Сработает только 'D'
