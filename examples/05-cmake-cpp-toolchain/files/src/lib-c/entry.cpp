#include "lib_c.hpp"

double lib_c_compute(int seed) {
    return run_kernel_lib_c_0(static_cast<double>(seed + 0)) + run_kernel_lib_c_1(static_cast<double>(seed + 1));
}
