# Bituo Device for Home Assistant

## Installation

### Install with HACS 

1. Open HACS (Home Assistant Community Store).
2. Navigate to Integrations.
3. Click on the "![](/images/symbol-1.jpg)" button to add a new repository.
4. Click "Custom repositories".
5. Enter the URL of this GitHub repository.
6. Select the "Integration" category and click "Add".

### Install manually

1. Install this platform by creating a `custom_components` folder in the same folder as your configuration.yaml, if it doesn't already exist.
2. Create another folder `bituo` in the `custom_components` folder. Copy all files from custom_components into the `bituo` folder. Do not copy files from master branch, download latest release (.zip).

## Configuration
After connecting your ESP device to the network following the manual guide, you can use the device's IP address to bind it to Home Assistant.
1. Enter the device's IP address into the input field.
2. Click the submit button.
![](/images/config-1.png)
3. Wait a moment, and the device will appear in Home Assistant.
![](/images/config-2.png)
4. Click the device to view its details.
![](/images/interface-1.jpg)

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