#include "lib_d.hpp"

double lib_d_compute(int seed) {
    return run_kernel_lib_d_0(static_cast<double>(seed + 0)) + run_kernel_lib_d_1(static_cast<double>(seed + 1));
}
