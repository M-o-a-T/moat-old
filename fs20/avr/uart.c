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

/** This file implements UART handling.
 * For data reception, you need to implement this procedure:
 *
 * void line_reader(task_head *tsk)
 *
 * Each input line (without CRLF, data appended to the struct) is passed
 * to the function. Don't forget to free() 'tsk': it's not done for you.
 *
 * Note that there is no echo and no line editor.
 *
 * The sender will use two stop bits in order to circumvent
 * syncronization issues (missed start bit, wire plugged in
 * after startup) with continuous transfers.
 *
 * This code is based on work by: */

/*************************************************************************
Title:     Interrupt UART library with receive/transmit circular buffers
Author:    Peter Fleury <pfleury@gmx.ch>   http://jump.to/fleury
File:      $Id: uart.c,v 1.5.2.2 2004/02/27 22:00:28 peter Exp $
Software:  AVR-GCC 3.3 
Hardware:  any AVR with built-in UART, 
           tested on AT90S8515 at 4 Mhz and ATmega at 1Mhz
Extension: uart_puti, uart_puthex by M.Thomas 9/2004

DESCRIPTION:
    An interrupt is generated when the UART has finished transmitting or
    receiving a byte. The interrupt handling routines use circular buffers
    for buffering received and transmitted data.
    
    The UART_RX_BUFFER_SIZE and UART_TX_BUFFER_SIZE variables define
    the buffer size in bytes. Note that these variables must be a 
    power of 2.
    
USAGE:
    Refere to the header file uart.h for a description of the routines. 
    See also example test_uart.c.

NOTES:
    Based on Atmel Application Note AVR306
                    
*************************************************************************/
#include <stdlib.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <stdlib.h>
#include <stdio.h>
#include "uart.h"
#include "util.h"
#include "qtask.h"
#include "assert.h"


/*
 *  constants and macros
 */

/* size of RX/TX buffers */
#define UART_RX_BUFFER_MASK ( UART_RX_BUFFER_SIZE - 1)
#define UART_TX_BUFFER_MASK ( UART_TX_BUFFER_SIZE - 1)

#if ( UART_RX_BUFFER_SIZE & UART_RX_BUFFER_MASK )
#error RX buffer size is not a power of 2
#endif
#if ( UART_TX_BUFFER_SIZE & UART_TX_BUFFER_MASK )
#error TX buffer size is not a power of 2
#endif

#if defined(__AVR_AT90S2313__) \
 || defined(__AVR_AT90S4414__) || defined(__AVR_AT90S4434__) \
 || defined(__AVR_AT90S8515__) || defined(__AVR_AT90S8535__)
 /* old AVR classic with one UART */
 #define AT90_UART
 #define UART0_RECEIVE_INTERRUPT   SIG_UART_RECV
 #define UART0_TRANSMIT_INTERRUPT  SIG_UART_DATA
 #define UART0_STATUS   USR
 #define UART0_CONTROL  UCR
 #define UART0_DATA     UDR  
 #define UART0_UDRIE    UDRIE
#elif defined(__AVR_AT90S2333__) || defined(__AVR_AT90S4433__)
 /* old AVR classic with one UART */
 #define AT90_UART
 #define UART0_RECEIVE_INTERRUPT   SIG_UART_RECV
 #define UART0_TRANSMIT_INTERRUPT  SIG_UART_DATA
 #define UART0_STATUS   UCSRA
 #define UART0_CONTROL  UCSRB
 #define UART0_DATA     UDR 
 #define UART0_UDRIE    UDRIE
#elif  defined(__AVR_ATmega8__)  || defined(__AVR_ATmega16__) || defined(__AVR_ATmega32__) \
  || defined(__AVR_ATmega8515__) || defined(__AVR_ATmega8535__) \
  || defined(__AVR_ATmega323__) 
  /* ATMega with one USART */
 #define ATMEGA_USART
 #define UART0_RECEIVE_INTERRUPT   SIG_UART_RECV
 #define UART0_TRANSMIT_INTERRUPT  SIG_UART_DATA
 #define UART0_STATUS   UCSRA
 #define UART0_CONTROL  UCSRB
 #define UART0_DATA     UDR
 #define UART0_UDRIE    UDRIE
#elif defined(__AVR_ATmega163__) 
  /* ATMega163 with one UART */
 #define ATMEGA_UART
 #define UART0_RECEIVE_INTERRUPT   SIG_UART_RECV
 #define UART0_TRANSMIT_INTERRUPT  SIG_UART_DATA
 #define UART0_STATUS   UCSRA
 #define UART0_CONTROL  UCSRB
 #define UART0_DATA     UDR
 #define UART0_UDRIE    UDRIE
#elif defined(__AVR_ATmega162__) || defined(__AVR_ATmega168__)
 /* ATMega with two USART */
 #define ATMEGA_USART0
 #define UART0_RECEIVE_INTERRUPT   SIG_USART_RECV
 #define UART0_TRANSMIT_INTERRUPT  SIG_USART_DATA
 #define UART0_STATUS   UCSR0A
 #define UART0_CONTROL  UCSR0B
 #define UART0_DATA     UDR0
 #define UART0_UDRIE    UDRIE0
#elif defined(__AVR_ATmega64__) || defined(__AVR_ATmega128__) 
 /* ATMega with two USART */
 #define ATMEGA_USART0
 #define UART0_RECEIVE_INTERRUPT   SIG_UART0_RECV
 #define UART0_TRANSMIT_INTERRUPT  SIG_UART0_DATA
 #define UART0_STATUS   UCSR0A
 #define UART0_CONTROL  UCSR0B
 #define UART0_DATA     UDR0
 #define UART0_UDRIE    UDRIE0
#else
 #error "Your CPU is not yet supported by this libaray!"
#endif


/*
 *  module global variables
 */
static volatile unsigned char UART_TxBuf[UART_TX_BUFFER_SIZE];
static volatile unsigned char UART_RxBuf[UART_RX_BUFFER_SIZE];
static volatile unsigned char UART_TxHead;
static volatile unsigned char UART_TxTail;
static volatile unsigned char UART_RxHead;
static volatile unsigned char UART_RxTail;
static volatile unsigned char UART_LastRxError;

void __attribute__((weak)) line_reader(task_head *tsk)
{
	//unsigned char *buf = (unsigned char *)(tsk+1);
	//printf_P(PSTR(".IN: <%s>\n"),buf);
	free(tsk);
}

static volatile unsigned char lines;
static void rcv(task_head *dummy)
{
	while(TRUE) {
		cli();
		if(!lines) {
			sei();
			return;
		}
		lines--;
		sei();

		unsigned char bytes = 1;
		unsigned char tmptail = (UART_RxTail + 1) & UART_RX_BUFFER_MASK;
		//DBGS("Chk %d %d",tmptail,UART_RxBuf[tmptail]);
		while(UART_RxBuf[tmptail]) {
			assert (tmptail != UART_RxTail, "RCV Buffer chaos");
			bytes += 1;
			tmptail = (tmptail + 1) & UART_RX_BUFFER_MASK;
			//DBGS("Chk %d %d",tmptail,UART_RxBuf[tmptail]);
		}
		task_head *tsk = malloc(sizeof(*tsk)+bytes);
		if(!tsk)
			report_error("out of memory");
		unsigned char *buf = (unsigned char *)(tsk+1);
		*tsk = TASK_HEAD(line_reader);

		tmptail = (UART_RxTail + 1) & UART_RX_BUFFER_MASK;
		while(--bytes) {
			*buf++ = UART_RxBuf[tmptail];
			tmptail = (tmptail + 1) & UART_RX_BUFFER_MASK;
		}
		*buf = 0;
		UART_RxTail = tmptail;
		queue_task(tsk);
	}
}

static void rcv_over(task_head *dummy)
{
	cli();
	fputs_P(PSTR("\n-UART buffer full\n"),stderr);
	UART_RxHead = 0; UART_RxTail = 0; lines = 0;
	sei();
}

static void rcv_err(task_head *dummy)
{
	cli();
	fputs_P(PSTR("\n-serial recv error\n"),stderr);
	UART_RxHead = 0; UART_RxTail = 0; lines = 0;
	sei();
}

static task_head recv_task = TASK_HEAD(rcv);
static task_head recv_overflow = TASK_HEAD(rcv_over);
static task_head recv_err = TASK_HEAD(rcv_err);

SIGNAL(UART0_RECEIVE_INTERRUPT)
/*************************************************************************
Function: UART Receive Complete interrupt
Purpose:  called when the UART has received a character
**************************************************************************/
{
    unsigned char tmphead;
    unsigned char data;
    unsigned char usr;
    unsigned char lastRxError;
 
    usr  = UART0_STATUS;
    data = UART0_DATA;
    
#if defined( AT90_UART )
    lastRxError = (usr & (_BV(FE)|_BV(DOR)) );
#elif defined( ATMEGA_USART )
    lastRxError = (usr & (_BV(FE)|_BV(DOR)) );
#elif defined( ATMEGA_USART0 )
    lastRxError = (usr & (_BV(FE0)|_BV(DOR0)) );
#elif defined ( ATMEGA_UART )
    lastRxError = (usr & (_BV(FE)|_BV(DOR)) );
#endif
        
    /* calculate buffer index */ 
    tmphead = ( UART_RxHead + 1) & UART_RX_BUFFER_MASK;
    
    if ( tmphead == UART_RxTail ) {
        /* error: receive buffer overflow */
		_queue_task_if(&recv_overflow);
    } else if(lastRxError) {
		_queue_task_if(&recv_err);
	} else {
        /* store new index */
        /* store received data in buffer */
		if(data == '\n' || data == '\r') {
        	UART_RxBuf[tmphead] = 0;
			lines++;
			_queue_task_if(&recv_task);
		} else
        	UART_RxBuf[tmphead] = data;
        UART_RxHead = tmphead;
    }
    UART_LastRxError = lastRxError;   
}


SIGNAL(UART0_TRANSMIT_INTERRUPT)
/*************************************************************************
Function: UART Data Register Empty interrupt
Purpose:  called when the UART is ready to transmit the next byte
**************************************************************************/
{
    unsigned char tmptail;
    
    if ( UART_TxHead != UART_TxTail) {
        /* calculate and store new buffer index */
        tmptail = (UART_TxTail + 1) & UART_TX_BUFFER_MASK;
        UART_TxTail = tmptail;
        /* get one byte from buffer and write it to UART */
        UART0_DATA = UART_TxBuf[tmptail];  /* start transmission */
    } else {
        /* tx buffer empty, disable UDRE interrupt */
        UART0_CONTROL &= ~_BV(UART0_UDRIE);
    }
}


/*************************************************************************
Function: uart_init()
Purpose:  initialize UART and set baudrate
Input:    baudrate using macro UART_BAUD_SELECT()
Returns:  none
**************************************************************************/
void uart_init(unsigned int baudrate)
{
	static unsigned char UART_inited = 0;
	if(UART_inited) return;
	UART_inited = 1;

    UART_TxHead = 0;
    UART_TxTail = 0;
    UART_RxHead = 0;
    UART_RxTail = 0;
    
#if defined( AT90_UART )
    /* set baud rate */
    UBRR = (unsigned char)baudrate; 

    /* enable UART receiver and transmmitter and receive complete interrupt */
    UART0_CONTROL = _BV(RXCIE)|_BV(RXEN)|BV(TXEN);

#elif defined (ATMEGA_USART)
    /* Set baud rate */
    UBRRH = (unsigned char)(baudrate>>8);
    UBRRL = (unsigned char) baudrate;

    /* Enable USART receiver and transmitter and receive complete interrupt */
    UART0_CONTROL = _BV(RXCIE)|(1<<RXEN)|(1<<TXEN);
    
    /* Set frame format: asynchronous, 8data, no parity, 1stop bit */
    #ifdef URSEL
    UCSRC = (1<<URSEL)|(3<<UCSZ0);
    #else
    UCSRC = (3<<UCSZ0);
    #endif 
    
#elif defined (ATMEGA_USART0 )
    /* Set baud rate */
    UBRR0H = (unsigned char)(baudrate>>8);
    UBRR0L = (unsigned char) baudrate;

    /* Enable USART receiver and transmitter and receive complete interrupt */
    UART0_CONTROL = _BV(RXCIE0)|(1<<RXEN0)|(1<<TXEN0);
    
    /* Set frame format: asynchronous, 8data, no parity, 2stop bit */
    #ifdef URSEL0
    UCSR0C = (1<<URSEL0)|(3<<UCSZ00)|_BV(USBS0);
    #else
    UCSR0C = (3<<UCSZ00)|_BV(USBS0);
    #endif 

#elif defined ( ATMEGA_UART )
    /* set baud rate */
    UBRRHI = (unsigned char)(baudrate>>8);
    UBRR   = (unsigned char) baudrate;

    /* Enable UART receiver and transmitter and receive complete interrupt */
    UART0_CONTROL = _BV(RXCIE)|(1<<RXEN)|(1<<TXEN);

#endif

}/* uart_init */


inline void _uart_putc_now(unsigned char data)
{
	while(!(UCSR0A & _BV(UDRE0))) ;
	UDR0 = data;
	return;
}
inline void uart_putc_now(unsigned char data)
{
	unsigned char sreg = SREG;
	cli();
	if(data == '\n')
		_uart_putc_now('\r');
	_uart_putc_now(data);
	SREG = sreg;
}

/*************************************************************************
Function: uart_putc()
Purpose:  write byte to ringbuffer for transmitting via UART
Input:    byte to be transmitted
Returns:  none          
**************************************************************************/
void uart_putc(unsigned char data)
{
    unsigned char tmphead;

	if(data == '\n')
		uart_putc('\r');
#if 1
    if(!(SREG & _BV(SREG_I))) {
		_uart_putc_now(data);
		return;
	}
#endif

	unsigned char sreg = SREG;
	cli();
	while(1) {
    	tmphead  = (UART_TxHead + 1) & UART_TX_BUFFER_MASK;
    
    	if (tmphead != UART_TxTail) {
			break;
		} else if(sreg & _BV(SREG_I)) {
			/* This test is of course superfluous the second time
			 * around, but it doesn't hurt, so keep this simple
			 */
			_uart_putc_now(data);
			sreg = SREG;
			return;
		} else {
			sei();
			nop();
			cli();
		}
	}
    
    UART_TxBuf[tmphead] = data;
    UART_TxHead = tmphead;

    /* enable UDRE interrupt */
    UART0_CONTROL    |= _BV(UART0_UDRIE);

	SREG = sreg;

}/* uart_putc */


/*************************************************************************
Function: uart_puts()
Purpose:  transmit string to UART
Input:    string to be transmitted
Returns:  none          
**************************************************************************/
void uart_puts(const char *s )
{
    while (*s) 
      uart_putc(*s++);

}/* uart_puts */


/*************************************************************************
Function: uart_puts_p()
Purpose:  transmit string from program memory to UART
Input:    program memory string to be transmitted
Returns:  none
**************************************************************************/
void uart_puts_p(const char *progmem_s )
{
    register char c;
    
    while ( (c = pgm_read_byte(progmem_s++)) ) 
      uart_putc(c);

}/* uart_puts_p */

#if 0 /* unused */
/*************************************************************************
Function: uart_puti()
Purpose:  transmit integer as ASCII to UART
Input:    integer value
Returns:  none
This functions has been added by Martin Thomas <eversmith@heizung-thomas.de>
Don't blame P. Fleury if it doesn't work ;-)
**************************************************************************/
void uart_puti( const int val )
{
    char buffer[sizeof(int)*8+1];
    uart_puts( itoa(val, buffer, 10) );
}/* uart_puti */
void uart_putl( const long val )
{
    char buffer[sizeof(long)*8+1];
    uart_puts( ltoa(val, buffer, 10) );
}/* uart_puti */
#endif

/*************************************************************************
Function: uart_puthex_nibble()
Purpose:  transmit lower nibble as ASCII-hex to UART
Input:    byte value
Returns:  none
This functions has been added by Martin Thomas <eversmith@heizung-thomas.de>
Don't blame P. Fleury if it doesn't work ;-)
**************************************************************************/
void uart_puthex_nibble(const unsigned char b)
{
    unsigned char  c = b & 0x0f;
    if (c>9) c += 'A'-10;
    else c += '0';
    uart_putc(c);
} /* uart_puthex_nibble */

/*************************************************************************
Function: uart_puthex_byte()
Purpose:  transmit upper and lower nibble as ASCII-hex to UART
Input:    byte value
Returns:  none
This functions has been added by Martin Thomas <eversmith@heizung-thomas.de>
Don't blame P. Fleury if it doesn't work ;-)
**************************************************************************/
void uart_puthex_byte(const unsigned char  b)
{
    uart_puthex_nibble(b>>4);
    uart_puthex_nibble(b);
} /* uart_puthex_byte */
