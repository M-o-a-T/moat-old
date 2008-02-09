/*
 *  Copyright © 2008, Matthias Urlichs <matthias@urlichs.de>
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

/*
 * This file defines basics for the FS20 writer.
 */

#include <stdlib.h>
#include <stdio.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include "qtask.h"
#include "qdelay.h"
#include "util.h"
#include "assert.h"

#define FLOW_DATA
#include "flow_internal.h"
#include "flow.h"

extern flow_head *flows;

flow_head *flow_proc;

static void send_tx_data(task_head *dummy);
static void next_tx_data(task_head *dummy);
static void fill_tx_buf(task_head *dummy);

static task_head start_tx = TASK_HEAD(send_tx_data);
static task_head next_tx = TASK_HEAD(next_tx_data);
static task_head fill_tx = TASK_HEAD(fill_tx_buf);

write_head *sendq_head;
/* tail is F_writer_task */

#define TX_RING_SIZE 16
#define TX_RING_MASK (TX_RING_SIZE-1)
#if (TX_RING_SIZE & TX_RING_MASK)
#error TX timeout buffer size is not a power of 2
#endif

unsigned char tx_ring_buf[TX_RING_SIZE];
unsigned char tx_ring_head;
unsigned char tx_ring_tail;
unsigned char more_data;

static void
next_tx_data(task_head *dummy)
{
	/* TODO: check if a receiver is receiving something! */
	if(more_data == 2)
		fputs_P(PSTR(":TX buffer underrun\n"),stderr);

	write_head *tn = F_writer_task->next;
	free(F_writer_task);
	F_writer_task = tn;

	if(tn) {
		DBG("Next writer");
		queue_task_if(&start_tx);
	} else {
		sendq_head = NULL;
		//DBG("Turn off writer");
		TCCR0B = 0;
		if(PIND & _BV(PD6))
			TCCR0B |= _BV(FOC0A);
		PRR |= _BV(PRTIM0);
	}
}

static void
fill_tx_buf(task_head *dummy)
{
	unsigned int hi,lo;
	unsigned char tmptx1,tmptx2;
	if(more_data != 1)
		return;
	if(tx_ring_head == tx_ring_tail) {
		fputs_P(PSTR(":TX buffer: ran empty!\n"),stderr);
		more_data=2;
		return;
	}
	tmptx1 = (tx_ring_head+1)&TX_RING_MASK;
	while(tmptx1 != tx_ring_tail) {
		tmptx2 = (tmptx1+1)&TX_RING_MASK;
		if (tmptx2 == tx_ring_tail) {
			break;
		}
		flow_proc->write_step(&hi,&lo);
		if(!hi) {
			//DBG("TxE");
			more_data=0;
			break;
		}
		assert(hi<1024,"HI overflow");
		assert(lo<1024,"LO overflow");
		tx_ring_buf[tmptx1] = hi>>2;
		tx_ring_buf[tmptx2] = lo>>2;
		tx_ring_head = tmptx2;
		tmptx1 = (tmptx2+1)&TX_RING_MASK;
	}
	if(tmptx1 == tx_ring_tail) {
		//DBG("FillBuf limit1");
	}
}

static void
send_tx_data(task_head *dummy)
{
	flow_proc = flows;
	while(flow_proc) {
		if(flow_proc->type == F_writer_type)
			break;
		flow_proc = flow_proc->next;
	}
	if(!flow_proc) {
		//fprintf_P(stderr,PSTR("Unknown type '%c'\n"),F_writer_type);
		fputs_P(PSTR("Unknown type '"),stderr);
		fputc(F_writer_type,stderr);
		fputs_P(PSTR("'\n"),stderr);
		queue_task(&next_tx);
		return;
	}
	//DBGS("Tx %c %u",flow_proc->type,F_writer_len);
	
	unsigned int nhi,nlo;
	flow_proc->write_init();
	flow_proc->write_step(&nhi,&nlo);
	if(!nhi) {
		DBG("TxBroken1");
		queue_task(&next_tx);
		return;
	}
	assert(nhi<1024,"nHI overflow");
	assert(nlo<1024,"nLO overflow");

	//DBG("Tx Setup");
	cli();
	PRR &= ~_BV(PRTIM0);

	TCCR0A = _BV(COM0A0)|_BV(WGM01); /* CTC mode */
	//TCCR0A = _BV(COM0A0)|_BV(WGM01)|_BV(WGM00); /* Fast PWN mode */
#ifdef SLOW
	/* external clock, 2ms tick (see bottom of this file) */
	TCCR0B = _BV(CS02)|_BV(CS01)|_BV(CS00);
	//TCCR0B = _BV(WGM02)|_BV(CS02)|_BV(CS01)|_BV(CS00);
#else
	/* prescale 64x, 4µs/Tick */
	TCCR0B = _BV(CS01)|_BV(CS00);
	//TCCR0B = _BV(WGM02)|_BV(CS01)|_BV(CS00);
#endif
	OCR0A = (nhi>>2)-1;
	TCNT0 = 0;

	TIFR0 |= _BV(OCF0A);
	TIMSK0 |= _BV(OCIE0A);

	tx_ring_buf[1] = nlo >> 2;
	tx_ring_head = 1;
	tx_ring_tail = 0;
	//DBG("Tx Setup Done");
	more_data = 1;
	sei();
	queue_task_if(&fill_tx);
}

void
send_tx(write_head *task) {
	assert(!task->next,"SendFS20 next");

	if(sendq_head) {
		//DBG("Send Q next");
		sendq_head->next = task;
		sendq_head = task;
		return;
	}
	//DBG("Send Q now");
	sendq_head = task;
	F_writer_task = task;
	queue_task_if(&start_tx);
}


ISR(TIMER0_COMPA_vect)
{
	if(tx_ring_head == tx_ring_tail) {
		//DBG("T0 END");
		TIMSK0 &= ~_BV(OCIE0A);
		TCCR0B = 0;
		if(PIND & _BV(PD6)) {
			TCCR0B |= _BV(FOC0A);
			fputs_P(PSTR(":Tx on after send!\n"),stderr);
		}
		if(more_data == 1)
			more_data = 2;
		queue_task_usec(&next_tx, flow_proc->write_idle);
	}
	unsigned char tmptx = (tx_ring_tail+1) & TX_RING_MASK;
	OCR0A = tx_ring_buf[tmptx];
	//DBGS("T0 %u",tx_ring_buf[tmptx]);
	tx_ring_tail = tmptx;
	if(!((tmptx ^ tx_ring_head) & (TX_RING_MASK>>1))) {
		//DBG("T0 QF");
		_queue_task_if(&fill_tx);
	}
}

void tx_init(void) __attribute__((naked)) __attribute__((section(".init3")));
void tx_init(void)
{
	PORTD &=~ _BV(PD6);
	DDRD |= _BV (PD6);
#ifdef SLOW
	PORTD &= ~_BV(PD4);
	DDRD |= _BV (PD4);
#endif
}

#ifdef SLOW
static void flip_tx_clock(task_head *dummy);
task_head tx_clock = TASK_HEAD(flip_tx_clock);
static void flip_tx_clock(task_head *dummy)
{
	PORTD ^= _BV(PD4);
	queue_task_msec(&tx_clock,1);
}
#endif
