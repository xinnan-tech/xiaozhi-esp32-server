#!/bin/bash
#
#  Copyright © 2025 Agora
#  This file is part of TEN Framework, an open source project.
#  Licensed under the Apache License, Version 2.0, with certain conditions.
#  Refer to the "LICENSE" file in the root directory for more information.
#
set -euo pipefail

arch=x64
build_dir=build-linux/$arch
rm -rf $build_dir
mkdir -p $build_dir
cd $build_dir

# Step 1: Build the demo
cmake ../../
cmake --build . --config Release


# Step 2: Run the demo
export LD_LIBRARY_PATH=../../../lib/Linux/$arch
./ten_vad_demo ../../s0724-s0730.wav out.txt

cd ../../
