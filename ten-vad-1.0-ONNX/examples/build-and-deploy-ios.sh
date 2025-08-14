#!/usr/bin/env bash
#
#  Copyright © 2025 Agora
#  This file is part of TEN Framework, an open source project.
#  Licensed under the Apache License, Version 2.0, with certain conditions.
#  Refer to the "LICENSE" file in the root directory for more information.
#
set -euo pipefail

work_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
build_dir="${work_dir}/build-ios"

mkdir -p "${build_dir}"
cd "${build_dir}"

# Step 1: Generate Xcode project for iOS device
echo "[Info] Generating Xcode project"
cmake "${work_dir}" \
  -DCMAKE_SYSTEM_NAME=iOS \
  -DCMAKE_OSX_SYSROOT="iphoneos" \
  -DCMAKE_OSX_ARCHITECTURES="arm64" \
  -DCMAKE_XCODE_ATTRIBUTE_CODE_SIGN_IDENTITY="Apple Development" \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=12.1 \
  -DCMAKE_INSTALL_RPATH="@executable_path/Frameworks" \
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
  -G Xcode


# Step 2: Use Xcode to open the project in build-ios directory
# Step 3: Build and run the project in Xcode IDE