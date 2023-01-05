import os
import re
import sys
from pathlib import Path

from .ansi import c

space = "    "
line = "│   "
tee = "├─ "
knee = "└─ "

IGNORE_RE = re.compile(r"^(\.(git|idea|venv|tox|DS_Store)|venv|__pycache__|dist)$")
MAX_ITEMS = 1000
MAX_ITEMS_PER_BRANCH = 25


def is_exe(path):
    return os.access(path.absolute(), os.X_OK)


def is_py(path):
    return path.name.lower().endswith(".py")


def is_py_pkg(path):
    try:
        return (path / "__init__.py").exists()
    except Exception:
        return False


class C:
    TREE = c.black.bright
    DIR = c.bright.blue
    LINK = c.bright.purple
    EXE = c.red
    PY = c.green
    NOISE = c.black.bright.fade
    IMPORTANT = c.bright.white.bold
    RESET = c.reset


def render(path: Path) -> str:
    if path.is_symlink():
        d = "/" if path.is_dir() else ""
        return C.LINK(path.name) + "@ -> " + str(path.readlink()) + d
    elif path.is_dir():
        if IGNORE_RE.match(path.name):
            return C.DIR.fade(path.name) + C.NOISE("/...")
        elif is_py_pkg(path):
            return C.PY(path.name) + "/"
        else:
            return C.DIR(path.name) + "/"
    elif path.is_dir():
        dots = "..." if IGNORE_RE.match(path.name) else ""
        return C.DIR(path.name) + "/" + dots
    elif is_exe(path):
        return C.EXE(path.name) + "*"
    elif is_py(path):
        if path.name == "__init__.py":
            return C.PY.fade(path.name)
        else:
            return C.PY(path.name[:-3]) + C.PY.fade(path.name[-3:])
    elif IGNORE_RE.match(path.name):
        return C.NOISE(path.name)
    elif path.name in ["Makefile"]:
        return C.IMPORTANT(path.name)
    else:
        return path.name


def is_dir(path):
    return path.is_dir() and not path.is_symlink()


def print_tree(start_path: Path, depth: int = -1, only_dirs: bool = False):
    count = {"dirs": 0, "files": 0}

    def scan_tree(dir_path: Path, depth, prefix: str = "", count_only: bool = False):
        if depth <= 0:
            count_only = True
        try:
            items = sorted(list(dir_path.iterdir()))
        except Exception:
            yield C.TREE(prefix + knee) + c.red.bg("ERROR")
            return
        if only_dirs:
            items = [d for d in items if d.is_dir()]

        branches = (len(items) - 1) * [tee] + [knee]
        skipped = {"dirs": 0, "files": 0}
        last_prefix = None
        for idx, (branch, path) in enumerate(zip(branches, items)):
            last_prefix = C.TREE(prefix + branch)
            show = (idx < MAX_ITEMS_PER_BRANCH) or (len(items) * 0.8 < MAX_ITEMS_PER_BRANCH)
            if show and not count_only:
                yield last_prefix + render(path)
            elif is_dir(path):
                skipped["dirs"] += 1
            else:
                skipped["files"] += 1

            try:
                if is_dir(path):
                    count["dirs"] += 1
                    yield from scan_tree(
                        dir_path=path,
                        depth=depth - 1,
                        prefix=prefix + (line if branch == tee else space),
                        count_only=count_only or IGNORE_RE.match(path.name) or not show,
                    )
                elif not only_dirs:
                    count["files"] += 1
            except Exception:
                # print(path)
                yield C.TREE(prefix + (line if branch == tee else space)) + c.red.bg("ERROR2")
        if any(skipped.values()) and not count_only:
            yield last_prefix + C.NOISE("...skipped " + render_count(skipped))

    print(C.IMPORTANT(str(start_path.absolute())))
    iterator = scan_tree(start_path, depth=depth)
    for idx, ln in enumerate(iterator):
        if idx < MAX_ITEMS:
            print(ln)
        else:
            print(f"Warning: {MAX_ITEMS=} reached, aborting", file=sys.stderr)
            break

    print("\n" + render_count(count) + "\n")


def render_count(count):
    return " and ".join(f"{v} {k}" for k, v in count.items() if v)


def run(*args):
    def is_depth(arg):
        return re.match(r"^-\d+$", arg)

    path = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 and not is_depth(sys.argv[1]) else ".")

    depth = 4
    for arg in sys.argv[1:]:
        if re.match(r"^-\d$", arg):
            depth = int(arg[1:])

    print_tree(start_path=Path(path), depth=depth)


if __name__ == "__main__":
    run()
