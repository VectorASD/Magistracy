from typing import List, Tuple
from math import log2
import inspect

from qubit import Qubit, Q_0, Q_45, Q_135
from logic import BooleanFunction
from number_decorator import decorate_num
from misc import float_eq, float_neq, to_subscript
from matrix import apply_H_gate



def tensor_qubits_MSB(*qubits: Qubit) -> Tuple[complex, ...]:
    """Тензорное произведение векторов кубитов: Qubit.vector() → 2^n-комплексный вектор. (MSB)"""
    vec = (1+0j,) # (complex(1, 0),)
    for q in qubits:
        a0, a1 = q.vector()
        vec = (*(v * a0 for v in vec), *(v * a1 for v in vec))
    return vec

def tensor_qubits_LSB(*qubits: Qubit) -> Tuple[complex, ...]:
    """Тензорное произведение с добавлением кубита как младшего бита (LSB)"""
    vec = (1+0j,)
    for q in qubits:
        a0, a1 = q.vector()
        vec = tuple(x for v in vec for x in (v * a0, v * a1))
    return vec

def reg2str(vec: Tuple[complex, ...], misc="") -> None:
    """Печатает все базисные состояния вектора состояния"""
    n_qubits = round(log2(len(vec)))
    if 2 ** n_qubits != len(vec):
        raise ValueError(f"Длина вектора состояния ({len(vec)}) не равна 2^n для целого числа кубитов")
    vs = []
    decorator = lambda x: "" if float_eq(x, 1) else "-" if float_eq(x, -1) else f"{decorate_num(x)} " 
    for div, mul in ((None, 1), ("½", 2), ("1/√2", 2**0.5), ("1/(2√2)", 2 * 2**0.5), ("¼", 4)):
        mul_vec = tuple(i * mul for i in vec)
        v = " + ".join(f"{decorator(amp)}|{format(i, f'0{n_qubits}b')}⟩"
                       for i, amp in enumerate(mul_vec) if float_neq(amp, 0))
        if div: v = f"{div} ({v})"
        vs.append(v.replace("+ -", "-").replace("+ |", "+|"))
    # for i in vs: print(len(i), i)
    return f"ψ{to_subscript(misc)}> = " + min(vs, key=len)

def check_registers():
    #   Q_0 = |φ> |0>
    #  Q_45 = |φ> 1/√2 (|0> +|1>)     Соответствует |0> * H, т.е. |+>
    # Q_135 = |φ> 1/√2 (|0> -|1>)     Соответствует |1> * H, т.е. |->

    # Для параллелизма: tensor_qubits(Q_45, Q_45, Q_0)   — два входа в суперпозиции, выход в ∣0⟩.
    # Для Дойча–Ёжи:    tensor_qubits(Q_45, Q_45, Q_135) — два входа в суперпозиции, выход в ∣-⟩. (как на схеме)

    register = tensor_qubits_MSB(Q_45, Q_45, Q_0) # |+> |+> |0>
    print(register) # (0.5, 0.5, 0.5, 0.5, 0, 0, 0, 0) |000> |100> |010> |110>
    print("MSB:", reg2str(register)) # MSB: ψ> = 0.5 |000⟩ + 0.5 |001⟩ + 0.5 |010⟩ + 0.5 |011⟩

    # но мы получили        MSB (Most  Significant Bit) — «старший значащий бит»
    # а надо, для удобства, LSB (Least Significant Bit) — «младший значащий бит»

    register = tensor_qubits_LSB(Q_45, Q_45, Q_0) # |+> |+> |0>
    print(register) # (0.5, 0, 0.5, 0, 0.5, 0, 0.5, 0) |000> |010> |100> |110>
    print("LSB:", reg2str(register)) # LSB: ψ> = 0.5 |000⟩ + 0.5 |010⟩ + 0.5 |100⟩ + 0.5 |110⟩

    register = tensor_qubits_LSB(Q_45, Q_45, Q_135) # |+> |+> |->
    print(register) # (0.354, -0.354, 0.354, -0.354, 0.354, -0.354, 0.354, -0.354)
    print(reg2str(register)) # ψ> = 1/√2 (0.5 |000⟩ -0.5 |001⟩ + 0.5 |010⟩ -0.5 |011⟩ + 0.5 |100⟩ -0.5 |101⟩ + 0.5 |110⟩ -0.5 |111⟩)

# check_registers(); exit()



def simulate_parallelism(func, Q_arr: Tuple[Qubit, ...]) -> Tuple[complex, ...]:
    print("\n=== Квантовый параллелизм ===\n")

    sig = inspect.signature(func)
    n   = len(sig.parameters)
    bf  = BooleanFunction(n, func, outputs=" f")
    print(bf)
    ft = BooleanFunction(n+1).shift(1).quantum_transform(bf)
    print(ft)
    C_mat = ft.to_C()
    print(C_mat)

    psi_in = tensor_qubits_LSB(*Q_arr) # |+> |+> |0>
    print(reg2str(psi_in, "in"))  # ψ> = ½ (|000⟩ + |010⟩ + |100⟩ + |110⟩)
    psi_out = C_mat @ psi_in
    print(reg2str(psi_out, "out")) # ψ> = ½ (|000⟩ + |010⟩ + |100⟩ + |111⟩)
    return psi_out



# simulate_parallelism(lambda x, y: x & y, (Q_45, Q_45, Q_0)) # |+> |+> |0>
"""
=== Квантовый параллелизм ===

+----------+
| x₂ x₁  f |
+----------+
|  0  0  0 |
|  0  1  0 |
|  1  0  0 |
|  1  1  1 |
+----------+
+-----------+
| x₂ x₁ y⊕f |
+-----------+
|  0  0   0 |
|  0  0   1 |
|  0  1   0 |
|  0  1   1 |
|  1  0   0 |
|  1  0   1 |
|  1  1   1 |
|  1  1   0 |
+-----------+
+-----------------+
| 1 0 0 0 0 0 0 0 |
| 0 1 0 0 0 0 0 0 |
| 0 0 1 0 0 0 0 0 |
| 0 0 0 1 0 0 0 0 |
| 0 0 0 0 1 0 0 0 |
| 0 0 0 0 0 1 0 0 |
| 0 0 0 0 0 0 0 1 |
| 0 0 0 0 0 0 1 0 |
+-----------------+
ψᵢₙ> = ½ (|000⟩ +|010⟩ +|100⟩ +|110⟩)
ψₒᵤₜ> = ½ (|000⟩ +|010⟩ +|100⟩ +|111⟩)
"""

# simulate_parallelism(lambda x, y, z: x ^ ~y ^ z, (Q_45, Q_45, Q_45, Q_135)) # |+> |+> |+> |->
"""
ψᵢₙ> = ¼ (|0000⟩ -|0001⟩ +|0010⟩ -|0011⟩ +|0100⟩ -|0101⟩ +|0110⟩ -|0111⟩ +|1000⟩ -|1001⟩ +|1010⟩ -|1011⟩ +|1100⟩ -|1101⟩ +|1110⟩ -|1111⟩)
ψₒᵤₜ> = ¼ (-|0000⟩ +|0001⟩ -|0010⟩ +|0011⟩ -|0100⟩ +|0101⟩ -|0110⟩ +|0111⟩ -|1000⟩ +|1001⟩ -|1010⟩ +|1011⟩ -|1100⟩ +|1101⟩ -|1110⟩ +|1111⟩)
"""



def psi_eq(L_psi, R_psi):
    """Сравнивает два квантовых регистра, учитывая EPS-погрешность"""
    return all(float_eq(L, R) for L, R in zip(L_psi, R_psi))

def deutsch_jozsa(func, Q_arr: Tuple[Qubit, ...]):
    """
    Алгоритм Дойча–Ёжи для произвольной булевой функции.
    Использует simulate_parallelism для симуляции оракула.
    Возвращает (psi, probs, verdict).
    """
    psi = simulate_parallelism(func, Q_arr)

    print("~~~ Алгоритм Дойча–Ёжи ~~~")

    # Количество кубитов в регистре
    n_qubits = round(log2(len(psi)))
    if 2 ** n_qubits != len(psi):
        raise ValueError(f"Длина вектора ψₒᵤₜ ({len(psi)}) не равна 2^n для целого числа кубитов")
    n_inputs = len(Q_arr) - 1 # последний кубит — анцилла

    # Применяем H перед распознавателем
    H_psi = apply_H_gate(psi, n_qubits) # Hadamard_psi
    R_psi = apply_H_gate(H_psi, n_qubits) # reverse_psi
    print(reg2str(H_psi, "kron"), f"(eigenstates (Hᵢₙ=Hₒᵤₜ)? {'❌✅'[psi_eq(psi, H_psi)]})")
    print(reg2str(R_psi, "kron2"), f"(инволюция (self-inverse)? {'❌✅'[psi_eq(psi, R_psi)]})")

    # Вероятности по x-регистру (суммируем по анцилле)
    probs = [0.0] * (2 ** n_inputs)
    for i, amp in enumerate(H_psi):
        x_bits = i >> 1 # отбрасываем анциллу при LSB
        probs[x_bits] += abs(amp) ** 2
    # LSB: анцилла справа, склеиваются индексы 0<->1, 2<->3, 4<->5, 6<->7
    # MSB: анцилла слева,  склеиваются индексы 0<->4, 1<->5, 2<->6, 3<->7

    # Вердикт
    if float_eq(probs[0], 1):
        verdict = "константная"
    elif all(float_eq(p, 1/(2**n_inputs)) for p in probs):
        verdict = "сбалансированная"
    else:
        verdict = "ни константная, ни сбалансированная"

    print("Вероятности:", ", ".join(map(decorate_num, probs)))
    print("Вердикт:", verdict)

    return H_psi, probs, verdict



deutsch_jozsa(lambda x, y: x & y, (Q_45, Q_45, Q_0)) # |+> |+> |0>
"""
ψᵢₙ> = ½ (|000⟩ +|010⟩ +|100⟩ +|110⟩)
ψₒᵤₜ> = ½ (|000⟩ +|010⟩ +|100⟩ +|111⟩)
~~~ Алгоритм Дойча–Ёжи ~~~
ψₖᵣₒₙ> = ¼ (3 |000⟩ +|001⟩ +|010⟩ -|011⟩ +|100⟩ -|101⟩ -|110⟩ +|111⟩) (eigenstates (Hᵢₙ=Hₒᵤₜ)? ❌)
ψₖᵣₒₙ₂> = ½ (|000⟩ +|010⟩ +|100⟩ +|111⟩) (инволюция (self-inverse)? ✅)
Вероятности: 5/8, 1/8, 1/8, 1/8
Вердикт: ни константная, ни сбалансированная
    НЕТ ФАЗОВОГО КИКА, ОШИБКА ВЕРДИКТА! Это желозеботонное доказательство,
    что анцилла должна быть ВСЕГДА в фазе |-> (туда пихать |0> нельзя!)
    Тем ни менее ψₖᵣₒₙ₂> сошёлся с ψₒᵤₜ>, т.е. H-gate сам по себе обратимый
"""

deutsch_jozsa(lambda x, y: x & y, (Q_45, Q_45, Q_135)) # |+> |+> |->
"""
ψᵢₙ> = 1/(2√2) (|000⟩ -|001⟩ +|010⟩ -|011⟩ +|100⟩ -|101⟩ +|110⟩ -|111⟩)
ψₒᵤₜ> = 1/(2√2) (|000⟩ -|001⟩ +|010⟩ -|011⟩ +|100⟩ -|101⟩ -|110⟩ +|111⟩)
~~~ Алгоритм Дойча–Ёжи ~~~
ψₖᵣₒₙ> = 1/(2√2) (|000⟩ -|001⟩ +|010⟩ -|011⟩ +|100⟩ -|101⟩ -|110⟩ +|111⟩) (eigenstates (Hᵢₙ=Hₒᵤₜ)? ✅)
ψₖᵣₒₙ₂> = 1/(2√2) (|000⟩ -|001⟩ +|010⟩ -|011⟩ +|100⟩ -|101⟩ -|110⟩ +|111⟩) (инволюция (self-inverse)? ✅)
Вероятности: 1/4, 1/4, 1/4, 1/4
Вердикт: сбалансированная
    ВЕРНЫЙ ВЕРДИКТ! Ещё и на eigenstates попали (на выходе H-gate тоже самое, что и на входе)
"""

deutsch_jozsa(lambda x, y: 0, (Q_45, Q_45, Q_135)) # |+> |+> |0>
"""
ψᵢₙ> = 1/(2√2) (|000⟩ -|001⟩ +|010⟩ -|011⟩ +|100⟩ -|101⟩ +|110⟩ -|111⟩)
ψₒᵤₜ> = 1/(2√2) (|000⟩ -|001⟩ +|010⟩ -|011⟩ +|100⟩ -|101⟩ +|110⟩ -|111⟩)
~~~ Алгоритм Дойча–Ёжи ~~~
ψₖᵣₒₙ> = 1/√2 (|000⟩ -|001⟩) (eigenstates (Hᵢₙ=Hₒᵤₜ)? ❌)
ψₖᵣₒₙ₂> = 1/(2√2) (|000⟩ -|001⟩ +|010⟩ -|011⟩ +|100⟩ -|101⟩ +|110⟩ -|111⟩) (инволюция (self-inverse)? ✅)
Вероятности: 1, 0, 0, 0
Вердикт: константная
"""

deutsch_jozsa(lambda x, y: 1, (Q_45, Q_45, Q_135)) # |+> |+> |0>
"""
ψᵢₙ> = 1/(2√2) (|000⟩ -|001⟩ +|010⟩ -|011⟩ +|100⟩ -|101⟩ +|110⟩ -|111⟩)
ψₒᵤₜ> = 1/(2√2) (-|000⟩ +|001⟩ -|010⟩ +|011⟩ -|100⟩ +|101⟩ -|110⟩ +|111⟩)
~~~ Алгоритм Дойча–Ёжи ~~~
ψₖᵣₒₙ> = 1/√2 (-|000⟩ +|001⟩) (eigenstates (Hᵢₙ=Hₒᵤₜ)? ❌)
ψₖᵣₒₙ₂> = 1/(2√2) (-|000⟩ +|001⟩ -|010⟩ +|011⟩ -|100⟩ +|101⟩ -|110⟩ +|111⟩) (инволюция (self-inverse)? ✅)
Вероятности: 1, 0, 0, 0
Вердикт: константная
"""

deutsch_jozsa(lambda x, y: x ^ y, (Q_45, Q_45, Q_135)) # |+> |+> |0>
"""
ψᵢₙ> = 1/(2√2) (|000⟩ -|001⟩ +|010⟩ -|011⟩ +|100⟩ -|101⟩ +|110⟩ -|111⟩)
ψₒᵤₜ> = 1/(2√2) (|000⟩ -|001⟩ -|010⟩ +|011⟩ -|100⟩ +|101⟩ +|110⟩ -|111⟩)
~~~ Алгоритм Дойча–Ёжи ~~~
ψₖᵣₒₙ> = 1/√2 (|110⟩ -|111⟩) (eigenstates (Hᵢₙ=Hₒᵤₜ)? ❌)
ψₖᵣₒₙ₂> = 1/(2√2) (|000⟩ -|001⟩ -|010⟩ +|011⟩ -|100⟩ +|101⟩ +|110⟩ -|111⟩) (инволюция (self-inverse)? ✅)
Вероятности: 0, 0, 0, 1
Вердикт: ни константная, ни сбалансированная
"""
