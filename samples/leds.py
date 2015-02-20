# Usage:
# l = leds.Led('green')
# l.on()
# l.off()

import pyb

class Led:
  pin = None
  light = False

  def __init__(self, color):
    if (color == 'green'):
      self.pin = pyb.Pin('Y4', pyb.Pin.PULL_UP)
    elif (color == 'red'):
      self.pin = pyb.Pin('Y3', pyb.Pin.PULL_UP)
    else:
      print('Unknown led color')

  def on(self):
    if self.pin:
      self.pin.high()
      self.light = True

  def off(self):
    if self.pin:
      self.pin.low()
      self.light = False

  def toggle(self):
    if self.pin:
      if self.light:
        self.off()
      else:
        self.on()

  def is_lit(self):
    return self.light
