# Runs the selection for a given number of steps and creates a black and
# white animated GIF file.
# Based on giffer.pl, which is based on code by Tony Smith.

import golly as g
import os
import struct
from collections import namedtuple

try:
    from dialog import getstrings
except:
    from dialog_fallback import getstrings

########################################################################
# Color schemes
########################################################################
class ColorScheme(object):
    """Color scheme used in the gif file.

    ColorScheme is merely a container for these two things:
    table: Contains a table of the 2**(size+1) colors. As you can see
        below, the colors are represented as RGB, each color in which
        occupying 1 byte (values 0-255.) The 3-byte colors are simply
        concatenated to make the color table.
        **Note**
        The last color is used as the borderline color in this script.
    size: Contains a "color table size" that goes to the logical screen
        descriptor.
        **Note**
        The number of colors used in the gif file is: 2 ** (size + 1).
    """
    def __init__(self, table=b""):
        size = 0
        n_colors = len(table)
        while 3 * 2 ** (size+1) < n_colors:
            size += 1
        assert 3 * 2 ** (size+1) == n_colors, (
            "Length of color table should be 3 * (2**k)."
            "Currently it's {}.".format(n_colors)
        )
        self.size = size
        self.table = table

lifewiki = ColorScheme(
    b"\xFF\xFF\xFF" # State 0: white
    b"\x00\x00\x00" # State 1: black
    b"\x00\x00\x00" # (ignored)
    b"\xC6\xC6\xC6" # Boundary: LifeWiki gray
)

lifehistory = ColorScheme(
    b"\x00\x00\x00" # State 0: black
    b"\x00\xFF\x00" # State 1: green
    b"\x00\x00\x80" # State 2: dark blue
    b"\xD8\xFF\xD8" # State 3: light green
    b"\xFF\x00\x00" # State 4: red
    b"\xFF\xFF\x00" # State 5: yellow
    b"\x60\x60\x60" # State 6: gray
    b"\x00\x00\x00" # Boundary color
)

# Edit this to set the color scheme.
colors = lifewiki

########################################################################
# Parsing inputs
########################################################################

# Sanity check
def check_selrect():
    rect = g.getselrect()
    if rect == []:
        g.exit("Nothing in selection.")
    [_, _, width, height] = rect
    if(width>=65536 or height>=65536):
        g.exit("The width or height of the GIF file must be less than 65536 pixels.")
    return rect


def tryint(var, name):
    try:
        return int(var)
    except:
        g.exit("{} is not an integer: {}".format(name, var))


def parseinputs():
    # Get params
    gens, fpg, pause, purecellsize, gridwidth, v, filename = getstrings(entries=[
        ("Number of generations for the GIF file to run:", "4"),
        ("The number of frames per generation (1 for statonary patterns):", "1"),
        ("The pause time of each generation in centisecs:", "50"),
        ("The size of each cell in pixels:", "14"),
        ("The width of gridlines in pixels:", "2"),
        ("The offset of the total period:", "0 0"),
        ("The file name:", "out.gif")
        ])

    # Sanity check params
    try:
        vx, vy = v.split()
    except:
        g.exit("You should enter the speed as {x velocity} {y velocity}.\n"
               "ex1) 0 0\t ex2) -1 3")

    gens = tryint(gens, "Number of gens")
    pause = tryint(pause, "Pause time")
    purecellsize = tryint(purecellsize, "Cell size")
    gridwidth = tryint(gridwidth, "Grid width")
    vx = tryint(vx, "X velocity")
    vy = tryint(vy, "Y velocity")
    fpg = tryint(fpg, "Frames per gen")

    pause //= fpg

    return {
        "gens": gens,
        "fpg" : fpg,
        "vx": vx,
        "vy": vy,
        "purecellsize": purecellsize,
        "gridwidth": gridwidth,
        "pause": pause,
        "filename": filename
    }

########################################################################
# GIF formatting
# Useful information on GIF formats in:
# http://www.matthewflickinger.com/lab/whatsinagif/bits_and_bytes.asp
########################################################################

def makegif(
    gens, fpg, pause, vx, vy,
    rect, purecellsize, gridwidth,
    colors, filename
):
    rectx, recty, width, height = rect
    cellsize = purecellsize + gridwidth
    canvasheight = cellsize*height + gridwidth
    canvaswidth = cellsize*width + gridwidth

    if(canvaswidth>=65536 or canvasheight>=65536):
        g.exit("The width or height of the GIF file must be less than 65536 pixels. "
               "Received width: {}, height: {}".format(canvaswidth, canvasheight))
    

    header, trailer = "GIF89a", '\x3B'
    screendesc = struct.pack("<2HB2b", canvaswidth, canvasheight,
                             0x90+colors.size, 0, 0)
    applic = "\x21\xFF\x0B" + "NETSCAPE2.0" + struct.pack("<2bHb", 3, 1, 0, 0)
    imagedesc = "\x2C" + struct.pack("<4HB", 0, 0, canvaswidth, canvasheight, 0x00)

    bordercolor = 2 ** (colors.size + 1) - 1
    borderrow = [bordercolor] * (canvaswidth + cellsize)
    # Gather contents to write as gif file.
    gifcontent = [header, screendesc, colors.table, applic]
    for f in xrange(gens*fpg):
        # Graphics control extension
        gifcontent += ["\x21\xF9", struct.pack("<bBH2b", 4, 0x00, pause, 0, 0)]
        # Get data for this frame
        dx = int(vx * f * cellsize // (fpg * gens))
        dy = int(vy * f * cellsize // (fpg * gens))
        dx_cell, dx_px = divmod(dx, cellsize)
        dy_cell, dy_px = divmod(dy, cellsize)
        # Get cell states (shifted dx_cell, dy_cell)
        # The bounding box is [rectx+dx_cell, recty+dy_cell, width+1, height+1]
        cells = []
        # The image is made of cell rows (height purecellsize) sandwiched
        # by border rows (height gridwidth).
        for y in xrange(recty+dy_cell, recty+dy_cell+height+1):
            cells += [borderrow] * gridwidth
            row = []
            # Each row is made of cell pixels (width purecellsize)
            # sandwiched by border pixels (width gridwidth)
            for x in xrange(rectx+dx_cell, rectx+dx_cell+width+1):
                row += [bordercolor] * gridwidth
                row += [g.getcell(x, y)] * purecellsize
            row += [bordercolor] * gridwidth
            cells += [row] * purecellsize
        cells += [borderrow] * gridwidth
        #g.setclipstr('\n'.join(str(row) for row in cells).replace(', ', ''))
        #g.note('')
        # Cut a canvaswidth x canvasheight image starting from dx_px, dy_px.
        newcells = [row[dx_px:dx_px+canvaswidth] for row in
                    cells[dy_px:dy_px+canvasheight]]
        image = ''.join(''.join(chr(i) for i in row) for row in newcells)
        # Image descriptor + Image
        gifcontent += [imagedesc, compress(image, colors.size+1)]
        g.show("{}/{}".format(f+1, gens*fpg))
        if (f % fpg == fpg - 1):
            g.run(1)
            g.update()
    gifcontent.append(trailer)

    with open(os.path.join(os.getcwd(), filename),"wb") as gif:
        gif.write("".join(gifcontent))
    g.show("GIF animation saved in {}".format(filename))

########################################################################
# GIF compression
# Algorithm explained in detail in:
# http://www.matthewflickinger.com/lab/whatsinagif/lzw_image_data.asp
########################################################################

def compress(data, mincodesize):
    """Apply lzw compression to the given data and minimum code size."""

    ncolors = 2**mincodesize
    cc, eoi = ncolors, ncolors + 1

    table = {chr(i): i for i in xrange(ncolors)}
    codesize = mincodesize + 1
    newcode = ncolors + 2

    outputbuff, outputbuffsize, output = cc, codesize, []

    databuff = ''

    for next in data:
        newbuff = databuff + next
        if newbuff in table:
            databuff = newbuff
        else:
            table[newbuff] = newcode
            newcode += 1
            # Prepend table[databuff] to outputbuff (bitstrings)
            outputbuff += table[databuff] << outputbuffsize
            outputbuffsize += codesize
            databuff = next
            if newcode > 2**codesize:
                if codesize < 12:
                    codesize += 1
                else:
                    # Prepend clear code.
                    outputbuff += cc << outputbuffsize
                    outputbuffsize += codesize
                    # Reset table
                    table = {chr(i): i for i in xrange(ncolors)}
                    newcode = ncolors + 2
                    codesize = mincodesize + 1
            while outputbuffsize >= 8:
                output.append(outputbuff & 255)
                outputbuff >>= 8
                outputbuffsize -= 8
    outputbuff += table[databuff] << outputbuffsize
    outputbuffsize += codesize
    while outputbuffsize >= 8:
        output.append(outputbuff & 255)
        outputbuff >>= 8
        outputbuffsize -= 8
    output.append(outputbuff)
    # Slice outputbuff into 255-byte chunks
    words = []
    for start in xrange(0, len(output), 255):
        end = min(len(output), start+255)
        words.append(''.join(chr(i) for i in output[start:end]))
    contents = [chr(mincodesize)]
    for word in words:
        contents.append(chr(len(word)))
        contents.append(word)
    contents.append('\x00')
    return ''.join(contents)

########################################################################
# Main
########################################################################
def main():
    rect = check_selrect()
    kwargs = parseinputs()
    makegif(colors=lifewiki, rect=rect, **kwargs)

main()

