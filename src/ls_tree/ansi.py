from dataclasses import dataclass


class Mods:
    reset = 0
    bold = 1
    fade = 2
    cursive = 3
    underline = 4
    blink_slow = 5
    blink_fast = 6
    reverse = 7
    hide = 8
    cross = 9


class Colors:
    _base = 30
    _bg = 10
    _bright = 60

    black = 0
    red = 1
    green = 2
    yellow = 3
    blue = 4
    purple = 5
    cyan = 6
    white = 7


@dataclass
class State:
    reset: bool = False
    bold: bool = False
    fade: bool = False
    cross: bool = False
    cursive: bool = False
    underline: bool = False
    reverse: bool = False
    blink_slow: bool = False
    blink_fast: bool = False
    hide: bool = False
    # colors
    bg: bool = False
    bright: bool = False
    hue: int = 0

    def value(self, key):
        return getattr(self, key)

    def serialize(self):
        return {k: self.value(k) for k in self.__annotations__ if self.value(k)}

    def clone(self, **kwargs):
        return self.__class__(**{**self.serialize(), **kwargs})


class Col:
    def __init__(self, state=None):
        self.state = state or State()

    def clone(self, **kwargs):
        return type(self)(state=self.state.clone(**kwargs))

    def __call__(self, text) -> str:
        if text:
            return self.s + str(text) + self.clean.reset.s
        else:
            return ""

    @property
    def clean(self):
        return type(self)()

    @property
    def s(self) -> str:
        return str(self)

    def __getattr__(self, name):
        if name in self.state.__annotations__:
            return self.clone(**{name: True})
        if not name.startswith("_") and name in Colors.__dict__:
            return self.clone(hue=getattr(Colors, name) + 1)
        raise AttributeError(name)

    def __str__(self) -> str:
        data = self.state.serialize()
        bg = data.pop("bg", False)
        bright = data.pop("bright", False)
        if not data:
            return ""
        parts = []

        hue = data.pop("hue", None)
        if hue:
            hue += Colors._base - 1
            if bg:
                hue += Colors._bg
            if bright:
                hue += Colors._bright
            parts.append(hue)
        if data.pop("reset", False):
            parts.append(Mods.reset)
        for key in data:
            parts.append(getattr(Mods, key))
        return esc(*parts)

    def __add__(self, other) -> str:
        if isinstance(other, str):
            return str(self) + other
        if isinstance(other, type(self)):
            return str(self) + str(other)
        raise NotImplementedError(repr(other))


def esc(*mods):
    parts = list(map(str, mods))
    if parts:
        parts = ";".join(parts)
        return f"\033[{parts}m"
    else:
        return ""


c = Col()
