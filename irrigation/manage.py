#!/usr/bin/python
#from moat import patch;patch()
from moat import twist
import os
import sys

### this import must not happen before settings are completely loaded
from hamlish_jinja import Hamlish
Hamlish._self_closing_jinja_tags.add('csrf_token')

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
