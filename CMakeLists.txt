# SPDX-License-Identifier: GPL-3.0-or-later
cmake_minimum_required(VERSION 3.25)

project(RPTP VERSION 0.1.0 LANGUAGES CXX)

find_package(Python3 3.10 REQUIRED COMPONENTS Interpreter)
include(CTest)

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

if(BUILD_TESTING)
    add_test(
        NAME artifact_guard
        COMMAND "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tools/check_forbidden_artifacts.py" --root "${PROJECT_SOURCE_DIR}"
    )
    add_test(
        NAME python_unit_tests
        COMMAND "${Python3_EXECUTABLE}" -m unittest discover -s tests -v
    )
    add_test(
        NAME gate0_differential_spike
        COMMAND "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tools/rptp_gate0_spike.py"
                --out "${CMAKE_BINARY_DIR}/gate0" --compiler "${RPTP_GATE0_COMPILER}"
    )
    set_tests_properties(
        artifact_guard python_unit_tests gate0_differential_spike
        PROPERTIES WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    )
endif()

add_custom_target(
    rptp-ci
    COMMAND "${CMAKE_CTEST_COMMAND}" --output-on-failure
    DEPENDS rptp-doctor
    WORKING_DIRECTORY "${CMAKE_BINARY_DIR}"
    COMMENT "Running artifact guard, unit tests and Gate 0 differential test"
    USES_TERMINAL
    VERBATIM
)
