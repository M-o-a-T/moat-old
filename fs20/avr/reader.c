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
extern flow_head em_head;

flow_head *flows;

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
	OV_NO, OV_YES, OV_FIRST=5, OV_RESET,
	} overflow = OV_FIRST;
static unsigned short last_icr;
static unsigned short this_icr;

static void do_times(task_head *dummy);
static task_head times_task = TASK_HEAD(do_times);

static void do_reset1(task_head *dummy);
static task_head reset1_task = TASK_HEAD(do_reset1);

static void do_reset2(task_head *dummy);
static task_head reset2_task = TASK_HEAD(do_reset2);

static void do_reset(void);

static unsigned short w1t,w2t;
static void do_times(task_head *dummy)
{
	w1t=TCNT1;
	unsigned char hi = (PINB & _BV(PB0)) ? 1 : 0;
	switch(overflow)
	{
	default:
		DBGS("?? rx times exit:%d",overflow);
		return;
	case OV_NO:
	case OV_YES:
		break;
	case OV_RESET:
	case OV_FIRST:
		return;
	}

	unsigned short icr = this_icr;
#ifdef SLOW
	icr <<= 2; /* undo the shift from the sender */
#else
	icr >>= 1; /* clock is .5µs, we want µs */
#endif
	//DBGS("Time %u: %d", icr, hi);
	flow_head *fp;
	for(fp=flows;fp;fp=fp->next) {
		fp->read_time(icr,hi);
	}
	w2t = TCNT1;
}

static void do_reset(void)
{
	switch(overflow)
	{
	case OV_RESET:
		DBGS("No Reset, %d",overflow);
		return;
	default:
		break;
	}
	//DBGS("Reset, %d",overflow);
	TIMSK1 &= ~(_BV(ICIE1)|_BV(OCIE1A));
	overflow = OV_RESET;
	_queue_task(&reset1_task);
}
static void do_reset1(task_head *dummy)
{
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
	TCCR1B |= _BV(ICES1);
	overflow = OV_FIRST;
	//DBG("reset done");
	sei();
}

#ifdef SLOW
#define OCR_INCR1 50
#define OCR_INCR2 1000
#else
#define OCR_INCR1 200
#define OCR_INCR2 5000
#endif

ISR(TIMER1_CAPT_vect)
{
	unsigned short icr = ICR1;
	this_icr = icr-last_icr;
	TCCR1B ^= _BV(ICES1);
	switch(overflow) {
	case OV_FIRST:
		TIMSK1 |= _BV(OCIE1A);
		break;
		
	case OV_NO:
		//DBGS("Edge %u  last %u  this %u",icr, last_icr,icr);
		OCR1A = icr + OCR_INCR1;
		TIMSK1 &= ~_BV(ICIE1);
		if(times_task.delay) {
			DBGS("Work is too slow! %x %x  %x %x",last_icr,icr, w1t,w2t);
			do_reset();
			return;
		}

		_queue_task(&times_task);
		break;

	default:
		report_error("Recv Capture ?");
		return;
	}
	OCR1A = icr + OCR_INCR1;
	TIFR1 |= _BV(OCF1A);
	TIMSK1 &= ~_BV(ICIE1);
	last_icr = icr;
	overflow = OV_YES;
}

ISR(TIMER1_COMPA_vect)
{
	if(overflow == OV_YES) {
		if(TIFR1 & _BV(ICF1)) {
			DBG("RX: Change while working");
			do_reset();
			return;
		}
		overflow = OV_NO;
		OCR1A = TCNT1 + OCR_INCR2;
		TIMSK1 |= _BV(ICIE1);
	} else {
		DBG("OCR end");
		do_reset();
	}
}

void rx_chain(void)
{
	static flow_head **fp = &flows;
	*fp = &fs20_head; fp = &((*fp)->next);
	*fp = &em_head; fp = &((*fp)->next);
	*fp = NULL;
}

void rx_init(void) __attribute__((naked)) __attribute__((section(".init3")));
void rx_init(void)
{
	PRR &= ~_BV(PRTIM1);
#ifdef SLOW
	TCCR1B = _BV(ICES1)|_BV(CS12)|_BV(CS11)|_BV(CS10); /* ext input */
#else
	TCCR1B = _BV(ICNC1)|_BV(ICES1)|_BV(CS11); /* 2MHz, noice cancel */
#endif
	TIMSK1 = _BV(ICIE1);
	TIFR1 = _BV(ICF1);
	TCNT1 = 0;
}

