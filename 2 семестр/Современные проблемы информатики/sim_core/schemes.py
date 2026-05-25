from blocks import Builder



# Справка: приборы обслуживания работают в режиме E[S] = 1/μ, а не μ,
# из-за того, что изначально, они работали в режиме uniform, а не exponential.
# Тоже самое касается и датчиков: работают в режиме τ, т.к. просто так было в заданиях по моделированию.

def build_single_server(lmbd = 1.0, mu=0.9) -> Builder:
    """Одноканальная СМО: λ=1.0, μ=0.9 (экспоненциальное обслуживание)."""
    b = Builder()
    s1  = b.Sensor(1/lmbd)                             # τ = 1/λ = 1.0
    sd1 = b.ServiceDevice(a=1/mu, uniform_mode=False)  # μ = 0.9, E[S] = 1/0.9
    si1 = b.Sink()

    b.connect(s1, sd1, si1)

    return b

def build_three_servers(lmbd=1.0, mu_per_server=0.3) -> Builder:
    """Трёхканальная СМО: λ=1.0, μ=0.3 (экспоненциальное обслуживание)."""
    b = Builder()
    src = b.Sensor(1/lmbd)
    ro1 = b.RandomOutput()
    Es = 1 / mu_per_server
    sd1 = b.ServiceDevice(Es, uniform_mode=False)
    sd2 = b.ServiceDevice(Es, uniform_mode=False)
    sd3 = b.ServiceDevice(Es, uniform_mode=False)
    si1 = b.Sink()

    b.connect(src, ro1)
    b.connect(ro1, sd1, si1)
    b.connect(ro1, sd2, si1)
    b.connect(ro1, sd3, si1)

    return b



def main():
    b = build_single_server()
  # print(b.buildings, b["sd1"], b.sd1)
    runner, history = b.run_with_logging()
    for i in range(10):
        print(history[b.sd1]["queue_length"])
        runner(10)
  # b.stats()

    b = build_three_servers()
    runner, history = b.run_with_logging()
    for i in range(10):
        print(history[b.sd1]["queue_length"], history[b.sd2]["queue_length"], history[b.sd3]["queue_length"])
        runner(10)
    b.stats()

if __name__ == "__main__":
    main()
