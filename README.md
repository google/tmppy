
[![Build Status](https://img.shields.io/travis/google/tmppy/master.svg?label=Linux/OSX%20build/tests)](https://travis-ci.org/google/tmppy)

TMPPy is a subset of Python that can be compiled to C++ meta-functions using the `py2tmp` compiler.
This project is aimed at C++ library developers whose libraries include a non-trivial amount of C++
metaprogramming.

Compared to writing C++ metaprogramming code directly, using TMPPy allows that code to be expressed in a
more concise and readable way, provides static type checking (avoiding some classes of instantiation-time
errors) and produces optimized C++ meta-functions, reducing the compile time for the C++ compilation.

#### Example

As an example, let's write a metafunction (aka type trait class) `add_pointer_multiple` such that:

* `add_pointer_multiple<T, 0>::type` is `T`
* `add_pointer_multiple<T, 1>::type` is `T*`
* `add_pointer_multiple<T, 2>::type` is `T**`
* (and so on)

This can be written as a template, as follows:

    template <typename T, int64_t n>
    struct add_pointer_multiple {
        using type = typename add_pointer_multiple<T, n - 1>::type*;
    };
    
    template <typename T>
    struct add_pointer_multiple<T, 0> {
        using type = T;
    };

However this syntax is quite verbose and not very readable. For more complex metafunctions this becomes a significant issue, leading to more bugs and more effort when debugging or maintaining the code.

Some C++ metaprogramming libraries (notably Boost's MPL library) can be used to reduce the verbosity, however that comes at the price of slower compile times.

Using TMPPy, the above can be written as:

    def add_pointer_multiple(t: Type, n: int) -> Type:
        if n == 0:
            return t
        else:
            return add_pointer_multiple(Type.pointer(t), n-1)

And this TMPPy code can then be compiled to C++ code equivalent to the metafunction above (without the overhead of e.g. MPL).

For more information on TMPPy, see [the wiki](https://github.com/google/tmppy/wiki).

#### License

TMPPy is released under the Apache 2.0 license. See the `LICENSE` file for details.

This is not an official Google product.
