# SPDX-License-Identifier: GPL-3.0-or-later
cmake_minimum_required(VERSION 3.25)

project(RPTP VERSION 0.1.0 LANGUAGES CXX)

find_package(Python3 3.10 REQUIRED COMPONENTS Interpreter)
include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

function(rptp_enable_strict_warnings target)
    if(MSVC)
        target_compile_options("${target}" PRIVATE /W4 /WX /permissive-)
    else()
        target_compile_options("${target}" PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
endfunction()

if(MSVC)
    set(_rptp_default_gate0_compiler "cl")
else()
    set(_rptp_default_gate0_compiler "auto")
endif()

set(
    RPTP_GATE0_COMPILER
    "${_rptp_default_gate0_compiler}"
    CACHE STRING "C++ compiler executable used by the Gate 0 generated-code spike"
)

add_custom_target(
    rptp-doctor
    COMMAND "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tools/rptp_doctor.py" --root "${PROJECT_SOURCE_DIR}"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMENT "Checking RPTP build environment and repository hygiene"
    USES_TERMINAL
    VERBATIM
)

add_library(
    rptp_runtime
    STATIC
    runtime/src/elf_loader.cpp
    runtime/src/guest_memory.cpp
)
target_include_directories(rptp_runtime PUBLIC "${PROJECT_SOURCE_DIR}/runtime/include")
target_compile_features(rptp_runtime PUBLIC cxx_std_20)
rptp_enable_strict_warnings(rptp_runtime)

add_executable(rptp-load runtime/tools/rptp_load.cpp)
target_link_libraries(rptp-load PRIVATE rptp_runtime)
rptp_enable_strict_warnings(rptp-load)

if(BUILD_TESTING)
    function(rptp_add_python_test name)
        add_test(
            NAME "${name}"
            COMMAND "${Python3_EXECUTABLE}" ${ARGN}
        )
        set_tests_properties(
            "${name}"
            PROPERTIES WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
        )
    endfunction()

    rptp_add_python_test(
        artifact_guard
        "${PROJECT_SOURCE_DIR}/tools/check_forbidden_artifacts.py" --root "${PROJECT_SOURCE_DIR}"
    )
    rptp_add_python_test(
        python_unit_tests
        -m unittest discover -s tests -v
    )
    rptp_add_python_test(
        gate0_differential_spike
        "${PROJECT_SOURCE_DIR}/tools/rptp_gate0_spike.py"
        --out "${CMAKE_BINARY_DIR}/gate0" --compiler "${RPTP_GATE0_COMPILER}"
    )

    add_executable(rptp-runtime-tests runtime/tests/runtime_tests.cpp)
    target_link_libraries(rptp-runtime-tests PRIVATE rptp_runtime)
    rptp_enable_strict_warnings(rptp-runtime-tests)
    add_test(NAME runtime_loader_tests COMMAND rptp-runtime-tests)
    set_tests_properties(
        runtime_loader_tests
        PROPERTIES WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    )
    add_test(
        NAME runtime_loader_cli
        COMMAND "${CMAKE_COMMAND}" -E env "RPTP_LOAD_BINARY=$<TARGET_FILE:rptp-load>"
                "${Python3_EXECUTABLE}" -m unittest tests.test_runtime_loader -v
    )
    set_tests_properties(
        runtime_loader_cli
        PROPERTIES WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    )
    set(_rptp_runtime_test_target rptp-runtime-tests)
else()
    set(_rptp_runtime_test_target "")
endif()

add_custom_target(
    rptp-ci
    COMMAND "${CMAKE_CTEST_COMMAND}" --output-on-failure
    DEPENDS rptp-doctor rptp-load ${_rptp_runtime_test_target}
    WORKING_DIRECTORY "${CMAKE_BINARY_DIR}"
    COMMENT "Running artifact guard, unit tests and Gate 0 differential test"
    USES_TERMINAL
    VERBATIM
)
