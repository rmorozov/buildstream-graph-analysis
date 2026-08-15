#include "lib_a.hpp"

double lib_a_compute(int seed) {
    return run_kernel_lib_a_0(static_cast<double>(seed + 0)) + run_kernel_lib_a_1(static_cast<double>(seed + 1));
}
