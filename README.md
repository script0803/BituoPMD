# Bituo Device for Home Assistant

## Installation

### Install with HACS 

[![Open BituoPMD inside your Home Assistant Community Store (HACS).](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Script0803&repository=bituopmd&category=integration)

1. Open HACS (Home Assistant Community Store).
2. Navigate to Integrations.
3. Click on the "![](/images/symbol-1.png)" button to add a new repository.
4. Click "Custom repositories".
5. Enter the URL of this GitHub repository.
6. Select the "Integration" category and click "Add".

### Install manually

1. Install this platform by creating a `custom_components` folder in the same folder as your configuration.yaml, if it doesn't already exist.
2. Create another folder `bituopmd` in the `custom_components` folder. Copy all files from custom_components into the `bituopmd` folder. Do not copy files from master branch, download latest release (.zip).

## Configuration

After connecting your ESP device to the network following the manual guide, We have three ways to add your ESP devices to HomeAssistant.

### Discoverd

When you add your ESP device to the same network as Home Assistant, the device will be automatically scanned and appear in the discovered list.
![](/images/discoverd.jpg)

After clicking 'Configure,' the following dialog box will pop up. Then, click 'Submit' to add the device.
![](/images/discoverd-config.jpg)

### Zeroconf scan

1. Select 'Use Zeroconf to scan device', and click 'Submit'. The integration will start scanning for devices on the current network.
![](/images/zeroconf-1.jpg)
2. The integration will list the devices it has scanned. Select the device you want to add and proceed with the addition.
![](/images/zeroconf-2.jpg)

### Manual configure

1. Select 'Use Zeroconf to scan device', and click 'Submit'.
![](/images/manual-1.jpg)
2. Enter the device's IP address into the input field. Click the submit button.
![](/images/manual-2.jpg)

## Devices supported
- SPM01-D1EW
- SPM01-D2EW
- SPM01-U1EW
- SPM01-U2EW
- SPM02-D1EW
- SPM02-D2EW
- SPM02-U1EW
- SPM02-U2EW
- SDM01-EW0
- SDM01-EWM
- SDM02-EW

## Detail information

Click on the device name to enter the details page, where you can view all the parameters measured by the device.
![](/images/interface-1.jpg)
Clicking 'View' will redirect you to the device's embedded webpage.
![](/images/interface-2.jpg)
All entities can have their units adjusted according to Home Assistant's rules.
![](/images/interface-3.jpg)

## Device settings

Once the integration is activated, you can see the entry to the settings page in Home Assistant's sidebar.
![](/images/UI-1.jpg)

On this page, you can adjust all the settings of the device, as well as access other functions like Zero Energy, Restart, Erase Factory, and OTA.
![](/images/UI-2.jpg)
Click the dropdown menu at the top to select the device you want to configure.
![](/images/UI-3.png)

## Device OTA
The device's parameter page will display the OTA status. When 'OTA available' is shown, please proceed to the embedded web page or the integration's settings page to perform the OTA.
![](/images/OTA-2.jpg)

![](/images/OTA-3.jpg)
If 'Up to date' is displayed, it means the device is already on the latest version and no OTA is required.
![](/images/OTA-1.jpg)
