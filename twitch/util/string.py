try:
    import regex as re
except ImportError:
    import re


# Taken from inflection library
def underscore(word):
    word = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1.\2', word)
    word = re.sub(r'([a-z\d])([A-Z])', r'\1.\2', word)
    word = word.replace('-', '_')
    return word.lower()


def get_event_name_from_doc_string(doc_string):
    event_re = re.compile(r"(Twitch Name: )(\'[a-z._]*\')")
    matches = event_re.findall(doc_string)
    event_name = matches[0][1]
    return event_name.replace('\'', '')

