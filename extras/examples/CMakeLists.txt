
add_custom_command(OUTPUT example.tmppyc
                   DEPENDS builtins-tmppyc
                   WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                   COMMAND PYTHONPATH=${CMAKE_SOURCE_DIR} ${PYTHON} ${CMAKE_SOURCE_DIR}/py2tmp/main.py -o ${CMAKE_CURRENT_BINARY_DIR}/example.tmppyc --builtins-path=${CMAKE_BINARY_DIR}/builtins.tmppyc extras/examples/example.py
                   )

add_custom_command(OUTPUT example_for_coverage.tmppyc
                   DEPENDS builtins-tmppyc
                   WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                   COMMAND PYTHONPATH=${CMAKE_SOURCE_DIR} ${PYTHON} ${CMAKE_SOURCE_DIR}/py2tmp/main.py -o ${CMAKE_CURRENT_BINARY_DIR}/example_for_coverage.tmppyc --builtins-path=${CMAKE_BINARY_DIR}/builtins_for_coverage.tmppyc --enable_coverage=true extras/examples/example.py
                   )

add_custom_target(example-tmppyc ALL
                  DEPENDS example.tmppyc example_for_coverage.tmppyc)
