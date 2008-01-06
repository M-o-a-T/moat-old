/*
 *  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
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

#ifndef FLOW_INTERNAL_H
#define FLOW_INTERNAL_H

struct _FLOW;
typedef struct _FLOW FLOW;

#ifdef FLOW_STANDALONE /* marker "do we need a 'struct FLOW *flow'? */
#error FLOW_STANDALONE and flow_internal.h do not mix
#endif

#include "flow.h"

#include <time.h>
#include <sys/time.h>

#define flow_rate(f,x) (int)(F_rate*x/1000000)

/**
 * Analyze incoming 868.35MHz signal.
 *
 * Yes I know, this should be a struct instead of a bunch of global
 * variables. If I ever need to parse more than one audio stream in a
 * single program at the same time (or make it Python-callable),
 * I'll be sure to put that in.
 */

/* All those #define statements are useful for embedded stuff, as the
 * code can be optimized to death if you don't need any parameters.
 */


struct _FLOW {
	unsigned long rate;
#	define F_rate (flow->rate)

	/* width; 4 or 8 bits */
	unsigned char bits;
#	define F_bits (flow->bits)
	char id;
#	define F_id (flow->id)

	/* check bit after each byte */
	unsigned char parity;
#	define F_parity (flow->parity)

	/* most significant bit first? */
	unsigned char msb;
#	define F_msb (flow->msb)

	/* read */
	unsigned int r_times[R_IDLE+1];
#	define F_r_times (flow->r_times)
	unsigned short r_sync;
#	define F_r_sync (flow->r_sync)

	flow_readproc reader;
#	define F_reader (flow->reader)
	void *reader_param;
#	define F_reader_param (flow->reader_param)

	int readlen;
#	define F_readlen (flow->readlen)
	char lasthi;
#	define F_lasthi (flow->lasthi)
	char r_mark_one,r_space_one, r_mark_zero,r_space_zero;
#	define F_r_mark_one (flow->r_mark_one)
#	define F_r_space_one (flow->r_space_one)
#	define F_r_mark_zero (flow->r_mark_zero)
#	define F_r_space_zero (flow->r_space_zero)
	unsigned int cnt;
#	define F_cnt (flow->cnt)
	int qsum;
#	define F_qsum (flow->qsum)

	unsigned char byt,bit;
#	define F_byt (flow->byt)
#	define F_bit (flow->bit)
	char syn;
#	define F_syn (flow->syn)

	unsigned char *readbuf;
#	define F_readbuf (flow->readbuf)
	unsigned int read_max;
#	define F_read_max (flow->read_max)

	/* read tracing */
#define F_LOG
	unsigned short log_low,log_high; /* signal length */
#	define F_log_low (flow->log_low)
#	define F_log_high (flow->log_high)
	unsigned short log_min; /* # valid signals before starting to log */
#	define F_log_min (flow->log_min)
	unsigned short *logbuf;
#	define F_logbuf (flow->logbuf)
	unsigned short log_valid, log_invalid;
#	define F_log_valid (flow->log_valid)
#	define F_log_invalid (flow->log_invalid)

	/* write */
	unsigned int w_times[W_IDLE+1];
#	define F_w_times (flow->w_times)
	unsigned short w_sync;
#	define F_w_sync (flow->w_sync)

	struct timeval last_sent;
#	define F_last_sent (flow->last_sent)
	unsigned long bytes_sent; /* never more than "rate" */
#	define F_bytes_sent (flow->bytes_sent)

	flow_writeproc writer;
#	define F_writer (flow->writer)
	void *writer_param;
#	define F_writer_param (flow->writer_param)

};


#endif
