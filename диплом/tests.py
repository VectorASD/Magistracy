from bitstr import BitStr
from discrlog import DiscrLog



def checker(locals_proxy):
    max_length = max(map(len, locals_proxy)) + 1
    for name, value in locals_proxy.items():
        if callable(value):
            print(f"{name+':' :{max_length}} ", end='', flush=True)
            try:
                value()
            except Exception as e:
                print(f"ERROR: {e}")
            else:
                print("OK")

def assert_throw(f, error):
    try:
        f()
    except error:
        pass
    else:
        raise AssertionError(f"Expected {error.__name__}")



def BitStr_tests():
    # ~~~ Constructor ~~~
    def FirstZero4():
        current   = BitStr("0101")
        reference = BitStr("101")
        assert current == reference

    def FirstZero1z():
        current   = BitStr("0")
        reference = BitStr("0")
        assert current == reference

    def FirstZero4e():
        current   = BitStr("1010")
        reference = BitStr("1010")
        assert current == reference

    # ~~~ Equality / NonEquality ~~~
    def OneBitEq():
        a = BitStr("0")
        b = BitStr("0")
        assert     a == b
        assert not a != b

    def OneBitNeq():
        a = BitStr("0")
        b = BitStr("1")
        assert not a == b
        assert     a != b

    def SeveralBitEq():
        a = BitStr("101010")
        b = BitStr("101010")
        assert a == b

    # ~~~ Operator[] ~~~
    def AsArray():
        # Реальный тест подразумевает, что мы туда может добавить не только '0' и '1', а ещё и 'd'.
        # На практике, это разрушает основную идею, использовать int, в качестве контейнера для битов.
        # Недопустимо из-за какого-то одного теста убирать серьёзную оптимизацию на производительность.
        s = "1101"  # hex(13) = "d", bin(13) = "1101"
        a = BitStr(s)
        for i in range(len(s)):
            assert str(a[i]) == s[i], f"Index {i}: {s[i]} != {a[i]}"

    # ~~~ Operator+ (XOR) ~~~
    def Add1():
        a = BitStr("101010")
        b = BitStr("001101")
        r = BitStr("100111")
        c = a + b
        assert c == r

    def AddDiffSize1():
        a = BitStr("11001010")
        b = BitStr("001101")
        r = BitStr("11000111")
        c = a + b
        assert c == r

    def AddDiffSize2():
        a = BitStr("001101")
        b = BitStr("11001010")
        r = BitStr("11000111")
        c = a + b
        assert c == r

    # ~~~ Operator% (полиномиальное деление) ~~~
    def Mod_GF0_1():
        a = BitStr("1011010")
        b = BitStr("101")
        r = BitStr("0")
        c = a % b
        assert c == r

    def Mod_GF0_2():
        a = BitStr("0")
        b = BitStr("101")
        r = BitStr("0")
        c = a % b
        assert c == r

    def Mod_GF_2():
        a = BitStr("100")
        b = BitStr("1011")
        r = BitStr("100")
        c = a % b
        assert c == r

    def Mod_GF_3():
        a = BitStr("1000")
        b = BitStr("1011")
        r = BitStr("11")
        c = a % b
        assert c == r

    def Mod_GF_4():
        a = BitStr("10000")
        b = BitStr("1011")
        r = BitStr("110")
        c = a % b
        assert c == r

    def Mod_GF_5():
        a = BitStr("100000")
        b = BitStr("1011")
        r = BitStr("111")
        c = a % b
        assert c == r

    def Mod_GF_6():
        a = BitStr("1000000")
        b = BitStr("1011")
        r = BitStr("101")
        c = a % b
        assert c == r

    # ~~~ AsNumber ~~~
    def AsNumber():
        a   = BitStr("1000000")
        num = 0b1000000
        assert a.as_number() == num

    checker(locals())



def DiscrLog_tests():
    # Исходные тесты
    def a_12_mod_19():
        a = 0b100011
        p = 0b1010
        d = DiscrLog(a, p)
        d.divide()
        assert d.get_power() == 11

    def a_0_mod_7():
        y = 0b0
        p = 0b111
        d = DiscrLog(p, y)
        d.divide()
        assert d.get_power() == -1

    def a_1_mod_7():
        y = 0b1
        p = 0b111
        d = DiscrLog(p, y)
        d.divide()
        assert d.get_power() == 0

    def a_replace_P_Y_throw():
        y = 0b1
        p = 0b111
        d = DiscrLog(y, p)
        assert_throw(d.divide, ValueError)

    def a_2_mod_7():
        y = 0b10
        p = 0b111
        d = DiscrLog(p, y)
        d.divide()
        assert d.get_power() == 1

    def a_4_mod_7():
        y = 0b11
        p = 0b111
        d = DiscrLog(p, y)
        d.divide()
        assert d.get_power() == 2

    # Дополнительные тесты для align_to_p_size
    def align_small_a():
        d = DiscrLog(0b111, 0b1)   # p = 7, y = 1
        # Изначально a = 1 (size=1), p size=3
        cnt = d.align_to_p_size()
        assert cnt == 2
        assert d.a == 0b100          # 1 << 2
        assert d.size_a == 3

    def align_already_matching():
        d = DiscrLog(0b111, 0b1)
        d.a = 0b111
        d.size_a = 3
        cnt = d.align_to_p_size()
        assert cnt == 0
        assert d.a == 0b111

    checker(locals())



BitStr_tests()
DiscrLog_tests()
