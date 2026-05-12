# DES - Discrete‑Event Simulation
# (дискретно‑событийное моделирование)

from sortedcontainers import SortedList  # v2.4.0

from typing import Callable, Any, Tuple



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
            time, _, callback, payload = self.events.pop(0)  # Runtime complexity: `O(log(n))` -- approximate.
            if time > until:
                break
            self.time = time
            callback(*payload)



if __name__ == "__main__":
    events = EventEngine()
    events.schedule(0.5, lambda des: print("event A:", des.time))
    events.schedule(0.8, lambda des: print("event B:", des.time))
    events.next    (0.5, lambda des: print("event C:", des.time))
    events.schedule(0.3, lambda des: print("event D:", des.time))

    events.run(0.5)  # Сработают события: 'D' -> 'A' -> 'C'
  # events.run(0.49) # Сработает только 'D'
