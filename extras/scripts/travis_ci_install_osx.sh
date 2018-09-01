#!/bin/bash -x

set -e

install_brew_package() {
  if brew list -1 | grep -q "^$1\$"; then
    # Package is installed, upgrade if needed
    time (brew outdated "$1" || brew upgrade "$@")
  else
    # Package not installed yet, install.
    # If there are conflicts, try overwriting the files (these are in /usr/local anyway so it should be ok).
    time (brew install "$@" || brew link --overwrite gcc49)
  fi
}

time brew update

# For md5sum
install_brew_package md5sha1sum
# For `timeout'
install_brew_package coreutils
# For clang-format
install_brew_package clang-format

which cmake &>/dev/null || install_brew_package cmake

case "${COMPILER}" in
gcc-4.9)       install_brew_package gcc@4.9 ;;
gcc-5)         install_brew_package gcc@5 ;;
gcc-6)         install_brew_package gcc@6 ;;
clang-default) ;;
clang-4.0)     install_brew_package llvm@4 --with-toolchain ;;
clang-5.0)     install_brew_package llvm@5 --with-toolchain ;;
clang-6.0)     install_brew_package llvm@6 --with-toolchain ;;
*) echo "Compiler not supported: ${COMPILER}. See travis_ci_install_osx.sh"; exit 1 ;;
esac

time brew upgrade python
time pip3 install pytest
time pip3 install pytest-xdist
time pip3 install typed_ast
time pip3 install networkx

# This adds python-installed executables to PATH (notably py.test).
export PATH="$(brew --prefix)/bin:$PATH"
