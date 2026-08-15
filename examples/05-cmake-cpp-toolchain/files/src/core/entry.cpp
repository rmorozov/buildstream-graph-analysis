#include "core.hpp"

double core_compute(int seed) {
    return run_kernel_core_0(static_cast<double>(seed + 0)) + run_kernel_core_1(static_cast<double>(seed + 1)) + run_kernel_core_2(static_cast<double>(seed + 2)) + run_kernel_core_3(static_cast<double>(seed + 3));
}
