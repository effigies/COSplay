import path
import pyb
import uos

#switch of laser immediately
pin_out1 = pyb.Pin('Y1',pyb.Pin.OUT_PP,pull=pyb.Pin.PULL_UP)
pin_out1.value(1)
pin_out2 = pyb.Pin('Y3',pyb.Pin.OUT_PP,pull=pyb.Pin.PULL_UP)
pin_out2.value(1)

#Open drain pins
pin_out3 = pyb.Pin('Y12',pyb.Pin.OUT_OD)
pin_out3.value(0)
pin_out4 = pyb.Pin('X2',pyb.Pin.OUT_OD)
pin_out4.value(0)

#Amplitude modulation pins
pin_out5 = pyb.Pin('X5',pyb.Pin.OUT_PP,pull=pyb.Pin.PULL_DOWN)
pin_out5.value(0)
pin_out6 = pyb.Pin('X6',pyb.Pin.OUT_PP,pull=pyb.Pin.PULL_DOWN)
pin_out6.value(0)

if path.exists('/flash/bootincopymode'):
	uos.remove('/flash/bootincopymode')
	pyb.usb_mode('VCP+MSC')
	pyb.main('copymodemain.py')
else:
	pyb.usb_mode('VCP')
	pyb.main('main.py')
