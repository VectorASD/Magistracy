from random import choice

from qubit import Q_0, Q_45, Q_90, Q_135
from matrix import H

# variants = Q_0, Q_90, Q_45, Q_135
# print(*variants, sep="\n")
# |φ> |0>
# |φ> |1>
# |φ> 1/√2 (|0> +|1>)
# |φ> 1/√2 (|0> -|1>)

def simulation():
    while True:
        # 1.)
        A_H_basis   = choice(range(2))
        state       = choice((Q_45, Q_135) if A_H_basis else (Q_0, Q_90))
        A_measuring = (H * state if A_H_basis else state).measure(1)[0]
        print("A:", "❌✅"[A_measuring])
        print("A->B (state):", state) # квантовый канал связи

        # 2.)
        B_H_basis   = choice(range(2))
        B_measuring = (H * state if B_H_basis else state).measure(1)[0]
        print("B:", "❌✅"[B_measuring])

        # 3.)
        print("B->A (H_basis):", B_H_basis) # классический канал связи

        # 4.)
        if B_H_basis == A_H_basis:
            print("A->B: ОК")
            break
        print("A->B: ПОВТОР")

    successful = A_measuring == B_measuring
    print("Сошлись ли показатели?", "❌✅"[successful])
    return successful

# Почему нельзя 'A' просто передать 'B' то, какой измеритель использован?
# От человека по середине (Еви) эта информация не скрыта...

count = 16
successfuls = 0
for i in range(1, count+1):
    print(f"~~~ Симуляция №{i} ~~~")
    successfuls += simulation()
    print("~" * 77)

print("Удачных       симуляций:", successfuls)
print("Провалившихся симуляций:", count - successfuls)
