#ifndef FLOW_H
#define FLOW_H

/* Setup */
#ifndef FLOW_INTERNAL_H
typedef void FLOW;
#endif

FLOW *flow_setup(unsigned int rate,
	unsigned short _low, unsigned short _mid, unsigned short _high);
void flow_free(FLOW *);

/* read */
typedef void(*flow_readproc)(unsigned char *buf, unsigned int len);

void flow_reader(FLOW *flow, flow_readproc proc);
void flow_read_buf(FLOW *flow, unsigned char *buf, unsigned int len);


/* write */
typedef int(*flow_writeproc)(unsigned char *buf, unsigned int len);
void flow_writer(FLOW *flow, flow_readproc proc);
void flow_write_buf(FLOW *flow, flow_readproc proc);

void flow_write_idle(FLOW *flow);

/* There is no read_idle procedure because data is supposed to come in
 * continuously. */

#endif /* FLOW_H */
