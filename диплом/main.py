from stego_container import StegoContainer
from bitstr import BitStr



capacity = 7

for value in range(1 << capacity):
    source = BitStr(value, capacity)
    print(f"> {source}")
    container = StegoContainer(source)
    for message in range(1 << container.get_container_capacity()):
        stego = container.write_to_container(message)
        unstego = container.read_from_container(stego)
        fixed = StegoContainer(str(stego))
        stego2 = fixed.write_to_container(message)
        print(stego, repr(stego), unstego, stego == stego2)
        assert int(unstego) == message
        assert stego == stego2



""" При capacity = 2:
> 00
00 BitStr('00', 2) 0 True
01 BitStr('01', 2) 1 True
> 01
00 BitStr('00', 2) 0 True
01 BitStr('01', 2) 1 True
> 10
11 BitStr('11', 2) 0 True
10 BitStr('10', 2) 1 True
> 11
11 BitStr('11', 2) 0 True
10 BitStr('10', 2) 1 True

Выводы теста:

1) Разные пустые контейнеры (source) при одном и том же сообщении могут давать
   одинаковые stego. Это исключает возможность однозначного восстановления
   исходного контейнера, даже если известно сообщение → метод не является RDH
   (обратимой стеганографией). Обратимость потребовала бы дополнительных знаний.

2) После встраивания сообщения повторное применение того же сообщения
   к полученному stego не меняет контейнер (идемпотентность).
   Если перестроить контейнер на основе stego, write_to_container сохранит его неизменным.
"""
