![TEN VAD banner][ten-vad-banner]

[![Discussion posts](https://img.shields.io/github/discussions/TEN-framework/ten-vad?labelColor=gray&color=%20%23f79009)](https://github.com/TEN-framework/ten-vad/discussions/)
[![Commits](https://img.shields.io/github/commit-activity/m/TEN-framework/ten-vad?labelColor=gray&color=pink)](https://github.com/TEN-framework/ten-vad/graphs/commit-activity)
[![Issues closed](https://img.shields.io/github/issues-search?query=repo%3ATEN-framework%2Ften-vad%20is%3Aclosed&label=issues%20closed&labelColor=gray&color=green)](https://github.com/TEN-framework/ten-vad/issues)
![](https://img.shields.io/github/contributors/ten-framework/ten-vad?color=c4f042&labelColor=gray&style=flat-square)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome!-brightgreen.svg?style=flat-square)](https://github.com/TEN-framework/ten-vad/pulls)
[![GitHub license](https://img.shields.io/badge/License-Apache_2.0_with_certain_conditions-blue.svg?labelColor=%20%23155EEF&color=%20%23528bff)](https://github.com/TEN-framework/ten-vad/blob/main/LICENSE)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/TEN-framework/TEN-vad)

[![GitHub watchers](https://img.shields.io/github/watchers/TEN-framework/ten-vad?style=social&label=Watch)](https://GitHub.com/TEN-framework/ten-vad/watchers/?WT.mc_id=academic-105485-koreyst)
[![GitHub forks](https://img.shields.io/github/forks/TEN-framework/ten-vad?style=social&label=Fork)](https://GitHub.com/TEN-framework/ten-vad/network/?WT.mc_id=academic-105485-koreyst)
[![GitHub stars](https://img.shields.io/github/stars/TEN-framework/ten-vad?style=social&label=Star)](https://GitHub.com/TEN-framework/ten-vad/stargazers/?WT.mc_id=academic-105485-koreyst)

<br>

## Latest News 🔥

- [2025/07] We support **Python inference** on **macOS** and **Windows** with usage of the prebuilt-lib!  
- [2025/06] We **finally** released and **open-sourced** the **ONNX** model and the corresponding **preprocessing code**! Now you can deploy **TEN VAD** on **any platform** and **any hardware architecture**!
- [2025/06] We are excited to announce the release of **WASM+JS** for Web WASM Support.

<br>

## Table of Contents

- [Welcome to TEN](#welcome-to-ten)
- [TEN Hugging Face Space](#ten-hugging-face-space)
- [Introduction](#introduction)
- [Key Features](#key-features)
  - [High-Performance](#1-high-performance)
  - [Agent-Friendly](#2-agent-friendly)
  - [Lightweight](#3-lightweight)
  - [Multiple Programming Languages and Platforms](#4-multiple-programming-languages-and-platforms)
  - [Supported Sampling Rate and Hop Size](#5-supproted-sampling-rate-and-hop-size)
- [Installation](#installation)
- [Quick Start](#quick-start)
  - [Python Usage](#python-usage)
    - [Linux](#1-linux)
  - [JS Usage](#js-usage)
    - [Web](#1-web)
  - [C Usage](#c-usage)
    - [Linux](#1-linux-1)
    - [Windows](#2-windows)
    - [macOS](#3-macos)
    - [Android](#4-android)
    - [iOS](#5-ios)
- [TEN Ecosystem](#ten-ecosystem)
- [Ask Questions](#ask-questions)
- [Citations](#citations)
- [License](#license)

<br>

## Welcome to TEN

TEN is a comprehensive open-source ecosystem for creating, customizing, and deploying real-time conversational AI agents with multimodal capabilities including voice, vision, and avatar interactions.

TEN includes [TEN Framework](https://github.com/ten-framework/ten-framework), [TEN Turn Detection](https://github.com/ten-framework/ten-turn-detection), [TEN VAD](https://github.com/ten-framework/ten-vad), [TEN Agent](https://github.com/TEN-framework/ten-framework/tree/main/ai_agents/demo), [TMAN Designer](https://github.com/TEN-framework/ten-framework/tree/main/core/src/ten_manager/designer_frontend), and [TEN Portal](https://github.com/ten-framework/portal). Check out [TEN Ecosystem](#ten-ecosystem) for more details.

<br>

| Community Channel                                                                                                                                                                      | Purpose                                                          |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [![Follow on X](https://img.shields.io/twitter/follow/TenFramework?logo=X&color=%20%23f5f5f5)](https://twitter.com/intent/follow?screen_name=TenFramework)                             | Follow TEN Framework on X for updates and announcements          |
| [![Follow on LinkedIn](https://custom-icon-badges.demolab.com/badge/LinkedIn-TEN_Framework-0A66C2?logo=linkedin-white&logoColor=fff)](https://www.linkedin.com/company/ten-framework)  | Follow TEN Framework on LinkedIn for updates and announcements   |
| [![Discord TEN Community](https://dcbadge.vercel.app/api/server/VnPftUzAMJ?&style=flat&theme=light&color=lightgray)](https://discord.gg/VnPftUzAMJ)                                    | Join our Discord community to connect with developers            |
| [![Hugging Face Space](https://img.shields.io/badge/Hugging%20Face-TEN%20Framework-yellow?style=flat&logo=huggingface)](https://huggingface.co/TEN-framework)                          | Join our Hugging Face community to explore our spaces and models |
| [![WeChat](https://img.shields.io/badge/TEN_Framework-WeChat_Group-%2307C160?logo=wechat&labelColor=darkgreen&color=gray)](https://github.com/TEN-framework/ten-agent/discussions/170) | Join our WeChat group for Chinese community discussions          |

<br>

> \[!IMPORTANT]
>
> **Star TEN Repositories** ⭐️
>
> Get instant notifications for new releases and updates. Your support helps us grow and improve TEN!

<br>

![TEN star us gif](https://github.com/user-attachments/assets/eeebe996-8c14-4bf7-82ae-f1a1f7e30705)

<br>

## TEN Hugging Face Space

<https://github.com/user-attachments/assets/725a8318-d679-4b17-b9e4-e3dce999b298>

You are more than welcome to [Visit TEN Hugging Face Space](https://huggingface.co/spaces/TEN-framework/ten-agent-demo) to try VAD and Turn Detection together.

<br>

## **Introduction**

**TEN VAD** is a real-time voice activity detection system designed for enterprise use, providing accurate frame-level speech activity detection. It shows superior precision compared to both WebRTC VAD and Silero VAD, which are commonly used in the industry. Additionally, TEN VAD offers lower computational complexity and reduced memory usage compared to Silero VAD. Meanwhile, the architecture's temporal efficiency enables rapid voice activity detection, significantly reducing end-to-end response and turn detection latency in conversational AI systems.

<br>

## **Key Features**

### **1. High-Performance:**

The precision-recall curves comparing the performance of WebRTC VAD (pitch-based), Silero VAD, and TEN VAD are shown below. The evaluation is conducted on the precisely manually annotated testset. The audio files are from librispeech, gigaspeech, DNS Challenge etc. As demonstrated, TEN VAD achieves the best performance. Additionally, cross-validation experiments conducted on large internal real-world datasets demonstrate the reproducibility of these findings. The **testset with annotated labels** is released in directory "testset" of this repository.

 <br>

<div style="text-align:">
  <img src="./examples/images/PR_Curves_testset.png" width="800">
</div>

Note that the default threshold of 0.5 is used to generate binary speech indicators (0 for non-speech signal, 1 for speech signal). This threshold needs to be tuned according to your domain-specific task. The precision-recall curve can be obtained by executing the following script on Linux x64. The output figure will be saved in the same directory as the script.

```
cd ./examples
python plot_pr_curves.py
```

<br>

### **2. Agent-Friendly:**

As illustrated in the figure below, TEN VAD rapidly detects speech-to-non-speech transitions, whereas Silero VAD suffers from a delay of several hundred milliseconds, resulting in increased end-to-end latency in human-agent interaction systems. In addition, as demonstrated in the 6.5s-7.0s audio segment, Silero VAD fails to identify short silent durations between adjacent speech segments.

<div style="text-align:">
  <img src="./examples/images/Agent-Friendly-image.png" width="800">
</div>
<br>

### **3. Lightweight:**

We evaluated the RTF (Real-Time Factor) across five distinct platforms, each equipped with varying CPUs. TEN VAD demonstrates much lower computational complexity and smaller library size than Silero VAD.

<table>
  <tr>
    <th align="center" rowspan="2" valign="middle"> Platform </th>
    <th align="center" rowspan="2" valign="middle"> CPU </th>
    <th align="center" colspan="2"> RTF </th>
    <th align="center" colspan="2"> Lib Size </th>

  </tr>
  <tr>
    <th align="center" style="white-space: nowrap;"> TEN VAD </th>
    <th align="center" style="white-space: nowrap;"> Silero VAD </th>
    <th align="center"> TEN VAD </th>
    <th align="center"> Silero VAD </th>
  </tr>
  <tr>
    <th align="center" rowspan="3"> Linux </th>
    <td style="white-space: nowrap;"> AMD Ryzen 9 5900X 12-Core </td>
    <td align="center"> 0.0150 </td>
    <td align="center" rowspan="2" valign="middle"> / </td>
    <td align="center" rowspan="3" valign="middle"> 306KB </td>
    <td align="center" rowspan="10" style="white-space: nowrap;" valign="middle"> 2.16MB(JIT) / 2.22MB(ONNX) </td>
  </tr>
  <tr>
    <td style="white-space: nowrap;"> Intel(R) Xeon(R) Platinum 8253 </td>
    <td align="center"> 0.0136 </td>
  </tr>
  <tr>
    <td style="white-space: nowrap;"> Intel(R) Xeon(R) Gold 6348 CPU @ 2.60GHz </td>
    <td align="center"> 0.0086 </td>
    <td align="center"> 0.0127 </td>
  </tr>
  <tr>
    <th align="center"> Windows </th>
    <td> Intel i7-10710U </td>
    <td align="center"> 0.0150 </td>
    <td align="center" rowspan="7" valign="middle"> / </td>
    <td align="center" style="white-space: nowrap;"> 464KB(x86) / 508KB(x64) </td>
  </tr>
  <tr>
    <th align="center"> macOS </th>
    <td> M1 </td>
    <td align="center"> 0.0160 </td>
    <td align="center"> 731KB </td>
  </tr>
  <tr>
    <th align="center"> Web </th>
    <td> macOS(M1) </td>
    <td align="center"> 0.010 </td>
    <td align="center"> 277KB </td>
  </tr>
  <tr>
    <th align="center" rowspan="2"> Android </th>
    <td> Galaxy J6+ (32bit, 425) </td>
    <td align="center"> 0.0570 </td>
    <td align="center" rowspan="2" style="white-space: nowrap;"> 373KB(v7a) / 532KB(v8a)</td>
  </tr>
  <tr>
    <td> Oppo A3s (450) </td>
    <td align="center"> 0.0490 </td>
  </tr>
  <tr>
    <th align="center" rowspan="2"> iOS </th>
    <td> iPhone6 (A8) </td>
    <td align="center"> 0.0210 </td>
    <td align="center" rowspan="2"> 320KB</td>
  </tr>
  <tr>
    <td> iPhone8 (A11) </td>
    <td align="center"> 0.0050 </td>
  </tr> 
</table>
<br>

### **4. Multiple programming languages and platforms:**

TEN VAD provides cross-platform C compatibility across five operating systems (Linux x64, Windows, macOS, Android, iOS), with Python bindings optimized for Linux x64, with wasm for Web.
<br>
<br>

### **5. Supproted sampling rate and hop size:**

TEN VAD operates on 16kHz audio input with configurable hop sizes (optimized frame configurations: 160/256 samples=10/16ms). Other sampling rates must be resampled to 16kHz.
<br>
<br>

## **Installation**

```
git clone https://github.com/TEN-framework/ten-vad.git
```

<br>

## **Quick Start**

The project supports five major platforms with dynamic library linking.

<table>
  <tr>
    <th align="center"> Platform </th>
    <th align="center"> Dynamic Lib </th>
    <th align="center"> Supported Arch </th>
    <th align="center"> Interface Language </th>
    <th align="center"> Header </th>
    <th align="center"> Comment </v>
  </tr>
  <tr>
    <th align="center"> Linux </th>
    <td align="center"> libten_vad.so </td>
    <td align="center"> x64 </td>
    <td align="center"> Python, C </td>
    <td rowspan="6">ten_vad.h <br> ten_vad.py <br> ten_vad.js</td>
    <td>  </td>
  </tr>
  <tr>
    <th align="center"> Windows </th>
    <td align="center"> ten_vad.dll </td>
    <td align="center"> x64, x86 </td>
    <td align="center"> C </td>
    <td>  </td>
  </tr>
  <tr>
    <th align="center"> macOS </th>
    <td align="center"> ten_vad.framework </td>
    <td align="center"> arm64, x86_64 </td>
    <td align="center"> C </td>
    <td>  </td>
  </tr>
  <tr>
    <th align="center"> Web </th>
    <td align="center"> ten_vad.wasm </td>
    <td align="center"> / </td>
    <td align="center"> JS </td>
    <td>  </td>
  </tr>
  <tr>
    <th align="center"> Android </th>
    <td align="center"> libten_vad.so </td>
    <td align="center"> arm64-v8a, armeabi-v7a </td>
    <td align="center"> C </td>
    <td>  </td>
  </tr>
  <tr>
    <th align="center"> iOS </th>
    <td align="center"> ten_vad.framework </td>
    <td align="center"> arm64 </td>
    <td align="center"> C </td>
    <td> 1. not simulator <br> 2. not iPad </td>
  </tr>

</table>
<br>

### **Python Usage**

#### **1. Linux / macOS / Windows**

#### **Requirements**

- numpy (Version 1.17.4/1.26.4 verified)
- scipy (Version >= 1.5.0)
- scikit-learn (Version 1.2.2/1.5.0 verified, for plotting PR curves)
- matplotlib (Version 3.1.3/3.10.0 verified, for plotting PR curves)
- torchaudio (Version 2.2.2 verified, for plotting PR curves)

- Python version 3.8.19/3.10.14 verified

Note: You could use other versions of above packages, but we didn't test other versions.

<br>

The **lib** only depend on numpy, you have to install the dependency via requirements.txt:

`pip install -r requirements.txt`

For **running demo or plotting PR curves**, you have to install the dependencies:

`pip install -r ./examples/requirements.txt`

Note that if you did not install **libc++1** (Linux), you have to run the code below to install it:

```
sudo apt update
sudo apt install libc++1
```

<br>

#### **Usage**

Note: For usage in python, you can either use it by **git clone** or **pip**.

##### **By using git clone:**

1. Clone the repository

```
git clone https://github.com/TEN-framework/ten-vad.git
```

2. Enter examples directory

```
cd ./examples
```

3. Test

```
python test.py s0724-s0730.wav out.txt
```

<br>

##### **By using pip:**

1. Install via pip

```
pip install -U --force-reinstall -v git+https://github.com/TEN-framework/ten-vad.git
```

2. Write your own use cases and import the class, the attributes of class TenVAD you can refer to ten_vad.py

```
from ten_vad import TenVad
```

<br>

### **JS Usage**

#### **1. Web**

##### **Requirements**

- Node.js (macOS v14.18.2, Linux v16.20.2 verified)
- Terminal

##### **Usage**

```
1) cd ./examples
2) node test_node.js s0724-s0730.wav out.txt
```

<br>

### **C Usage**

#### **Build Scripts**

Located in examples/ directory or examples_onnx/ (for **ONNX** usage on Linux):

- Linux: build-and-deploy-linux.sh
- Windows: build-and-deploy-windows.bat
- macOS: build-and-deploy-mac.sh
- Android: build-and-deploy-android.sh
- iOS: build-and-deploy-ios.sh

#### **Dynamic Library Configuration**

Runtime library path configuration:

- Linux/Android: LD_LIBRARY_PATH
- macOS: DYLD_FRAMEWORK_PATH
- Windows: DLL in executable directory or system PATH

#### **Customization**

- Modify platform-specific build scripts
- Adjust CMakeLists.txt
- Configure toolchain and architecture settings

#### **Overview of Usage**

- Navigate to examples/ or examples_onnx/ (for **ONNX** usage on Linux)
- Execute platform-specific build script
- Configure dynamic library path
- Run demo with sample audio s0724-s0730.wav
- Processed results saved to out.txt

<br>

The detailed usage methods of each platform are as follows <br>

#### **1. Linux**

##### **Requirements**

- Clang (e.g. 6.0.0-1ubuntu2 verified)
- CMake
- Terminal

Note that if you did not install **libc++1**, you have to run the code below to install it:

```
sudo apt update
sudo apt install libc++1
```

##### **Usage (prebuilt-lib)**

```
1) cd ./examples
2) ./build-and-deploy-linux.sh
```

##### **Usage (ONNX)**

You have to download the **onnxruntime** packages from the [microsoft official onnxruntime github website](https://github.com/microsoft/onnxruntime). Note that the version of onnxruntime must be higher than or equal to 1.17.1 (e.g. onnxruntime-linux-x64-1.17.1.tgz).
<br>
<br>
You can check the official **ONNX Runtime releases** from [this website](https://github.com/microsoft/onnxruntime/tags). And for example, to download version 1.17.1 (Linux x64), use [this link](https://github.com/microsoft/onnxruntime/releases/download/v1.17.1/onnxruntime-linux-x64-1.17.1.tgz). After extracting the compressed file, you'll find two important directories:`include/` - header files, `lib/` - library files

```
1) cd examples_onnx/
2) ./build-and-deploy-linux.sh --ort-path /absolute/path/to/your/onnxruntime/root/dir
```

**Note 1**: If executing the onnx demo from a different directory than the one used when running build-and-deploy-linux.sh, ensure to create a symbolic link to src/onnx_model/ to prevent ONNX model file loading failures.
<br>
**Note 2**: The **ONNX model** locates in `src/onnx_model` directory.

<br>

#### **2. Windows**

##### **Requirements**

- Visual Studio (2017, 2019, 2022 verified)
- CMake (3.26.0-rc6 verified)
- Terminal (MINGW64 or powershell)

##### **Usage**

```
1) cd ./examples
2) Configure "build-and-deploy-windows.bat" with your preferred:
    - Architecture (default: x64)
    - Visual Studio version (default: 2019)
3) ./build-and-deploy-windows.bat
```

<br>

#### **3. macOS**

##### **Requirements**

- Xcode (15.2 verified)
- CMake (3.19.2 verified)

##### **Usage**

```
1) cd ./examples
2) Configure "build-and-deploy-mac.sh" with your target architecture:
  - Default: arm64 (Apple Silicon)
  - Alternative: x86_64 (Intel)
3) ./build-and-deploy-mac.sh
```

<br>

#### **4. Android**

##### **Requirements**

- NDK (r25b, macOS verified)
- CMake (3.19.2, macOS verified)
- adb (1.0.41, macOS verified)

##### **Usage**

```
1) cd ./examples
2) export ANDROID_NDK=/path/to/android-ndk  # Replace it with your NDK installation path
3) Configure "build-and-deploy-android.sh" with your build settings:
  - Architecture: arm64-v8a (default) or armeabi-v7a
  - Toolchain: aarch64-linux-android-clang (default) or custom NDK toolchain
4) ./build-and-deploy-android.sh
```

<br>

#### **5. iOS**

##### **Requirements**

Xcode (15.2, macOS verified)
CMake (3.19.2, macOS verified)

##### **Usage**

1. Enter examples directory

```
cd ./examples
```

2. Creates Xcode project files for iOS build

```
./build-and-deploy-ios.sh
```

3.  Follow the steps below to build and test on iOS device:

    3.1. Use Xcode to open .xcodeproj files: a) cd ./build-ios, b) open ./ten_vad_demo.xcodeproj

    3.2. In Xcode IDE, select ten_vad_demo target (should check: Edit Scheme → Run → Release), then select your iOS Device (not simulator).

    <div style="text-align:">
      <img src="./examples/images/ios_image_1.jpg" width="800">
    </div>

    3.3. Drag ten_vad/lib/iOS/ten_vad.framework to "Frameworks, Libraries, and Embedded Content"

    - (in TARGETS → ten_vad_demo → ten_vad_demo → General, should set Embed to "Embed & Sign").

    - or add it directly in this way: "Frameworks, Libraries, and Embedded Content" → "+" → Add Other... → Add Files →...

    - Note: If this step is not completed, you may encounter the following runtime error: "dyld: Library not loaded: @rpath/ten_vad.framework/ten_vad".

          <div style="text-align:">
            <img src="./examples/images/ios_image_2.png" width="800">
          </div>

      3.4. Configure iOS device Signature

    - in TARGETS → ten_vad_demo → Signing & Capabilities → Signing

      - Modify Bundle Identifier: modify "com.yourcompany" to yours;

      - Specify Provisioning Profile

    - In TARGETS → ten_vad_demo → Build Settings → Signing → Code Signing Identity:

      - Specify your Certification

        3.5. Build in Xcode and run demo on your device.

<br>

## TEN Ecosystem

| Project                                                                                                                                                          | Preview                        |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| [**🏚️ TEN Framework**][ten-framework-link]<br>TEN is an open-source framework for real-time, multimodal conversational AI.<br><br>![][ten-framework-shield]      | ![][ten-framework-banner]      |
| [**️🔂 TEN Turn Detection**][ten-turn-detection-link]<br>TEN is for full-duplex dialogue communication.<br><br>![][ten-turn-detection-shield]                    | ![][ten-turn-detection-banner] |
| [**🔉 TEN VAD**][ten-vad-link]<br>TEN VAD is a low-latency, lightweight and high-performance streaming voice activity detector (VAD).<br><br>![][ten-vad-shield] | ![][ten-vad-banner]            |
| [**🎙️ TEN Agent**][ten-agent-link]<br>TEN Agent is a showcase of TEN Framewrok.<br><br>                                                                          | ![][ten-agent-banner]          |
| [**🎨 TMAN Designer**][tman-designer-link]<br>TMAN Designer is low/no code option to make a voice agent with easy to use workflow UI.<br><br>                    | ![][tman-designer-banner]      |
| [**📒 TEN Portal**][ten-portal-link]<br>The official site of TEN framework, it has documentation and blog.<br><br>![][ten-portal-shield]                         | ![][ten-portal-banner]         |

<br>

## Ask Questions

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/TEN-framework/TEN-vad)

Most questions can be answered by using DeepWiki, it is fast, intutive to use and supports multiple languages.

<br>

## **Citations**

```
@misc{TEN VAD,
  author = {TEN Team},
  title = {TEN VAD: A Low-Latency, Lightweight and High-Performance Streaming Voice Activity Detector (VAD)},
  year = {2025},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {https://github.com/TEN-framework/ten-vad.git},
  email = {developer@ten.ai}
}
```

<br>

## License

This project is licensed under Apache 2.0 with certain conditions. Refer to the "LICENSE" file in the root directory for detailed information. Note that `pitch_est.cc` contains modified code derived from [LPCNet](https://github.com/xiph/LPCNet), which is [BSD-2-Clause](https://spdx.org/licenses/BSD-2-Clause.html) and [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) licensed, refer to the NOTICES file in the root directory for detailed information.

<br>

[back-to-top]: https://img.shields.io/badge/-Back_to_top-gray?style=flat-square
[ten-framework-shield]: https://img.shields.io/github/stars/ten-framework/ten_framework?color=ffcb47&labelColor=gray&style=flat-square&logo=github
[ten-framework-banner]: https://github.com/user-attachments/assets/7c8f72d7-3993-4d01-8504-b71578a22944
[ten-framework-link]: https://github.com/ten-framework/ten_framework
[ten-vad-link]: https://github.com/ten-framework/ten-vad
[ten-vad-shield]: https://img.shields.io/github/stars/ten-framework/ten-vad?color=ffcb47&labelColor=gray&style=flat-square&logo=github
[ten-vad-banner]: https://github.com/user-attachments/assets/d45870e4-9453-4047-8163-08737f82863f
[ten-turn-detection-link]: https://github.com/ten-framework/ten-turn-detection
[ten-turn-detection-shield]: https://img.shields.io/github/stars/ten-framework/ten-turn-detection?color=ffcb47&labelColor=gray&style=flat-square&logo=github
[ten-turn-detection-banner]: https://github.com/user-attachments/assets/8d0ec716-5d0e-43e4-ad9a-d97b17305658
[ten-agent-link]: https://github.com/TEN-framework/ten-framework/tree/main/ai_agents
[ten-agent-banner]: https://github.com/user-attachments/assets/38de2207-939b-4702-a0aa-04491f5b5275
[tman-designer-banner]: https://github.com/user-attachments/assets/804c3543-0a47-42b7-b40b-ef32b742fb8f
[tman-designer-link]: https://github.com/TEN-framework/ten-framework/tree/main/core/src/ten_manager/designer_frontend
[ten-portal-link]: https://github.com/ten-framework/portal
[ten-portal-shield]: https://img.shields.io/github/stars/ten-framework/portal?color=ffcb47&labelColor=gray&style=flat-square&logo=github
[ten-portal-banner]: https://github.com/user-attachments/assets/e17d8aaa-5928-45dd-ac71-814928e26a89
