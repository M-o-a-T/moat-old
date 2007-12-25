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

#ifndef FLOW_H
#define FLOW_H

/* Setup */
#ifndef FLOW_INTERNAL_H
typedef void FLOW;
#endif

FLOW *flow_setup(unsigned int rate,
	unsigned short _low, unsigned short _l, unsigned short _mid, unsigned short _h, unsigned short _high);
void flow_free(FLOW *);

/* read */
typedef void(*flow_readproc)(void *param, unsigned char *buf, unsigned int len);

void flow_reader(FLOW *flow, flow_readproc proc, void *param);
void flow_read_buf(FLOW *flow, unsigned char *buf, unsigned int len);

void flow_report(FLOW *flow, unsigned short low, unsigned short high, unsigned short minlen);
int flow_read_logging(FLOW *flow);

/* write */
typedef int(*flow_writeproc)(void *param, unsigned char *buf, unsigned int len);

void flow_writer(FLOW *flow, flow_writeproc proc, void *param);

int flow_write_buf(FLOW *flow, unsigned char *data, unsigned int len);
int flow_write_idle(FLOW *flow);
/* These return -1/errno when the external write fails, or something else
 * goes wrong*/

/*
 * There is no read_idle procedure because data is supposed to come in
 * continuously.
 */

#endif /* FLOW_H */
