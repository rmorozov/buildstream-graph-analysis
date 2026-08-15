#!/usr/bin/env python3
"""One-time source generator for this example's real C++ modules (P4-16 /
UX-05 round 2). Not run at build time - the *output* of this script is
what's committed and what BuildStream actually compiles, so the example
stays fully self-contained (no python needed inside the sandbox, matching
every other example project's "real, committed source" convention).

Produces real, valid, compilable C++ that takes a genuinely tunable
amount of gcc time to compile - the real-workload analogue of
examples/04-critical-path-optimization's `sleep N` durations, so this
project's critical path/fan-out shape is just as deliberately designed,
but now exercises a real native build system (cmake + make) instead of a
proxy.

Calibration note: an early version of this generator used template-heavy
matrix-multiply kernels, expecting that to be slow to compile. Measured
directly (`time g++ -O2 -c ...`) it compiled in under 0.1s regardless of
matrix size - `-O2`'s loop optimizer doesn't fully unroll/inline that
shape of code, so it never became a real CPU cost. What actually scales
gcc's own compile time close to linearly (confirmed: ~4000 arithmetic
statements in one function body ~= 1.5s, ~30000 ~= 37s) is a large
straight-line sequence of scalar floating-point statements in a single
function body - `-O2`'s scheduling/optimization passes are working over
the whole basic block. That's what each generated file below does.
"""
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "files", "src")

# (file_count, lines_per_file) per module - tuned against this real
# toolchain (examples/stage_cpp_toolchain.sh) so each file takes ~1.5-2s
# of real gcc compile time. core is the deliberate single-slowest,
# highest-blast-radius module (5 downstream: lib-a..d + app) - mirrors
# examples/04-critical-path-optimization's core.bst (sleep 4) design
# intent, but with real work; lib-a..d are a genuine 4-way fan-out, each
# with multiple files so `make -j` (real intra-element parallelism) has
# real work to distribute - the whole point of this round's experiment
# (see docs/scenarios/UX-09-builders-max-jobs-joint-optimization.md).
MODULE_CONFIG = {
    "core": (4, 5000),
    "lib-a": (2, 4000),
    "lib-b": (2, 4000),
    "lib-c": (2, 4000),
    "lib-d": (2, 4000),
}


def generate_heavy_function(name: str, num_lines: int, seed: int) -> str:
    rng = random.Random(seed)
    lines = [f"double {name}(double x) {{"]
    for _ in range(num_lines):
        a, b, c = rng.random(), rng.random(), rng.random()
        lines.append(f"    x = x * {a:.6f} + {b:.6f} - x / ({c:.6f} + 1.0);")
    lines.append("    return x;")
    lines.append("}")
    return "\n".join(lines)


def generate_module(module: str, file_count: int, lines_per_file: int):
    mod_dir = os.path.join(SRC, module)
    os.makedirs(mod_dir, exist_ok=True)
    sym = module.replace("-", "_")  # C++ identifiers can't contain "-"
    header_path = os.path.join(mod_dir, f"{sym}.hpp")
    guard = f"{module.upper().replace('-', '_')}_HPP"
    decls = "\n".join(
        f"double run_kernel_{sym}_{i}(double x);" for i in range(file_count)
    )
    with open(header_path, "w") as f:
        f.write(
            f"#ifndef {guard}\n#define {guard}\n\n{decls}\n\n"
            f"double {sym}_compute(int seed);\n\n#endif\n"
        )

    for i in range(file_count):
        cpp_path = os.path.join(mod_dir, f"generated_{i}.cpp")
        with open(cpp_path, "w") as f:
            f.write(f'#include "{sym}.hpp"\n\n')
            f.write(generate_heavy_function(f"run_kernel_{sym}_{i}", lines_per_file, seed=hash((module, i)) & 0xFFFF))
            f.write("\n")

    entry_path = os.path.join(mod_dir, "entry.cpp")
    calls = " + ".join(f"run_kernel_{sym}_{i}(static_cast<double>(seed + {i}))" for i in range(file_count))
    with open(entry_path, "w") as f:
        f.write(f'#include "{sym}.hpp"\n\n')
        f.write(f"double {sym}_compute(int seed) {{\n")
        f.write(f"    return {calls};\n}}\n")


def main():
    for module, (file_count, lines_per_file) in MODULE_CONFIG.items():
        generate_module(module, file_count, lines_per_file)
    print(f"Generated sources for {len(MODULE_CONFIG)} modules under {SRC}")


if __name__ == "__main__":
    main()
