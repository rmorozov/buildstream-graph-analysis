#include <cstdio>
#include "app.hpp"

int main() {
    std::size_t acc = 0;
    acc += app_probe_0(acc + 0);
    acc += app_probe_1(acc + 1);
    std::printf("%zu\n", acc);
    return 0;
}
