class BituoPanel extends HTMLElement {
    constructor() {
        super();
        this.intervalId = null;  // 定义intervalId用于存储定时器的ID
    }

    set hass(hass) {
        this._hass = hass;
        if (!this.content) {
            const title = this.config ? this.config.title : "BituoPMD";
            this.innerHTML = `
                <style>
                    /* 默认样式，适用于白色模式 */
                    .container {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 20px;
                        margin-left: 5px;
                        margin-right: 5px;
                    }
                    .panel {
                        flex: 1;
                        min-width: 250px;
                        padding: 20px;
                        background-color: #f9f9f9;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        color: #000; /* 黑色文字 */
                    }
                    .device-selection {
                        flex: 1;
                        min-width: 250px;
                        padding: 20px;
                        background-color: #f9f9f9;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        margin-left: 5px;
                        margin-right: 5px;
                        margin-bottom: 5px;
                        color: #000; /* 黑色文字 */
                    }
                    .device-selection select {
                        width: calc(30%);
                        padding: 5px;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        background-color: #fff; /* 白色背景 */
                        color: #000; /* 黑色文字 */
                    }
                    .panel h3 {
                        margin-top: 0;
                        color: #000; /* 黑色文字 */
                    }
                    .panel label {
                        display: block;
                        margin-bottom: 5px;
                        font-weight: bold;
                        color: #333; /* 深色文字 */
                    }
                    .panel input, .panel select {
                        width: calc(100% - 10px);
                        padding: 5px;
                        margin-bottom: 10px;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        background-color: #fff; /* 白色背景 */
                        color: #000; /* 黑色文字 */
                    }
                    .panel .checkbox-container {
                        display: flex;
                        align-items: center;
                    }

                    .panel .checkbox-container label {
                        margin-right: 10px; 
                        margin-bottom: 0; 
                    }
                    .panel button {
                        padding: 10px 20px;
                        background-color: #007bff;
                        color: #fff;
                        border: none;
                        border-radius: 3px;
                        cursor: pointer;
                        margin: 5px;
                        flex: 1 1 calc(50% - 20px);
                    }
                    .panel button:hover {
                        background-color: #0056b3;
                    }
                    .button-group {
                        display: flex;
                        flex-wrap: wrap;
                        margin-bottom: 10px;
                    }
                    .checkbox-container {
                        display: flex;
                        align-items: center;
                        gap: 5px;
                    }
                    .checkbox-container input[type="checkbox"] {
                        width: auto;
                        height: auto;
                    }
                    h1 {
                        margin-left: 20px;
                        color: #000; /* 黑色文字 */
                    }
                    .mqtt-report-frequency-label {
                        margin-top: 20px;
                        color: #333; /* 深色文字 */
                    }
                    /* 遮罩层样式 */
                    .ota-overlay {
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background-color: rgba(0, 0, 0, 0.7);
                        color: white;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        font-size: 24px;
                        z-index: 1000;
                        display: none; /* 初始状态隐藏 */
                    }

                    .confirmation-dialog {
                        position: fixed;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        padding: 20px;
                        background-color: #fff;
                        border: 1px solid #ccc;
                        border-radius: 5px;
                        z-index: 1000;
                        max-width: 80%;
                        max-height: 80%;
                        overflow: auto;
                        box-sizing: border-box;
                    }

                    .confirmation-content {
                        text-align: left;
                    }

                    .confirmation-dialog p {
                        margin-bottom: 20px;
                        word-wrap: break-word;
                        overflow-wrap: break-word;
                        white-space: normal;
                    }

                    .confirmation-dialog button {
                        padding: 10px 20px;
                        margin: 5px;
                        cursor: pointer;
                    }
                    /* 黑色模式 */
                    @media (prefers-color-scheme: dark) {
                        .panel {
                            background-color: #333; /* 深色背景 */
                            border: 1px solid #444;
                            color: #fff; /* 白色文字 */
                        }
                        .device-selection {
                            background-color: #333; /* 深色背景 */
                            border: 1px solid #444;
                            color: #fff; /* 白色文字 */
                        }
                        .device-selection select {
                            background-color: #444; /* 深色背景 */
                            border: 1px solid #555;
                            color: #fff; /* 白色文字 */
                        }
                        .panel h3, .panel label, .mqtt-report-frequency-label, h1 {
                            color: #fff; /* 白色文字 */
                        }
                        .panel input, .panel select {
                            background-color: #444; /* 深色背景 */
                            border: 1px solid #555;
                            color: #fff; /* 白色文字 */
                        }
                        .panel button {
                            background-color: #007bff;
                            color: #fff;
                        }
                        .panel button:hover {
                            background-color: #0056b3;
                        }
                        .confirmation-dialog {
                            background-color: #444 !important; /* 强制应用深色背景 */
                            border: 1px solid #555 !important; /* 强制应用深色边框 */
                            color: #fff !important; /* 强制应用白色文字 */
                        }

                        .confirmation-dialog p {
                            color: #fff !important; /* 强制应用白色文字 */
                        }

                        .confirmation-dialog button {
                            background-color: #007bff !important; /* 强制应用按钮背景颜色 */
                            color: #fff !important; /* 强制应用按钮文字颜色 */
                            border: none !important; /* 确保没有其他边框干扰 */
                        }

                        .confirmation-dialog button:hover {
                            background-color: #0056b3 !important; /* 按钮悬停时的颜色 */
                        }
                    }
                </style>
                <div>
                    <h1>${title}</h1>
                    <div id="device-selection" class="device-selection">
                        <label for="device-select">Select Device:</label>
                        <select id="device-select">
                            <option value="" disabled selected>Select a device</option>
                        </select>
                    </div>
                    <div class="container">
                        <div class="panel">
                            <h3>Device Setting</h3>
                            <div class="button-group">
                                <button id="zero-energy">Zero Energy</button>
                                <button id="erase-factory">Reset Device</button>
                                <button id="restart">Restart</button>
                                <button id="ota">OTA</button>
                            </div>
                            <label for="report-frequency" class="mqtt-report-frequency-label">MQTT Report Interval (seconds):</label>
                            <input id="report-frequency" type="number" min="1" />
                            <button id="set-report-frequency">Set Report Interval</button>
                        </div>
                        ${this.getPostActionsHtml()}
                        <div class="panel">
                            <h3>Polling Interval (5-3600s)</h3>
                            <label for="data-frequency">Interval (seconds):</label>
                            <input id="data-frequency" type="number" min="5" max="3600"/><br /> <!-- 限制值为 5 到 3600 -->
                            <small style="color: #555;">Notice: If you have paired multiple devices, it is recommended to increase the polling interval to avoid excessive network load.(default=5s)</small><br />
                            <div class="checkbox-container">
                                <input id="apply-to-all" type="checkbox">
                                <label for="apply-to-all">Apply to all devices</label>
                            </div>
                            <button id="set-data-frequency">Set Polling Interval</button> <!-- 按钮文本也可相应修改 -->
                        </div>
                    </div>
                </div>
                <div class="ota-overlay" id="ota-overlay">
                    In progress, please wait...
                </div>
                <div id="confirmation-dialog" class="confirmation-dialog" style="display: none;">
                    <div class="confirmation-content">
                        <p id="confirmation-message"></p>
                        <div style="text-align: center;">
                            <button id="confirm-yes">Yes</button>
                            <button id="confirm-no">No</button>
                        </div>
                    </div>
                </div>
            `;
            this.content = this.querySelector('div');

            this.addEventListeners(); // 确保所有内容都已加载后再添加事件监听器

            this.loadDevices();
            this.startRefreshingDevices();  // 启动定时器
        }
    }

    addEventListeners() {
        const actions = [
            { id: '#zero-energy', action: 'zeroenergy' },
            { id: '#ota', action: 'ota' }
        ];
        
        actions.forEach(({ id, action }) => {
            const element = this.querySelector(id);
            if (element) {
                element.addEventListener('click', async () => {
                    this.showOtaOverlay();
                    this.showConfirmationDialog('Are you sure you want to perform this action?', async () => {
                        await this.performGetAction(action);
                        this.hideOtaOverlay();
                    });
                });
            }
        });
    
        const postActions = [
            { id: '#wifi-config', getConfig: this.getWiFiConfig },
            { id: '#mqtt-config', getConfig: this.getMQTTConfig },
            { id: '#clear-energy', getConfig: () => ({ configType: "clear", ConfirmClearValue: "true" }) },
            { id: '#restart', getConfig: () => ({ configType: "restart", EspRestart: "true" }) },
            { id: '#erase-factory', getConfig: () => ({ configType: "erase", EraseMessage: "true" }) },
            { id: '#set-report-frequency', getConfig: () => ({ configType: "report", ReportFrequency: parseInt(this.querySelector('#report-frequency').value) }) },
            { id: '#set-topic', getConfig: this.getTopicConfig },
            { id: '#set-udp', getConfig: this.getUdpConfig }
        ];
    
        postActions.forEach(({ id, getConfig }) => {
            const element = this.querySelector(id);
            if (element) {
                element.addEventListener('click', async () => {
                    this.showOtaOverlay();
                    this.showConfirmationDialog('Are you sure you want to perform this action?', async () => {
                        await this.performPostAction('save-config', getConfig.call(this));
                        this.hideOtaOverlay();
                    });
                });
            }
        });
    
        const setFrequencyButton = this.querySelector('#set-data-frequency');
        if (setFrequencyButton) {
            setFrequencyButton.addEventListener('click', async () => {
                this.showOtaOverlay();
                await this.setDataRequestFrequency();
                this.hideOtaOverlay();
            });
        }
    
        const uploadCaButton = this.querySelector('#upload-ca-cert');
        if (uploadCaButton) {
            uploadCaButton.addEventListener('click', async () => {
                this.showOtaOverlay();
                await this.uploadCaCertificate();
                this.hideOtaOverlay();
            });
        }

        const setModbusButton = this.querySelector('#set-modbus');
        if (setModbusButton) {
            setModbusButton.addEventListener('click', async () => {
                this.showConfirmationDialog('Are you sure you want to set Modbus configuration?', async () => {
                    const config = this.getModbusConfig();

                    // Validate Modbus address
                    const modbusAddress = parseInt(config.Modbusaddress, 10);
                    if (isNaN(modbusAddress) || modbusAddress < 1 || modbusAddress > 247) {
                        this.showAlert('Modbus address must be between 1 and 247.');
                        this.hideOtaOverlay();
                        return;  // Stop execution if invalid address
                    }

                    this.showOtaOverlay();

                    try {
                        // Send all Modbus POST requests in sequence
                        await Promise.all([
                            this.performPostAction('save-config', {
                                configType: 'baudrate',
                                baudrate: config.baudrate
                            }),
                            this.performPostAction('save-config', {
                                configType: 'ParityStop',
                                ParityStop: config.ParityStop
                            }),
                            this.performPostAction('save-config', {
                                configType: 'Modbusaddress',
                                Modbusaddress: config.Modbusaddress
                            })
                        ]);

                        this.showAlert('Modbus configuration set successfully.');
                    } catch (error) {
                        this.showAlert(`Error: ${error.message}`);
                    } finally {
                        this.hideOtaOverlay();
                    }
                });
            });
        }
    }
    
    showConfirmationDialog(message, onConfirm) {
        const dialog = this.querySelector('#confirmation-dialog');
        const messageElement = this.querySelector('#confirmation-message');
        const yesButton = this.querySelector('#confirm-yes');
        const noButton = this.querySelector('#confirm-no');
    
        messageElement.textContent = message;
        dialog.style.display = 'block';
    
        yesButton.onclick = () => {
            dialog.style.display = 'none';
            onConfirm();
        };
    
        noButton.onclick = () => {
            dialog.style.display = 'none';
            this.hideOtaOverlay();
        };
    }

    async setDataRequestFrequency() {
        const frequency = parseInt(this.querySelector('#data-frequency').value);
    
        if (isNaN(frequency) || frequency < 5 || frequency > 3600) {
            this.showAlert('Polling Interval must be between 5 and 3600 seconds.');
            this.hideOtaOverlay();
            return;
        }
    
        const applyToAll = this.querySelector('#apply-to-all').checked;
        const offlineDevices = [];
        const onlineTasks = [];
        const deviceSelectElement = this.querySelector('#device-select');
        const options = Array.from(deviceSelectElement.options).filter(option => option.value);
    
        if (applyToAll) {
            // 收集任务并检查设备在线状态
            for (const option of options) {
                const deviceIp = option.value;
                const task = async () => {
                    try {
                        const isOnline = await this.checkDeviceStatus(deviceIp);
                        if (isOnline) {
                            await this.updateDeviceFrequency(deviceIp, frequency);
                        } else {
                            offlineDevices.push(deviceIp);
                        }
                    } catch (error) {
                        offlineDevices.push(deviceIp);
                    }
                };
                onlineTasks.push(task);
            }
    
            // 限制并发数量
            await this.runWithConcurrencyLimit(onlineTasks, 10);
    
            const onlineDevices = options.length - offlineDevices.length;
            this.showAlert(`Polling interval has been successfully updated for ${onlineDevices} online devices.`);
        } else {
            const { deviceIp } = this.getSelectedDevice();
            if (!deviceIp) {
                this.showAlert('No device selected.');
                return;
            }
            try {
                const isOnline = await this.checkDeviceStatus(deviceIp);
                if (isOnline) {
                    await this.updateDeviceFrequency(deviceIp, frequency);
                    this.showAlert('Polling interval has been successfully updated for the selected device.');
                } else {
                    this.showAlert('Selected device is offline, cannot update.');
                }
            } catch (error) {
                this.showAlert(`Error checking status or updating frequency for device ${deviceIp}: ${error.message}`);
            }
        }
    }
    
    async runWithConcurrencyLimit(tasks, limit) {
        const results = [];
        const executing = [];
        for (const task of tasks) {
            const p = task().then(result => {
                executing.splice(executing.indexOf(p), 1);
                return result;
            });
            results.push(p);
            executing.push(p);
            if (executing.length >= limit) {
                await Promise.race(executing);
            }
        }
        return Promise.all(results);
    }

    async updateDeviceFrequency(deviceIp, frequency) {
        try {
            // 使用 deviceIp 作为设备标识符传递给服务
            await this._hass.callService('bituopmd', 'set_frequency', {
                device_id: deviceIp,
                frequency: frequency
            });
        } catch (error) {
            this.showAlert(`Error updating frequency for device ${deviceIp}: ${error.message}`);
        }
    }

    setConfig(config) {
        this.config = config;
    }

    getCardSize() {
        return 1;
    }

    startRefreshingDevices() {
        this.intervalId = setInterval(() => this.loadDevices(), 30000); // 每30秒刷新一次设备列表
    }

    stopRefreshingDevices() {
        clearInterval(this.intervalId);
    }

    async limitConcurrency(tasks, limit) {
        const results = [];
        const executing = [];
    
        for (const task of tasks) {
            const p = task();  // 执行任务
            results.push(p);
    
            if (limit <= tasks.length) {
                const e = p.then(() => executing.splice(executing.indexOf(e), 1));
                executing.push(e);
                if (executing.length >= limit) {
                    await Promise.race(executing);
                }
            }
        }
        return Promise.all(results);
    }

    async loadDevices() {
        const deviceSelectElement = this.querySelector('#device-select');
        const selectedDeviceIp = deviceSelectElement.value;  // 保存当前选中的设备IP
        deviceSelectElement.innerHTML = '<option value="" disabled selected>Loading devices...</option>';

        try {
            const response = await this._hass.callApi('GET', 'bituopmd/devices');
            deviceSelectElement.innerHTML = '';  // 清空之前的内容

            if (response && response.length) {
                const tasks = response.map(device => async () => {
                    const option = this.findOrCreateOption(deviceSelectElement, device.ip);
                    let isOnline = false;
                    try {
                        isOnline = await this.checkDeviceStatus(device.ip);
                    } catch (error) {
                        isOnline = false;  // 超时或错误，视为离线
                    }
                    option.text = isOnline ? device.name : `${device.name} (offline)`;
                    option.disabled = !isOnline;
                    deviceSelectElement.add(option);
                });

                // 使用并发限制执行任务，每次最多执行10个
                await this.limitConcurrency(tasks, 10);

                // 恢复之前选中的设备
                deviceSelectElement.value = selectedDeviceIp;
            } else {
                deviceSelectElement.innerHTML = '<option value="" disabled>No devices found</option>';
            }
        } catch (error) {
            deviceSelectElement.innerHTML = '<option value="" disabled>Error loading devices</option>';
            console.error('Error loading devices:', error);
        }
    }

    findOrCreateOption(selectElement, value) {
        let option = Array.from(selectElement.options).find(opt => opt.value === value);
        if (!option) {
            option = document.createElement('option');
            option.value = value;
        }
        return option;
    }

    async checkDeviceStatus(ip, timeout = 3000) {
        const url = `bituopmd/proxy/${ip}/data`;
    
        // 创建超时的 Promise
        const timeoutPromise = new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Request timed out')), timeout)
        );
    
        // 创建 API 请求的 Promise
        const apiPromise = this._hass.callApi('GET', url)
            .then(response => {
                // 确保有有效的响应数据
                if (response && response.response) {
                    // 根据实际数据来判断设备状态
                    return response.response !== "404: Not Found";
                } else {
                    // 没有有效数据时视为离线
                    return false;
                }
            })
            .catch(() => false); // 处理请求错误
    
        try {
            // 使用 Promise.race 来处理超时和 API 请求
            return await Promise.race([apiPromise, timeoutPromise]);
        } catch {
            return false; // 返回 false 表示设备离线或请求超时
        }
    }

    getPostActionsHtml() {
        return `
            <div class="panel">
                <h3>WIFI Configuration</h3>
                <label for="wifi-ssid">SSID:</label>
                <input id="wifi-ssid" type="text" /><br />
                <label for="wifi-password">Password:</label>
                <input id="wifi-password" type="password" /><br />
                <button id="wifi-config">Configure WiFi</button>
            </div>
            <div class="panel">
                <h3>MQTT Configuration</h3>
                <label for="mqtt-host">Host:</label>
                <input id="mqtt-host" type="text" /><br />
                <label for="mqtt-port">Port:</label>
                <input id="mqtt-port" type="number" /><br />
                <label for="mqtt-clientid">Client ID:</label>
                <input id="mqtt-clientid" type="text" /><br />
                <label for="mqtt-username">Username:</label>
                <input id="mqtt-username" type="text" /><br />
                <label for="mqtt-password">Password:</label>
                <input id="mqtt-password" type="password" /><br />
                <div style="display: flex; align-items: center;">
                    <label for="mqtt-ssltls" style="margin-right: 10px;">Use SSL/TLS:</label>
                    <input id="mqtt-ssltls" type="checkbox"/>
                </div><br />
                <button id="mqtt-config">Configure MQTT</button>
                <label for="mqtt-ca-cert">CA Certificate:</label>
                <textarea id="mqtt-ca-cert" rows="10" style="width:100%;"></textarea><br />
                <button id="upload-ca-cert">Upload CA Certificate</button>
            </div>
            <div class="panel">
                <h3>Modbus Configuration(Optional)</h3>
                
                <label for="baudrate">Baud Rate:</label>
                <select id="baudrate">
                    <option value="2400">2400</option>
                    <option value="4800">4800</option>
                    <option value="9600">9600</option>
                    <option value="19200">19200</option>
                    <option value="38400">38400</option>
                </select><br />
                
                <label for="parity-stop">Data Format:</label>
                <select id="parity-stop">
                    <option value="N81">N81</option>
                    <option value="E81">E81</option>
                    <option value="O81">O81</option>
                    <option value="N82">N82</option>
                </select><br />
                
                <label for="modbus-address">Address (1-247):</label>
                <input id="modbus-address" type="number" min="1" max="247"/><br />
                
                <button id="set-modbus">Set Modbus Configuration</button>
            </div>
            <div class="panel">
                <h3>Topic Configuration</h3>
                <label for="topic-post">Topic Post:</label>
                <input id="topic-post" type="text" /><br />
                <label for="topic-set">Topic Set:</label>
                <input id="topic-set" type="text" /><br />
                <label for="topic-response">Topic Response:</label>
                <input id="topic-response" type="text" /><br />
                <label for="topic-metadata">Topic Metadata:</label>
                <input id="topic-metadata" type="text" /><br />
                <button id="set-topic">Set Topic</button>
            </div>
            <div class="panel">
                <h3>UDP Configuration</h3>
                <label for="udp-ip">IP Address:</label>
                <input id="udp-ip" type="text" /><br />
                <label for="udp-port">Local UDP Port:</label>
                <input id="udp-port" type="number" /><br />
                <label for="udp-frequency">Reporting interval (seconds):</label>
                <input id="udp-frequency" type="number" min="1000"/><br />
                <button id="set-udp">Set UDP</button>
            </div>
        `;
    }

    async performGetAction(action) {
        const { deviceIp } = this.getSelectedDevice();
        if (!deviceIp) {
            this.showAlert('No device selected.');
            this.hideOtaOverlay(); // 如果没有设备被选择，也要隐藏覆盖页面
            return;
        }
    
        try {
            const response = await this._hass.callApi('GET', `bituopmd/proxy/${deviceIp}/${action}`);
            this.showAlert(`Response: ${JSON.stringify(response)}`);
        } catch (error) {
            this.showAlert(`Error: ${error.message}`);
        } finally {
            this.hideOtaOverlay(); // 在最后无论成功还是失败，都要隐藏覆盖页面
        }
    }

    async performPostAction(action, body) {
        const { deviceIp } = this.getSelectedDevice();

        if (!this.validateInputs(body)) {
            this.showAlert('One or more fields are invalid or empty.');
            this.hideOtaOverlay();
            return;
        }

        if (!deviceIp) {
            this.showAlert('No device selected.');
            this.hideOtaOverlay(); // 如果没有设备被选择，也要隐藏覆盖页面
            return;
        }
    
        try {
            if (body.configType === 'wifi') {
                this.showOtaOverlay();
                this._hass.callApi('POST', `bituopmd/proxy/${deviceIp}/${action}`, body);
                setTimeout(() => {
                    this.showAlert('WiFi information sent successfully. The device may now be disconnected.');
                    this.hideOtaOverlay();
                }, 5000);
    
            } else {
                const response = await this._hass.callApi('POST', `bituopmd/proxy/${deviceIp}/${action}`, body);
                this.showAlert(response.response);
            }
        } catch (error) {
            this.showAlert(`Error: ${error.message}`);
        } finally {
            if (body.configType !== 'wifi') {
                this.hideOtaOverlay();  // 在非WiFi配置的情况下，继续使用正常流程
            }
        }
    }

    validateInputs(body) {
        // 排除不需要验证的字段
        const fieldsToExclude = ['password'];
    
        // 遍历对象的所有字段，检查是否有为空的情况
        for (const key in body) {
            if (fieldsToExclude.includes(key) && body.configType === 'wifi') continue;  // 排除 WiFi 密码的验证
            if (!body[key] || (typeof body[key] === 'string' && body[key].trim() === '')) {
                return false;  // 如果字段为空或只有空格，则返回 false
            }
        }
    
        return true;  // 所有字段都有效
    }

    getSelectedDevice() {
        const deviceSelectElement = this.querySelector('#device-select');
        const selectedOption = deviceSelectElement.options[deviceSelectElement.selectedIndex];
        if (selectedOption) {
            return {
                deviceIp: selectedOption.value
            };
        }
        return { deviceIp: null };
    }

    getWiFiConfig() {
        return {
            configType: 'wifi',
            username: this.querySelector('#wifi-ssid').value.trim(),
            password: this.querySelector('#wifi-password').value,  // 密码可以为空
        };
    }
    
    getMQTTConfig() {
        return {
            configType: 'mqtt',
            ssltls: this.querySelector('#mqtt-ssltls').checked ? 'true' : 'false',
            host: this.querySelector('#mqtt-host').value.trim(),
            port: this.querySelector('#mqtt-port').value.trim(),
            clientid: this.querySelector('#mqtt-clientid').value.trim(),
            username: this.querySelector('#mqtt-username').value.trim(),
            password: this.querySelector('#mqtt-password').value.trim(),  // 密码不能为空
        };
    }

    

    async uploadCaCertificate() {
        const caCert = this.querySelector('#mqtt-ca-cert').value.trim();
        const { deviceIp } = this.getSelectedDevice();
    
        if (!caCert) {
            this.showAlert('CA Certificate cannot be empty.');
            return;
        }
    
        if (!deviceIp) {
            this.showAlert('No device selected.');
            return;
        }
    
        const body = {
            ca_cert: caCert,
        };
    
        try {
            const response = await this._hass.callApi(
                'POST',
                `bituopmd/proxy/${deviceIp}/uploadcefile`,
                caCert,
                {
                    headers: {
                        'Content-Type': 'text/plain',
                    }
                }
            );
            this.showAlert(`Response: ${JSON.stringify(response)}`);
        } catch (error) {
            this.showAlert(`Error: ${error.message}`);
        }
    }

    getModbusConfig() {
    return {
        configType: 'modbus',
        baudrate: this.querySelector('#baudrate').value.trim(),
        ParityStop: this.querySelector('#parity-stop').value.trim(),
        Modbusaddress: this.querySelector('#modbus-address').value.trim()
    };
}
    
    getTopicConfig() {
        return {
            configType: 'topic',
            topic_post: this.querySelector('#topic-post').value.trim(),
            topic_set: this.querySelector('#topic-set').value.trim(),
            topic_response: this.querySelector('#topic-response').value.trim(),
            topic_metadata: this.querySelector('#topic-metadata').value.trim()
        };
    }
    
    getUdpConfig() {
        return {
            configType: 'udp',
            IpAddress: this.querySelector('#udp-ip').value.trim(),
            localUdpPort: this.querySelector('#udp-port').value.trim(),
            Frequency: this.querySelector('#udp-frequency').value.trim()
        };
    }

    showAlert(message) {
        const alertBox = document.createElement('div');
    
        // 检查是否为黑色模式
        const isDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    
        // 基本样式
        alertBox.style.position = 'fixed';
        alertBox.style.top = '50%';
        alertBox.style.left = '50%';
        alertBox.style.transform = 'translate(-50%, -50%)';
        alertBox.style.padding = '20px';
        alertBox.style.borderRadius = '5px';
        alertBox.style.zIndex = '1000';
        alertBox.style.maxWidth = '80%';
        alertBox.style.maxHeight = '80%';
        alertBox.style.overflow = 'auto';
        alertBox.style.wordWrap = 'break-word';
        alertBox.style.overflowWrap = 'break-word';
        alertBox.style.whiteSpace = 'normal';
        alertBox.style.boxSizing = 'border-box';
    
        // 根据模式设置样式
        if (isDarkMode) {
            alertBox.style.backgroundColor = '#444'; // 深色背景
            alertBox.style.border = '1px solid #555'; // 深色边框
            alertBox.style.color = '#fff'; // 白色文字
        } else {
            alertBox.style.backgroundColor = '#fff'; // 白色背景
            alertBox.style.border = '1px solid #ccc'; // 浅色边框
            alertBox.style.color = '#000'; // 黑色文字
        }
    
        alertBox.innerHTML = `
            <p style="margin-bottom: 20px; text-align: left;">${message}</p>
            <div style="text-align: center;">
                <button style="
                    padding: 10px 20px; 
                    cursor: pointer;
                    background-color: #007bff; /* 蓝色背景 */
                    color: #fff; /* 白色文字 */
                    border: none;
                    border-radius: 3px;
                ">OK</button>
            </div>
        `;
    
        alertBox.querySelector('button').addEventListener('click', () => {
            alertBox.remove();
        });
    
        document.body.appendChild(alertBox);
    }

    showOtaOverlay() {
        const overlay = this.querySelector('#ota-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
        } else {
            console.error('OTA overlay element not found.');
        }
    }

    hideOtaOverlay() {
        const overlay = this.querySelector('#ota-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
}

customElements.define('Bituo-panel', BituoPanel);