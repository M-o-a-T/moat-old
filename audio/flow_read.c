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
	f->cnt = 0;
	f->lasthi = 0;
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
	int hi;

	hi = ((c & 0x80) != 0);
	if(hi == f->lasthi) {
		if (f->cnt > f->high) {
			if (f->readlen)
				flow_init(f);
		}
		if(f->cnt < INT_MAX)
			f->cnt++;
		return;
	}
	if (f->logbuf && (f->log_valid || hi)) {
#define R(_x) (_x*100000/f->rate)
		if ((f->cnt >= f->log_low || (f->log_valid > 0 && ++f->log_invalid < 3)) && f->cnt <= f->log_high) {
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
#undef R
	}
	f->lasthi = hi;
	if(f->cnt < f->low || f->cnt > f->high)
		goto init;
	if (hi) {
		f->cnt = 0;
		return;
	}
	hi = (f->cnt >= f->mid);
	f->cnt = 0;

	if (!f->syn) {
		++f->bit;
		if(!hi) return;
		if(f->bit < 6) goto init;
		f->bit = 0;
		f->syn=1;
		return;
	}
	if(++(f->bit) <= 8) {
		f->byt = (f->byt<<1) | hi;
		return;
	}
	unsigned char par = f->byt;
	par ^= par >> 4;
	par ^= par >> 2;
	par ^= par >> 1;
	if((par&1) == !hi)
		goto init;
	if(f->readlen >= FLOWMAX)
		goto init;
	f->readbuf[f->readlen++] = f->byt;
	f->bit=0;
	return;

init:
	flow_init(f);
}


void flow_read_buf(FLOW *flow, unsigned char *buf, unsigned int len)
{
	while(len--)
		flow_char(flow, *buf++);
}



