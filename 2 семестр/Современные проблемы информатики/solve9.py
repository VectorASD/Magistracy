import matplotlib.pyplot as plt  # pip install matplotlib

from sim_core.schemes import build_single_server, build_three_servers



def run_and_collect(builder, total_time=500, dt=0.5):
    """
    Запускает моделирование, возвращает time_axis и список длин очереди.
    Для многоканальной — суммирует очереди всех ServiceDevice.
    """
    runner, history = builder.run_with_logging()
    # history имеет структуру: {device: {"queue_length": [...]}} для каждого блока с queue_length

    time_axis = []
    steps = int(total_time / dt)
    for _ in range(steps):
        runner(dt)
        time_axis.append(builder.engine.time)

    queue_lists = []
    for props in history.values(): # т.к. в нынешней реализации ТОЛЬКО терминалы обслуживания имеют параметр queue_length, то keys() нас не интересует
        if "queue_length" in props:
            queue_lists.append(props["queue_length"])
    builder.stats()

    return time_axis, queue_lists



def main():
    TOTAL_TIME = 10000
    DT = 1

    b1 = build_single_server()
    t1, q1s = run_and_collect(b1, TOTAL_TIME, DT)

    b3 = build_three_servers()
    t3, q3s = run_and_collect(b3, TOTAL_TIME, DT)

    plt.figure(figsize=(12, 6))

    plt.subplot(1, 2, 1)
    for q1 in q1s:
        plt.plot(t1, q1)
    plt.xlabel("Модельное время")
    plt.ylabel("Длина очереди")
    plt.title("Одноканальная СМО (μ=0.9)")
    plt.grid(True)

    plt.subplot(1, 2, 2)
    for i, q3 in enumerate(q3s):
        plt.plot(t3, q3, label=f"q{i}")
    total_queue = [sum(vals) for vals in zip(*q3s)]
    plt.plot(t3, total_queue, label=f"q_total")
    plt.legend()
    plt.xlabel("Модельное время")
    plt.ylabel("Длина очереди")
    plt.title("Трёхканальная СМО (μ=0.3×3)")
    plt.grid(True)

    plt.tight_layout()
    plt.savefig("sim_queues.png", dpi=200)
    plt.show()

if __name__ == "__main__":
    main()
