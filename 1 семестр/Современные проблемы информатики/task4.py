from typing import List, Tuple

from qubit import Qubit, Q_0, Q_45, Q_135
from logic import BooleanFunction
from number_decorator import decorate_num
from misc import float_neq



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

def reg2str(vec: Tuple[complex, ...], n_qubits: int) -> None:
    v0 = " ".join(f"|{format(i, f'0{n_qubits}b')}⟩ {decorate_num(amp)}"
                for i, amp in enumerate(vec) if float_neq(amp, 0))
    v1 = " ".join(f"|{format(i, f'0{n_qubits}b')}⟩ {decorate_num(amp * 2**0.5)}"
                  for i, amp in enumerate(vec) if float_neq(amp, 0))
    v1 = f"1/√2 ({v1})"
    return v1 if len(v1) < len(v0) else v0



bf_and = BooleanFunction(2, lambda x, y: x & y)
print(bf_and)
"""
+----------+
| x₂ x₁  y |
+----------+
|  0  0  0 |
|  0  1  0 |
|  1  0  0 |
|  1  1  1 |
+----------+
"""

#   Q_0 = |φ> |0>
#  Q_45 = |φ> 1/√2 (|0> +|1>)     Соответствует |0> * H, т.е. |+>
# Q_135 = |φ> 1/√2 (|0> -|1>)     Соответствует |1> * H, т.е. |->

# Для параллелизма: tensor_qubits(Q_45, Q_45, Q_0)   — два входа в суперпозиции, выход в ∣0⟩.
# Для Дойча–Ёжи:    tensor_qubits(Q_45, Q_45, Q_135) — два входа в суперпозиции, выход в ∣-⟩. (как на схеме)

register = tensor_qubits_MSB(Q_45, Q_45, Q_0) # |+> |+> |0>
print(register) # (0.5, 0.5, 0.5, 0.5, 0, 0, 0, 0) |000> |100> |010> |110>
print("MSB:", reg2str(register, 3)) # |000⟩ 0.5 |001⟩ 0.5 |010⟩ 0.5 |011⟩ 0.5

# но мы получили        MSB (Most  Significant Bit) — «старший значащий бит»
# а надо, для удобства, LSB (Least Significant Bit) — «младший значащий бит»

register = tensor_qubits_LSB(Q_45, Q_45, Q_0) # |+> |+> |0>
print(register) # (0.5, 0, 0.5, 0, 0.5, 0, 0.5, 0) |000> |010> |100> |110>
print("LSB:", reg2str(register, 3)) # |000⟩ 0.5 |010⟩ 0.5 |100⟩ 0.5 |110⟩ 0.5

register = tensor_qubits_LSB(Q_45, Q_45, Q_135) # |+> |+> |->
print(register) # (0.354, -0.354, 0.354, -0.354, 0.354, -0.354, 0.354, -0.354)
print(reg2str(register, 3)) # 1/√2 (|000⟩ 0.5 |001⟩ -0.5 |010⟩ 0.5 |011⟩ -0.5 |100⟩ 0.5 |101⟩ -0.5 |110⟩ 0.5 |111⟩ -0.5)
