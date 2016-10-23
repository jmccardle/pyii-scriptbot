#!/usr/bin/python
from random import randint
import sys

min = 1
max = 100

if len(sys.argv) == 1:
    min = 1
    max = 100
elif len(sys.argv) == 2:
    min = 1
    max = int(sys.argv[1])
elif len(sys.argv) == 3 and ("--min" not in sys.argv and "--max" not in sys.argv):
    min = int(sys.argv[1])
    max = int(sys.argv[2])

#if "--min" in sys.argv:
else:
    try:
        min = int(sys.argv[sys.argv.index("--min")+1])
    except:
        min = 0

    #if "--max" in sys.argv:
    try:
        max = int(sys.argv[sys.argv.index("--max")+1])
    except:
        max = 100
if min > max:
    min, max = max, min
print(randint(min, max))

