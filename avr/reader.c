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
 * This file defines basics for the FS20 writer.
 */

#include <stdlib.h>
#include <stdio.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include "qtask.h"
#include "qdelay.h"
#include "util.h"
#include "assert.h"

#define FLOW_DATA
#include "flow_internal.h"
#include "flow.h"

extern flow_head fs20_head;
static flow_head *flows;

extern void read_response(task_head *task);

void read_data(unsigned char param, unsigned char *data, unsigned char len)
{
	task_head *task = malloc(sizeof(task_head)+2+len);
	if(!task)
		report_error("out of memory");
	DBGS("read_data: type %c  len %d",param,len);
	*task = TASK_HEAD(read_response);
	unsigned char *buf = (unsigned char *)(task+1);
	*buf++ = param;
	*buf++ = len;
	while(len--)
		*buf++ = *data++;
	queue_task(task);
}


static enum {
	OV_NO, OV_FIRST=5, OV_WORK_NO=10, OV_WORK_OVER
	} overflow = OV_FIRST;
static unsigned short last_icr;
static unsigned short this_icr;

static void do_times(task_head *dummy);
static task_head times_task = TASK_HEAD(do_times);

static void do_times1(task_head *dummy);
static task_head times1_task = TASK_HEAD(do_times1);

static void do_reset(void);

static void do_times(task_head *dummy)
{
	unsigned char hi = (PINB & _BV(PB0)) ? 0 : 1;
	/* inverted because we want the state _before_ the trailing edge */
	switch(overflow)
	{
	default:
		DBG("?? rx times exit1");
		return;
	case OV_WORK_NO:
		{
		unsigned short icr = this_icr;
#ifdef DEBUGGING
		icr <<= 2; /* clock is 4 ticks for some reason */
#else
		icr >>= 1; /* clock is .5µs, we want µs */
#endif
		//DBGS("Time %u: %d", icr, hi);
		flow_head *fp;
		for(fp=flows;fp;fp=fp->next) {
			fp->read_time(icr,hi);
		}
		queue_task_usec(&times1_task,10);
		}
	}
}
static void do_times1(task_head *dummy)
{
	cli();
	if(TIFR1 & _BV(ICF1)) {
		DBG("RX: Change while working");
		do_reset();
		sei();
		return;
	}
	switch(overflow) {
	case OV_WORK_NO:
		overflow = OV_NO;
		break;
	default:
		DBGS("?? rx times exit2 %d",overflow);
		do_reset();
		sei();
		return;
	}
	TIMSK1 |= _BV(ICIE1);
	//DBG("... ready");
	sei();
}

static void do_reset1(task_head *dummy);
static task_head reset1_task = TASK_HEAD(do_reset1);

static void do_reset2(task_head *dummy);
static task_head reset2_task = TASK_HEAD(do_reset2);

static void do_reset(void)
{
	DBG("rcv reset");
	TIMSK1 &= ~(_BV(ICIE1)|_BV(OCIE1A));
	overflow = OV_FIRST;
	_queue_task(&reset1_task);
}
static void do_reset1(task_head *dummy)
{
	DBG("rcv reset1");
	flow_head *fp;
	for(fp=flows;fp;fp=fp->next) {
		fp->read_reset();
	}
	queue_task_msec(&reset2_task,20);
}
static void do_reset2(task_head *dummy)
{
	cli();
	TIFR1 |= _BV(ICF1);
	TIMSK1 |= _BV(ICIE1);
	DBG("reset done");
	sei();
}

ISR(TIMER1_CAPT_vect)
{
	unsigned short icr = ICR1;
	this_icr = icr-last_icr;
	TCCR1B ^= _BV(ICES1);
	switch(overflow) {
	case OV_FIRST:
		DBGS("FirstEdge %u",icr);
		TIFR1 |= _BV(OCF1A);
		TIMSK1 |= _BV(OCIE1A);
		TIMSK1 &= ~_BV(ICIE1);
		OCR1A = icr + 1000;
		overflow = OV_WORK_NO;
		queue_task_usec(&times1_task,10);
		break;
	case OV_NO:
		//DBGS("Edge %u  last %u  this %u",icr, last_icr,this_icr);
		overflow = OV_WORK_NO;
		OCR1A = icr + 1000;
		TIMSK1 &= ~_BV(ICIE1);
		_queue_task(&times_task);
		break;

	case OV_WORK_NO:
		DBGS("EdgeWork %u",icr);
		overflow = OV_WORK_OVER;
		TIMSK1 &= ~(_BV(ICIE1)|_BV(OCIE1A));
		break;
	default:
		report_error(PSTR("Recv Capture ?"));
		break;
	}
	last_icr = icr;
}

ISR(TIMER1_COMPA_vect)
{
	DBG("OCR end");

	do_reset();
}

void rx_chain(void)
{
	flows = &fs20_head;
	fs20_head.next = NULL;
}

void rx_init(void) __attribute__((naked)) __attribute__((section(".init3")));
void rx_init(void)
{
	PRR &= ~_BV(PRTIM1);
#ifdef DEBUGGING
	TCCR1B = _BV(ICES1)|_BV(CS12)|_BV(CS11)|_BV(CS10); /* ext input */
#else
	TCCR1B = _BV(ICNC1)|_BV(ICES1)|_BV(CS11); /* 2MHz, noice cancel */
#endif
	TIMSK1 = _BV(ICIE1);
	TIFR1 = _BV(ICF1);
	TCNT1 = 0;
}

