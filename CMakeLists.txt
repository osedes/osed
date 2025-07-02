cmake_minimum_required(VERSION 3.28.3)
project(OSED VERSION 0.2.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

find_package(yaml-cpp REQUIRED)

add_library(parser.o parser.cpp)
target_include_directories(parser.o PUBLIC include)
target_link_libraries(parser.o yaml-cpp::yaml-cpp)

add_executable(parser main.cpp $<TARGET_OBJECTS:parser.o>)
target_link_libraries(parser PRIVATE parser.o)
