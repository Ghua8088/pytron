cmake_minimum_required(VERSION 3.18.1)

project("pytron-native")

# Define the prebuilt python library
add_library(python-lib SHARED IMPORTED)
set_target_properties(python-lib PROPERTIES IMPORTED_LOCATION "${CMAKE_CURRENT_SOURCE_DIR}/../jnilibs/${ANDROID_ABI}/libpython3.14.so")

# Include Python Headers
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

# Create our native library
add_library(pytron-native SHARED pytron_bridge.cpp)

# Find system libraries
find_library(log-lib log)
find_library(android-lib android)

# Link libraries
target_link_libraries(
    pytron-native
    python-lib
    ${log-lib}
    ${android-lib}
)
