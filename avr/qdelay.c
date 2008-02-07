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
 * This header defines a task queue for AVR.
 */

#include "local.h"

#include <stdlib.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include "qtask.h"
#include "qdelay.h"
#include "util.h"
#include "assert.h"

task_head *head_usec;
task_head *head_msec;
task_head *head_sec;

void setup_delay_timer();
void clear_delay_timer();

//#define TESTING
#ifdef TESTING
#define THOUSAND 10
#else
#define THOUSAND 1000
#endif

volatile unsigned int offset = 0;

void queue_task_sync(void)
{
	unsigned char tn = TCNT2;
	TCNT2 = 0;
	tn = OCR2A - tn;
	if (head_usec)
		head_usec->delay -= tn;
	OCR2A = tn;
}

static void run_task_later(task_head *dummy);

static task_head timer_task = TASK_HEAD(run_task_later);

static void
run_task_later(task_head *dummy)
{
	assert(!(TIMSK2 & _BV(OCIE2A)),"RTL called with active timer");
	task_head *tp = head_usec;

	if(!tp) {
		clear_delay_timer();
		return;
	}

	while(tp) {
		if(tp->delay > offset)
			break;

		offset -= tp->delay;
		tp->delay = 0;

		task_head *tn = tp->next;
		tp->next = NULL;
		//DBGS("TR run %x",tp);
		queue_task(tp);

		tp = tn;
	}
	if(tp) {
		tp->delay -= offset;
		offset = 0;
	}
	cli();
	head_usec = tp;

	/* now setup the timeout */
	unsigned int delay;
	if(head_usec) {
		delay = head_usec->delay;
		if(delay > 255)
			delay = 255;
	} else
		delay = (255 < DLY(50)) ? 255 : DLY(50);
	//DBGS("setup dly %u",delay);

	PRR &= ~_BV(PRTIM2);
	OCR2A = delay;
	if(TCCR2B & 0x07) { /* timer running? */
		if(TCNT2 >= delay) {
			_queue_task_if(&timer_task);
			sei();
			return;
		}
	} else {
		TCCR2A = 0x02; /* CTC mode */
		TCCR2B = 4; /* prescale 64x */
		TCNT2 = 0;
	}
	TIFR2 |= _BV(OCF2B);
	TIMSK2 |= _BV(OCIE2A);

	sei();
}

void clear_delay_timer(void)
{
	//DBG("clear dly");
	TIMSK2 &= ~_BV(OCIE2A);
	TCCR2B = 0; /* off */
	PRR |= _BV(PRTIM2);
	offset = 0;
}

ISR(TIMER2_COMPA_vect)
{
	TIMSK2 &= ~_BV(OCIE2A);
	offset += OCR2A;
	OCR2A = 0xFF;
	//DBG("Q RTL");
	_queue_task_if(&timer_task);
}

void _queue_task_later(task_head *task, uint16_t delay)
{
	unsigned char do_setup = FALSE;
	assert (!task->delay,"QTL again");
	if(delay == 0) {
		//DBG("LTN");
		queue_task(task);
		return;
	}
	cli();
	if(TIMSK2 & _BV(OCIE2A)) {
		TIMSK2 &= ~_BV(OCIE2A);
		unsigned char tn = TCNT2 || OCR2A;
		OCR2A = 0xFF;
		TCNT2 = 0;
		//DBGS("OFF %u - %u (old +%u)",delay, tn,offset);
		offset += tn;
		sei();
		//DBGS("QTL first %x %u  at %u",head_usec,head_usec->delay,tn);
	} else {
		//DBGS("OFF %u - old +%u",delay, offset);
		sei();
//		if(head_usec)
//			DBGS("QTL_first %x %u",head_usec,head_usec->delay);
//		else
//			DBG("QTL_first empty");
	}

	task_head **tp = &head_usec;
	task_head *tn = *tp;
	while(tn) {
		if (tn->delay > delay) {
			tn->delay -= delay;
			break;
		}
		delay -= tn->delay;
		tp = &(tn->next);
		tn = *tp;
	}
	task->next = tn;
	task->delay = delay;
	*tp = task;
	assert(head_usec,"RTL no head?");

	queue_task_if(&timer_task);
}

/* miliseconds */

void run_task_msec(task_head *dummy);

static task_head msec_task = TASK_HEAD(run_task_msec);
void run_task_msec(task_head *dummy)
{
	task_head *tp = head_msec;
	tp->delay -= 1;
	while(tp) {
		if(tp->delay > 0)
			break;
		task_head *tn = tp->next;
		tp->next = NULL;
		//DBG("TPM");
		queue_task(tp);
		tp = tn;
	}
	head_msec = tp;
	if(tp)
		queue_task_usec(&msec_task,THOUSAND);
}


void queue_task_msec(task_head *task, uint16_t delay)
{
	if(delay < 65535/RDLY(1000)) {
		queue_task_usec(task, delay*1000);
		return;
	}

	task_head **tp = &head_msec;
	task_head *tn = *tp;
	if(!tn)
		queue_task_usec(&msec_task,THOUSAND);

	while(tn) {
		if (tn->delay > delay) {
			tn->delay -= delay;
			break;
		}
		delay -= tn->delay;
		tp = &(tn->next);
		tn = *tp;
	}
	task->next = tn;
	*tp = task;
	task->delay = delay;
}

/* seconds */

void run_task_sec(task_head *dummy);

static task_head sec_task = TASK_HEAD(run_task_sec);
void run_task_sec(task_head *dummy)
{
	task_head *tp = head_sec;
	tp->delay -= 1;
	while(tp) {
		if(tp->delay > 0)
			break;
		task_head *tn = tp->next;
		tp->next = NULL;
		//DBG("TPS");
		queue_task(tp);
		tp = tn;
	}
	head_sec = tp;
	if(tp)
		queue_task_msec(&sec_task,THOUSAND);
}


void queue_task_sec(task_head *task, uint16_t delay)
{
	if(delay <= 65535/1000) {
		queue_task_msec(task, delay*1000);
		return;
	}

	task_head **tp = &head_sec;
	task_head *tn = *tp;
	if(!tn)
		queue_task_msec(&sec_task,THOUSAND);

	while(tn) {
		if (tn->delay > delay) {
			tn->delay -= delay;
			break;
		}
		delay -= tn->delay;
		tp = &(tn->next);
		tn = *tp;
	}
	task->next = tn;
	*tp = task;
	task->delay = delay;
}
