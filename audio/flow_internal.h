/*
 *  Copyright © 2007, Matthias Urlichs <matthias@urlichs.de>
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

#include "flow.h"

#include <time.h>
#include <sys/time.h>

#define flow_rate(f,x) (int)(f->rate*x/1000000)

/**
 * Analyze incoming 868.35MHz signal.
 *
 * Yes I know, this should be a struct instead of a bunch of global
 * variables. If I ever need to parse more than one audio stream in a
 * single program at the same time (or make it Python-callable),
 * I'll be sure to put that in.
 */
struct _FLOW {
	unsigned long rate;

	/* width; 4 or 8 bits */
	unsigned char bits;

	/* check bit after each byte */
	unsigned char parity;

	/* most significant bit first? */
	unsigned char msb;

	/* read */
	unsigned int r_times[R_IDLE+1];
	unsigned short r_sync;

	flow_readproc reader;
	void *reader_param;

	int readlen;
	char lasthi;
	char r_mark_one,r_space_one, r_mark_zero,r_space_zero;
	unsigned int cnt;
	int qsum;

	unsigned char byt,bit;
	char syn;

	unsigned char *readbuf;
	unsigned int read_max;

	/* read tracing */
	unsigned short log_low,log_high; /* signal length */
	unsigned short log_min; /* # valid signals before starting to log */
	unsigned short *logbuf;
	unsigned short log_valid, log_invalid;

	/* write */
	unsigned int w_times[W_IDLE+1];
	unsigned short w_sync;

	struct timeval last_sent;
	unsigned long bytes_sent; /* never more than "rate" */

	flow_writeproc writer;
	void *writer_param;

	unsigned char *sendbuf;
	unsigned int sendbuf_len;
	unsigned int sendbuf_used;

	unsigned char *fillbuf; /* a bunch of zeroes */
	unsigned int fillbuf_len;

	unsigned char blocking;
};


#endif
