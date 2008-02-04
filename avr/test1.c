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
 * Test program(s).
 */

#include <avr/pgmspace.h>
#include <stdio.h>
#include "uart.h"
#include "qtask.h"
#include "qdelay.h"
#include "util.h"

volatile char doit=1;
int run = 0;

void runit(unsigned int dummy) {
	//uart_puti(++run);
	//uart_puts_p(PSTR(" Test123\n"));
	fprintf(stderr,"%d Test\n",++run);

	doit=1;
}

task_head ts = TASK_HEAD(runit);

extern void check_do_qtask(void);

int __attribute__((noreturn)) main(void)
{
	setup_stdio();
	fputs_P(PSTR(":Startup\n"),stderr);
	fputs_P(PSTR(":*********************************************\n"),stderr);
	//while(uart_getc() == 0x100);
	while(1) {
		if(doit) {
			doit=0;
			queue_task_sec(&ts,1);
		}
		run_tasks();
		check_do_qtask();
	}
}
