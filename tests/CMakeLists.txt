
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

set(INSTALL_INCLUDE_DIR include/fruit CACHE PATH "Installation directory for headers")

set(TMPPY_VERSION "0.1.3")

install(DIRECTORY include/fruit/
  DESTINATION "${INSTALL_INCLUDE_DIR}"
  FILES_MATCHING PATTERN "*.h")

set(CPACK_PACKAGE_NAME "TMPPy")
set(CPACK_PACKAGE_VENDOR "Marco Poletti")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "TMPPy - A Subset Of Python That Can Be Compiled to C++ Meta-Functions")
string(REGEX REPLACE "([^.]*)\\.([^.]*)\\.([^.]*)" "\\1" CPACK_PACKAGE_VERSION_MAJOR "${TMPPY_VERSION}")
string(REGEX REPLACE "([^.]*)\\.([^.]*)\\.([^.]*)" "\\2" CPACK_PACKAGE_VERSION_MINOR "${TMPPY_VERSION}")
string(REGEX REPLACE "([^.]*)\\.([^.]*)\\.([^.]*)" "\\3" CPACK_PACKAGE_VERSION_PATCH "${TMPPY_VERSION}")
set(CPACK_PACKAGE_VERSION "${TMPPY_VERSION}")
set(CPACK_PACKAGE_INSTALL_DIRECTORY "TMPPy")
