@echo off
setlocal

@REM
@REM  Copyright © 2025 Agora
@REM  This file is part of TEN Framework, an open source project.
@REM  Licensed under the Apache License, Version 2.0, with certain conditions.
@REM  Refer to the "LICENSE" file in the root directory for more information.
@REM

@REM Customize the arch
set arch=x64
@REM set arch=x86

@REM step 1: Build the demo
set "build_dir=%~dp0\build-windows"
if exist "%build_dir%" rmdir /s /q "%build_dir%"
mkdir "%build_dir%"
cd /d "%build_dir%"

@REM Customize the Visual Studio version
@REM REM VS 2017
@REM if %arch% == x64 (
@REM   cmake .. -G "Visual Studio 15 2017" -A x64
@REM ) else if %arch% == x86 (
@REM   cmake .. -G "Visual Studio 15 2017" -A Win32
@REM )

REM VS 2019
if %arch% == x64 (
  cmake .. -G "Visual Studio 16 2019" -A x64
) else if %arch% == x86 (
  cmake .. -G "Visual Studio 16 2019" -A Win32
)

@REM REM VS 2022
@REM if %arch% == x64 (
@REM   cmake .. -G "Visual Studio 17 2022" -A x64
@REM ) else if %arch% == x86 (
@REM   cmake .. -G "Visual Studio 17 2022" -A Win32
@REM )

cmake --build . --config Release
cd ..


@REM step 2: Run the demo
pushd "%~dp0"
copy /Y "s0724-s0730.wav" "%build_dir%\Release"
copy /Y "..\lib\Windows\%arch%\ten_vad.dll" "%build_dir%\Release"
if errorlevel 1 (
  echo [Error] copy file failed
  popd
  exit /b 1
)
cd /d "%build_dir%\Release"
if not exist "ten_vad_demo.exe" (
    echo Error: ten_vad_demo.exe not found
    exit /b 1
)
if not exist "s0724-s0730.wav" (
    echo Error: s0724-s0730.wav not found
    exit /b 1
)

ten_vad_demo.exe "s0724-s0730.wav" out.txt
if errorlevel 1 (
    echo Error: ten_vad_demo.exe failed
    exit /b 1
)

cd /d "%~dp0"
popd
exit /b 0
