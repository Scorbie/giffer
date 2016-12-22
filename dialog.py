import golly as g
from Tkinter import *
import ttk


class StringsDialog(ttk.Frame):
    """A dialog window that can get a multiple string responses."""
    def __init__(self, master, entries, width=10):
        ttk.Frame.__init__(self, master)
        self.grid(column=0, row=0, sticky=(N, W, E, S))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        # Response data
        self.responses = []
        self.respentries = []
        # Build the items in the window
        for index, entry in enumerate(entries):
            try:
                prompt, initial = entry
                if initial is None:
                    initial = ''
            except:
                raise TypeError('Each prompt should contain a prompt and '
                                'an initial value!')
            ttk.Label(self, text=prompt).grid(column=0, row=index)
            resp = ttk.Entry(self, width=width)
            resp.grid(column=1, row=index)
            resp.insert(0, initial)
            self.respentries.append(resp)
            self.responses.append(initial)
        ttk.Button(self, text="OK",
                   command=self.getresponses).grid(column=0, row=index+1)
        ttk.Button(self, text="Cancel",
                   command=self.master.destroy).grid(column=1, row=index+1)

    def getresponses(self):
        """Get all the responses and close the window."""
        self.responses = [resp.get() for resp in self.respentries]
        self.master.destroy()


class BoolDialog(ttk.Frame):
    """A dialog window that can get a boolean response."""

    def __init__(self, master, prompt):
        ttk.Frame.__init__(self, master)
        self.grid(column=0, row=0, sticky=(N, W, E, S))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        ttk.Label(self, text=prompt).grid(column=0, row=0)
        ttk.Button(self, text="Yes", command=self.settrue).grid(column=0, row=1)
        ttk.Button(self, text="No", command=self.setfalse).grid(column=1, row=1)
        self.response = False

    def settrue(self):
        """Set the response to True and close the window."""
        self.response = True
        self.master.destroy()

    def setfalse(self):
        """Set the response to False and close the window."""
        self.response = False
        self.master.destroy()


def getstrings(entries, title='', width=10):
    """Return the responses with the given entries.

    <<Arguments>>
    entries -- list of (prompt, initial value) pairs.
    title -- the tile text of the window
    width -- the width of the entry box
    """
    root = Tk()
    root.title(title)
    # This places the window at the center.
    root.eval('tk::PlaceWindow {} center'.format(
                root.winfo_pathname(root.winfo_id())))
    sd = StringsDialog(root, entries, width)
    root.mainloop()
    return sd.responses


def getbool(prompt, title=''):
    """Return the user's choice as a boolean."""
    root = Tk()
    root.title(title)
    # This places the window at the center.
    root.eval('tk::PlaceWindow {} center'.format(
                root.winfo_pathname(root.winfo_id())))
    bd = BoolDialog(root, prompt)
    root.mainloop()
    return bd.response


if __name__ == '__builtin__':
    # getstrings test
    strings = getstrings(
        entries=[
            ('Prompt 1', None),
            ('Prompt 2', 'Default 2'),
            ('Prompt 3', 'Default 3')
        ],
        title="getstrings test",
        width=30
        )
    g.note("This is the input received:\n{}".format(strings))
    # getbool test
    boolean = getbool("Do you like GollyGUI?", "getbool test")
    if boolean:
        g.note("Thanks!")
    else:
        g.note("I'll try to make it better.")
