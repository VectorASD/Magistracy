from stego_container import StegoContainer
from bitstr import BitStr

for i in range(1, 21):
    container = StegoContainer('0' * i)
  # print(i, container.capacity)

container = StegoContainer('0' * 7)
for i in range(1 << container.capacity):
    stego = container.write_to_container(i)
    print(stego, repr(stego))
