TMPPy is a subset of Python that can be compiled to C++ meta-functions using the `py2tmp` compiler.
This project is aimed at C++ library developers whose libraries include a non-trivial amount of C++
metaprogramming.

Compared to writing C++ metaprogramming code directly, using TMPPy allows that code to be expressed in a
more concise and readable way, provides static type checking (avoiding some classes of instantiation-time
errors) and produces optimized C++ meta-functions, reducing the compile time for the C++ compilation.

#### License

This is not an official Google product.
