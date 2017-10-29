
package(default_visibility = ["//visibility:public"])
licenses(["notice"])

filegroup(
    name = "tmppy_headers",
    srcs = glob([
        "include/**/*.h",
    ]),
)

cc_library(
    name = "tmppy",
    srcs = [],
    hdrs = glob(["include/tmppy/*.h"]),
    includes = ["include"],
    deps = [],
    linkopts = ["-lm"],
)
