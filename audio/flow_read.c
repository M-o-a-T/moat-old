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

void flow_setup_reader(FLOW *f, unsigned int nsync, unsigned int param[R_IDLE])
{
	unsigned int i;
	f->r_sync = nsync;
	for(i=R_IDLE+1; i-- > 0;) {
		f->r_times[i] = flow_rate(f,param[i]);
	}
	if (!f->readbuf)
		f->readbuf = malloc(f->read_max);
}

void flow_reader(FLOW *f, flow_readproc proc, void *param)
{
	f->reader = proc;
	f->reader_param = param;
}

static void flow_init(FLOW *f)
{
	if(f->readlen) {
		if (f->reader)
			(f->reader)(f->reader_param, f->readbuf, f->readlen);
		f->readlen = 0;
	}
	f->byt = 0;
	f->bit = 0;
	f->syn = 0;
	f->qsum = 0;
}

void flow_report(FLOW *f, unsigned short low, unsigned short high, unsigned short minlen)
{
	if (minlen % 1) minlen++; /* needs to be even, for later */
	f->logbuf = realloc(f->logbuf, sizeof(unsigned short) * minlen);
	f->log_min = minlen;
#define r(x) (int)(f->rate*.0001*x)
	f->log_low = r(low);
	f->log_high = r(high);
#undef r
	f->log_valid = 0;
}

int flow_read_logging(FLOW *f) {
	return (f->log_valid == f->log_min);
}

static inline void flow_char(FLOW *f, unsigned char c)
{
	unsigned char hi;
	unsigned char ex=0;

	hi = ((c & 0x80) != 0);
	if(++f->cnt >= f->r_times[R_IDLE])
		ex=1;
	else if(hi == f->lasthi)
		return;

#define R(_x) (_x*1000000/f->rate)
	if (f->logbuf && (f->log_valid || hi)) {
		if ((f->cnt >= f->log_low || (f->log_valid > 0 && ++f->log_invalid < 6)) && f->cnt <= f->log_high) {
			if (f->log_valid < f->log_min) {
				f->logbuf[f->log_valid++] = f->cnt;
				if (f->log_valid == f->log_min) {
					unsigned short i;
					for(i=0; i < f->log_min; i++) {
						if (!i) fputs("log ",stderr);
						else if (i & 1) fputc(hi?'_':' ',stderr);
						else fputc(hi?' ':'_',stderr);
						fprintf(stderr,"%lu",R(f->logbuf[i]));
					}
					fprintf(stderr,"%c%lu",hi?' ':'_', R(f->cnt));
				}
			} else {
				fprintf(stderr,"%c%lu",hi?' ':'_', R(f->cnt));
			}
		} else {
			if (f->log_valid == f->log_min) 
				fprintf(stderr,"%c%lu\n",hi?' ':'_', R(f->cnt));
			f->log_valid = 0;
			f->log_invalid = 0;
		}
	}
#undef R

	if (ex) { /* R_IDLE exceeed, see above */
		if (f->lasthi) /* somebody's sending an always-on? */
			goto init;
		if (f->r_times[R_SPACE+R_MAX+R_ONE] > 
			f->r_times[R_SPACE+R_MAX+R_ZERO])
			f->r_mark_one=1;
		else
			f->r_mark_zero=1;
	} else if (hi) { /* calc space bit */
		if (f->cnt > f->r_times[R_SPACE+R_MIN+R_ONE]
		 && f->cnt < f->r_times[R_SPACE+R_MAX+R_ONE])
			f->r_space_one=1;
		if (f->cnt > f->r_times[R_SPACE+R_MIN+R_ZERO]
		 && f->cnt < f->r_times[R_SPACE+R_MAX+R_ZERO])
			f->r_space_zero=1;
	} else {
		if (f->cnt > f->r_times[R_MARK+R_MIN+R_ONE]
		 && f->cnt < f->r_times[R_MARK+R_MAX+R_ONE])
			f->r_mark_one=1;
		if (f->cnt > f->r_times[R_MARK+R_MIN+R_ZERO]
		 && f->cnt < f->r_times[R_MARK+R_MAX+R_ZERO])
			f->r_mark_zero=1;
	}
	f->lasthi = hi;
	if (!hi && !ex) {
		f->cnt = 0;
		return;
	}
	{
		char r_one=f->r_mark_one+f->r_space_one;
		char r_zero=f->r_mark_zero+f->r_space_zero;

		f->r_mark_one=0;
		f->r_space_one=0;
		f->r_mark_zero=0;
		f->r_space_zero=0;

		if (r_one == r_zero) goto init;
		hi = (r_one > r_zero);
	}
	f->cnt = 0;

	if (!f->syn) {
		++f->bit;
		if(!hi) return;
		if(f->bit < f->r_sync) return;
		f->bit = 0;
		f->syn=1;
		return;
	}
	if(++(f->bit) <= f->bits) {
		if (f->msb)
			f->byt = (f->byt<<1) | hi;
		else {
			if(hi)
				f->byt |= (1<<f->bits);
		}
		if (f->parity || f->bit < f->bits)
			return;

	} else if(f->parity) {
		unsigned char par;
		switch(f->parity) {
		case P_MARK:
			if (!hi) goto init;
			break;
		case P_SPACE:
			if (hi) goto init;
			break;
		default:
			par = f->byt;
			par ^= par >> 4;
			par ^= par >> 2;
			par ^= par >> 1;
			if (f->parity == P_EVEN) {
				if((par&1) == !hi)
					goto init;
			} else {
				if((par&1) == hi)
					goto init;
			}
		}
	}
	if(f->readlen >= f->read_max)
		goto init;
	f->readbuf[f->readlen++] = f->byt;
	f->byt=0;
	f->bit=0;
	if(!ex) return;

init:
	flow_init(f);
}


void flow_read_buf(FLOW *flow, const unsigned char *buf, unsigned int len)
{
	while(len--)
		flow_char(flow, *buf++);
}



