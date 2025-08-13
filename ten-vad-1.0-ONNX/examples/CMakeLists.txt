#
#  Copyright © 2025 Agora
#  This file is part of TEN Framework, an open source project.
#  Licensed under the Apache License, Version 2.0, with certain conditions.
#  Refer to the "LICENSE" file in the root directory for more information.
#
cmake_minimum_required(VERSION 3.10)
get_filename_component(ROOT ${CMAKE_CURRENT_SOURCE_DIR}/../ ABSOLUTE)

project(ten_vad_demo)

add_executable(ten_vad_demo ${ROOT}/examples/main.c)
target_include_directories(ten_vad_demo PRIVATE "${ROOT}/include")

if(WIN32)
  if(CMAKE_SIZEOF_VOID_P EQUAL 8)
    target_link_libraries(ten_vad_demo "${ROOT}/lib/Windows/x64/ten_vad.lib")
  else()
    target_link_libraries(ten_vad_demo "${ROOT}/lib/Windows/x86/ten_vad.lib")
  endif()
elseif(ANDROID)
  if(CMAKE_SYSTEM_PROCESSOR STREQUAL "aarch64")
    target_link_libraries(ten_vad_demo "${ROOT}/lib/Android/arm64-v8a/libten_vad.so")
  else()
    target_link_libraries(ten_vad_demo "${ROOT}/lib/Android/armeabi-v7a/libten_vad.so")
  endif()
elseif(IOS)
  target_link_libraries(ten_vad_demo "${ROOT}/lib/iOS/ten_vad.framework")
  set_target_properties(ten_vad_demo PROPERTIES
    XCODE_ATTRIBUTE_FRAMEWORK_SEARCH_PATHS "${ROOT}/lib/iOS"
    XCODE_ATTRIBUTE_LD_RUNPATH_SEARCH_PATHS "@executable_path/Frameworks"
    XCODE_ATTRIBUTE_CODE_SIGN_STYLE "Manual"
    XCODE_ATTRIBUTE_DEVELOPMENT_TEAM "${CMAKE_XCODE_ATTRIBUTE_DEVELOPMENT_TEAM}"
    XCODE_ATTRIBUTE_PRODUCT_BUNDLE_IDENTIFIER "com.yourcompany.ten_vad_demo"
    XCODE_ATTRIBUTE_SUPPORTED_PLATFORMS "iphoneos"
    XCODE_ATTRIBUTE_ARCHS "arm64"
  )
elseif(APPLE)
  target_link_libraries(ten_vad_demo "${ROOT}/lib/macOS/ten_vad.framework")
  set_target_properties(ten_vad_demo PROPERTIES
    INSTALL_RPATH "@loader_path"
    BUILD_WITH_INSTALL_RPATH TRUE
  )
elseif(UNIX)
  target_link_libraries(ten_vad_demo "${ROOT}/lib/Linux/x64/libten_vad.so")
endif()
