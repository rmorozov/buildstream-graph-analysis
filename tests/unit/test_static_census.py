"""UX-105: the blind spot, measured instead of disclaimed.

Every Plane 2 report carried one footnote - statically-linked processes
ran but produced no trace entry, and the hook "cannot detect its own
absence". Honest and useless in equal measure: it fired identically on a
capture that missed nothing and on `examples/01`, whose entire process
list is empty because every command it runs is static busybox.

Whether a binary is static is knowable before anything runs, from the
file on disk.
"""
import struct

import pytest

from tools.bst_native_build_tracer import (
    census_project, census_static_executables, classify_elf,
)


def _elf(path, *, e_type, interp: bool, bits=64, endian="<"):
    """A minimal but structurally real ELF file.

    Written by hand rather than fixtured from a binary: the point of
    these tests is the header arithmetic, and a checked-in binary would
    make it a test about one machine's `/bin`.
    """
    ph_entsize = 56 if bits == 64 else 32
    ph_off = 64 if bits == 64 else 52
    header = bytearray(ph_off)
    header[0:4] = b"\x7fELF"
    header[4] = 2 if bits == 64 else 1
    header[5] = 1 if endian == "<" else 2
    struct.pack_into(endian + "H", header, 16, e_type)
    if bits == 64:
        struct.pack_into(endian + "Q", header, 32, ph_off)
        struct.pack_into(endian + "HH", header, 54, ph_entsize, 1)
    else:
        struct.pack_into(endian + "I", header, 28, ph_off)
        struct.pack_into(endian + "HH", header, 42, ph_entsize, 1)
    program_header = bytearray(ph_entsize)
    struct.pack_into(endian + "I", program_header, 0, 3 if interp else 1)  # PT_INTERP/PT_LOAD
    path.write_bytes(bytes(header) + bytes(program_header))
    path.chmod(0o755)
    return path


def test_an_executable_without_pt_interp_is_static(tmp_path):
    """The whole of Plane 2's blind spot: no `PT_INTERP` means the
    dynamic linker is never invoked, so `LD_PRELOAD` never reaches it."""
    assert classify_elf(str(_elf(tmp_path / "busybox", e_type=2, interp=False))) == "static"


def test_an_executable_with_pt_interp_is_dynamic(tmp_path):
    assert classify_elf(str(_elf(tmp_path / "sh", e_type=2, interp=True))) == "dynamic"


def test_a_pie_executable_is_dynamic_not_static(tmp_path):
    """A PIE is `ET_DYN` *with* `PT_INTERP`, and most distributions ship
    every binary that way - reading `ET_DYN` as "not an executable"
    would blind the census to nearly everything."""
    assert classify_elf(str(_elf(tmp_path / "pie", e_type=3, interp=True))) == "dynamic"


def test_a_shared_library_is_neither(tmp_path):
    """The correction the first real run forced: `examples/06`'s staged
    glibc toolchain reported five "static executables" that were
    `ld-linux-x86-64.so.2` and three copies of `liblto_plugin.so`.
    Shared objects have no `PT_INTERP` either - they are loaded, not
    exec'd - so `PT_INTERP` alone calls every library on the system a
    static binary."""
    assert classify_elf(str(_elf(tmp_path / "libfoo.so", e_type=3, interp=False))) == "library"


@pytest.mark.parametrize("bits,endian", [(64, "<"), (32, "<"), (64, ">"), (32, ">")])
def test_both_widths_and_both_endiannesses_are_read(tmp_path, bits, endian):
    """A cross-built sysroot is exactly the case where this question
    matters, so the header arithmetic cannot assume the host's shape."""
    path = _elf(tmp_path / f"bin-{bits}-{endian}", e_type=2, interp=False,
                bits=bits, endian=endian)
    assert classify_elf(str(path)) == "static"


def test_a_non_elf_file_is_not_classified(tmp_path):
    plain = tmp_path / "notes.txt"
    plain.write_text("hello")
    assert classify_elf(str(plain)) is None


def test_a_truncated_header_is_unclassified_rather_than_static(tmp_path):
    """"Not classifiable" and "not static" are different answers and
    only one of them is safe to act on."""
    stub = tmp_path / "truncated"
    stub.write_bytes(b"\x7fELF\x02\x01")
    assert classify_elf(str(stub)) is None


# --- the census ---------------------------------------------------------

def test_the_census_lists_static_binaries_and_counts_the_rest(tmp_path):
    root = tmp_path / "root"
    (root / "bin").mkdir(parents=True)
    _elf(root / "bin" / "busybox", e_type=2, interp=False)
    _elf(root / "bin" / "sh", e_type=2, interp=True)
    (root / "lib").mkdir(parents=True)
    _elf(root / "lib" / "libc.so", e_type=3, interp=False)
    census = census_static_executables(str(root))
    assert census["static"] == ["bin/busybox"]
    assert census["dynamic"] == 1
    assert census["libraries"] == 1


def test_a_script_is_classified_as_its_interpreter(tmp_path):
    """The interpreter is the process that execs, and so the one the
    hook either sees or does not."""
    root = tmp_path / "root"
    (root / "bin").mkdir(parents=True)
    _elf(root / "bin" / "busybox", e_type=2, interp=False)
    script = root / "bin" / "build.sh"
    script.write_text("#!/bin/busybox sh\necho hi\n")
    script.chmod(0o755)
    census = census_static_executables(str(root))
    assert census["scripts"] == 1
    assert census["static"] == ["bin/build.sh", "bin/busybox"]


def test_a_non_executable_file_is_not_censused(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    binary = _elf(root / "data.bin", e_type=2, interp=False)
    binary.chmod(0o644)
    assert census_static_executables(str(root))["static"] == []


def test_a_missing_root_is_empty_rather_than_an_error(tmp_path):
    """A census that dies on a path that is not there is a census nobody
    runs from a capture path."""
    assert census_static_executables(str(tmp_path / "nope"))["static"] == []


# --- per-element attribution --------------------------------------------

def _project(tmp_path):
    """A two-element project: one imports a static binary, the other
    build-depends on it - which is `examples/01`'s exact shape."""
    project = tmp_path / "project"
    (project / "elements").mkdir(parents=True)
    (project / "files" / "runtime" / "bin").mkdir(parents=True)
    _elf(project / "files" / "runtime" / "bin" / "busybox", e_type=2, interp=False)
    (project / "elements" / "runtime.bst").write_text(
        "kind: import\nsources:\n- kind: local\n  path: files/runtime\n"
    )
    (project / "elements" / "work.bst").write_text(
        "kind: manual\ndepends:\n- filename: runtime.bst\n  type: build\n"
    )
    return project


def test_an_element_inherits_what_its_dependencies_stage(tmp_path):
    """An element's sandbox holds what its build closure staged, so the
    element that *runs* the static binary is the one worth naming - not
    only the one that imported it."""
    census = census_project(str(_project(tmp_path)), ["runtime.bst", "work.bst"])
    assert census["elements_at_risk"] == ["runtime.bst", "work.bst"]
    work = census["per_element"]["work.bst"]
    assert work["own_static"] == []
    assert work["static_executables"] == ["bin/busybox"]
    assert work["staged_by_dependencies"] == {"runtime.bst": ["bin/busybox"]}


def test_the_payload_states_what_it_cannot_see(tmp_path):
    """A zero here is "nothing this project stages is static", not
    "nothing static will run" - a binary from a remote artifact cache or
    produced by the build is outside it, and that is the limit `UX-106`
    exists to close."""
    census = census_project(str(_project(tmp_path)), ["runtime.bst"])
    assert "remote artifact cache" in census["note"]
    assert "bounds what Plane 2 can miss, not what it did miss" in census["note"]


def test_two_censuses_of_one_project_are_identical(tmp_path):
    project = str(_project(tmp_path))
    assert census_project(project, ["runtime.bst", "work.bst"]) == census_project(
        project, ["runtime.bst", "work.bst"]
    )
