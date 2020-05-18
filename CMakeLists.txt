cmake_minimum_required(VERSION 3.2)
project(TMPPy VERSION 3.5.0 LANGUAGES CXX)

add_custom_command(OUTPUT builtins.tmppyc
                   WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
                   COMMAND PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR} python3.8 _py2tmp/compiler/_generate_ir0_builtins.py -o ${CMAKE_CURRENT_BINARY_DIR}/builtins.tmppyc
                   )

add_custom_target(builtins-tmppyc ALL
                  DEPENDS builtins.tmppyc)

option(TMPPY_TESTS_USE_PRECOMPILED_HEADERS "Whether to use pre-compiled headers (PCHs) in TMPPy tests." ON)

set(TMPPY_COMPILE_FLAGS
"-W -Wall -g0 -Werror -Wno-error=tautological-compare -std=c++11")

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
ADDITIONAL_COMPILER_FLAGS='${TMPPY_TESTONLY_CXXFLAGS}'
ADDITIONAL_LINKER_FLAGS='${CMAKE_EXE_LINKER_FLAGS}'
CMAKE_BUILD_TYPE='${CMAKE_BUILD_TYPE}'
MPYL_INCLUDE_DIR='${CMAKE_CURRENT_SOURCE_DIR}/include'
")

file(GENERATE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/pytest.ini"
     CONTENT "
[pytest]
testpaths = \"${CMAKE_CURRENT_SOURCE_DIR}/_py2tmp\"
addopts = -r a --tb=short
")

file(GENERATE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/conftest.py"
     CONTENT "
")

add_subdirectory(_py2tmp)
