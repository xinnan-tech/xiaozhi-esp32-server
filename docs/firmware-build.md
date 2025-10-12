# esp32 firmware compilation

## Step 1 Prepare your OTA address

If you are using version 0.3.12 of this project, whether it is a simple server deployment or a full module deployment, there will be an ota address.

Since the OTA address setting methods for simple server deployment and full module deployment are different, please choose the specific method below:

### If you are using simple server deployment
At this moment, please use your browser to open your OTA address, for example my OTA address
```
http://192.168.1.25:8003/xiaozhi/ota/
```
If it displays "OTA interface is running normally, the websocket address sent to the device is: ws://xxx:8000/xiaozhi/v1/

You can use the `test_page.html` that comes with the project to test whether you can connect to the websocket address output by the ota page.

If you cannot access it, you need to modify the address of `server.websocket` in the configuration file `.config.yaml`, restart and test again until `test_page.html` can be accessed normally.

After success, please proceed to step 2

### If you are using full module deployment
At this moment, please use your browser to open your OTA address, for example my OTA address
```
http://192.168.1.25:8002/xiaozhi/ota/
```

If it displays "OTA interface is running normally, number of websocket clusters: X", proceed to step 2.

If it shows "OTA interface is not running properly", it is probably because you have not configured the `Websocket` address in the `Smart Console`. Then:

- 1. Log in to the smart console as a super administrator

- 2. Click `Parameter Management` in the top menu

- 3. Find the `server.websocket` item in the list and enter your `Websocket` address. For example, mine is

```
ws://192.168.1.25:8000/xiaozhi/v1/
```

After configuration, use the browser to refresh your OTA interface address to see if it is normal. If it is still not normal, please confirm again whether the Websocket is started normally and whether the Websocket address is configured.

## Step 2 Configure the environment
First, configure the project environment according to this tutorial ["Building ESP IDF 5.3.2 Development Environment and Compiling Xiaozhi on Windows"](https://icnynnzcwou8.feishu.cn/wiki/JEYDwTTALi5s2zkGlFGcDiRknXf)

## Step 3 Open the configuration file
After configuring the compilation environment, download the source code of the iaozhi-esp32 project.

Download the xiaozhi-esp32 project source code from here.

After downloading, open the `xiaozhi-esp32/main/Kconfig.projbuild` file.

## Step 4 Modify the OTA address

Find the `default` content of `OTA_URL` and replace `https://api.tenclass.net/xiaozhi/ota/`
   Change it to your own address. For example, my interface address is `http://192.168.1.25:8002/xiaozhi/ota/`, so change the content to this.

Before modification:
```
config OTA_URL
    string "Default OTA URL"
    default "https://api.tenclass.net/xiaozhi/ota/"
    help
        The application will access this URL to check for new firmwares and server address.
```
After modification:
```
config OTA_URL
    string "Default OTA URL"
    default "http://192.168.1.25:8002/xiaozhi/ota/"
    help
        The application will access this URL to check for new firmwares and server address.
```

## Step 4 Set compilation parameters

Set compilation parameters

```
# Enter the root directory of xiaozhi-esp32 in the terminal command line
cd xiaozhi-esp32
# For example, the board I use is esp32s3, so set the compilation target to esp32s3. If your board is other models, please replace it with the corresponding model
idf.py set-target esp32s3
# Enter menu configuration
idf.py menuconfig
```

After entering the menu configuration, enter `Xiaozhi Assistant` and set `BOARD_TYPE` to the specific model of your board
Save and exit, returning to the terminal command line.

## Step 5 Compile the firmware

```
idf.py build
```

## Step 6: Pack the bin firmware

```
cd scripts
python release.py
```

After the above packaging command is executed, the firmware file `merged-binary.bin` will be generated in the `build` directory under the project root directory.
This `merged-binary.bin` is the firmware file to be burned to the hardware.

Note: If a "zip" related error is reported after executing the second command, please ignore this error and just generate the firmware file `merged-binary.bin` in the `build` directory
, it won’t have much impact on you, please continue.

## Step 7 Burn the firmware
   Connect the ESP32 device to the computer and use the Chrome browser to open the following URL

```
https://espressif.github.io/esp-launchpad/
```

Open this tutorial, [Flash Tool/Web-based Firmware Burning (Without IDF Development Environment)](https://ccnphfhqs21z.feishu.cn/wiki/Zpz4wXBtdimBrLk25WdcXzxcnNS).
Go to Method 2: ESP-Launchpad Web-based Programming and follow the instructions starting from 3. Programming/Downloading the Firmware to the Development Board.

After the program is successfully burned and the network is successfully connected, wake up Xiaozhi using the wake-up word and pay attention to the console information output by the server.

## Frequently Asked Questions
Here are some frequently asked questions for your reference:

[1. Why does Xiaozhi recognize a lot of Korean, Japanese, and English in my words?](./FAQ.md)

[2. Why does the error "TTS task error file does not exist" appear?](./FAQ.md)

[3. TTS often fails and times out](./FAQ.md)

[4. I can connect to my own server using Wi-Fi, but not 4G](./FAQ.md)

[5. How can I improve Xiaozhi's conversational response speed?](./FAQ.md)

[6. I speak very slowly, and Xiaozhi always interrupts me when I pause.](./FAQ.md)

[7. I want to use Xiaozhi to control lights, air conditioning, remote power on and off, etc.](./FAQ.md)
