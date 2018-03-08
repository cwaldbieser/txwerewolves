
import six

def term_attrib_str(x):
    """
    Converts `x` to a terminal attribute string.
    For python2, this means bytes.
    For python3, this means unicode.
    """
    if six.PY2:
        return x.encode('utf-8')
    else:
        return x

