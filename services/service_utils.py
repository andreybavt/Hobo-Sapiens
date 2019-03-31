import re


def only_digits(s):
    return int(''.join(re.findall('\d', s)))
