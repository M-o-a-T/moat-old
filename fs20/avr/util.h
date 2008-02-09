/*
 *  Copyright © 2008, Matthias Urlichs <matthias@urlichs.de>
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License (included; see the file LICENSE)
 *  for more details.
 */

/*
 * This header defines misc utility stuff.
 */

#ifndef UTIL_H
#define UTIL_H

#ifndef FALSE
#define FALSE 0
#endif
#ifndef TRUE
#define TRUE 1
#endif

#include "local.h"
#ifdef DEBUGGING
#include <stdio.h>
#include <avr/pgmspace.h>
#endif

void __attribute__((noreturn)) _report_error(char *err); /* Program memory */
#define report_error(x) _report_error(PSTR(x))

void __attribute__((noreturn)) reset(void);

void setup_stdio(void);

#ifdef DEBUGGING
#define DBG(x) fputs_P(PSTR(":" x "\n"),stderr)
#define DBGS(x, y ...) fprintf_P(stderr, PSTR(":" x "\n"), y)
#else
#define DBG(x) do{}while(0)
#define DBGS(x ...) do{}while(0)
#endif

#ifndef nop
#define nop() __asm__ __volatile__ ("nop")
#endif

#endif /* UTIL_H */
