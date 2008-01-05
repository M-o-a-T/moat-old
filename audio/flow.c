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

FLOW *flow_setup(unsigned int rate, unsigned int maxlen, unsigned char bits, 
                 unsigned char parity, unsigned char msb)
{
	FLOW *f = malloc(sizeof(*f));
	if (!f) return NULL;
	memset(f,0,sizeof(*f));

	f->rate = rate;
	f->bits = bits;
	f->parity = parity;
	f->msb = msb;
	f->read_max = maxlen;

	gettimeofday(&f->last_sent, NULL);

	return f;
}

void flow_free(FLOW *f)
{
	if(!f) return;
	free(f->readbuf);
	free(f->sendbuf);
	free(f->fillbuf);
	free(f->logbuf);
	free(f);
}
