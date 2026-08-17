cmake_minimum_required(VERSION 3.10)
project(unrelated CXX)
add_library(unrelated STATIC unrelated.cpp)
install(TARGETS unrelated ARCHIVE DESTINATION lib)
