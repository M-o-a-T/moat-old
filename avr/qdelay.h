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

#ifndef QDELAY_H
#define QDELAY_H

#include "local.h"
#include "qtask.h"
#include <stdlib.h>

#ifdef DEBUGGING
#include "util.h"
#endif

void _queue_task_later(task_head *task, uint16_t delay);
#define DLY(_d) (_d)*(F_CPU/1000000L)/64
#define RDLY(_d) (_d)*64/(F_CPU/1000000L)

#if 0 /* def DEBUGGING */
static inline void
queue_task_usec(task_head *_t, uint16_t _d)
{
	//DBGS("later:%x %d",_t,_d);
	_queue_task_later((_t),DLY(_d));
}
#else
#define queue_task_usec(_t,_d) _queue_task_later((_t),DLY(_d))
#endif

void queue_task_msec(task_head *task, uint16_t delay);
void queue_task_sec(task_head *task, uint16_t delay);

void queue_task_sync(void);
/* Call this from interrupt! to drop accumulated timeouts */

#endif /* QDELAY_H */
