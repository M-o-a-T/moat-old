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
 * This code defines misc utility stuff.
 */

#include <stdlib.h>
#include <stdio.h>
#include <avr/pgmspace.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include "uart.h"
#include "util.h"

void _report_error(char *err) /* Program memory */
{
	//unsigned char sreg = SREG;
	cli();
	//uart_init(57600);
	uart_puts_p(PSTR("\n:ERROR: "));
	uart_puts_p(err);
	uart_putc('\n');
	//sreg = SREG;
	reset();
}

void reset(void)
{
	wdt_enable(WDTO_15MS);
	for(;;);
}

void wdt_init(void) __attribute__((naked)) __attribute__((section(".init3")));
void wdt_init(void)
{
     MCUSR = 0;
     wdt_disable();
}

void do_uart_init(void)
{
     uart_init(UART_BAUD_SELECT(57600,16000000));
}

typedef int (*putc_type)(char, struct __file *);
//FILE uart_io = FDEV_SETUP_STREAM((putc_type)uart_putc, uart_getc, _FDEV_SETUP_RW);
FILE uart_io = FDEV_SETUP_STREAM((putc_type)uart_putc, NULL, _FDEV_SETUP_WRITE);
FILE uart_err = FDEV_SETUP_STREAM((putc_type)uart_putc_now, NULL, _FDEV_SETUP_WRITE);

void setup_stdio(void)
{
	do_uart_init();
	
	//stdin = &uart_io;
	stdout = &uart_io;
	stderr = &uart_err;
}

/* BADISR_vect doesn't work */
ISR(__vector_default)
{
	report_error("Bad IRQ!");
}
