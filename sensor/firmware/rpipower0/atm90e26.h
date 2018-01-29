#ifndef ATM90E26_H
#define ATM90E26_H

#include <stdint.h>
#include <SPI.h>

const uint8_t pin_SCK = 13;
const uint8_t pin_MISO = 12;
const uint8_t pin_MOSI = 11;
const uint8_t pin_SS = 10;
const uint8_t pin_energy_indic0 = 8;
const uint8_t pin_energy_indic1 = 9;


typedef enum atm90e26_addrs_e {
    reset    = 0x00,
    status   = 0x01,
    funcen   = 0x02,
    sagthr   = 0x03,
    smallmod = 0x04,
    lastdat  = 0x06,
    plconsth = 0x21,
    plconstl = 0x22,
    calstart = 0x20,
    mmode    = 0x2b,
    adjstart = 0x30,
    ugain    = 0x31,
    igainl   = 0x32,
    igainn   = 0x33,
    apenergy = 0x40,
    anenergy = 0x41,
    rpenergy = 0x43,
    rnenergy = 0x44,
    irms     = 0x48,
    enstatus = 0x46,
    irmsl    = 0x48,
    urms     = 0x49,
    pmeanl   = 0x4a,
    qmeanl   = 0x4b,
    freq     = 0x4c,
    pfl      = 0x4d,
    panglel  = 0x4e,
    smeanl   = 0x4f,
    irmsn    = 0x68,
} atm90e16_addrs_e;


class atm90e26_c {
    public:
        atm90e26_c(uint8_t cspin) : pin_cs(cspin) { };
        void init();
        uint16_t r(atm90e26_addrs_e reg) {
            return _doRead((uint8_t)reg);
        };
        void w(atm90e26_addrs_e reg, uint16_t d) {
            _doWrite((uint8_t)reg,d);
        };


    private:
        SPISettings ss;
        uint8_t pin_cs;

        uint16_t _doRead(uint8_t addr);
        void _doWrite(uint8_t addr, uint16_t od);
};

#endif

