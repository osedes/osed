cmake_minimum_required(VERSION 3.28.3)

# This block makes the project self-contained by running 'conan install' if
# the toolchain file is missing. This is robust for both VS Code and
# command-line builds, ensuring dependencies are present before configuration.
if(NOT EXISTS "${CMAKE_BINARY_DIR}/conan_toolchain.cmake")
  message(STATUS "Conan toolchain not found. Running 'conan install'...")

  # Find the conan executable, providing a hint for common user-level pip
  # installations.
  find_program(CONAN_CMD conan HINTS "./bin")
  if(NOT CONAN_CMD)
    message(FATAL_ERROR "Conan executable not found. Please install Conan "
                        "(e.g., 'pip install conan') and ensure it is in "
                        "your system's PATH.")
  endif()

  execute_process(
    COMMAND  ${CONAN_CMD} install conanfile.txt --output-folder= --build=missing
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    RESULT_VARIABLE conan_result
    ERROR_VARIABLE conan_error)
  if(conan_result) # Non-zero exit code indicates an error
    message(FATAL_ERROR "Conan install failed with exit code .\n"
                        "Details:\n\n"
                        "Please check your Conan installation and
conanfile.txt.")
  endif()
endif()

project(OSED VERSION 0.2.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# When using Conan with the CMakeDeps generator, package configuration files
# (like yaml-cpp-config.cmake) are created in the build directory. The
# conan_toolchain.cmake file should handle this, but explicitly adding the
# build directory to CMAKE_PREFIX_PATH makes the configuration more robust.
list(APPEND CMAKE_PREFIX_PATH "")

find_package(yaml-cpp REQUIRED)

# Create a static library for the parser logic.
# Using a more descriptive name than 'parser.o'.
add_library(osed_parser STATIC parser.cpp)

# The library needs to know where its headers are.
# PUBLIC propagation means consumers of this library also get this include path.
target_include_directories(osed_parser PUBLIC include)

# Link the parser library against its dependencies.
# PUBLIC propagation means consumers of osed_parser will know it depends on yaml-cpp
# and link to it automatically.
target_link_libraries(osed_parser PUBLIC yaml-cpp::yaml-cpp)

# Create the main executable, renaming from 'parser' to 'osed_cli' for clarity.
add_executable(osed_cli main.cpp)

# Link the executable against our parser library.
target_link_libraries(osed_cli PRIVATE osed_parser)
