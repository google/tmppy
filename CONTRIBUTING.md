
This file is aimed at TMPPy contributors. If you just want to use TMPPy, more documentation is coming soon, stay tuned.

# How to Contribute

We'd love to accept your patches and contributions to this project. There are
just a few small guidelines you need to follow.

## Contributor License Agreement

Contributions to this project must be accompanied by a Contributor License
Agreement. You (or your employer) retain the copyright to your contribution,
this simply gives us permission to use and redistribute your contributions as
part of the project. Head over to <https://cla.developers.google.com/> to see
your current agreements on file or to sign a new one.

You generally only need to submit a CLA once, so if you've already submitted one
(even if it was for a different project), you probably don't need to do it
again.

## Code reviews

All submissions, including submissions by project members, require review. We
use GitHub pull requests for this purpose. Consult

## Useful commands

Run tests:

    cd $PATH_TO_TMPPY
    mkdir build
    cd build
    cmake .. -DCMAKE_BUILD_TYPE=Debug
    cd _tmppy/tests
    make -j
    PYTHONPATH=.:.. py.test-3 -n auto

To also collect coverage, add the following flags to the last command:

    --cov-config=$PATH_TO_TMPPY/.coveragerc --cov=_py2tmp --cov-report html

Note: if your `$PATH_TO_TMPPY` contains a `~` you need to replace it with `$HOME` in this command, or it won't be
expanded.
