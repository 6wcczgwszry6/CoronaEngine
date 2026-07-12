#include "../optics_debug_labels.h"

#include <cassert>

int main() {
    assert(!Corona::Systems::OpticsDetail::debug_labels_enabled(false));
    assert(Corona::Systems::OpticsDetail::debug_labels_enabled(true));
    return 0;
}
