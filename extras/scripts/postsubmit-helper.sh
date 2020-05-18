#!/bin/bash -x

set -e

# This only exists in OS X, but it doesn't cause issues in Linux (the dir doesn't exist, so it's
# ignored).
export PATH="/usr/local/opt/coreutils/libexec/gnubin:$PATH"

case $COMPILER in
gcc-4.9)
    export CC=gcc-4.9
    export CXX=g++-4.9
    ;;
    
gcc-5)
    export CC=gcc-5
    export CXX=g++-5
    ;;
    
gcc-6)
    export CC=gcc-6
    export CXX=g++-6
    ;;
    
gcc-7)
    export CC=gcc-7
    export CXX=g++-7
    ;;

gcc-8)
    export CC=gcc-8
    export CXX=g++-8
    ;;

gcc-9)
    export CC=gcc-9
    export CXX=g++-9
    ;;

gcc-10)
    export CC=gcc-10
    export CXX=g++-10
    ;;

clang-3.5)
    export CC=clang-3.5
    export CXX=clang++-3.5
    ;;

clang-3.6)
    export CC=clang-3.6
    export CXX=clang++-3.6
    ;;

clang-3.7)
    export CC=clang-3.7
    export CXX=clang++-3.7
    ;;

clang-3.8)
    export CC=clang-3.8
    export CXX=clang++-3.8
    ;;

clang-3.9)
    export CC=clang-3.9
    export CXX=clang++-3.9
    ;;

clang-4.0)
    export CC=clang-4.0
    export CXX=clang++-4.0
    ;;

clang-5.0)
    case "$OS" in
    linux)
        export CC=clang-5.0
        export CXX=clang++-5.0
        ;;
    osx)
        export CC=/usr/local/opt/llvm/bin/clang-5.0
        export CXX=/usr/local/opt/llvm/bin/clang++
        ;;
    *) echo "Error: unexpected OS: $OS"; exit 1 ;;
    esac
    ;;

clang-6.0)
    export CC=clang-6.0
    export CXX=clang++-6.0
    ;;

clang-7.0)
    export CC=clang-7
    export CXX=clang++-7
    ;;

clang-8.0)
    export CC=clang-8
    export CXX=clang++-8
    ;;

clang-9.0)
    export CC=clang-9
    export CXX=clang++-9
    ;;

clang-10.0)
    export CC=clang-10
    export CXX=clang++-10
    ;;

clang-default)
    export CC=clang
    export CXX=clang++
    ;;

*)
    echo "Unrecognized value of COMPILER: $COMPILER"
    exit 1
esac

run_make() {
  make -j$N_JOBS
}

COMMON_CXX_FLAGS="$STLARG -Werror -pedantic -Winvalid-pch"

echo CXX version: $($CXX --version)
echo C++ Standard library location: $(echo '#include <vector>' | $CXX -x c++ -E - | grep 'vector\"' | awk '{print $3}' | sed 's@/vector@@;s@\"@@g' | head -n 1)
echo Normalized C++ Standard library location: $(readlink -f $(echo '#include <vector>' | $CXX -x c++ -E - | grep 'vector\"' | awk '{print $3}' | sed 's@/vector@@;s@\"@@g' | head -n 1))

case "$1" in
DebugPlain)           CMAKE_ARGS=(-DCMAKE_BUILD_TYPE=Debug   -DTMPPY_TESTS_USE_PRECOMPILED_HEADERS=ON  -DCMAKE_CXX_FLAGS="$COMMON_CXX_FLAGS -D_GLIBCXX_DEBUG -O2") ;;
DebugPlainNoPch)      CMAKE_ARGS=(-DCMAKE_BUILD_TYPE=Debug   -DTMPPY_TESTS_USE_PRECOMPILED_HEADERS=OFF -DCMAKE_CXX_FLAGS="$COMMON_CXX_FLAGS -D_GLIBCXX_DEBUG -O2") ;;
ReleasePlain)         CMAKE_ARGS=(-DCMAKE_BUILD_TYPE=Release -DTMPPY_TESTS_USE_PRECOMPILED_HEADERS=ON  -DCMAKE_CXX_FLAGS="$COMMON_CXX_FLAGS") ;;
ReleasePlainNoPch)    CMAKE_ARGS=(-DCMAKE_BUILD_TYPE=Release -DTMPPY_TESTS_USE_PRECOMPILED_HEADERS=OFF -DCMAKE_CXX_FLAGS="$COMMON_CXX_FLAGS") ;;
*) echo "Error: you need to specify one of the supported postsubmit modes (see postsubmit.sh)."; exit 1 ;;
esac

# Setting compilers only via env vars doesn't work when using recent versions of XCode.
CMAKE_ARGS+=(-DCMAKE_C_COMPILER=$CC -DCMAKE_CXX_COMPILER=$CXX)

SOURCES_PATH="$PWD"

# This is not needed on Travis CI, but it's sometimes needed when running postsubmit.sh locally, to avoid "import
# file mismatch" errors.
rm -rf */__pycache__/ */*.pyc */*/__pycache__/ */*/*.pyc

rm -rf build
mkdir build
cd build
cmake .. "${CMAKE_ARGS[@]}"
echo
echo "Content of CMakeFiles/CMakeError.log:"
if [ -f "CMakeFiles/CMakeError.log" ]
then
  cat CMakeFiles/CMakeError.log
fi
echo
run_make

# We specify the path explicitly because old versions of pytest (e.g. the one in Ubuntu 14.04)
# don't support the testpaths setting in pytest.ini, so they will ignore it and they would
# otherwise run no tests.
py.test -n auto -r a "$SOURCES_PATH"/_py2tmp

make install
