class Symbolic:
    def __init__(self, value):
        if isinstance(value, int):
            self.coeff = value
            self.var = None
        elif isinstance(value, str):
            value = value.strip()
            if value == "0":
                self.coeff = 0
                self.var = None
            elif value.startswith("-"):
                self.coeff = -1
                self.var = value[1:]
            else:
                self.coeff = 1
                self.var = value
        else:
            raise TypeError("Symbolic accepts int or str")

    def __str__(self):
        if self.coeff == 0:
            return "0"
        if self.var is None:
            return str(self.coeff)
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
        # print(self, "+", other, "=", result)
        return result

    def __radd__(self, other):
        return self.__add__(other)

    def mul(self, other):
        if isinstance(other, (int, float)):
            if self.coeff == 0 or other == 0:
                return Symbolic(0)
            if self.var is None:
                return Symbolic(self.coeff * other)
            sign = "-" if self.coeff * other < 0 else ""
            abs_coeff = abs(self.coeff * other)
            if abs_coeff == 1:
                return Symbolic(f"{sign}{self.var}")
            return Symbolic(f"{sign}{abs_coeff}*{self.var}")

        if isinstance(other, str):
            return Symbolic(str(self) + "*" + other)

        if isinstance(other, Symbolic):
            if self.coeff == 0 or other.coeff == 0:
                return Symbolic(0)

            new_coeff = self.coeff * other.coeff
            left = self.var if self.var else str(self.coeff)
            right = other.var if other.var else str(other.coeff)

            # Удаляем лишние скобки и двойные минусы
            def clean(expr):
                expr = expr.strip()
                if expr.startswith("(") and expr.endswith(")"):
                    expr = expr[1:-1]
                if expr.startswith("-(") and expr.endswith(")"):
                    expr = "-" + expr[2:-1]
                if expr.startswith("--"):
                    expr = expr[2:]
                return expr

            left = clean(left)
            right = clean(right)

            core = f"{left}*{right}"
            if new_coeff == 1:
                return Symbolic(core)
            elif new_coeff == -1:
                return Symbolic(f"-{core}")
            else:
                return Symbolic(f"{new_coeff}*{core}")

        return NotImplemented

    def __mul__(self, other):
        result = self.mul(other)
        # print(self, "*", other, "=", result)
        return result

    def __rmul__(self, other):
        return self.__mul__(other)



from matrix import Matrix

def MetaMatrix(*rows):
    return Matrix(*(tuple(Symbolic(cell) if type(cell) is str else cell for cell in row) for row in rows))



if __name__ == "__main__":
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
    print((P @ Y @ R)("P@Y@R"))
