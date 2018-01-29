#include "atm90e26.h"

void atm90e26_c::init() {
    pinMode(pin_energy_indic0, OUTPUT);
    pinMode(pin_energy_indic1, OUTPUT);
    pinMode(pin_cs, OUTPUT);
    pinMode(pin_SCK, OUTPUT);
    pinMode(pin_MOSI, OUTPUT);
    pinMode(pin_MISO, INPUT);
    SPISettings settings(200000, MSBFIRST, SPI_MODE3);
    ss = settings;

    w(reset, 0x789a);
    delay(1000);
};


uint16_t atm90e26_c::_doRead(uint8_t addr) {
    noInterrupts();
    SPI.beginTransaction(ss);
    digitalWrite(pin_cs, LOW);
    delayMicroseconds(10);
    addr |= 0x80;
    SPI.transfer(addr);
    delayMicroseconds(4);
    uint8_t dh = SPI.transfer(0);
    uint8_t dl = SPI.transfer(0);
    delayMicroseconds(10);
    digitalWrite(pin_cs, HIGH);
    interrupts();
    return ((uint16_t)dh << 8 | (uint16_t)dl);
};

void atm90e26_c::_doWrite(uint8_t addr, uint16_t od) {
    noInterrupts();
    SPI.beginTransaction(ss);
    digitalWrite(pin_cs, LOW);
    delayMicroseconds(10);
    addr &= ~0x80;
    SPI.transfer(addr);
    delayMicroseconds(4);
    SPI.transfer((od >> 8) & 0xff);
    SPI.transfer(od & 0xff);
    delayMicroseconds(10);
    digitalWrite(pin_cs, HIGH);
    interrupts();
};

