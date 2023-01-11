import os

from . import ansi

types = [
    "directory",
    "symbolic_link",
    "socket",
    "pipe",
    "executable",
    "block_special",
    "character_special",
    "executable_with_setuid",
    "executable_with_setgid",
    "directory_writable_to_others_with_sticky_bit",
    "directory_writable_to_others_without_sticky_bit",
]


def colors():
    default = "exfxcxdxbxegedabagacad"  # noqa
    return os.environ.get("LSCOLORS") or default


class ColorCodes:
    a = ansi.c.black
    b = ansi.c.red
    c = ansi.c.green
    d = ansi.c.brown
    e = ansi.c.blue
    f = ansi.c.magenta
    g = ansi.c.cyan
    h = ansi.c.reset  # light grey

    A = ansi.c.gray.bold  # bold black
    B = b.bold
    C = c.bold
    D = d.bold
    E = e.bold
    F = f.bold
    G = g.bold
    H = ansi.c.white.bright  # bold light grey

    x = None  # default foreground or background


def color(name):
    i = types.index(name)
    a, b = i * 2, (i + 1) * 2
    foreground, background = colors()[a:b]
    if foreground != "x":
        clr = getattr(ColorCodes, foreground)
    else:
        clr = ""
    if background != "x":
        clr += getattr(ColorCodes, background).bg.s
    return clr


def print_colors():
    for t in types:
        print(color(t) + t.replace("_", " ") + ansi.c.reset.s)


class ColorWrapper:
    def __init__(self, name):
        self.name = name

    def __call__(self, text):
        return color(self.name) + text + ansi.c.reset.s

    def __str__(self):
        return color(self.name)

    def __getattr__(self, item):
        return getattr(color(self.name), item)


class Colors:
    def __getattr__(self, item):
        return ColorWrapper(name=item)


LSCOLORS = Colors()


if __name__ == "__main__":
    print_colors()
