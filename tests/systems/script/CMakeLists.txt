add_executable(corona_python_lifecycle_tests
    test_python_lifecycle.cpp
)
target_include_directories(corona_python_lifecycle_tests PRIVATE
    ${PROJECT_SOURCE_DIR}/include
)
add_test(NAME PythonLifecycleTests COMMAND corona_python_lifecycle_tests)

add_executable(corona_python_runtime_coordinator_tests
    test_python_runtime_coordinator.cpp
)
target_include_directories(corona_python_runtime_coordinator_tests PRIVATE
    ${PROJECT_SOURCE_DIR}/include
)
target_link_libraries(corona_python_runtime_coordinator_tests PRIVATE
    corona::python::runtime
)
add_test(NAME PythonRuntimeCoordinatorTests COMMAND corona_python_runtime_coordinator_tests)
