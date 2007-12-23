#include "flow_internal.h"

void flow_reader(FLOW *f, flow_readproc proc, void *param)
{
	f->reader = proc;
	f->reader_param = param;
}

#include <stdio.h>
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

static inline void flow_char(FLOW *f, unsigned char c)
{
	int hi;

	hi = ((c & 0x80) != 0);
	if(hi == f->lasthi) {
		if (f->cnt > f->high) {
			if (f->readlen) {
				flow_init(f);
				f->cnt = f->high+1;
			}
		} else {
			f->cnt++;
		}
		return;
	}
	f->lasthi = hi;
	if (hi) {
		f->cnt = 0;
		return;
	}
	if(f->cnt < f->low || f->cnt > f->high)
		goto init;
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



