
#ifndef I2CIF_H
#define I2CIF_H

#include "atm90e26.h"
#include <stdint.h>
#include <Wire.h>

void i2c_receiver(uint8_t);
void i2c_requester();

class i2c_c {
    public:
        enum afe_state_t {
            idle, pending_read, pending_write, working,
        };
        i2c_c(uint8_t myaddr, atm90e26_c* pchip) : 
            myaddr(myaddr), pafe(pchip), afe_state(idle) { };
        void init();
        void receiveEvent(uint8_t count);
        void requestEvent();
        void work();
    private:
        atm90e26_c* pafe;
        uint8_t rdata[4];
        uint8_t myaddr;
        uint8_t wdata[3];
        afe_state_t afe_state;

};

#endif

