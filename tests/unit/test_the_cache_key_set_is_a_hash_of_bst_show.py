"""UX-844: the tracer's report records `cache_key_set` -
`hash_cache_key_lines`'s digest of one pre-build `bst show --format
'%{name} %{full-key}'`, so a later capture is comparable against it
without carrying the raw key lines. Pure - fed pasted `bst show` output,
never a live binary.
"""
from tools import bst_native_build_tracer as tracer

_TWO_LINES = (
    "base.bst 4a9059d4a6baa1bba27a9fecc0b7b838b60540e6f5d7cff43d549bb54fca9bf6\n"
    "app.bst 6a4dd258b5e3c6fd3f9190bc8811936bbba00a0bb97d61c10f1d1d5bcb1403b2\n"
)


def test_zero_lines_hashes_the_empty_string():
    result = tracer.hash_cache_key_lines("")
    assert result["elements"] == 0
    # Whitespace-only input is zero lines too, and hashes the same way.
    assert result == tracer.hash_cache_key_lines("   \n\n")


def test_one_line_counts_one_element():
    result = tracer.hash_cache_key_lines("base.bst deadbeef\n")
    assert result["elements"] == 1


def test_many_lines_are_order_independent():
    """The two `bst show` runs this guards do not promise the same
    resolution order - only the same key set."""
    forward = tracer.hash_cache_key_lines(_TWO_LINES)
    backward = tracer.hash_cache_key_lines(
        "\n".join(reversed(_TWO_LINES.strip().splitlines())) + "\n"
    )
    assert forward == backward
    assert forward["elements"] == 2


def test_a_different_key_for_the_same_name_changes_the_hash():
    one = tracer.hash_cache_key_lines("app.bst aaaa\n")
    two = tracer.hash_cache_key_lines("app.bst bbbb\n")
    assert one["sha256"] != two["sha256"]
    assert one["elements"] == two["elements"] == 1


def test_blank_lines_are_not_counted():
    result = tracer.hash_cache_key_lines("base.bst deadbeef\n\n\napp.bst cafef00d\n")
    assert result["elements"] == 2
