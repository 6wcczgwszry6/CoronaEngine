include_guard(GLOBAL)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# UTF-8 source/execution charset is enforced globally in
# misc/cmake/corona_compile_config.cmake via /utf-8.

add_compile_definitions(
    NOMINMAX
    _CRT_SECURE_NO_WARNINGS
)