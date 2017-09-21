Time specifications
===================

MoaT understands the following ways to specify a date and/or time:

These keywords don't need a number:

* a weekday. ``mo`` ``mon`` or ``monday`` through ``su`` ``sun`` ``sunday``
  means "next …day", i.e. max 6 days in the future.

You need a number in front of these keywords:

* ``n mo|tu|…``: the n'th monday of a month.

* ``n wk``: a week number. Week 1 is defined as the week which contains the
  year's first Thursday.
  
* ``n yr``: Gregorian year N.

* ``n mo``: Gregorian month N.

* ``n dy``: Gregorian month N.

* ``n hr``: Hour N.

* ``n min``: Minute N.

* ``n sec``: Second N.

Negative numbers start from the end of the next-larger range, i.e. "-1 hr"
is the hour before midnight.

All values must match. There is currently no way to specify alternates
like "1st or 3rd Monday" and no way to say "the next Monday in two weeks".
Use code to do that: if the current day-of-month is >7, sekect the 3rd
Monday, otherwise wait for the 1st; call the matching code with a time two
weeks from now.

