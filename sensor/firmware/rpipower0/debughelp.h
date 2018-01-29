#ifndef DEBUGHELP_H
#define DEBUGHELP_H

#include "atm90e26.h"

template<typename T, int sz>
int size(T(&)[sz]) {
    return sz;
}


void showThings(atm90e26_c &);

#endif

