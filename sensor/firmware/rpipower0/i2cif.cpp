#include "i2cif.h"

void i2c_c::init() {
    Wire.begin(myaddr);
    Wire.setClock(400000);
    Wire.onReceive(i2c_receiver);
    Wire.onRequest(i2c_requester);
};

void i2c_c::receiveEvent(uint8_t count) {
    // Serial.print("recvEvent "); Serial.println(count);
    if ((afe_state != idle) || (count != 3)) {
        while (count) {
            uint8_t x = Wire.read();
            // Serial.print("dumping: "); Serial.println(x,HEX);
            count--;
        }
        return;
    };

    wdata[0] = Wire.read();
    wdata[1] = Wire.read();
    wdata[2] = Wire.read();

    rdata[0] = 0;
    rdata[1] = 0;
    rdata[2] = 0;
    rdata[3] = 0;

    if (0) {
        Serial.print(" addr: "); Serial.print(wdata[0],HEX);
        Serial.print(" dh: "); Serial.print(wdata[1],HEX);
        Serial.print(" dl: "); Serial.println(wdata[2],HEX);
    }

    afe_state = (wdata[0] & 0x80) ? pending_read : pending_write;

};

void i2c_c::requestEvent() {
    if (0) {
        Serial.print("reqEvent sending: ");
        Serial.print(rdata[0],HEX);
        Serial.print(" ");
        Serial.print(rdata[1],HEX);
        Serial.print(" ");
        Serial.print(rdata[2],HEX);
        Serial.print(" ");
        Serial.println(rdata[3],HEX);
    }
    if (afe_state == idle) {
        Wire.write(rdata,4);
    } else {
        const uint8_t x[] = {0x99,0x88,0x77,0x66};
        Wire.write(x,4);
    }
}

void i2c_c::work() {
    noInterrupts();
    uint16_t temp;
    atm90e26_addrs_e addr = wdata[0];
    switch (afe_state) {
        case pending_read:
            afe_state = working;
            Serial.print("[work] r_addr: "); Serial.print(addr,HEX);
            temp = pafe->r(addr);
            Serial.print(" value: "); Serial.println(temp,HEX);

            rdata[0] = 0x12;
            rdata[1] = wdata[0] & ~0x80;
            rdata[2] = (temp >> 8) & 0xff;
            rdata[3] = temp & 0xff;
            afe_state = idle;
            break;

        case pending_write:
            afe_state = working;
            Serial.print("[work] w_addr: "); Serial.print(addr,HEX);
            temp = (((uint16_t)wdata[1]) << 8) | wdata[2];
            Serial.print(" value: "); Serial.println(temp,HEX);
            pafe->w(addr, temp);
            rdata[0] = 0x12;
            rdata[1] = wdata[0] & ~0x80;
            rdata[2] = 0;
            rdata[3] = 0;
            afe_state = idle;
            break;

        case working :
        case idle : 
        default: 
            break;
    }
    interrupts();
};

