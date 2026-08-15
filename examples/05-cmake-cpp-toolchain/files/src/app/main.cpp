#include <cstdio>
#include "core.hpp"
#include "lib_a.hpp"
#include "lib_b.hpp"
#include "lib_c.hpp"
#include "lib_d.hpp"

int main() {
    double total = core_compute(1) + lib_a_compute(2) + lib_b_compute(3)
                 + lib_c_compute(4) + lib_d_compute(5);
    std::printf("total=%f\n", total);
    return 0;
}
