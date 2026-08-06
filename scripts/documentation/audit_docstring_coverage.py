"""Audit the public doc surface of the five SCAMP packages for missing docstrings.

Mirrors what the Sphinx build actually renders:
  - every non-underscore module/subpackage of each package (makePackageRSTs.py)
  - within each, public classes/functions (autosummary module.rst template)
  - within each class, :members: :inherited-members: :undoc-members:
"""
import importlib
import inspect
import pkgutil
import sys
from types import ModuleType, FunctionType

PACKAGES = ["scamp", "clockblocks", "expenvelope", "pymusicxml", "scamp_extensions"]
OWNED = tuple(PACKAGES)


def owned(obj_module_name):
    return obj_module_name and obj_module_name.split(".")[0] in OWNED


def all_modules(package_name):
    """Every module Sphinx documents for this package, recursively."""
    out = [package_name]
    pkg = importlib.import_module(package_name)
    if not hasattr(pkg, "__path__"):
        return out
    for info in pkgutil.iter_modules(pkg.__path__):
        if info.name.startswith("_"):
            continue
        full = f"{package_name}.{info.name}"
        if info.ispkg:
            out.extend(all_modules(full))
        else:
            out.append(full)
    return out


def has_doc(obj):
    d = inspect.getdoc(obj)
    return bool(d and d.strip())


def own_doc(obj):
    """True if the object has its own docstring (not inherited from a parent)."""
    d = getattr(obj, "__doc__", None)
    return bool(d and d.strip())


findings = []  # (kind, qualified_name, defining_module)


def check_class(cls, seen_classes):
    if cls in seen_classes:
        return
    seen_classes.add(cls)
    cname = f"{cls.__module__}.{cls.__qualname__}"
    if not own_doc(cls):
        findings.append(("class", cname, cls.__module__))

    # conf.py sets autoclass_content = 'class', so an __init__ docstring is never rendered — any
    # :param: block stranded there is invisible in the docs. Params belong on the class docstring.
    init = cls.__dict__.get("__init__")
    if init is not None and own_doc(init) and ":param" in init.__doc__:
        findings.append(("params on __init__ (not rendered)", cname, cls.__module__))

    for name, member in vars(cls).items():
        if name.startswith("_"):
            continue
        # unwrap the underlying callable for staticmethod/classmethod/property
        targets = []
        if isinstance(member, property):
            targets.append(("property", member.fget))
        elif isinstance(member, (staticmethod, classmethod)):
            targets.append(("method", member.__func__))
        elif isinstance(member, FunctionType):
            targets.append(("method", member))
        elif inspect.isclass(member):
            check_class(member, seen_classes)
            continue
        else:
            continue

        for kind, func in targets:
            if func is None:
                continue
            if not own_doc(func):
                inherited = has_doc(getattr(cls, name, None))
                tag = kind + (" (inherits doc)" if inherited else "")
                findings.append((tag, f"{cname}.{name}", cls.__module__))


def main():
    seen_classes = set()
    modules = []
    for p in PACKAGES:
        modules.extend(all_modules(p))

    for mod_name in modules:
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            print(f"!! could not import {mod_name}: {e}", file=sys.stderr)
            continue

        if not own_doc(mod):
            findings.append(("module", mod_name, mod_name))

        for name, obj in vars(mod).items():
            if name.startswith("_") or isinstance(obj, ModuleType):
                continue
            defining = getattr(obj, "__module__", None)
            if not owned(defining):
                continue  # re-export from elsewhere, or a third-party/stdlib object
            if inspect.isclass(obj):
                check_class(obj, seen_classes)
            elif inspect.isfunction(obj):
                if not own_doc(obj):
                    findings.append(("function", f"{defining}.{obj.__qualname__}", defining))

    # group by package, then module
    by_pkg = {}
    for kind, name, mod in findings:
        by_pkg.setdefault(mod.split(".")[0], {}).setdefault(mod, []).append((kind, name))

    total = 0
    for pkg in PACKAGES:
        mods = by_pkg.get(pkg)
        if not mods:
            continue
        count = sum(len(v) for v in mods.values())
        total += count
        print(f"\n{'=' * 70}\n{pkg}  —  {count} undocumented\n{'=' * 70}")
        for mod in sorted(mods):
            print(f"\n  {mod}")
            for kind, name in sorted(mods[mod], key=lambda x: x[1]):
                short = name[len(mod) + 1:] if name.startswith(mod + ".") else name
                print(f"      [{kind}] {short}")
    print(f"\n\nTOTAL: {total} undocumented public entries")


if __name__ == "__main__":
    main()
