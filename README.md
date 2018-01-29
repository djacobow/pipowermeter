# pipowermeter

sensor / server code for electric power meter based on raspberry pi + atm90e26

##

Implements remote measurement of AC power. The overall project goal is to create 
an AC power meter with WiFi upload that is small and self-contained so that it can 
deployed /inside/ appliances, so that their energy use can be studied.

## Hardware

The hardware platform consists of a custom circuit board and a Raspberry Pi Zero W.
The custom board is built around an ATM90E26 power measurement chip. An Atemga328p
configures and queries the AFE chip via SPI. The 328p can itself be queried by 
the Pi Zero W via i2c. The 328p is thus acting primarily as a bridge, though it 
has plenty of spare memory to implement other features (high speed sampling, 
averaging, watchdog, etc.)

The ATM90E26 is at the potential of the AC mains and so is dangerous to touch. For
this reason, it is isolated from the Atmega (and the RPi) via the ISO7841 isolation
chip. The RPi plugs directly into a 40 pin connect on the isolated side. The board
provides 5V power for the RPi.

A sketch is included that forwards i2c transactions to SPI.

## Server

A simple server written in node.js is provided to accept http POSTs from various 
deployed power meters. It demonstrated the collection and display of power data,
but it does not store it to a permanent database.

## Device

A simple daemon style app is provided for the RPi that qeries the hardware
and periodically POSTs measurements to the server.

