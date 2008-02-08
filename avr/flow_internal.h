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
 * This header defines misc flow stuff.
 */

#ifndef FLOW_INTERNAL_H
#define FLOW_INTERNAL_H

#define FLOW_STANDALONE
#include "qtask.h"
#include "flow.h"
#include "flow_data.h"

#define STATIC static
#ifdef FLOW_DATA
#define EXTERN 
#else
#define EXTERN extern
#endif

struct _flow_head;

typedef struct _flow_head {
	/* chain ptr */
	struct _flow_head *next;

	/* Initialize internal data */
	int (*write_init)(void);

	/* Generate a hi/low timing sequence */
	void (*write_step)(unsigned int *hi, unsigned int *lo);

	/* time after sending */
	unsigned short write_idle;

	/* Feed a read time delta into the reader */
	void (*read_time)(unsigned int duration, unsigned char hi);

	/* Check if the reader is synced (or trying to!) */
	unsigned char (*read_at_work)();

	/* The timer has been running for too long */
	void (*read_reset)();

	char type; // 'f' for fs20
} flow_head;

EXTERN enum { FW_idle, FW_sync, FW_data } F_writer_state;
EXTERN unsigned char F_writer_byte;
EXTERN unsigned char F_writer_bit;
EXTERN unsigned char F_writer_parity;

EXTERN write_head *F_writer_task;
/* 1 byte type, 1 byte length, data */
#define F_writer_data (F_writer_task->data)
#define F_writer_len  (F_writer_task->len)
#define F_writer_type (F_writer_task->type)

#endif /* FLOW_INTERNAL_H */
