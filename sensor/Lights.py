#!/usr/bin/env python3

import RPi.GPIO as GPIO
import time

class Lights:
    def __init__(self, thresholds = None):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(22,GPIO.OUT)
        GPIO.setup(27,GPIO.OUT)
        if thresholds is not None:
            self.thresholds = thresholds
        else:
            self.thresholds = (0.005, 0.050, 0.100)
   
    def set(self,a=False,b=False):
        GPIO.output(22,True if a else False)
        GPIO.output(27,True if b else False)


    def showMeasure(self, val):
        level = 0
        while level < len(self.thresholds) and val >= self.thresholds[level]:
            level += 1

        if level == 0:
            GPIO.output(22, False)
            GPIO.output(27, False)
        elif level == 1:
            GPIO.output(22, False)
            GPIO.output(27, True)
        elif level == 2:
            GPIO.output(22, True)
            GPIO.output(27, False)
        elif level == 3:
            GPIO.output(22, True)
            GPIO.output(27, True)

    def __del__(self):
        GPIO.cleanup()

if __name__ == '__main__':
    l = Lights()
    l.showMeasure(0)
    time.sleep(1)
    l.showMeasure(0.006)
    time.sleep(1)
    l.showMeasure(0.060)
    time.sleep(1)
    l.showMeasure(0.600)
    time.sleep(1)
    l.showMeasure(0.000)
    time.sleep(1)


