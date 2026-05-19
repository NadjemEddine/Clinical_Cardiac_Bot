
// executor.js
let bluetoothDevice = null;
let ecgData = [];
let totalSamples = 0;
let validSamples = 0;
let lastElectrodeStatus = null;
let gattServer = null;          // <--- ADD THIS LINE

// This object is visible to both onDisconnected AND executeTool
const BLE_MANAGER = {
    activeSocket: null,
    isRecording: false,
    patientId: null
};

// Queue for pairing requests from agent
let pendingPairingRequest = null;

async function executeTool(chatSocket, data, record) {
    const functionName = data.function_name;
    const patientId = patient_id;

    // Save the reference so the global handler can find it
    BLE_MANAGER.activeSocket = chatSocket;
    BLE_MANAGER.patientId = patientId; // ensure this is defined
    BLE_MANAGER.isRecording = true;

    // This inner function can "see" chatSocket because of its scope
    const handleBleFailure = (event) => {
        console.log("The bridge caught the disconnect event!");
        
        if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
            chatSocket.send(JSON.stringify({
                type: 'js_function_response',
                message: 'The device was powered off. Recording stopped.',
                sender: 'executor'
            }));
        }
        
        // Stop listening after the error is handled
        window.removeEventListener('ble_disconnected', handleBleFailure);
    };

    // Start listening for the "alarm" we named in Step 1
    window.addEventListener('ble_disconnected', handleBleFailure);

    if (functionName === 'checkBluetoothConnection') {
        try {
            console.log(`Checking Bluetooth connection...`);

            // Check 1: Is Bluetooth API available?
            const isBluetoothAvailable = await navigator.bluetooth.getAvailability();
            if (!isBluetoothAvailable) {
                console.error('Bluetooth is not available on this device/browser.');
                chatSocket.send(JSON.stringify({
                    type: 'js_function_response',
                    message: 'Not connected',
                    patient_id: patientId,
                    sender: "executor",
                }));
                return;
            }

            // Check 2: Do we have a device reference?
            if (!bluetoothDevice) {
                console.log('No device paired yet');
                // chatSocket.send(JSON.stringify({
                //     type: 'js_function_response',
                //     message: 'Not connected',
                //     patient_id: patientId,
                //     sender: "executor",
                // }));
                return;
            }

            // Check 3: Is the device still connected via GATT?
            if (!gattServer || !gattServer.connected) {
                console.log('Device was paired but GATT is disconnected');

                // Try to reconnect automatically (no user gesture needed)
                try {
                    console.log('Attempting automatic reconnection...');
                    gattServer = await bluetoothDevice.gatt.connect();
                    console.log('Reconnected successfully');

                    chatSocket.send(JSON.stringify({
                        type: 'js_function_response',
                        message: 'Connected',
                        patient_id: patientId,
                        sender: "executor",
                    }));
                    return;
                } catch (reconnectError) {
                    console.log('Auto-reconnect failed:', reconnectError.message);
                    chatSocket.send(JSON.stringify({
                        type: 'js_function_response',
                        message: 'Not connected',
                        patient_id: patientId,
                        sender: "executor",
                    }));
                    return;
                }
            }

            // All checks passed - device is actually connected
            console.log('Device is connected:', bluetoothDevice.name);
            chatSocket.send(JSON.stringify({
                type: 'js_function_response',
                message: 'Connected',
                patient_id: patientId,
                sender: "executor",
            }));

        } catch (error) {
            console.error('Error in checkBluetoothConnection:', error);
            chatSocket.send(JSON.stringify({
                type: 'js_function_response',
                message: `Error: ${error.message}`,
                patient_id: patientId,
                sender: "executor",
            }));
        }

    } else if (functionName === 'pairBluetoothDevice') {
        try {
            // Check if already connected
            if (bluetoothDevice && gattServer && gattServer.connected) {
                console.log('Device already connected:', bluetoothDevice.name);
                chatSocket.send(JSON.stringify({
                    type: 'js_function_response',
                    message: 'Paired and connected',
                    patient_id: patientId,
                    sender: "executor",
                }));
                return;
            }

            // Try to reconnect to existing device first (no user gesture needed)
            if (bluetoothDevice && bluetoothDevice.gatt) {
                try {
                    console.log('Attempting to reconnect to existing device...');
                    gattServer = await bluetoothDevice.gatt.connect();
                    console.log('Reconnected successfully');

                    chatSocket.send(JSON.stringify({
                        type: 'js_function_response',
                        message: 'Paired and connected',
                        patient_id: patientId,
                        sender: "executor",
                    }));
                    return;
                } catch (reconnectError) {
                    console.log('Reconnection failed, need new pairing:', reconnectError.message);
                    bluetoothDevice = null;
                    gattServer = null;
                }
            }

            // CRITICAL: Can't call requestDevice() from WebSocket
            // Store the request and show UI button
            console.log('Pairing requires user gesture - showing button');

            pendingPairingRequest = {
                chatSocket: chatSocket,
                patientId: patientId,
                data: data
            };

            // Show the pairing button to user
            showPairingButton();

            // Send immediate response (agent expects a response)
            chatSocket.send(JSON.stringify({
                type: 'js_function_response',
                message: 'Waiting for user to approve pairing',
                patient_id: patientId,
                sender: "executor",
            }));

        } catch (error) {
            console.error('Error in pairBluetoothDevice:', error);
            chatSocket.send(JSON.stringify({
                type: 'js_function_response',
                message: `Error: ${error.message}`,
                patient_id: patientId,
                sender: "executor",
            }));
        }
    }
    else if (functionName === 'startECGRecording') {
        // try {
        //     const duration = data.args[0] * 1000 || 10000; // Hardcoded 10s for now (adjust as needed)
        //     record = data.recordID
        //     if (!bluetoothDevice || !bluetoothDevice.gatt.connected) {
        //         chatSocket.send(JSON.stringify({
        //             type: 'js_function_response',
        //             message: 'Bluetooth device not connected',
        //             patient_id: patientId,
        //             sender: "executor",
        //         }));
        //         return;
        //     }

        //     const server = bluetoothDevice.gatt;
        //     const service = await server.getPrimaryService('4fafc201-1fb5-459e-8fcc-c5c9c331914b');
        //     const characteristic = await service.getCharacteristic('beb5483e-36e1-4688-b7f5-ea07361b26a8');

        //     ecgData = [];
        //     console.log('Starting ECG recording for 10 seconds...');
        //     const recordingAlert = showCustomAlert(
        //         'Recording in progress, please keep electrodes attached.',
        //         'http://127.0.0.1:8000/static/js/Animation-heart-ecg.json' // Heartbeat animation
        //     );

        //     characteristic.addEventListener('characteristicvaluechanged', (event) => {
        //         const value = new TextDecoder().decode(event.target.value);
        //         const [ecgValue, electrodesConnected] = value.split(',');
        //         const dataPoint = {
        //             timestamp: Date.now(),
        //             value: parseInt(ecgValue),
        //             electrodesConnected: electrodesConnected === '1'
        //         };
        //         ecgData.push(dataPoint);
        //         console.log(`ECG: ${dataPoint.value}, Electrodes: ${dataPoint.electrodesConnected ? 'Yes' : 'No'}`);
        //     });

        //     await characteristic.startNotifications();
        //     console.log('Notifications started.');

        //     await new Promise(resolve => setTimeout(resolve, duration));
        //     await characteristic.stopNotifications();
        //     console.log('Recording stopped. Total data points:', ecgData.length);
        //     recordingAlert.remove(); // Remove "in progress" alert
        //     showCustomAlert(
        //         'Recording complete, you may remove electrodes.',
        //         'http://127.0.0.1:8000/static/js/Animation-done.json', // Checkmark animation
        //         3000 // Auto-remove after 3 seconds
        //     );


        //     postECGRecord(ecgData);
        //     console.log('Recording details', ecgData);


        //     chatSocket.send(JSON.stringify({
        //         type: 'js_function_response',
        //         message: 'Recording completed',
        //         patient_id: patientId,
        //         sender: "executor",
        //     }));
        // } catch (error) {
        //     console.error('Error recording ECG:', error);
        //     alert('Recording failed due to an error.');
        //     chatSocket.send(JSON.stringify({
        //         type: 'js_function_response',
        //         message: `Error: ${error.message}`,
        //         patient_id: patientId,
        //         sender: "executor",
        //     }));
        // }
        try {
            const duration = data.args[0] * 1000 || 10000;

            if (!bluetoothDevice || !bluetoothDevice.gatt.connected) {
                chatSocket.send(JSON.stringify({
                    type: 'js_function_response',
                    message: 'Bluetooth device not connected',
                    patient_id: patientId,
                    sender: "executor",
                }));
                return;
            }

            const server = bluetoothDevice.gatt;
            const service = await server.getPrimaryService('4fafc201-1fb5-459e-8fcc-c5c9c331914b');
            const characteristic = await service.getCharacteristic('beb5483e-36e1-4688-b7f5-ea07361b26a8');

            // Reset global state
            ecgData = [];
            totalSamples = 0;
            validSamples = 0;
            lastElectrodeStatus = true;

            let isRecording = true;
            let hasSentDetachMessage = false;  // ← THIS IS KEY: send detach message ONLY ONCE

            const recordingAlert = showCustomAlert(
                'Recording in progress...<br><strong>Keep electrodes attached!</strong>',
                'http://127.0.0.1:8000/static/js/Animation-heart-ecg.json'
            );

            const stopRecording = async (reason = "completed") => {
                if (!isRecording) return;
                isRecording = false;

                try { await characteristic.stopNotifications(); } catch (e) { }
                characteristic.removeEventListener('characteristicvaluechanged', handleNotification);
                recordingAlert.remove();

                const actualDuration = Date.now() - startTime;

                if (reason === "electrodes_lost") {
                    showCustomAlert(
                        'Electrodes detached!<br>Recording stopped.',
                        'http://127.0.0.1:8000/static/js/Warning.json',
                        8000
                    );
                } if (reason === "device disconnected") {
                    showCustomAlert(
                        'Device Disconnected!<br>Recording stopped.',
                        'http://127.0.0.1:8000/static/js/Warning.json',
                        8000
                    );
                } else {
                    showCustomAlert(
                        lastElectrodeStatus
                            ? `Recording complete!<br>${validSamples} samples`
                            : `Recording finished<br>Electrodes were unstable`,
                        lastElectrodeStatus ? 'http://127.0.0.1:8000/static/js/Animation-done.json'
                            : 'http://127.0.0.1:8000/static/js/Animation-warning.json',
                        6000
                    );
                }

                // Send final payload
                const payload = {
                    recordID: record,
                    patientId: patientId,
                    timestamp: new Date().toISOString(),
                    durationMs: actualDuration,
                    totalSamples,
                    validSamples,
                    electrodesStable: lastElectrodeStatus,
                    samplingRateHz: totalSamples / (actualDuration / 1000) || 0,
                    ecgValues: ecgData,
                    stoppedEarly: reason === "electrodes_lost"
                };

                if (lastElectrodeStatus) {
                    postECGRecord(payload);
                }
                

                chatSocket.send(JSON.stringify({
                    type: 'js_function_response',
                    message: reason === "electrodes_lost" ? 'Recording aborted: Electrodes detached' : 'ECG recording completed',
                    electrodesOK: lastElectrodeStatus,
                    stoppedEarly: reason === "electrodes_lost",
                    validSamples,
                    patient_id: patientId,
                    sender: "executor",
                }));
            };

            const startTime = Date.now();

            const handleNotification = (event) => {

                if (!isRecording) return;
                if (BLE_MANAGER.isRecording === false) { console.error("Recording stopped by BLE_MANAGER"); return; }
                

                
                const value = new TextDecoder().decode(event.target.value).trim();
                const [ecgPart, flag] = value.split(';');
                if (!ecgPart || flag === undefined) return;

                const electrodeConnected = flag === '1';
                lastElectrodeStatus = electrodeConnected;

                // DETACH DETECTED → STOP EVERYTHING IMMEDIATELY
                if (!electrodeConnected) {
                    if (!hasSentDetachMessage) {
                        hasSentDetachMessage = true;
                        chatSocket.send(JSON.stringify({
                            type: 'js_function_response',
                            message: 'Electrodes detached! Recording stopped.',
                            electrodesOK: false,
                            patient_id: patientId,
                            sender: "executor",
                        }));
                    }
                    stopRecording("electrodes_lost");
                    return;
                }

                // Only process if electrodes OK
                const samples = ecgPart.split(',').filter(s => s !== '');
                for (const s of samples) {
                    totalSamples++;
                    const mv = parseFloat(s);
                    if (!isNaN(mv)) {
                        ecgData.push(mv);
                        validSamples++;
                    }
                }
            };

            // Start listening
            characteristic.addEventListener('characteristicvaluechanged', handleNotification);
            await characteristic.startNotifications();

            // Wait for either: time up OR electrodes lost
            const timeoutPromise = new Promise(resolve => setTimeout(() => resolve("timeout"), duration));
            const manualStopPromise = new Promise(resolve => {
                window.stopECGNow = () => resolve("manual");
            });

            const result = await Promise.race([timeoutPromise, manualStopPromise]);

            if (isRecording) {
                await stopRecording(result === "timeout" ? "completed" : "manual");
            }

        } catch (error) {
            console.error('ECG Recording Error:', error);
            recordingAlert?.remove();
            showCustomAlert('Recording failed!', null, 5000);
            chatSocket.send(JSON.stringify({
                type: 'js_function_response',
                message: `Error: ${error.message}`,
                patient_id: patientId,
                sender: "executor",
            }));
        }

    } else if (functionName === 'request_cardiac_mri') {
        try {
            console.log("the MRI is request is activate")
            handleUpload('mriForm', 'http://127.0.0.1:8000/chatbot/api/mri/upload/');

            chatSocket.send(JSON.stringify({
                type: 'js_function_response',
                message: 'Cardiac MRI completed successfully',
                patient_id: patientId,
                sender: "executor",
            }));

        } catch (error) {
            console.error('Error uploading Cardiac MRI:', error);
            alert('uploading failed due to an error.');
            chatSocket.send(JSON.stringify({
                type: 'js_function_response',
                message: `Error: ${error.message}`,
                patient_id: patientId,
                sender: "executor",
            }));
        }
    } else if (functionName === 'request_cardiac_ct') {
        try {
            handleUpload('ctForm', 'http://127.0.0.1:8000/chatbot/api/ct/upload/');
            showCustomAlert(
                'Uploading Complete Seccussfully. Thanks You',
                'http://127.0.0.1:8000/static/js/Animation-done.json', // Checkmark animation
                3000 // Auto-remove after 3 seconds
            );
            chatSocket.send(JSON.stringify({
                type: 'js_function_response',
                message: 'Cardiac CT completed successfully',
                patient_id: patientId,
                sender: "executor",
            }));
            doc

        } catch (error) {
            console.error('Error uploading Cardiac CT:', error);
            alert('uploading failed due to an error.');
            chatSocket.send(JSON.stringify({
                type: 'js_function_response',
                message: `Error: ${error.message}`,
                patient_id: patientId,
                sender: "executor",
            }));
        }

    }
}

// Export the executor function
export { executeTool };

// Plotting function


// Custom alert function
function showCustomAlert(message, animationUrl, duration = null) {
    // Remove any existing alert
    const existingAlert = document.querySelector('.custom-alert');
    if (existingAlert) existingAlert.remove();

    // Create the alert container
    const alertDiv = document.createElement('div');
    alertDiv.classList.add('custom-alert');
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '50%';
    alertDiv.style.left = '50%';
    alertDiv.style.transform = 'translate(-50%, -50%)';
    alertDiv.style.zIndex = '1000';
    alertDiv.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
    alertDiv.style.padding = '20px';
    alertDiv.style.borderRadius = '10px';
    alertDiv.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.2)';
    alertDiv.style.textAlign = 'center';
    alertDiv.style.maxWidth = '400px';

    // Add Lottie animation
    const lottiePlayer = document.createElement('div');
    lottiePlayer.innerHTML = `
        <lottie-player 
            src="${animationUrl}" 
            background="transparent" 
            speed="1" 
            style="width: 300px; height: 300px; margin: 0 auto;" 
            loop  
            autoplay
        ></lottie-player>
    `;

    // Add text
    const text = document.createElement('p');
    text.textContent = message;
    text.style.fontSize = '18px';
    text.style.fontFamily = 'Arial, sans-serif';
    text.style.marginTop = '10px';

    // Append elements
    alertDiv.appendChild(lottiePlayer);
    alertDiv.appendChild(text);
    document.body.appendChild(alertDiv);

    // Auto-remove after duration (if provided)
    if (duration) {
        setTimeout(() => {
            alertDiv.remove();
        }, duration);
    }

    return alertDiv; // Return for manual removal if needed
}

// Function to post ECG record
// async function postECGRecord(ecgData) {
//     try {
//         const ecg_record = ecgData.map(d => d.value);
//         console.log('ECG RECORD TEST:', ecg_record)
//         const response = await fetch("http://127.0.0.1:8000/chatbot/ecg-records/", {
//             method: "POST",
//             headers: {
//                 "Content-Type": "application/json",
//                 'X-CSRFToken': getCSRFToken(),  // Correct
//                 // Add authentication token if required (e.g., JWT or API key)
//                 // "Authorization": "Bearer YOUR_TOKEN_HERE"
//             },
//             body: JSON.stringify({
//                 record_id: record,
//                 ECG: ecg_record.toString(), // Convert array to JSON string as per your model
//             })
//         });

//         if (!response.ok) {
//             throw new Error(`HTTP error! Status: ${response.status}`);
//         }

//         const result = await response.json();
//         console.log("ECG Record created successfully:", result);
//     } catch (error) {
//         console.error("Error posting ECG record:", error);
//     }
// }

async function postECGRecord(payload) {
    try {
        // payload now contains: ecgValues (array of numbers), recordID, patientId, etc.
        const ecgValues = payload.ecgValues || [];  // Safety first

        console.log('ECG RECORD TEST (raw numbers):', ecgValues);
        console.log(`Sending ${ecgValues.length} ECG samples to server...`);

        const response = await fetch("http://127.0.0.1:8000/chatbot/ecg-records/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken(),  // Django CSRF protection
            },
            body: JSON.stringify({
                record_id: record,           // Use correct record ID
                // patient: payload.patientId,            // Assuming your model has patient ForeignKey
                // OR if your Django model uses TextField and expects string:
                ECG: ecgValues.join(','),

                // // Optional metadata (very useful for doctors & debugging)
                // duration_seconds: payload.durationMs / 1000,
                // valid_samples: payload.validSamples,
                // total_samples: payload.totalSamples,
                // electrodes_stable: payload.electrodesStable,
                // sampling_rate_hz: parseFloat(payload.samplingRateHz.toFixed(2)),
                // recorded_at: payload.timestamp,
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const result = await response.json();
        console.log("ECG Record created successfully:", result);

        // Optional: Show success to user
        showCustomAlert("ECG saved successfully!",
            "http://127.0.0.1:8000/static/js/Animation-done.json", 4000);

    } catch (error) {
        console.error("Error posting ECG record:", error);
        showCustomAlert("Failed to save ECG data", null, 5000);
    }
}



async function handleUpload(formId, endpoint) {
    console.log("We Call the Echo")
    const form = document.getElementById(formId);
    const modalId = formId.replace('Form', 'Modal');
    const modalElement = document.getElementById(modalId);

    if (!form || !modalElement) {
        console.error(`Form with ID ${formId} or Modal with ID ${modalId} not found.`);
        return;
    }

    // Show the modal programmatically
    try {
        const modalInstance = new bootstrap.Modal(modalElement);
        modalInstance.show();
    } catch (error) {
        console.error('Error showing modal:', error);
        alert('Unable to open the upload form. Please try again.');
        return;
    }

    // Prevent multiple event listeners by cloning the form
    const newForm = form.cloneNode(true);
    form.parentNode.replaceChild(newForm, form);

    // Reassign form to the new cloned form
    const updatedForm = document.getElementById(formId);

    updatedForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        const formData = new FormData(updatedForm);
        formData.append("patient", patient_id); // Add patient ID

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCSRFToken(), // CSRF token for Django
                },
            });
            const data = await response.json();

            if (response.ok) {
                showCustomAlert(
                    'Uploading Complete Seccussfully. Thanks You',
                    'http://127.0.0.1:8000/static/js/Animation-done.json', // Checkmark animation
                    3000 // Auto-remove after 3 seconds
                );
                updatedForm.reset(); // Reset the form
                const modalInstance = bootstrap.Modal.getInstance(modalElement);
                if (modalInstance) {
                    modalInstance.hide(); // Hide the modal
                } else {
                    console.warn(`Bootstrap modal instance for ${modalId} not found.`);
                    modalElement.classList.remove('show'); // Fallback to hide manually
                    modalElement.style.display = 'none';
                    document.body.classList.remove('modal-open');
                    document.querySelector('.modal-backdrop')?.remove();
                }
            } else {
                alert("Upload failed: " + JSON.stringify(data));
            }
        } catch (error) {
            console.error('Upload error:', error);
            alert("Something went wrong. Please try again.");
        }
    });
}

// This function is called when user clicks the pairing button
async function handleUserPairingClick() {
    if (!pendingPairingRequest) {
        console.error('No pending pairing request');
        return;
    }

    const { chatSocket, patientId } = pendingPairingRequest;

    try {
        console.log('User clicked pairing - showing device selector...');

        // NOW we can call requestDevice because it's from a user click
        bluetoothDevice = await navigator.bluetooth.requestDevice({
            filters: [{ name: 'ESP32_ECG_Device' }],
            optionalServices: ['4fafc201-1fb5-459e-8fcc-c5c9c331914b']
        });
        console.log('Device selected:', bluetoothDevice.name);

        // Connect to GATT server
        gattServer = await bluetoothDevice.gatt.connect();
        console.log('GATT connected:', gattServer.connected);

        // Set up disconnect handler
        bluetoothDevice.addEventListener('gattserverdisconnected', onDisconnected);

        // Clear pending request
        pendingPairingRequest = null;

        // Hide the button
        hidePairingButton();

        // Send success notification to agent
        chatSocket.send(JSON.stringify({
            type: 'js_function_response',
            message: 'Device paired successfully',
            patient_id: patientId,
            sender: "executor",
            pairing_completed: true
        }));


        return { success: true };

    } catch (error) {
        console.error('User pairing failed:', error);

        bluetoothDevice = null;
        gattServer = null;

        // Keep the button visible so user can retry
        updatePairingButtonError(error.message);

        // Notify agent of failure
        chatSocket.send(JSON.stringify({
            type: 'js_function_response',
            message: `Pairing failed: ${error.message}`,
            patient_id: patientId,
            sender: "executor",
            pairing_failed: true
        }));

        return { success: false, error: error.message };
    }
}

// 1. Ensure your variables are accessible to this function
// (gattServer, chatSocket, etc. should be in a scope this function can see)

function onDisconnected(event) {
    const deviceName = event.target.name || "ECG Device";
    console.warn(`[HALT] ${deviceName} disconnected from Bluetooth.`);

    // 2. STOP THE RECORDING LOGIC IMMEDIATELY
    BLE_MANAGER.isRecording = false;
    
    // 3. REMOVE THE DATA LISTENER (The "Kill Switch")
    // This prevents handleNotification from ever running again
    if (characteristic) {
        characteristic.removeEventListener('characteristicvaluechanged', handleNotification);
        console.log("Listener detached: handleNotification will no longer execute.");
    }

    // 4. CLEAR TIMERS (Stop the 60-second countdown)
    if (typeof recordingInterval !== 'undefined') {
        clearInterval(recordingInterval);
        console.log("Recording timer stopped.");
    }

    // 5. NOTIFY THE AGENT / WEBSOCKET
    if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        chatSocket.send(JSON.stringify({
            type: 'js_function_response',
            message: 'FATAL ERROR: The device was powered off or lost connection. The session has been terminated.',
            status: 'failed',
            sender: 'executor'
        }));
    }

    // 6. UI CLEANUP
    // Remove any loading spinners or "Recording..." alerts
    document.getElementById('status-indicator').innerText = "Disconnected";
    alert("Bluetooth link lost. Please ensure the ECG device is powered on and try again.");
    
    // 7. RESET GLOBALS
    gattServer = null;
    deviceConnected = false;
}
// UI Functions
function showPairingButton() {
    let btn = document.getElementById('bluetooth-pair-btn');

    if (!btn) {
        btn = document.createElement('button');
        btn.id = 'bluetooth-pair-btn';
        btn.innerHTML = '🔗 Connect ECG Device';
        btn.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 8px 16px rgba(102, 126, 234, 0.4);
            z-index: 10000;
            transition: all 0.3s ease;
            animation: slideIn 0.5s ease, pulse 2s infinite;
        `;

        btn.onmouseover = () => {
            btn.style.transform = 'scale(1.05)';
            btn.style.boxShadow = '0 12px 24px rgba(102, 126, 234, 0.6)';
        };

        btn.onmouseout = () => {
            btn.style.transform = 'scale(1)';
            btn.style.boxShadow = '0 8px 16px rgba(102, 126, 234, 0.4)';
        };

        btn.onclick = async () => {
            btn.disabled = true;
            btn.innerHTML = '⏳ Connecting...';
            btn.style.background = '#6c757d';

            await handleUserPairingClick();
        };

        document.body.appendChild(btn);

        // Add animations
        if (!document.getElementById('pairing-btn-styles')) {
            const style = document.createElement('style');
            style.id = 'pairing-btn-styles';
            style.textContent = `
                @keyframes slideIn {
                    from {
                        transform: translateX(400px);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                @keyframes pulse {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                }
            `;
            document.head.appendChild(style);
        }
    }

    btn.style.display = 'block';
}

function hidePairingButton() {
    const btn = document.getElementById('bluetooth-pair-btn');
    if (btn) {
        btn.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            btn.style.display = 'none';
        }, 300);
    }
}

function updatePairingButtonError(errorMsg) {
    const btn = document.getElementById('bluetooth-pair-btn');
    if (btn) {
        btn.disabled = false;
        btn.innerHTML = '❌ Failed - Try Again';
        btn.style.background = '#dc3545';

        setTimeout(() => {
            btn.innerHTML = '🔗 Connect ECG Device';
            btn.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        }, 2000);
    }
}

// Make function available globally
window.handleUserPairingClick = handleUserPairingClick;