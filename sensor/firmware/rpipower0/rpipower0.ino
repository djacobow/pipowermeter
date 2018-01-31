#include <Arduino.h>
#include <stdint.h>
#include <Wire.h>
#include "atm90e26.h"
#include "i2cif.h"
#include "debughelp.h"

atm90e26_c afe(pin_SS);
i2c_c i2c(0x32, &afe);

void i2c_receiver(uint8_t hM) { i2c.receiveEvent(hM); };
void i2c_requester()          { i2c.requestEvent();   };




void setup() {
    Serial.begin(57600);
    Serial.println("setup START");
    afe.init();
    Serial.println("setup x 0");
    afe.w(funcen, 0x0);
    // go into cal mode(s)
    afe.w(calstart, 0x5678);
    afe.w(plconsth, 0x1c);
    afe.w(plconstl, 0xa90e);
    afe.w(plconsth, 0x1c);
    afe.w(plconstl, 0xa90e);
    uint16_t mm = afe.r(mmode);
    mm &= ~0xe000; // set l frontend gain to 4
    afe.w(mmode,mm);
    // values from calibration
    afe.w(adjstart, 0x5678);
    afe.w(ugain, 14959);
    afe.w(igainl, 36232);

    i2c.init();
    Serial.println("setup DONE!");
};


uint32_t last_show = 0;
bool xyz = false;

void loop() {
    uint32_t now = millis();

    if (true) {
        if ((now - last_show) > 2000) {
            digitalWrite(pin_energy_indic0, xyz);
            digitalWrite(pin_energy_indic1, !xyz);
            xyz = !xyz;
            last_show = now;
        }
    }
    if (false) {
        if ((now - last_show) > 30000) {
            digitalWrite(pin_energy_indic0, LOW);
            digitalWrite(pin_energy_indic1, LOW);
            showThings(afe);
            last_show = now;
        }
    }
    i2c.work();
};


