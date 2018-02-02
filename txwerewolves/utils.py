
import textwrap

def wrap_paras(text, width):
    """
    textwrap.wrap() for multiple paragraphs.
    """
    paras = text.split("\n")
    lines = []
    for para in paras:
        lines.extend(textwrap.wrap(para, width, drop_whitespace=False))
    return lines

def peek_ahead(iterable):
    """
    yield (value, more) from an iterable where `more` is a boolean value that
    indicates if there is another value yet to be yielded.
    """
    flag = False
    prev_value = None
    for value in iterable:
        if not flag:
            flag = True
            prev_value = value
            continue
        yield (prev_value, True)
        prev_value = value
    yield (prev_value, False)
        
