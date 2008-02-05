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

struct _task_head;
typedef void (*task_proc)(struct _task_head *);

typedef struct _task_head {
	struct _task_head *next;
	uint16_t delay; /* for a delayed job */

	task_proc proc;
} task_head;

#define TASK_HEAD(_proc) { .proc = _proc, .next = NULL }

void _queue_task(task_head *task); /* call with IRQ disabled */
static inline void queue_task(task_head *task)
{
	cli();
	_queue_task(task);
	sei();
}

void dequeue_task(task_head *task);

unsigned char run_tasks(void);

#endif /* QTASK_H */
