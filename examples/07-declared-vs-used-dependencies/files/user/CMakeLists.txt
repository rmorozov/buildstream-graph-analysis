cmake_minimum_required(VERSION 3.10)
project(user CXX)
add_library(user STATIC user.cpp)
install(TARGETS user ARCHIVE DESTINATION lib)
