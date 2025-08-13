#!/bin/bash
#
#  Copyright © 2025 Agora
#  This file is part of TEN Framework, an open source project.
#  Licensed under the Apache License, Version 2.0, with certain conditions.
#  Refer to the "LICENSE" file in the root directory for more information.
#
set -euo pipefail

# Customize the arch
arch=arm64
# arch=x86_64

build_dir=build-mac/$arch
rm -rf $build_dir
mkdir -p $build_dir
cd $build_dir

# Step 1: Build the demo
cmake ../../ \
  -DCMAKE_CXX_COMPILER=/usr/bin/clang++ \
  -DCMAKE_C_COMPILER=/usr/bin/clang \
  -DCMAKE_OSX_ARCHITECTURES=${arch} \
  -G Xcode

cmake --build . --config Release -- -UseModernBuildSystem=NO


# Step 2: Run the demo
export DYLD_FRAMEWORK_PATH="../../../lib/macOS/"
Release/ten_vad_demo ../../s0724-s0730.wav out.txt
cd ../../