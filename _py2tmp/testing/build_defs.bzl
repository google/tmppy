
def tmppy_tests(srcs):
    for filename in srcs:
        native.py_test(
            name = filename[:-3],
            srcs = [filename],
            srcs_version = "PY3ONLY",
            imports = ["."],
            deps = [
                "//third_party/tmppy/_py2tmp/testing:tmppy_test_common",
            ],
            data = [
                "//third_party/tmppy:tmppy_headers",
            ],
            args = [
                "-p",
                "no:cacheprovider",
                "-n",
                "4",
            ],
        )
