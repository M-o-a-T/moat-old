#include <stdio.h>
#include "flow_in.h"

/**
 * Analyze incoming 868.35MHz signal.
 *
 * Yes I know, this should be a struct instead of a bunch of global
 * variables. If I ever need to parse more than one audio stream in a
 * single program at the same time (or make it Python-callable),
 * I'll be sure to put that in.
 */
static int c;
static int len = 0;
static char hi;
static char lasthi;
static int cnt;
static int qsum;

static unsigned char byt,bit;
static char syn;

static int low,mid,high;

static void flow_init(void)
{
	if(len) {
		putchar('\n'); fflush(stdout);
		len = 0;
	}
	byt = 0;
	bit = 0;
	cnt = 0;
	lasthi = 0;
	hi = 0;
	syn = 0;
	qsum = 0;
}

void flow_setup(unsigned int rate,
	unsigned short _low, unsigned short _mid, unsigned short _high)
{
#define r(x) (int)(rate*.0001*x)
	low = r(_low);
	mid = r(_mid);
	high = r(_high);
#undef r

	flow_init();
}

void flow_char(unsigned char c)
{
	hi = ((c & 0x80) != 0);
	if(hi == lasthi) {
		cnt++;
		return;
	}
	lasthi = hi;
	if (hi) {
		cnt = 0;
		return;
	}
	if(cnt < low || cnt > high)
		goto init;
	hi = (cnt >= mid);
	cnt = 0;

	if (!syn) {
		++bit;
		if(!hi) return;
		if(bit < 6) goto init;
		bit = 0;
		syn=1;
		return;
	}
	if(++bit <= 8) {
		byt = (byt<<1) | hi;
		return;
	}
	unsigned char par = byt ^ (byt >> 4);
	par ^= par >> 2;
	par ^= par >> 1;
	if((par&1) == !hi)
		goto init;
	if(++len > 50)
		goto init;
	printf("%02x",byt);
	bit=0;
	return;

init:
	flow_init();
}

