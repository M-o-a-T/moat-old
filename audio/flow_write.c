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

#include <stdio.h>
#ifdef FLOW_STANDALONE
#include <stdlib.h>
#else
#include <malloc.h>
#endif
#include <string.h>
#include <errno.h>
#include "flow_internal.h"

/* Note that care must be taken to keep accurate track of how many bytes
 * per second need to get sent, given that the time a byte requires
 * processing for cannot be represented accurately.
 *
 * Not if you have a sample rate of 44100 bytes/sec, anyway.
 *
 * This code assumes, however, that the sample rate itself
 * *can* be thus represented.
 */

#ifndef FLOW_STANDALONE
void
flow_setup_writer(FLOW_PARAM
                  unsigned int nsync, unsigned int param[W_IDLE])
{
	unsigned int i;
	F_w_sync = nsync;
	for(i=W_IDLE+1; i-- > 0;) {
		F_w_times[i] = flow_rate(f,param[i]);
	}
}

void
flow_writer(FLOW_PARAM
            flow_writeproc proc, void *param)
{
	F_writer = proc;
	F_writer_param = param;
}
#endif

STATIC int
flow_write_init(FLOW_PARAM1)
{
	if(F_writer_state != FW_idle)
		return -1;
	F_writer_state = FW_sync;
	F_writer_byte = 0;
	F_writer_bit = 0;
	F_writer_parity = 0;
	return 0;;
}

#ifndef FLOW_STANDALONE
STATIC int
flow_write_buf(FLOW_PARAM
               unsigned char *data, unsigned int len)
{
	int res = flow_write_init(FLOW_ARG1);
	if (res) return res;

#ifndef FLOW_STANDALONE
	F_writer_data = data;
	F_writer_len = len;
	if(F_writer) {
		unsigned int t1,t2;
		do {
			flow_write_step(FLOW_ARG &t1,&t2);
			F_writer(F_writer_param, t1,t2);
		} while (t1 != 0);
		F_writer(F_writer_param, 0,F_w_times[W_IDLE]);
	}
#endif
	return 0;
}
#endif

STATIC void
flow_write_step(FLOW_PARAM
                unsigned int *hi, unsigned int *lo)
{
#define RI() do { \
	*hi=0; \
	*lo=F_w_times[W_IDLE]; \
	return; \
} while(0)
#define R(_x) do { \
	if(_x) { \
		*hi=F_w_times[W_MARK|W_ONE]; \
		*lo=F_w_times[W_SPACE|W_ONE]; \
	} else { \
		*hi=F_w_times[W_MARK|W_ZERO]; \
		*lo=F_w_times[W_SPACE|W_ZERO]; \
	} \
	return; \
} while(0)

	if(F_writer_state == FW_idle) {
		//DBG("W idle");
		RI();
	} else if(F_writer_state == FW_sync) {
		F_writer_bit ++;
		if (F_writer_bit > F_w_sync) {
			F_writer_state = FW_data;
			F_writer_bit = 0;
			//DBG("W last_syn");
			R(1);
		} else {
			//DBG("W syn");
			R(0);
		}
	} else if(F_writer_byte >= F_writer_len) {
		F_writer_state = FW_idle;
		//DBG("W end_bit");
		R(0);
	} else if(F_writer_bit >= F_bits) {
		//DBG("W parity");
		F_writer_bit ++;
		unsigned char bit;
		switch(F_parity) {
		default:
		case P_NONE:
			flow_error("Oops Parity");
			*hi=0; *lo=0;
			return;
		case P_MARK:  bit=1; break;
		case P_SPACE: bit=0; break;
		case P_ODD:   bit=F_writer_parity^1; break;
		case P_EVEN:  bit=F_writer_parity; break;
		}
		F_writer_byte++;
		F_writer_bit=0;
		F_writer_parity=0;
		R(bit & 1);
	} else {
		//DBGS("W bit %u/%u",F_writer_byte,F_writer_bit);
		unsigned char bit;
		if(F_msb)
			bit = F_writer_data[F_writer_byte] >> (F_bits-1-F_writer_bit);
		else
			bit = F_writer_data[F_writer_byte] >> F_writer_bit;
		F_writer_bit ++;
		F_writer_parity ^= bit;

		if(F_writer_bit == F_bits && F_writer_parity == P_NONE) {
			F_writer_byte++;
			F_writer_bit=0;
			F_writer_parity=0;
		}
		R(bit & 1);
	}
}


