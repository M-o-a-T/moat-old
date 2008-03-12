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

#ifndef QTASK_H
#define QTASK_H

#include <stdlib.h>
#include <avr/interrupt.h>
#include "assert.h"

#define TASK_MAGIC 0xBEEF

struct _task_head;
typedef void (*task_proc)(struct _task_head *);

typedef struct _task_head {
	struct _task_head *next;
	uint16_t delay; /* for a delayed job */

	task_proc proc;
} task_head;

#define TASK_HEAD(_proc) (task_head) { .proc = _proc, .next = NULL }

void real_queue_task(task_head *task); /* call with IRQ disabled */

#ifdef QTASK_DEBUG
static inline void r_queue_task(task_head *task,char *f,int l)
{
	assert(!(SREG & _BV(SREG_I)),"_queue_task from non-IRQ");
	if(task->delay)
		printf_P(f,l);
	real_queue_task(task);
}
#define _queue_task(x) r_queue_task(x,PSTR(":QTD " __FILE__ ":%d\n"),__LINE__)

static inline void queue_task(task_head *task)
{
	assert(SREG & _BV(SREG_I),"queue_task from IRQ");
	cli();
	PORTD &= _BV(PINB7);
	_queue_task(task);
	PORTD |= _BV(PINB7);
	sei();
}
static inline void x_queue_task_if(task_head *task,char *f,int l)
{
	if(SREG & _BV(SREG_I)) {
		printf_P(f,l);
		report_error("dud");
	}
	assert(!(SREG & _BV(SREG_I)),"_queue_task_if from non-IRQ");
	if(task->delay != TASK_MAGIC) {
		assert(!task->delay,"QueueTask");
		_queue_task(task);
	}
}
#define _queue_task_if(t) x_queue_task_if(t,PSTR(": _qti "__FILE__":%d"),__LINE__)

static inline void xqueue_task_if(task_head *task, char *f,int l)
{
	if(!(SREG & _BV(SREG_I))) {
		printf_P(f,l);
		report_error("dud");
	}
	assert(SREG & _BV(SREG_I),"queue_task_if from IRQ");
	cli();
	PORTD &= _BV(PINB7);
	_queue_task_if(task);
	PORTD |= _BV(PINB7);
	sei();
}
#define queue_task_if(t) xqueue_task_if(t,PSTR(": _qtn "__FILE__":%d"),__LINE__)


#else


static inline void _queue_task(task_head *task)
{
	assert(!(SREG & _BV(SREG_I)),"_queue_task from non-IRQ");
	real_queue_task(task);
}

static inline void queue_task(task_head *task)
{
	assert(SREG & _BV(SREG_I),"queue_task from IRQ");
	cli();
	PORTD &= _BV(PINB7);
	_queue_task(task);
	PORTD |= _BV(PINB7);
	sei();
}

static inline void _queue_task_if(task_head *task)
{
	assert(!(SREG & _BV(SREG_I)),"_queue_task_if from non-IRQ");
	if(task->delay != TASK_MAGIC) {
		assert(!task->delay,"QueueTask");
		_queue_task(task);
	}
}
static inline void queue_task_if(task_head *task)
{
	assert(SREG & _BV(SREG_I),"queue_task_if from IRQ");
	cli();
	PORTD &= _BV(PINB7);
	_queue_task_if(task);
	PORTD |= _BV(PINB7);
	sei();
}

#endif

void dequeue_task(task_head *task);

unsigned char run_tasks(void);

#endif /* QTASK_H */
