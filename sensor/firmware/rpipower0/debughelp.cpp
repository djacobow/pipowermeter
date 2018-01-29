
#include "debughelp.h"

void showThings(atm90e26_c &afe) {
    const char *names[] = {
        "status",
        "mmode",
        "adjstart",
        "calstart",
        "ugain",
        "igainl",
        "urms",
        "irmsl",
        "freq",
        "pmeanl",
        "qmeanl",
        "pfl",
        "panglel",
        "apenergy",
        "anenergy",
        "rpenergy",
        "rnenergy",
    };
   const atm90e26_addrs_e regs[] = { status,
        mmode,
        adjstart,
        calstart,
        ugain,
        igainl,
        urms,
        irmsl,
        freq,
        pmeanl,
        qmeanl,
        pfl,
        panglel,
        apenergy,
        anenergy,
        rpenergy,
        rnenergy,
   };

   for (uint8_t i=0; i<size(names); i++) {
       Serial.print(names[i]);
       Serial.print(": ");
       atm90e26_addrs_e reg = regs[i];
       uint16_t v = afe.r(reg);
       Serial.print(v,HEX);
       Serial.print(" [ ");
       Serial.print(v);
       Serial.println(" ]");
       switch (reg) {
           case apenergy:
               if (v) digitalWrite(pin_energy_indic0, HIGH);
               break;
           case rpenergy:
           case rnenergy:
               if (v) digitalWrite(pin_energy_indic1, HIGH);
               break;
       }
   }
   Serial.println("\n");
};

