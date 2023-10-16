try:
    import regex as re
except ImportError:
    import re


# Taken from inflection library
def underscore(word):
    print(f"0 - {word}")
    word = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1.\2', word)
    print(f"1 - {word}")
    word = re.sub(r'([a-z\d])([A-Z])', r'\1.\2', word)
    print(f"2 - {word}")
    word = word.replace('-', '_')
    print(f"3 - {word}")
    return word.lower()