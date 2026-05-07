from bitstr import BitStr
from discr_log import DiscrLog
from lambda_table import Lambda
from stego_container import StegoContainer



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
    except Exception as e:
        raise AssertionError(f"Expected {error.__name__}, but received: {e}")
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



def Lambda_tests():
    def dec2bin_0():
        L = Lambda(3, 13)
        assert L.dec2bin(0) == "0"

    def dec2bin_13():
        L = Lambda(3, 13)
        assert L.dec2bin(13) == "1101"

    def f_lambda_0():
        L = Lambda(5, 61)
        a = BitStr("0")
        b = L.f_lambda(a)
        assert b == BitStr("0")

    def f_lambda_8():
        L = Lambda(5, 61)
        tmp = BitStr("10000000")
        b = L.f_lambda(tmp)
        assert b == BitStr("1110")

    def f_lambda_29():
        L = Lambda(5, 61)
        tmp = BitStr("1" + "0" * 28)
        b = L.f_lambda(tmp)
        assert b == BitStr("11001")

    checker(locals())



def StegoContainer_tests():
    # ~~~ Read ~~~
    def read_e111m00():
        s = StegoContainer("101")
        assert s.read_from_container("111") == "00"

    def read_e001m01():
        s = StegoContainer("101")
        assert s.read_from_container("001") == "01"

    def read_e101m10():
        s = StegoContainer("101")
        assert s.read_from_container("101") == "10"

    def read_e100m11():
        s = StegoContainer("101")
        assert s.read_from_container("100") == "11"

    # ~~~ Write ~~~
    def write_s111m00():
        s = StegoContainer("101")
        assert s.write_to_container("00") == "111"

    def write_s001m01():
        s = StegoContainer("101")
        assert s.write_to_container("01") == "001"

    def write_s101m10():
        s = StegoContainer("101")
        assert s.write_to_container("10") == "101"

    def write_s100m11():
        s = StegoContainer("101")
        assert s.write_to_container("11") == "100"

    # ~~~ Complex 7 ~~~
    def write_complex7():
        s = StegoContainer("1111111")
        assert s.write_to_container("000") == "1111111"
        assert s.write_to_container("001") == "1111110"
        assert s.write_to_container("010") == "1111101"
        assert s.write_to_container("011") == "1011111"
        assert s.write_to_container("100") == "1111011"
        assert s.write_to_container("101") == "1110111"
        assert s.write_to_container("110") == "0111111"
        assert s.write_to_container("111") == "1101111"

    def read_complex7():
        s = StegoContainer("1111111")
        assert s.read_from_container("1111111") == "000"
        assert s.read_from_container("1111110") == "001"
        assert s.read_from_container("1111101") == "010"
        assert s.read_from_container("1011111") == "011"
        assert s.read_from_container("1111011") == "100"
        assert s.read_from_container("1110111") == "101"
        assert s.read_from_container("0111111") == "110"
        assert s.read_from_container("1101111") == "111"

    # ~~~ Complex 15 ~~~
    def write_complex15():
        s = StegoContainer("111111111111111")
        assert s.write_to_container("0000") == "111111111111111"
        assert s.write_to_container("0001") == "111111111111110"
        assert s.write_to_container("0010") == "111111111111101"
        assert s.write_to_container("0011") == "111111111101111"
        assert s.write_to_container("0100") == "111111111111011"
        assert s.write_to_container("0101") == "111111011111111"
        assert s.write_to_container("0110") == "111111111011111"
        assert s.write_to_container("0111") == "111101111111111"
        assert s.write_to_container("1000") == "111111111110111"
        assert s.write_to_container("1001") == "011111111111111"
        assert s.write_to_container("1010") == "111110111111111"
        assert s.write_to_container("1011") == "111111101111111"
        assert s.write_to_container("1100") == "111111110111111"
        assert s.write_to_container("1101") == "101111111111111"
        assert s.write_to_container("1110") == "111011111111111"
        assert s.write_to_container("1111") == "110111111111111"

    def read_complex15():
        s = StegoContainer("111111111111111")
        assert s.read_from_container("111111111111111") == "0000"
        assert s.read_from_container("111111111111110") == "0001"
        assert s.read_from_container("111111111111101") == "0010"
        assert s.read_from_container("111111111101111") == "0011"
        assert s.read_from_container("111111111111011") == "0100"
        assert s.read_from_container("111111011111111") == "0101"
        assert s.read_from_container("111111111011111") == "0110"
        assert s.read_from_container("111101111111111") == "0111"
        assert s.read_from_container("111111111110111") == "1000"
        assert s.read_from_container("011111111111111") == "1001"
        assert s.read_from_container("111110111111111") == "1010"
        assert s.read_from_container("111111101111111") == "1011"
        assert s.read_from_container("111111110111111") == "1100"
        assert s.read_from_container("101111111111111") == "1101"
        assert s.read_from_container("111011111111111") == "1110"
        assert s.read_from_container("110111111111111") == "1111"

    checker(locals())



BitStr_tests()
DiscrLog_tests()
Lambda_tests()
StegoContainer_tests()
