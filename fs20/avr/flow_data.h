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
 * This header defines misc flow stuff.
 */

#ifndef FLOW_DATA_H
#define FLOW_DATA_H

struct _write_head;
typedef struct _write_head {
	struct _write_head *next;
	unsigned char type;
	unsigned char len;
	unsigned char data[0];
} write_head;

void send_tx(write_head *data);
void read_data(unsigned char param, unsigned char *data, unsigned char len);

#endif /* FLOW_DATA_H */
