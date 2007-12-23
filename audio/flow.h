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
