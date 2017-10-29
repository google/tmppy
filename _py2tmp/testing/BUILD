licenses(["notice"])

genrule(
    name = "tmppy_test_config_genrule",
    srcs = [
        "//third_party/tmppy:tmppy_headers",
    ],
    outs = [
        "tmppy_test_config.py",
    ],
    visibility = ["//third_party/tmppy:__subpackages__"],
    cmd = ""
          + "TMPPY_HEADERS_LOCATION=`echo $(location //third_party/tmppy:tmppy_headers) | sed 's|include/tmppy/.*|./|'`;"
          + "echo -e \""
          + "CXX='g++'\n"
          + "CXX_COMPILER_NAME='GNU'\n"
          + "CXX_COMPILER_VERSION='5.0.0'\n"
          + "ADDITIONAL_LINKER_FLAGS=''\n"
          + "CMAKE_BUILD_TYPE=None\n"
          + "TMPPY_INCLUDE_DIR='$${TMPPY_HEADERS_LOCATION}/include'\n"
          + "\" > $(location tmppy_test_config.py)",
)

py_library(
    name = "tmppy_test_common",
    srcs = ["tmppy_test_config.py", "utils.py"],
    imports = ["."],
    srcs_version = "PY3ONLY",
    visibility = ["//third_party/tmppy:__subpackages__"],
)
