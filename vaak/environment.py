"""परिवेशः — lexical scopes for Vāk.

Each block, function call and loop body gets its own Environment whose
`parent` is the scope that encloses it, forming the scope chain.
"""

from __future__ import annotations

from typing import Any

from .errors import RuntimeVakError


class Environment:
    __slots__ = ("values", "constants", "types", "parent")

    # `values` is a dict, and a dict remembers the order things were put
    # in it — so the nth binding of a scope is the nth key, which is what
    # a slot-resolved instruction asks for.  Nothing is ever removed from
    # a scope, and redefining a name keeps its place, so the numbering a
    # chunk was compiled against stays true while it runs.

    def __init__(self, parent: "Environment | None" = None):
        self.values: dict[str, Any] = {}
        self.constants: set[str] = set()
        self.types: dict[str, str] = {}      # declared प्रकारः, if any
        self.parent = parent

    # -- declaration -------------------------------------------------------
    def define(self, name: str, value: Any, constant: bool = False, line: int = 0,
               declared: str = "किमपि") -> None:
        if name in self.values and name in self.constants:
            raise RuntimeVakError(
                f"ध्रुवः {name!r} पुनः न परिवर्तनीयः / constant {name!r} cannot be redefined",
                line, code="ध्रुवदोषः",
            )
        self.values[name] = value
        if constant:
            self.constants.add(name)
        else:
            self.constants.discard(name)
        if declared and declared != "किमपि":
            self.types[name] = declared
        else:
            self.types.pop(name, None)

    # -- lookup ------------------------------------------------------------
    def binding(self, hops: int, slot: int, name: str) -> "Environment | None":
        """स्थानम् — the scope a resolved instruction means, if it really holds
        `name` at `slot`.  None asks the caller to search by name instead."""
        env: Environment | None = self
        for _ in range(hops):
            if env is None:
                return None
            env = env.parent
        if env is None or slot >= len(env.values):
            return None
        for index, key in enumerate(env.values):
            if index == slot:
                return env if key == name else None
        return None

    def get(self, name: str, line: int = 0) -> Any:
        env: Environment | None = self
        while env is not None:
            if name in env.values:
                return env.values[name]
            env = env.parent
        raise RuntimeVakError(
            f"अपरिभाषितम् नाम {name!r} / undefined name {name!r}", line, code="नामदोषः"
        )

    def has(self, name: str) -> bool:
        env: Environment | None = self
        while env is not None:
            if name in env.values:
                return True
            env = env.parent
        return False

    # -- mutation ----------------------------------------------------------
    def assign(self, name: str, value: Any, line: int = 0) -> Any:
        from .values import check_type

        env: Environment | None = self
        while env is not None:
            if name in env.values:
                if name in env.constants:
                    raise RuntimeVakError(
                        f"ध्रुवः {name!r} न परिवर्तनीयः / cannot reassign the constant {name!r}",
                        line, code="ध्रुवदोषः",
                    )
                if name in env.types:            # the declared प्रकारः is binding
                    check_type(value, env.types[name], f"चरः {name!r}", line)
                env.values[name] = value
                return value
            env = env.parent
        raise RuntimeVakError(
            f"अपरिभाषितम् नाम {name!r} — प्रथमम् 'मान' इति उपयुज्यताम् / "
            f"undefined name {name!r} — declare it with 'मान' first",
            line, code="नामदोषः",
        )
