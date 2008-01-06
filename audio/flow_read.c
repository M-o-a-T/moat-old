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

#include "flow_internal.h"
#include <stdio.h>
#include <malloc.h>
#include <limits.h>

void flow_setup_reader(FLOW_PARAM
                       unsigned int nsync, unsigned int param[R_IDLE])
{
	unsigned int i;
	F_r_sync = nsync;
	for(i=R_IDLE+1; i-- > 0;) {
		F_r_times[i] = flow_rate(f,param[i]);
	}
	if (!F_readbuf)
		F_readbuf = malloc(F_read_max);
}

void flow_reader(FLOW_PARAM
                 flow_readproc proc, void *param)
{
	F_reader = proc;
	F_reader_param = param;
}

static void flow_init(FLOW_PARAM1)
{
	if(F_readlen) {
		if (F_reader)
			(F_reader)(F_reader_param, F_readbuf, F_readlen);
		F_readlen = 0;
	}
	F_byt = 0;
	F_bit = 0;
	F_syn = 0;
	F_qsum = 0;
}

#ifdef F_LOG
void
flow_report(FLOW_PARAM
            unsigned short low, unsigned short high, unsigned short minlen)
{
	if (minlen % 1) minlen++; /* needs to be even, for later */
	F_logbuf = realloc(F_logbuf, sizeof(unsigned short) * minlen);
	F_log_min = minlen;
#define r(x) (int)(F_rate*.000001*x)
	F_log_low = r(low);
	F_log_high = r(high);
#undef r
	F_log_valid = 0;
}

int
flow_read_logging(FLOW_PARAM1) {
	return (F_log_valid == F_log_min);
}
#endif

static inline void
flow_char(FLOW_PARAM
          unsigned char c)
{
	unsigned char ex=0;
	unsigned char hi;

	hi = ((c & 0x80) != 0);
	if(++F_cnt >= F_r_times[R_IDLE])
		ex=1;
	else if(hi == F_lasthi)
		return;
	flow_read_time(
#ifndef FLOW_STANDALONE
	               flow
#endif
	                   , F_cnt, hi);
	F_cnt = 0;
}

void
flow_read_time(FLOW_PARAM
               unsigned int duration, unsigned char hi)
{
	char ex = (duration >= F_r_times[R_IDLE]);

#ifdef F_LOG
#define R(_x) (_x*1000000/F_rate)
	if (F_logbuf && (F_log_valid || hi)) {
		if ((duration >= F_log_low || (F_log_valid > 0 && ++F_log_invalid < 6)) && duration <= F_log_high) {
			if (F_log_valid < F_log_min) {
				F_logbuf[F_log_valid++] = duration;
				if (F_log_valid == F_log_min) {
					unsigned short i;
					for(i=0; i < F_log_min; i++) {
						if (!i) fputs("log ",stderr);
						else if (i & 1) fputc(hi?'_':' ',stderr);
						else fputc(hi?' ':'_',stderr);
						fprintf(stderr,"%lu",R(F_logbuf[i]));
					}
					fprintf(stderr,"%c%lu",hi?' ':'_', R(duration));
				}
			} else {
				fprintf(stderr,"%c%lu",hi?' ':'_', R(duration));
			}
		} else {
			if (F_log_valid == F_log_min) 
				fprintf(stderr,"%c%lu\n",hi?' ':'_', R(duration));
			F_log_valid = 0;
			F_log_invalid = 0;
		}
	}
#undef R
#endif

	if (ex) { /* R_IDLE exceeed, see above */
		if (F_lasthi) /* somebody's sending an always-on? */
			goto init;
		if (F_r_times[R_SPACE+R_MAX+R_ONE] > 
			F_r_times[R_SPACE+R_MAX+R_ZERO])
			F_r_mark_one=1;
		else
			F_r_mark_zero=1;
	} else if (hi) { /* calc space bit */
		if (duration > F_r_times[R_SPACE+R_MIN+R_ONE]
		 && duration < F_r_times[R_SPACE+R_MAX+R_ONE])
			F_r_space_one=1;
		if (duration > F_r_times[R_SPACE+R_MIN+R_ZERO]
		 && duration < F_r_times[R_SPACE+R_MAX+R_ZERO])
			F_r_space_zero=1;
	} else {
		if (duration > F_r_times[R_MARK+R_MIN+R_ONE]
		 && duration < F_r_times[R_MARK+R_MAX+R_ONE])
			F_r_mark_one=1;
		if (duration > F_r_times[R_MARK+R_MIN+R_ZERO]
		 && duration < F_r_times[R_MARK+R_MAX+R_ZERO])
			F_r_mark_zero=1;
	}
	F_lasthi = hi;
	if (!hi && !ex)
		return;
	{
		char r_one=F_r_mark_one+F_r_space_one;
		char r_zero=F_r_mark_zero+F_r_space_zero;

		F_r_mark_one=0;
		F_r_space_one=0;
		F_r_mark_zero=0;
		F_r_space_zero=0;

		if (r_one == r_zero) goto init;
		hi = (r_one > r_zero);
	}

	if (!F_syn) {
		++F_bit;
		if(!hi) return;
		if(F_bit < F_r_sync) return;
		F_bit = 0;
		F_syn=1;
		return;
	}
	if(F_bit < F_bits) {
		if (F_msb)
			F_byt = (F_byt<<1) | hi;
		else {
			if(hi)
				F_byt |= (1<<F_bit);
		}
		F_bit++;
		if (F_parity || F_bit < F_bits)
			return;

	} else if(F_parity) {
		unsigned char par;
		switch(F_parity) {
		case P_MARK:
			if (!hi) goto init;
			break;
		case P_SPACE:
			if (hi) goto init;
			break;
		default:
			par = F_byt;
			par ^= par >> 4;
			par ^= par >> 2;
			par ^= par >> 1;
			if (F_parity == P_EVEN) {
				if((par&1) == !hi)
					goto init;
			} else {
				if((par&1) == hi)
					goto init;
			}
		}
	}
	if(F_readlen >= F_read_max)
		goto init;
	F_readbuf[F_readlen++] = F_byt;
	F_byt=0;
	F_bit=0;
	if(!ex) return;

init:
	flow_init(
#ifndef FLOW_STANDALONE
              flow
#endif
	              );
}


void
flow_read_buf(FLOW_PARAM
              const unsigned char *buf, unsigned int len)
{
	while(len--)
		flow_char(flow, *buf++);
}



