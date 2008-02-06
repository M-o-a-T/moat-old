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

int run = 0;

void runit1(task_head *dummy);
void runit10(task_head *dummy);

task_head ts1 = TASK_HEAD(runit1);
task_head ts2 = TASK_HEAD(runit10);

void runit1(task_head *dummy) {
	fprintf(stderr,"%d Test\n",++run);
	queue_task_msec(&ts1,1000);
}

void runit10(task_head *dummy) {
	fprintf(stderr,"%d Test slow\n",++run);

	queue_task_msec(&ts2,9900);
}

int __attribute__((noreturn)) main(void)
{
	setup_stdio();
	fputs_P(PSTR(":Startup\n"),stderr);
	//while(uart_getc() == 0x100);
	fputs_P(PSTR(":*********************************************\n"),stderr);

	queue_task_sec(&ts1,1);
	queue_task_sec(&ts2,10);

	while(1) {
		run_tasks();
	}
}
