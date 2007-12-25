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

#include <stdio.h>
#include <malloc.h>
#include <string.h>
#include <sys/time.h>

#include "flow_internal.h"

FLOW *flow_setup(unsigned int rate,
	unsigned short _low, unsigned short _l, unsigned short _mid, unsigned short _h, unsigned short _high)
{
	FLOW *f = malloc(sizeof(*f));
	if (!f) return NULL;
	memset(f,0,sizeof(*f));

#define r(x) (int)(rate*.0001*x)
	f->rate = rate;
	f->low = r(_low);
	f->mid = r(_mid);
	f->high = r(_high);

	f->s_zero = r(_l);
	f->s_one = r(_h);
#undef r
	gettimeofday(&f->last_sent, NULL);

	return f;
}

void flow_free(FLOW *f)
{
	if(!f) return;
	free(f->sendbuf);
	free(f->fillbuf);
	free(f->logbuf);
	free(f);
}
