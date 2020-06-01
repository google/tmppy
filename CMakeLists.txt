cmake_minimum_required(VERSION 3.2)
project(TMPPy VERSION 3.5.0 LANGUAGES CXX)

find_program(PYTHON
             NAMES python3.8 python3)

add_custom_command(OUTPUT builtins.tmppyc
                   WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
                   COMMAND PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR} ${PYTHON} _py2tmp/compiler/_generate_ir0_builtins.py -o ${CMAKE_CURRENT_BINARY_DIR}/builtins.tmppyc
                   )

add_custom_command(OUTPUT builtins_for_coverage.tmppyc
                   WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
                   COMMAND PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR} ${PYTHON} _py2tmp/compiler/_generate_ir0_builtins.py -o ${CMAKE_CURRENT_BINARY_DIR}/builtins_for_coverage.tmppyc --enable_coverage=true
                   )

add_custom_target(builtins-tmppyc ALL
                  DEPENDS builtins.tmppyc builtins_for_coverage.tmppyc)

option(TMPPY_TESTS_USE_PRECOMPILED_HEADERS "Whether to use pre-compiled headers (PCHs) in TMPPy tests." ON)

set(TMPPY_COMPILE_FLAGS "${CMAKE_CXX_FLAGS} -W -Wall -g0 -Werror -std=c++11")

if ("${TMPPY_TESTS_USE_PRECOMPILED_HEADERS}")
    if ("${CMAKE_CXX_COMPILER_ID}" STREQUAL "GNU")
        add_custom_command(
            OUTPUT tmppy-precompiled.h.gch
            WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
            DEPENDS include/tmppy/tmppy.h
            COMMAND bash -c "${CMAKE_CXX_COMPILER} -x c++-header ${TMPPY_COMPILE_FLAGS} -I${CMAKE_CURRENT_SOURCE_DIR}/include -I${CMAKE_CURRENT_BINARY_DIR}/include ${CMAKE_CURRENT_SOURCE_DIR}/include/tmppy/tmppy.h -o tmppy-precompiled.h.gch")
        add_custom_target(tmppy-precompiled-header ALL DEPENDS tmppy-precompiled.h.gch)
        # Note that the "tmppy-precompiled.h" header doesn't exist, but it's ok because GCC looks for
        # tmppy-precompiled.h.gch first. We don't call the precompiled header tmppy.h.gch so that if GCC doesn't
        # find it it reports an error instead of using the normal header.
        set(TMPPY_TESTONLY_CXXFLAGS "-include${CMAKE_CURRENT_BINARY_DIR}/tmppy-precompiled.h")

    elseif("${CMAKE_CXX_COMPILER_ID}" MATCHES "^(Clang|AppleClang)$")
        add_custom_command(
            OUTPUT tmppy.pch
            WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
            DEPENDS include/tmppy/tmppy.h
            COMMAND bash -c "${CMAKE_CXX_COMPILER} -x c++-header ${TMPPY_COMPILE_FLAGS} -I${CMAKE_CURRENT_SOURCE_DIR}/include -I${CMAKE_CURRENT_BINARY_DIR}/include ${CMAKE_CURRENT_SOURCE_DIR}/include/tmppy/tmppy.h -o tmppy.pch")
        add_custom_target(tmppy-precompiled-header ALL DEPENDS tmppy.pch)
        set(TMPPY_TESTONLY_CXXFLAGS "-include-pch ${CMAKE_CURRENT_BINARY_DIR}/tmppy.pch")
    else()
        message(ERROR "Using pre-compiled headers in tests is only supported with GCC and Clang. Please add -DTMPPY_TESTS_USE_PRECOMPILED_HEADERS=OFF to your cmake invocation and try again.")
    endif()
else()
    set(TMPPY_TESTONLY_CXXFLAGS "")
endif()

file(GENERATE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/py2tmp_test_config.py"
     CONTENT "
CXX='${CMAKE_CXX_COMPILER}'
CXX_COMPILER_NAME='${CMAKE_CXX_COMPILER_ID}'
CXX_COMPILER_VERSION='${CMAKE_CXX_COMPILER_VERSION}'
ADDITIONAL_COMPILER_FLAGS='${TMPPY_TESTONLY_CXXFLAGS} ${TMPPY_COMPILE_FLAGS}'
ADDITIONAL_LINKER_FLAGS='${CMAKE_EXE_LINKER_FLAGS}'
CMAKE_BUILD_TYPE='${CMAKE_BUILD_TYPE}'
MPYL_INCLUDE_DIR='${CMAKE_CURRENT_SOURCE_DIR}/include'
")

file(GENERATE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/pytest.ini"
     CONTENT "
[pytest]
testpaths = \"${CMAKE_CURRENT_SOURCE_DIR}/_py2tmp\" \"${CMAKE_CURRENT_SOURCE_DIR}/extras/examples\"
addopts = -r a --tb=short -p py2tmp.testing.pytest_plugin --tmppyc_files \"${CMAKE_CURRENT_BINARY_DIR}/extras/examples/example.tmppyc\"
")

file(GENERATE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/conftest.py"
     CONTENT "
")

file(GENERATE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/.coveragerc"
     CONTENT "
[run]
source = ${CMAKE_CURRENT_SOURCE_DIR}
omit =
  */tests/*
  testing/*
  */testing/*
# Enable branch coverage
branch = True
plugins =
    _py2tmp.coverage

[paths]
source =
    _py2tmp/
    */_py2tmp
[report]
# Regexes for lines to exclude from consideration
exclude_lines =
    pragma: no cover
    raise NotImplementedError
    : \.\.\.
")

add_subdirectory(_py2tmp)
add_subdirectory(extras)
