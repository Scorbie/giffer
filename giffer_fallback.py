import golly as g

"""Fallback functions when importing gets wrong."""


def getstrings(entries, title='', width=None):
    """Get a list of strings.

    This is a fallback function for dialog.getstrings.
    """
    return [g.getstring(prompt, initial, title) for prompt, initial in entries]

