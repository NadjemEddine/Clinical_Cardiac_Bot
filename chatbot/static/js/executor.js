// executor.js - Client-side tool executor for the HTTP agent flow
// All functions return Promises with results for the agent.

let bluetoothDevice = { name: 'Virtual_ECG_Device' }; // pre-paired for simulation
let ecgData = [];
let totalSamples = 0;
let validSamples = 0;
let lastElectrodeStatus = null;
let gattServer = null;
let _recordingBreaker = null; // call this to stop recording

async function executeTool(functionName, args, record) {
    console.log(`[EXECUTOR] Running: ${functionName}`);
    switch (functionName) {
        case 'checkBluetoothConnection':
            return await checkBluetoothConnection();
        case 'pairBluetoothDevice':
            return await pairBluetoothDevice();
        case 'startECGRecording':
            return await startECGRecording(args, record);
        case 'requestEchoImaging':
            requestUpload('echoForm', '/chatbot/api/echo/upload/');
            return null; // UI-only, no agent update
        case 'requestCardiacMRI':
            requestUpload('mriForm', '/chatbot/api/mri/upload/');
            return null; // UI-only, no agent update
        case 'requestCardiacCT':
            requestUpload('ctForm', '/chatbot/api/ct/upload/');
            return null; // UI-only, no agent update
        default:
            console.warn('Unknown tool function:', functionName);
            return null;
    }
}

async function checkBluetoothConnection() {
    console.log('[EXECUTOR] Bluetooth check → Connected (simulation)');
    return 'Connected';
}

async function pairBluetoothDevice() {
    bluetoothDevice = { name: 'Virtual_ECG_Device' };
    console.log('[EXECUTOR] Pairing virtual device');
    return 'Paired and connected';
}

async function startECGRecording(args, record) {
    const duration = (args && args[0]) ? args[0] * 1000 : 60000;
    if (!bluetoothDevice) return 'Bluetooth device not connected';

    ecgData = [];
    totalSamples = 0;
    validSamples = 0;
    lastElectrodeStatus = true;
    _recordingBreaker = null;

    return new Promise((resolve) => {
        let isRecording = true;
        const startTime = Date.now();

        showRecordingControls({
            onBreak: () => {
                if (!isRecording) return;
                isRecording = false;
                _recordingBreaker = null;
                hideRecordingControls();
                resolve('Recording aborted by user');
            },
            onDisconnect: () => {
                if (!isRecording) return;
                isRecording = false;
                _recordingBreaker = null;
                hideRecordingControls();
                resolve('Recording failed: Bluetooth connection lost');
            },
            onElectrodeOff: () => {
                if (!isRecording) return;
                isRecording = false;
                _recordingBreaker = null;
                hideRecordingControls();
                resolve('Recording failed: electrode off or moved during recording');
            },
        });

        const stopRecording = (reason) => {
            if (!isRecording) return;
            isRecording = false;
            _recordingBreaker = null;
            hideRecordingControls();

            if (reason === 'completed') {
                const payload = {
                    recordID: record,
                    ecgValues: ecgData,
                    totalSamples,
                    validSamples,
                };
                postECGRecord(payload)
                    .then(() => resolve('ECG recording completed'))
                    .catch(() => resolve('ECG recording completed but save failed'));
            } else if (reason === 'error') {
                resolve('Recording failed due to an error');
            }
        };

        let sampleIndex = 0;
        const tick = () => {
            if (!isRecording) return;
            for (let i = 0; i < 5; i++) {
                totalSamples++;
                const mv = ecgSampleData[sampleIndex % ecgSampleData.length];
                sampleIndex++;
                ecgData.push(mv);
                validSamples++;
            }
            if (Date.now() - startTime >= duration) {
                stopRecording('completed');
            } else {
                setTimeout(tick, 20);
            }
        };
        setTimeout(tick, 20);
    });
}

function breakCurrentAction() {
    if (_recordingBreaker) {
        _recordingBreaker();
    }
}

function showRecordingControls(handlers) {
    hideRecordingControls();

    const panel = document.createElement('div');
    panel.id = 'recording-controls';
    panel.style.cssText = 'position:fixed; bottom:20px; right:20px; display:flex; flex-direction:column; gap:8px; z-index:9999;';

    // Disconnect button
    const disconnectBtn = document.createElement('button');
    disconnectBtn.textContent = '📡 Lost Connection';
    disconnectBtn.style.cssText = 'padding:10px 16px; background:#6c757d; color:white; border:none; border-radius:8px; font-size:13px; font-weight:bold; cursor:pointer; box-shadow:0 4px 12px rgba(0,0,0,0.3);';
    disconnectBtn.onclick = () => {
        disconnectBtn.style.opacity = '0.5';
        disconnectBtn.textContent = '📡 Disconnecting...';
        disconnectBtn.disabled = true;
        handlers.onDisconnect();
    };
    panel.appendChild(disconnectBtn);

    // Electrode button
    const electrodeBtn = document.createElement('button');
    electrodeBtn.id = 'electrode-btn';
    electrodeBtn.textContent = '⚡ Off/Move Electrode';
    electrodeBtn.style.cssText = 'padding:10px 16px; background:#fd7e14; color:white; border:none; border-radius:8px; font-size:13px; font-weight:bold; cursor:pointer; box-shadow:0 4px 12px rgba(0,0,0,0.3);';
    electrodeBtn.onclick = () => {
        electrodeBtn.style.opacity = '0.5';
        electrodeBtn.textContent = '⚡ Electrode OFF...';
        electrodeBtn.disabled = true;
        handlers.onElectrodeOff();
    };
    panel.appendChild(electrodeBtn);

    // Break button
    const breakBtn = document.createElement('button');
    breakBtn.textContent = '⏹ Break';
    breakBtn.style.cssText = 'padding:10px 16px; background:#dc3545; color:white; border:none; border-radius:8px; font-size:13px; font-weight:bold; cursor:pointer; box-shadow:0 4px 12px rgba(220,53,69,0.4);';
    breakBtn.onclick = () => {
        breakBtn.style.opacity = '0.5';
        breakBtn.textContent = '⏹ Breaking...';
        breakBtn.disabled = true;
        handlers.onBreak();
    };
    panel.appendChild(breakBtn);

    document.body.appendChild(panel);
    _recordingBreaker = handlers.onBreak;
}

function hideRecordingControls() {
    const panel = document.getElementById('recording-controls');
    if (panel) panel.remove();
    _recordingBreaker = null;

    const status = document.getElementById('recording-status');
    if (status) status.remove();
}

let _statusTimeout = null;
function showRecordingStatus(text) {
    const existing = document.getElementById('recording-status');
    if (existing) existing.remove();
    if (_statusTimeout) clearTimeout(_statusTimeout);

    const div = document.createElement('div');
    div.id = 'recording-status';
    div.style.cssText = 'position:fixed; bottom:175px; right:20px; padding:8px 14px; background:#333; color:white; border-radius:6px; font-size:12px; z-index:9999; max-width:260px; box-shadow:0 2px 8px rgba(0,0,0,0.3);';
    div.textContent = text;
    document.body.appendChild(div);

    _statusTimeout = setTimeout(() => {
        div.remove();
        _statusTimeout = null;
    }, 4000);
}

async function requestUpload(formId, endpoint) {
    const form = document.getElementById(formId);
    const modalId = formId.replace('Form', 'Modal');
    const modalElement = document.getElementById(modalId);
    if (!form || !modalElement) return;

    const modalInstance = new bootstrap.Modal(modalElement);
    modalInstance.show();

    const newForm = form.cloneNode(true);
    form.parentNode.replaceChild(newForm, form);
    const updatedForm = document.getElementById(formId);

    const handler = async function (e) {
        e.preventDefault();
        const formData = new FormData(updatedForm);
        formData.append('patient', patient_id);
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': getCSRFToken() },
            });
            if (response.ok) {
                showCustomAlert('Upload Successful!', null, 3000);
                updatedForm.reset();
                modalInstance.hide();
            } else {
                alert('Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
        }
        updatedForm.removeEventListener('submit', handler);
    };
    updatedForm.addEventListener('submit', handler);
}

async function postECGRecord(payload) {
    const ecgValues = payload.ecgValues || [];
    console.log(`[EXECUTOR] Sending ${ecgValues.length} ECG samples...`);
    const response = await fetch('/chatbot/ecg-records/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({
            record_id: payload.recordID,
            ECG: ecgValues.join(','),
        }),
    });
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    console.log('[EXECUTOR] ECG saved successfully');
}

function showCustomAlert(message, animationUrl, duration) {
    const existing = document.querySelector('.custom-alert');
    if (existing) existing.remove();
    const div = document.createElement('div');
    div.className = 'custom-alert';
    div.style.cssText = 'position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); z-index:1000; background:rgba(255,255,255,0.95); padding:20px; border-radius:10px; box-shadow:0 4px 8px rgba(0,0,0,0.2); text-align:center; max-width:400px;';
    const p = document.createElement('p');
    p.innerHTML = message;
    p.style.cssText = 'font-size:18px; margin:10px 0;';
    div.appendChild(p);
    document.body.appendChild(div);
    if (duration) setTimeout(() => div.remove(), duration);
    return div;
}

function getCSRFToken() {
    return document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1] || '';
}
