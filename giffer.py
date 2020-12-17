# Runs the selection for a given number of steps and creates a black and
# white animated GIF file.
# Based on giffer.pl, which is based on code by Tony Smith.

import golly as g
import os
import struct
from collections import namedtuple

try:
    import dialog
except Exception as e:
    g.note(
        "Failed to use tk dialog, using fallback.\n"
        "{}: {}".format(type(e), e)
    )
    import dialog_fallback as dialog

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
    b"\xFF\xFF\xFF" # (ignored)
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

########################################################################
# Parsing inputs
########################################################################

# Sanity check
def checkselrect():
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

Params = namedtuple(
    "Params", [
        "gens", "offset", "filename",
        "time_per_gen", "time_per_frame",
        "purecellsize", "gridwidth",
    ]
)


def parseinputs():

    # Get params
    (
        gens, dx, dy,
        time_per_gen, frames_per_gen,
        purecellsize, gridwidth,
        filename
    ) = dialog.getstrings(entries=[
        ("Number of generations\nfor the GIF file to run:", "4"),
        ("The X offset throughout\nthe whole animation (cells):", "0"),
        ("The Y offset throughout\nthe whole animation (cells):", "0"),
        ("The duration for each gen (ms):", "400"),
        ("The number of frames per gen\n(Only 0 for max smoothness):", "0"),
        ("The size of each cell (px):", "15"),
        ("The width of gridlines (px):", "1"),
        ("The file name:", "out.gif")
    ])

    # Validate and Convert params
    gens = tryint(gens, "Number of gens")
    purecellsize = tryint(purecellsize, "Cell size")
    gridwidth = tryint(gridwidth, "Grid width")
    dx, dy = tryint(dx, "X Offset"), tryint(dy, "Y Offset")
    time_per_gen = tryint(time_per_gen, "Duration per gen")
    time_per_gen //= 10
    frames_per_gen = tryint(frames_per_gen, "Frames per gen")
    if (dx, dy) == (0, 0):
        time_per_frame = time_per_gen
    elif frames_per_gen == 0:
        time_per_frame = 5
    else:
        time_per_frame = time_per_gen // frames_per_gen

    # Return
    return Params(
        gens=gens,
        offset=(dx, dy),
        filename=filename,
        time_per_gen=time_per_gen,
        time_per_frame=time_per_frame,
        purecellsize=purecellsize,
        gridwidth=gridwidth,
    )

########################################################################
# GIF formatting
# Useful information on GIF formats in:
# http://www.matthewflickinger.com/lab/whatsinagif/bits_and_bchr.asp
########################################################################

def makegif(colors, rect, params):

    # Get canvas size
    rectx, recty, width, height = rect
    cellsize = params.purecellsize + params.gridwidth
    canvasheight = cellsize*height + params.gridwidth
    canvaswidth = cellsize*width + params.gridwidth

    # Validate canvas size
    if canvaswidth >= 65536 or canvasheight >= 65536:
        g.exit(
            "The width or height of the GIF file must be less than 65536 pixels."
            "Received width: {}, height: {}".format(canvaswidth, canvasheight)
        )

    # Generate header
    header = b"GIF89a"
    screendesc = struct.pack("<2HB2b", canvaswidth, canvasheight, colors.size+0x90, 0, 0)
    applic = b"\x21\xFF\x0B" + b"NETSCAPE2.0" + struct.pack("<2bHb", 3, 1, 0, 0)
    imagedesc = b"\x2C" + struct.pack("<4HB", 0, 0, canvaswidth, canvasheight, 0x00)

    # Buildup body
    bordercolor = 2 ** (colors.size + 1) - 1
    borderrow = [bordercolor] * (canvaswidth + cellsize)
    # Gather contents to write as gif file.
    gifcontent = [header, screendesc, colors.table, applic]
    # Helper variables
    gif_total_time = params.time_per_gen * params.gens
    gif_num_frames = gif_total_time // params.time_per_frame
    gif_dx, gif_dy = params.offset
    gif_dx_px, gif_dy_px = gif_dx * cellsize, gif_dy * cellsize
    for frame_time in range(0, gif_total_time, params.time_per_frame):
        # Graphics control extension
        gifcontent += [b"\x21\xF9", struct.pack("<bBH2b", 4, 0x00, params.time_per_frame, 0, 0)]
        # Get cumulative offset for this frame:
        # "Perunage" used as a term like "Percentage"; Couldn't find a better word.
        dx_px = gif_dx_px * frame_time // gif_total_time
        dy_px = gif_dy_px * frame_time // gif_total_time
        # Set offset in total cells && remaining pixels
        dx_cell, dx_subpx = divmod(dx_px, cellsize)
        dy_cell, dy_subpx = divmod(dy_px, cellsize)
        # Get cell states (shifted dx_cell, dy_cell)
        # The bounding box is [rectx+dx_cell, recty+dy_cell, width+1, height+1]
        cells = []
        # The image is made of cell rows (height purecellsize) sandwiched
        # by border rows (height gridwidth).
        for y in range(recty+dy_cell, recty+dy_cell+height+1):
            cells += [borderrow] * params.gridwidth
            row = []
            # Each row is made of cell pixels (width purecellsize)
            # sandwiched by border pixels (width gridwidth)
            for x in range(rectx+dx_cell, rectx+dx_cell+width+1):
                row += [bordercolor] * params.gridwidth
                row += [g.getcell(x, y)] * params.purecellsize
            row += [bordercolor] * params.gridwidth
            cells += [row] * params.purecellsize
        cells += [borderrow] * params.gridwidth
        # Cut a canvaswidth x canvasheight image starting from dx_px, dy_px.
        newcells = [
            row[dx_subpx:dx_subpx+canvaswidth]
            for row in cells[dy_subpx:dy_subpx+canvasheight]
        ]
        image = [i for row in newcells for i in row]  # list of integers
        # Image descriptor + Image
        gifcontent += [imagedesc, compress(image, colors.size+1)]
        g.show("Frame {}/{}".format(frame_time//params.time_per_frame+1, gif_num_frames))
        current_gen = frame_time // params.time_per_gen
        next_gen = (frame_time + params.time_per_frame) // params.time_per_gen
        if next_gen > current_gen:
            g.run(next_gen - current_gen)
            g.update()
    trailer = b'\x3B'
    gifcontent.append(trailer)

    with open(os.path.join(os.getcwd(), params.filename),"wb") as gif:
        gif.write(b"".join(gifcontent))
    g.show("GIF animation saved in {}".format(params.filename))

########################################################################
# GIF compression
# Algorithm explained in detail in:
# http://www.matthewflickinger.com/lab/whatsinagif/lzw_image_data.asp
########################################################################

def compress(data, mincodesize):
    """Apply lzw compression to the given data and minimum code size."""

    ncolors = 2**mincodesize
    cc, eoi = ncolors, ncolors + 1
    del eoi  # Not using it

    def bchr(i):
        """A py2/py3 compatible `int(0x??)` to `b'\\x??'` converter"""
        return bytes((i,))

    table = {bchr(i): i for i in range(ncolors)}
    codesize = mincodesize + 1
    newcode = ncolors + 2

    outputbuff, outputbuffsize, output = cc, codesize, []

    databuff = b''

    for next_ in data:
        newbuff = databuff + bchr(next_)
        if newbuff in table:
            databuff = newbuff
        else:
            table[newbuff] = newcode
            newcode += 1
            # Prepend table[databuff] to outputbuff (bitstrings)
            outputbuff += table[databuff] << outputbuffsize
            outputbuffsize += codesize
            databuff = bchr(next_)
            if newcode > 2**codesize:
                if codesize < 12:
                    codesize += 1
                else:
                    # Prepend clear code.
                    outputbuff += cc << outputbuffsize
                    outputbuffsize += codesize
                    # Reset table
                    table = {bchr(chr(i)): i for i in range(ncolors)}
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
    for start in range(0, len(output), 255):
        end = min(len(output), start+255)
        words.append(b''.join(bchr(i) for i in output[start:end]))
    contents = [bchr(mincodesize)]
    for word in words:
        contents.append(bchr(len(word)))
        contents.append(word)
    contents.append(b'\x00')
    return b''.join(contents)
########################################################################
# Main
########################################################################
def main():
    params = parseinputs()
    makegif(colors=lifewiki, rect=checkselrect(), params=params)

main()
