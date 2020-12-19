# Resto-Score-for-Hack-2021-for-Property
MicroPython on Heltec Wifi Kit 32 Connecting with Google IoT Core
=================================================================

In December 2020 I participated together with [Clint Guin](https://www.linkedin.com/in/clint-guin/) and [Dwain Robinson](https://www.linkedin.com/in/dwain-robinson/) in the [Google Hack 2021 for Positivity Hackathon](http://hack2021forpositivity-platform.bemyapp.com). 

For this Hackathon we built a Sensor Array into a set of Easy Buttons to report on space occupancy and environmental statistics. There was more to the full project but in this article I am describing just how we used Heltec LoRaWAN 32 and Heltec Wifi Kit 32 dev boards as the basis for the ESP32 Microcontroller based Sensor Array.

This is a simplified example to demonstrates how to build something like this and use MicroPython to connect to Cloud IoT Core 

This tutorial is geared toward Mac users but can be easily adopted to work on Windows or other Linux based systems,

## Quickstart for Heltec Wifi Kit 32 or Heltec LoRa 32

1. First you have to put together the hardware for this project. As mentioned earlier we used the Heltec ESP32 based microcontrollers. The sensors we used were the HC_SR04 to measure distance, an MQ135 to measure Air Quality, and a BME680 to measure temperature, humidity, air pressure and a secondary air quality reading.

```
    git clone https://github.com/cashoefman/Resto-Score-for-Hack-2021-for-Property
```

2. Clone or download this repository

```
    git clone https://github.com/GoogleCloudPlatform/iot-core-micropython
    cd iot-core-micropython
```

3. Create a virtual environment and install the tools for ESP32. (The creation of a virtual env is optional, your choice, you do what to install the tools though).

```
    virtualenv env
    source env/bin/activate
    pip install esptool adafruit-ampy rsa
```

4. Determine the port your board is on and set an environment variable to be reused later.

```
    ls /dev/ | grep -i "tty" | grep -i "usb"
    export SERIALPORT="/dev/tty.usbserial-0001"
```

5. Test flashing your device and [Download and install MicroPython](http://micropython.org/resources/firmware/esp32-idf4-20200902-v1.13.bin).
	Note: I have tried both the idf3 and idf4 versions, I prefer the idf4 version as it seems to have less issues.

```
	esptool.py --port $SERIALPORT flash_id
    esptool.py --chip esp32 --port $SERIALPORT erase_flash
    esptool.py --chip esp32 --port $SERIALPORT --baud 460800 write_flash -z 0x1000 ~/Downloads/esp32-idf4-20200902-v1.13.bin
```

6. Connect to your Device and get its Unique device ID. In this example I am using screen to connect to the device, you can also do this using the [Arduino IDE](https://arduino.cc), [uPycraft](https://github.com/DFRobot/uPyCraft_src) or other terminal tools. I use this unique ID to create the device in GCP IoT Core and in the application running on the controller to identify it when connecting to IoT Core.

```
   screen -L $SERIALPORT 115200
   import machine
   deviceid = ("DEV" + '{:02x}{:02x}{:02x}{:02x}'.format(machine.unique_id()[0], machine.unique_id()[1], machine.unique_id()[2], machine.unique_id()[3]))
   print (deviceid)
   export DEVUUID = "<replace-with-deviceid>"
   mkdir <replace-with-deviceid>
   cd <replace-with-deviceid>
```

7. In your device directory, generate your public / private key pair.

```
    openssl genrsa -out rsa_private.pem 2048
    openssl rsa -in rsa_private.pem -pubout -out rsa_public.pem
```

8. Create your Google IoT Core setup and registry, and setup your devices [as described in the Cloud IoT Core documentation](https://cloud.google.com/iot/docs/how-tos/devices), using the keys from the previous step. Or use the command line as shown before if you have the Google Cloud CLI installed. You are going to need the region and registry information to run the command line.

```
	export REGION = "<replacewithyourregion>"
	export REGISTRY = "<replacewithyourregistry>"
	gcloud iot devices create $DEVUUID --region=$REGION --registry=$REGISTRY --public-key="path=./rsa_public.pem,type=rsa-pem"
```

9. Decode the RSA key for your device configuration and add the output to your new config file based on `config.py.example`. You will have open the newly created config.py and as need update the Wifi network details.

```
    cp ../config.py.example config.py
    python ../utils/decode_rsa.py >> config.py
	echo '}' >> config.py
```

10. Copy the Python sources to the device. Note: that although I am listing ssd1306.py here, I am not really using that in this example. But if you like you could display something on the build in display on the device using that "device driver".

```
    ampy --port $SERIALPORT --baud 115200 put ../third_party
	ampy --port $SERIALPORT --baud 115200 put ../ssd1306.py
	ampy --port $SERIALPORT --baud 115200 put config.py
    ampy --port $SERIALPORT --baud 115200 put ../main.py
	ampy --port $SERIALPORT --baud 115200 put ../HC_SR04_.py
	ampy --port $SERIALPORT --baud 115200 put ../MQ135.py
	ampy --port $SERIALPORT --baud 115200 put ../bme680.py
```

11. Connect to the device over the serial port and press reset on the device.

```
    screen -L $SERIALPORT 115200
```

Note that on machines without screen, you can use other software such as the
[Arduino IDE](https://arduino.cc) for accessing the terminal.

If everything worked you should see output similar to the following.

    Publishing message {“temp”: 113, “device_id”: “DEV12345678”}.....
    Publishing message {“temp”: 114, “device_id”: “DEV12345678”}.....
    Publishing message {“temp”: 114, “device_id”: “DEV12345678”}.....

You can read the telemetry from PubSub using the following [Google Cloud SDK](https://cloud.google.com/sdk) command.

```
    gcloud pubsub subscriptions pull <your-pubsub-repo> --auto-ack --limit=10
```

## Troubleshooting
If the device freezes around the time network initialization completes you may want to try using a different pin for the LED. This can resolve some issues. Also these Heltec controllers are a bit different from for example a ESP32 DEVKit V1 make sure you use the correct input pins on the devices otherwise you might not get the sensors signal reading properly.

## Hardware target(s)
* Heltec Wifi Kit 32
* Heltec LoRa 32
* Can also works with other generic ESP32 boards if you remove the code for the OLED display.
* ESP32 DEVKIT v1

## Dependencies
* Some small modifications have been done to [python-rsa](https://github.com/sybrenstuvel/python-rsa) library to allow this to work on MicroPython.

## Pre-requisites
* Google Cloud Project with the Cloud IoT Core API enabled
* ESP32 compatble device

## See Also
* [Connecting MicroPython devices to Cloud IoT Core](https://medium.com/google-cloud/connecting-micropython-devices-to-google-cloud-iot-core-3680e632681e)

## License

Apache 2.0; see [LICENSE](LICENSE) for details.

## Disclaimer

I am not claiming that any of this works, you will have to tinker with it a bit to make it all work. But we had a handful of these sensor arrays submit a few hundred thousand sensor readings to Google IoT Core so it can all work. Some of the code for different sensors could use some updating to make the readings more accurate but I'll leave that up to you too.
