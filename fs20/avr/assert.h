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
 * This header defines support for assertions.
 */
#ifndef ASSERT_H
#define ASSERT_H

#include "local.h"
#ifdef ASSERTIONS

#include "util.h"
#include <avr/pgmspace.h>

#define assert(_a,_b) do { \
		if(!(_a)) report_error(_b); \
	} while(0)
#else
#define assert(_a,_b) do{} while(0)
#endif

#endif /* ASSERT_H */
