import re



# Удаляем лишние скобки и двойные минусы
def clean(expr):
    while True:
        expr = expr.strip()
        if expr.startswith("--"):
            expr = expr[2:]
        elif expr.startswith("(") and expr.endswith(")"):
            expr = expr[1:-1]
      # elif expr.startswith("-(") and expr.endswith(")"):
      #     expr = "-" + expr[2:-1]   Разрушит выражение вида -(a+b) или -(a-b)
        else: return expr

# Проверка, нужно ли обернуть в скобки
def needs_parentheses(expr):
    expr = expr.strip()
    level = 0
    for i, ch in enumerate(expr):
        if   ch == "(": level += 1
        elif ch == ")": level -= 1
        elif ch in "+-" and level == 0 and i != 0:
            return True
    return False



LOG_MUL = False
LOG_ADD = False

class Symbolic:
    _match = re.compile(r"^(-?\d+(?:\.\d*)?)\*?(.*)$").match

    def __init__(self, value):
        if isinstance(value, (int, float)):
            self.coeff = value
            self.var = None
        elif isinstance(value, str):
            value = value.strip()
            if value == "0":
                self.coeff = 0
                self.var = None
                return

            # Попытка распарсить коэффициент
            match = Symbolic._match(value)
            if match:
                num = match.group(1)
                self.coeff = (float if "." in num else int)(num)
                self.var = match.group(2).strip()
                if not self.var: self.var = None
            # Отдельный случай: "-x"
            elif value.startswith("-"):
                self.coeff = -1
                self.var = value[1:]
            # Обычный случай: "x"
            else:
                self.coeff = 1
                self.var = value
            if not self.var: self.var = None
        else:
            raise TypeError(f"Symbolic accepts int or str, not {type(value).__name__!r}")

    def __str__(self):
        if self.coeff == 0:
            return "0"
        if self.var is None:
            return str(self.coeff)
        if self.var.startswith("/"):
            return f"{self.coeff}{self.var}"
        sign = "-" if self.coeff == -1 else ""
        return f"{sign}{self.var}" if self.coeff in (-1, 1) else f"{self.coeff}*{self.var}"

    def add(self, other):
        if isinstance(other, (int, float)):
            other = Symbolic(other)
        if not isinstance(other, Symbolic):
            return NotImplemented

        if self.coeff == 0 and self.var is None:
            return other
        if other.coeff == 0 and other.var is None:
            return self

        if self.var is None and other.var is None:
            return Symbolic(self.coeff + other.coeff)

        if self.var == other.var:
            total = self.coeff + other.coeff
            if total == 0:
                return Symbolic(0)
            elif total == 1:
                return Symbolic(self.var)
            elif total == -1:
                return Symbolic("-" + self.var)
            else:
                return Symbolic(f"{total}*{self.var}")

        if self.var is None:
            const = self.coeff
            var = str(other)
        elif other.var is None:
            const = other.coeff
            var = str(self)
        else:
            left = str(self)
            right = str(other)
            if right.startswith("-"):
                return Symbolic(f"{left} - {right[1:]}")
            return Symbolic(f"{left} + {right}")

        if const == 0:
            return Symbolic(var)
        elif const > 0:
            return Symbolic(f"{var} + {const}")
        else:
            return Symbolic(f"{var} - {-const}")

    def __add__(self, other):
        result = self.add(other)
        if LOG_ADD: print(self, "+", other, "=", result)
        return result

    def __radd__(self, other):
        return self.__add__(other)

    def mul(self, other):
        if isinstance(other, str):
            other = Symbolic(other)

        if isinstance(other, (int, float)):
            if self.coeff == 0 or other == 0:
                return Symbolic(0)
            if self.var is None:
                return Symbolic(self.coeff * other)

            result_coeff = self.coeff * other

            var_expr = clean(self.var)
            if result_coeff < 0 and needs_parentheses(var_expr):
                var_expr = f"({var_expr})"

            sign = "-" if result_coeff < 0 else ""
            abs_coeff = abs(result_coeff)
            if abs_coeff == 1:
                return Symbolic(f"{sign}{var_expr}")
            return Symbolic(f"{sign}{abs_coeff}*{var_expr}")

        if isinstance(other, Symbolic):
            if self.coeff == 0 or other.coeff == 0:
                return Symbolic(0)

            if self.var is None:
                return other.mul(self.coeff)
            if other.var is None:
                return self.mul(other.coeff)

            # print("*", self, other, f"({self.coeff} {other.coeff})")

            new_coeff = self.coeff * other.coeff
            left = self.var
            right = other.var

            left = clean(left)
            right = clean(right)

            if needs_parentheses(left):  left  = f"({left})"
            if needs_parentheses(right): right = f"({right})"

            core = f"{left}{right}" if right.startswith("/") else f"{left}*{right}"
            if new_coeff == 1:
                return Symbolic(core)
            elif new_coeff == -1:
                return Symbolic(f"-{core}")
            else:
                return Symbolic(f"{new_coeff}*{core}")

        return NotImplemented

    def __mul__(self, other):
        result = self.mul(other)
        if LOG_MUL: print(self, "*", other, "=", result)
        return result

    def __rmul__(self, other):
        return self.__mul__(other)



from matrix import Matrix

def MetaMatrix(*rows):
    return Matrix(*(tuple(Symbolic(cell) if type(cell) is str else cell for cell in row) for row in rows))



if __name__ == "__main__":
    A = Symbolic("cP*sY*sR + sP*cR")
    print("A:  ", A);
    A *= -1;   print("*-1:", A)
    A *= -1;   print("*-1:", A)
    A *= "-1"; print('*"-1":', A)
    A *= "-1"; print('*"-1":', A)
    A *= "Z";  print('*"Z":', A)
    print()

    Y = MetaMatrix(("cY", 0, "sY"), (0, 1, 0), ("-sY", 0, "cY"))
    P = MetaMatrix((1, 0, 0), (0, "cP", "-sP"), (0, "sP", "cP"))
    R = MetaMatrix(("cR", "-sR", 0), ("sR", "cR", 0), (0, 0, 1))
    print(Y("Y"))
    print(P("P"))
    print(R("R"))
    print((Y @ P)("Y@P"))
    print((P @ R)("P@R"))
    print((Y @ R)("Y@R"))
    print((Y @ P @ R)("Y@P@R"))

    view = (P @ Y @ R)("P@Y@R") # используется в реальности, работает
    print(view)

    print("\n~~~\n")
    proj = MetaMatrix(
        ("F_A", 0, 0, 0),      # F_A = fovy / aspect
        (0, "F", 0, 0),        # F = fovy
        (0, 0, "-FN", "-2fn"), # -FN = -(far+near)/(far-near)
        (0, 0, -1, 0)          # -2fn = -2*far*near/(far-near)
    )
    """
    (r00, r01, r02), (r10, r11, r12), (r20, r21, r22) = view.mat
    view = Matrix((r00, r01, r02, 0), (r10, r11, r12, 0), (r20, r21, r22, 0), (0, 0, 0, 1))
    print(proj("proj"))
    print(view("view"))
    print((proj @ view)("proj@view"))
    """

    inv_proj = MetaMatrix(
        ("1/F_A", 0, 0, 0),
        (0, "1/F", 0, 0),
        (0, 0, 0, -1),
        (0, 0, "-1/(2fn)", "FN/(2fn)")
    )
    print((proj @ inv_proj)("proj@proj⁻¹"))
    print((inv_proj @ proj)("proj⁻¹@proj"))

