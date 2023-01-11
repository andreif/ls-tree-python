import datetime
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

from .ansi import c
from .ls import LSCOLORS


class Config:
    IGNORE_RE = re.compile(
        r"^(\.(git|idea|venv|venv_.*|tox|tox_.*|DS_Store)"
        r"|venv|venv_.*|__pycache__|dist|node_modules|cdk.out)/?$"
    )
    SHOW_IGNORED = True
    COUNT_IGNORED = False
    SHOW_STAT = False
    MAX_ITEMS = 2000
    MAX_ITEMS_PER_BRANCH = 250


def is_exe(path):
    return os.access(path.absolute(), os.X_OK)


def stat_(path):
    try:
        return path.stat()
    except Exception:
        return False


def is_exe_gid(st):
    if st:
        return stat.filemode(st.st_mode)[6] == "s"


def is_exe_uid(st):
    if st:
        return stat.filemode(st.st_mode)[3] == "s"


def is_socket(st):
    if st:
        return stat.filemode(st.st_mode)[0] == "s"


def is_py(path):
    return path.name.lower().endswith(".py")


def exists(path):
    try:
        return path.exists()
    except Exception:
        return False


# custom colors
class C:
    TREE = c.gray
    PY = c.green
    NOISE = c.gray.fade
    IMPORTANT = c.bright.white.bold
    RESET = c.reset


def render(path: Path, root=False) -> str:
    if path.is_symlink():
        d = is_dir(path, grace=True, choices=("/", "", " " + c.red.bg(" ? ")))
        pre = c.fade if Config.IGNORE_RE.match(path.name) else c.reset
        return pre + LSCOLORS.symbolic_link(path.name) + pre("@ -> " + str(path.readlink()) + d)
    elif is_dir(path, grace=True):
        if Config.IGNORE_RE.match(path.name) and not root:
            return LSCOLORS.directory.fade(path.name) + C.NOISE("/")
        elif exists(path / "__init__.py"):
            return C.PY(path.name) + "/"
        else:
            extra = ""
            # if exists(path / "Dockerfile"):
            #     extra += " 🐳"
            # if exists(path / "Makefile"):
            #     extra += " 🛠 "
            # if exists(path / "package.json"):
            #     extra += " ☕️"
            # if exists(path / "pyproject.toml"):
            #     extra += " 🐍"
            return LSCOLORS.directory(path.name) + "/" + extra
    elif is_exe_uid(stat_(path)):
        return LSCOLORS.executable_with_setuid(path.name) + "*"
    elif is_exe_gid(stat_(path)):
        return LSCOLORS.executable_with_setgid(path.name) + "*"
    elif is_socket(stat_(path)):
        return LSCOLORS.socket(path.name) + "="
    elif is_exe(path):
        if is_py(path):
            return C.PY(path.name[:-3]) + LSCOLORS.executable(path.name[-3:]) + "*"
        else:
            return LSCOLORS.executable(path.name) + "*"
    elif is_py(path):
        if path.name == "__init__.py":
            return C.PY.fade(path.name)
        else:
            return C.PY(path.name[:-3]) + C.PY.fade(path.name[-3:])
    elif Config.IGNORE_RE.match(path.name):
        return C.NOISE(path.name)
    elif path.name == "pyproject.toml":
        return C.PY.fade.bold(path.name)
    elif path.name in ["Makefile"] or path.name.startswith("Dockerfile"):
        return c.bold(path.name)
    elif path.name == "package.json":
        return c.yellow.fade.bold(path.name)
    elif path.name.endswith((".js", ".ts")):
        return c.yellow.fade(path.name)
    elif path.name in [
        ".gitignore",
        ".npmignore",
        ".python-version",
        "poetry.lock",
        "package-lock.json",
    ]:
        return C.NOISE(path.name)
    else:
        return path.name


def is_dir(path, grace=False, choices=None):
    try:
        result = path.is_dir() and not path.is_symlink()
    except Exception:
        if grace:
            if choices:
                return choices[2]
            else:
                return False
        else:
            raise
    else:
        return (choices[0] if result else choices[1]) if choices else result


@dataclass
class Count:
    dirs: int = 0
    files: int = 0
    errors: int = 0

    def count(self, path):
        try:
            if is_dir(path):
                self.dirs += 1
            else:
                self.files += 1
        except Exception:
            self.errors += 1

    def clone(self):
        return type(self)(**self.serialize())

    def __sub__(self, other):
        if isinstance(other, type(self)):
            a = self.serialize()
            b = other.serialize()
            return type(self)(**{k: (v - b[k]) for k, v in a.items()})
        raise NotImplementedError(type(other))

    def serialize(self):
        return {k: getattr(self, k) for k in self.__annotations__}

    def sum(self):
        return sum(self.serialize().values())

    def any(self):
        return bool(self.sum())

    def render(self):
        parts = [f"{v} {k[:-1] if v == 1 else k}" for k, v in self.serialize().items() if v]
        if len(parts) > 2:
            return f"{parts[0]}, {parts[1]} and {parts[2]}"
        else:
            return " and ".join(parts)


class TooManyLines(Exception):
    pass


class Node:
    def __init__(
        self,
        path: Path,
        depth: int,
        count_only: bool = False,
        only_dirs: bool = False,
        total: Count = None,
        shown: Count = None,
        hidden: Count = None,
        last: bool = False,
        parent=None,
    ):
        self.parent = parent
        self.path = path if isinstance(path, Path) else Path(path)
        self.depth = depth
        self.count_only = count_only or depth <= 0
        self.total = total or Count()
        self.shown = shown or Count()
        self.hidden = hidden or Count()
        self.only_dirs = only_dirs
        self.last = last

    @property
    def root(self):
        return not self.parent

    def prefix(self, sub=False, add_knee=False):
        tab, line = "    ", "│   "
        tee, knee = "├─ ", "└─ "
        if self.root:
            return "  "
        prefix = self.parent.prefix(sub=True) if self.parent else ""
        if sub or add_knee:
            prefix += tab if self.last else line
            if add_knee:
                prefix += knee
        else:
            prefix += knee if self.last else tee
        return prefix

    def write(self, txt):
        if not self.count_only:
            print(txt, end="")

    def ignored(self):
        return Config.IGNORE_RE.match(self.path.name) and not self.root

    def is_hidden(self):
        return self.ignored() and not Config.SHOW_IGNORED

    def stat(self):
        if not Config.SHOW_STAT:
            return ""
        try:
            s = self.path.stat()
        except Exception:
            return " " * 61
        xattr = ""
        # if stat.S_ISSOCK(s.st_mode):
        #     xattr = "S"
        # else:
        #     try:
        #         import subprocess
        #         xattr = subprocess.check_output(["xattr", str(self.path.absolute())])
        #         xattr = "@" if xattr else " "
        #     except Exception:
        #         xattr = "?"
        oc = str(oct(s.st_mode))
        if oc.startswith("0o100"):  # file
            oc = (" " * 3) + oc[5:]
        elif oc.startswith(("0o102", "0o104")):  # setuid
            oc = (" " * 2) + oc[4:]
        elif oc.startswith("0o40"):  # directory
            oc = (" " * 3) + oc[4:]
        else:
            oc = oc[2:]

        def trim(t, n):
            t = t[:5] + ".." if len(t) > n else t
            return f"{t:7}"

        def time(st):
            dt = datetime.datetime.fromtimestamp(st.st_mtime)
            now = datetime.datetime.now()
            if now.year != dt.year:
                fmt = "%Y-%b-%d %H:%M"
            elif now.month != dt.month:
                fmt = "-----%b-%d %H:%M"
            elif now.day != dt.day:
                fmt = "---------%d %H:%M"
            elif now.hour != dt.hour:
                fmt = "----------- %H:%M"
            elif now.minute != dt.minute:
                fmt = "----------- --:%M"
            else:
                fmt = "----------- --:--"

            return dt.strftime(fmt)

        return " ".join(
            map(
                str,
                [
                    oc,
                    stat.filemode(s.st_mode) + xattr,
                    trim(self.path.owner(), 7),
                    trim(self.path.group(), 7),
                    f"{s.st_size:-9}",
                    time(s),
                ],
            )
        )

    def print(self):
        if self.depth < 0 and not Config.COUNT_IGNORED:
            return
        post = ""
        try:
            if is_dir(self.path) and (not self.ignored() or Config.COUNT_IGNORED):
                try:
                    items = sorted(list(self.path.iterdir()))  # this can fail too
                except Exception:
                    post = " " + c.red.bg(" ? ")
                    raise
            else:
                items = []
        except Exception:
            # if not self.is_hidden():
            #     self.write(rnd + " " + c.red.bg(" ? "))
            post += "\n"
            return
        finally:
            if self.is_hidden():
                if not self.count_only:
                    self.hidden.count(self.path)
            else:
                if self.root:
                    self.write("\n" + C.NOISE(self.stat()) + "  ")
                else:
                    self.write(C.NOISE(self.stat() + " "))
                    self.write(C.TREE(self.prefix()))
                self.write(render(self.path, self.root) + post)

            self.total.count(self.path)

        if self.ignored():
            freeze = self.total.clone()
        else:
            self.write("\n")

        if not self.count_only:
            if not self.is_hidden() and not self.root:
                self.shown.count(self.path)
            if self.shown.sum() > Config.MAX_ITEMS:
                print(f"Warning: {Config.MAX_ITEMS=} reached, aborting", file=sys.stderr)
                if self.root:
                    return
                else:
                    exit()  # TODO
                    raise TooManyLines

        skipped = Count()
        for idx, path in enumerate(items):
            skip = (idx > Config.MAX_ITEMS_PER_BRANCH) and (
                len(items) * 0.8 > Config.MAX_ITEMS_PER_BRANCH
            )

            last = idx == len(items) - 1

            if skip or self.count_only or self.ignored():
                skipped.count(path)

            try:
                type(self)(
                    path=path,
                    depth=self.depth - 1,
                    last=last,
                    parent=self,
                    count_only=self.count_only or skip or self.ignored(),
                    total=self.total,
                    shown=self.shown,
                    hidden=self.hidden,
                ).print()
            except TooManyLines:
                return

        if self.ignored():
            if Config.SHOW_IGNORED:
                if is_dir(self.path, grace=True):
                    if Config.COUNT_IGNORED:
                        diff = self.total - freeze
                        if diff.any():
                            self.write(C.NOISE("... " + diff.render()))
                    else:
                        # self.write(C.NOISE("..."))
                        pass
                self.write("\n")

        elif not self.count_only and skipped.any():
            self.write(
                C.TREE(self.prefix(add_knee=True))
                + C.NOISE("...skipped " + skipped.render())
                + "\n"
            )

        elif self.root:
            if self.shown.any():
                self.write("\n  Shown: " + self.shown.render() + ".")
            if self.hidden.any():
                self.write(" Hidden: " + self.hidden.render() + ".")
            if Config.COUNT_IGNORED:
                self.write(" Total: " + self.total.render() + ".")
            self.write("\n\n")


def run(*args):
    def is_depth(arg):
        return re.match(r"^-\d+$", arg)

    path = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 and not is_depth(sys.argv[1]) else ".")

    depth = 4
    for arg in sys.argv[1:]:
        if re.match(r"^-\d$", arg):
            depth = int(arg[1:])

    # Config.COUNT_IGNORED = True
    Config.COUNT_IGNORED = False
    Config.SHOW_IGNORED = False
    Config.SHOW_IGNORED = True
    Config.SHOW_STAT = True
    Node(path=path, depth=depth).print()


if __name__ == "__main__":
    run()
