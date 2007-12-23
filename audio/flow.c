#include <stdio.h>
#include <malloc.h>
#include <string.h>

#include "flow_internal.h"

FLOW *flow_setup(unsigned int rate,
	unsigned short _low, unsigned short _mid, unsigned short _high)
{
	FLOW *f = malloc(sizeof(*f));
	if (!f) return NULL;
	memset(f,0,sizeof(*f));

#define r(x) (int)(rate*.0001*x)
	f->rate = rate;
	f->low = r(_low);
	f->mid = r(_mid);
	f->high = r(_high);
#undef r

	return f;
}

void flow_free(FLOW *f)
{
	if(!f) return;
	free(f);
}
