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

static void
run_task_later(task_head *dummy)
{
	task_head *tp = head_usec;

	assert(tp, "RTL head?");
	DBGS("TR %x is %u",tp,tp->delay);
	if(tp->delay > 255) {
		tp->delay -= 255;
		DBGS("TR now %u",tp->delay);
	} else {
		tp->delay = 0;
		while(tp) {
			task_head *tn = tp->next;
			tp->next = NULL;
			DBGS("TR run %x",tp);
			queue_task(tp);
			tp = tn;
			if(tp->delay > 0)
				break;
		}
		head_usec = tp;
		DBGS("TR head %x",tp);
	}
	setup_delay_timer();
}

void setup_delay_timer()
{
	unsigned int delay;
	unsigned char sreg = SREG;

	if(!head_usec) {
		clear_delay_timer();
		return;
	}
	delay = head_usec->delay;
	//DBGS("setup dly %u",delay);
	if(delay > 255)
		delay = 255;

	cli();
	PRR &= ~_BV(PRTIM2);
	TCCR2B = 4; /* prescale 64x */

	TIFR2 |= _BV(TOV2);
	TCNT2 = -delay; /* counting up -- time until wrap-around */
	TIMSK2 |= _BV(TOIE2);

	SREG = sreg;
}

void clear_delay_timer(void)
{
	//DBG("clear dly");
	TIMSK2 &= ~_BV(TOIE2);
	TCCR2B = 0; /* off */
	PRR |= _BV(PRTIM2);
}

static task_head timer_task = TASK_HEAD(run_task_later);

volatile unsigned char do_qtask = 0;
ISR(SIG_OVERFLOW2)
{
	TIMSK2 &= ~_BV(TOIE2);
	_queue_task(&timer_task);
}
void check_do_qtask(void)
{
	if(do_qtask) {
		do_qtask = 0;
		queue_task(&timer_task);
	}
}

void _queue_task_later(task_head *task, uint16_t delay)
{
	unsigned char do_setup = FALSE;
	assert (!task->delay,"QTL again");
	if(delay == 0) {
		DBG("LTN");
		queue_task(task);
		return;
	}
	cli();
	if(TIMSK2 & _BV(TOIE2)) {
		unsigned char tn = TCNT2;
		TIMSK2 &= ~_BV(TOIE2);
		sei();
		assert(head_usec,"QTL noHead");
		DBGS("QTL first %x %u  at %u",head_usec,head_usec->delay,tn);

		if(head_usec->delay > 255) {
			head_usec->delay -= tn;
		} else {
			head_usec->delay = (unsigned char)-tn;
		}
		do_setup = TRUE;
	} else {
		sei();
		if(head_usec)
			DBGS("QTL_first %x %u",head_usec,head_usec->delay);
		else
			DBG("QTL_first empty");
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
	*tp = task;
	task->delay = delay;
	if(do_setup || head_usec->next == NULL)
		setup_delay_timer();
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
		DBG("TPM");
		queue_task(tp);
		tp = tn;
	}
	head_msec = tp;
	if(tp)
		queue_task_usec(&msec_task,THOUSAND);
}


void queue_task_msec(task_head *task, uint16_t delay)
{
	DBGS("ma:%x %d",task,delay);
#ifndef TESTING
	if(delay < 10) {
		DBG("mb");
		queue_task_usec(task, delay*1000);
		DBG("mc");
		return;
	}
#endif /* TESTING */
	DBG("md");

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
		DBG("TPS");
		queue_task(tp);
		tp = tn;
	}
	head_sec = tp;
	if(tp)
		queue_task_msec(&sec_task,THOUSAND);
}


void queue_task_sec(task_head *task, uint16_t delay)
{
	DBGS("sa:%x %d",task,delay);
#ifndef TESTING
	if(delay < 10) {
		DBG("sb");
		queue_task_msec(task, delay*1000);
		DBG("sc");
		return;
	}
#endif /* TESTING */
	DBG("sd");

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
