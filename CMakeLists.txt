cmake_minimum_required(VERSION 3.6)
project(tmppy)

add_custom_command(
  OUTPUT example.h
  COMMAND "${CMAKE_COMMAND}" -E env "PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}" python3 "${CMAKE_CURRENT_SOURCE_DIR}/_py2tmp/main.py" "${CMAKE_CURRENT_SOURCE_DIR}/example.py" --output-dir "${CMAKE_CURRENT_BINARY_DIR}" --verbose
  DEPENDS "_py2tmp/main.py" "example.py"
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  COMMENT "Running py2tmp on example.py"
)

add_custom_target(example DEPENDS example.h)

add_subdirectory(_py2tmp/tests)
