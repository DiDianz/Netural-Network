import snap7

from snap7 import util

plc = snap7.client.Client()

plc.connect('192.168.1.109',0,1)

print(f'connect:{plc.get_connected()}')
