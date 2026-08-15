#include "lib_b.hpp"

double lib_b_compute(int seed) {
    return run_kernel_lib_b_0(static_cast<double>(seed + 0)) + run_kernel_lib_b_1(static_cast<double>(seed + 1));
}
