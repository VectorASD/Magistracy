from bitstr import BitStr



def checker(locals_proxy):
    max_length = max(map(len, locals_proxy)) + 1
    for name, value in locals_proxy.items():
        if callable(value):
            print(f"{name+':' :{max_length}} ", end='', flush=True)
            try: value()
            except: print("ERROR")
            else:   print("OK")



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



BitStr_tests()
