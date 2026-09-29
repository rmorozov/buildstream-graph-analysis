"""UX-1069: a JSON member read record by record under its disclosure trie.

The reader walks literal keys token by token and decodes whole only a
value whose subtrie repeats nowhere below, so memory is bounded by one
record and a sliding buffer, not by the member. It yields events:

    ("open", "{" | "[")  ("close", "}" | "]")  ("end",)  a document ends
    ("key", name, klass)  klass: the placeholder's class, None for a literal
    ("record", node, pattern, path, value)
    ("gap", disclosure.Gap)  the value under it is skipped child by child

`pattern` names the policy path (`{A}`, `[]`), `path` the document's.
"""

import json
import re
from collections.abc import Iterator

from . import disclosure

CHUNK = 65536

_DECODER = json.JSONDecoder()
_TOKEN = re.compile(r"[^ \t\n\r]")
_DELIMITERS = frozenset(" \t\n\r,:]}")


class _Buffer:
    """A sliding window over a text handle; a decode not followed by a
    delimiter waits for more, since `1` of `1.5` decodes alone."""

    def __init__(self, handle, chunk: int):
        self.handle, self.chunk = handle, chunk
        self.text, self.pos, self.eof = "", 0, False

    def _fill(self, want: int = 0) -> bool:
        if self.eof:
            return False
        data = self.handle.read(max(self.chunk, want))
        if not data:
            self.eof = True
            return False
        self.text = self.text[self.pos :] + data
        self.pos = 0
        return True

    def peek(self) -> str:
        """The next non-space character, `""` at the end of the handle."""
        while True:
            token = _TOKEN.search(self.text, self.pos)
            if token is not None:
                self.pos = token.start()
                return self.text[self.pos]
            self.pos = len(self.text)
            if not self._fill():
                return ""

    def take(self, char: str) -> None:
        if self.peek() != char:
            raise ValueError(f"expecting {char!r} at {self.peek()!r}")
        self.pos += 1

    def decode(self):
        self.peek()
        while True:
            try:
                value, end = _DECODER.raw_decode(self.text, self.pos)
            except json.JSONDecodeError:
                if self._fill(len(self.text) - self.pos):
                    continue
                raise
            if (end < len(self.text) and self.text[end] in _DELIMITERS) or not self._fill(len(self.text) - self.pos):
                self.pos = end
                return value


def _join(pattern: str, step: str) -> str:
    return f"{pattern}.{step}" if pattern else step


class _Reader:
    def __init__(self, handle, chunk: int):
        self.buffer = _Buffer(handle, chunk)
        self.repeats: dict = {}

    def _repeats(self, node: dict) -> bool:
        """Whether the policy repeats anywhere under `node`: then it is walked, not decoded."""
        found = self.repeats.get(id(node))
        if found is None:
            found = any(k.startswith(("{", "[")) or (k != "." and self._repeats(v)) for k, v in node.items())
            self.repeats[id(node)] = found
        return found

    def _skip(self) -> None:
        """An unnamed value, consumed one child at a time."""
        buffer = self.buffer
        char = buffer.peek()
        if not char or char not in "{[":
            buffer.decode()
            return
        closer = "}" if char == "{" else "]"
        buffer.pos += 1
        if buffer.peek() == closer:
            buffer.pos += 1
            return
        while True:
            if char == "{":
                buffer.decode()
                buffer.take(":")
            buffer.decode()
            if buffer.peek() == ",":
                buffer.pos += 1
                continue
            buffer.take(closer)
            return

    def value(self, node: dict, pattern: str, path: str) -> Iterator[tuple]:
        buffer = self.buffer
        char = buffer.peek()
        if char == "{" and self._repeats(node):
            if not any(not k.startswith(("[", ".")) for k in node):
                yield ("gap", disclosure.Gap(path, "a map where the policy names none"))
                self._skip()
                return
            yield from self._map(node, pattern, path)
        elif char == "[" and self._repeats(node):
            if "[]" not in node:
                yield ("gap", disclosure.Gap(path, "an array where the policy names none"))
                self._skip()
                return
            yield from self._array(node["[]"], pattern + "[]", path + "[]")
        else:
            yield ("record", node, pattern, path, buffer.decode())

    def _map(self, node: dict, pattern: str, path: str) -> Iterator[tuple]:
        buffer = self.buffer
        buffer.pos += 1
        yield ("open", "{")
        if buffer.peek() == "}":
            buffer.pos += 1
            yield ("close", "}")
            return
        while True:
            key = buffer.decode()
            if not isinstance(key, str):
                raise ValueError(f"a key that is not a string: {key!r}")
            buffer.take(":")
            step = disclosure.step(node, key, path)
            for gap in step.gaps:
                yield ("gap", gap)
            if step.node is None:
                self._skip()
            else:
                yield ("key", key, step.name[1:-1] if step.name.startswith("{") else None)
                yield from self.value(step.node, _join(pattern, step.name), step.path)
            if buffer.peek() == ",":
                buffer.pos += 1
                continue
            buffer.take("}")
            yield ("close", "}")
            return

    def _array(self, node: dict, pattern: str, path: str) -> Iterator[tuple]:
        buffer = self.buffer
        buffer.pos += 1
        yield ("open", "[")
        if buffer.peek() == "]":
            buffer.pos += 1
            yield ("close", "]")
            return
        while True:
            yield from self.value(node, pattern, path)
            if buffer.peek() == ",":
                buffer.pos += 1
                continue
            buffer.take("]")
            yield ("close", "]")
            return


def events(handle, trie: dict, many: bool = False) -> Iterator[tuple]:
    """Every event of the one document in `handle`, or of each when `many` (`.jsonl`).

    Raises `ValueError` on text that is not JSON.
    """
    reader = _Reader(handle, CHUNK)
    count = 0
    while reader.buffer.peek():
        if count and not many:
            raise ValueError("extra data after the document")
        yield from reader.value(trie, "", "")
        yield ("end",)
        count += 1
    if not count and not many:
        raise ValueError("no document")
