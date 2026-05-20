import sys

with open('d:\\StartUp\\ClinicalCardioBot-main\\Clinical_Cardio_Bot\\chatbot\\static\\js\\executor.js', 'r', encoding='utf-8') as f:
    text = f.read()

start_idx = text.find("else if (functionName === 'startECGRecording') {")
end_idx = text.find("} else if (functionName === 'request_cardiac_mri') {")

print("Start:", start_idx)
print("End:", end_idx)

if start_idx != -1 and end_idx != -1:
    replacement = """else if (functionName === 'startECGRecording') {
        try {
            const duration = data.args[0] * 1000 || 10000;

            if (!bluetoothDevice) {
                chatSocket.send(JSON.stringify({
                    type: 'js_function_response',
                    message: 'Bluetooth device not connected',
                    patient_id: patientId,
                    sender: "executor",
                }));
                return;
            }

            // Reset global state
            ecgData = [];
            totalSamples = 0;
            validSamples = 0;
            lastElectrodeStatus = true;

            let isRecording = true;
            let hasSentDetachMessage = false;

            const recordingAlert = showCustomAlert(
                'Recording in progress...<br><strong>Keep electrodes attached!</strong><br><br>'+
                '<div><button id="simDisconnectBtn" style="margin-right:10px; padding: 5px; background: red; color: white; border: none; border-radius: 5px; cursor: pointer;">Simulate Disconnect</button>'+
                '<button id="simElectrodeBtn" style="padding: 5px; background: orange; color: white; border: none; border-radius: 5px; cursor: pointer;">Simulate Electrode Off</button></div>',
                'http://127.0.0.1:8000/static/js/Animation-heart-ecg.json'
            );

            // Adding a small delay to attach listeners after DOM is updated by showCustomAlert
            setTimeout(() => {
                const discBtn = document.getElementById("simDisconnectBtn");
                const elecBtn = document.getElementById("simElectrodeBtn");
                if(discBtn) discBtn.onclick = () => { onDisconnected({target:{name:'Simulated Device'}}); };
                if(elecBtn) elecBtn.onclick = () => { lastElectrodeStatus = false; };
            }, 500);

            const stopRecording = async (reason = "completed") => {
                if (!isRecording) return;
                isRecording = false;

                recordingAlert.remove();

                const actualDuration = Date.now() - startTime;

                if (reason === "electrodes_lost") {
                    showCustomAlert(
                        'Electrodes detached!<br>Recording stopped.',
                        'http://127.0.0.1:8000/static/js/Warning.json',
                        8000
                    );
                } else if (reason === "device disconnected") {
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
                    stoppedEarly: reason === "electrodes_lost" || reason === "device disconnected"
                };

                if (lastElectrodeStatus && reason === "completed") {
                     await postECGRecord(payload);
                }

                chatSocket.send(JSON.stringify({
                    type: 'js_function_response',
                    message: reason === "electrodes_lost" ? 'Recording aborted: Electrodes detached' : 
                             reason === "device disconnected" ? 'FATAL ERROR: The device was powered off.' : 'ECG recording completed',
                    electrodesOK: lastElectrodeStatus,
                    stoppedEarly: reason === "electrodes_lost" || reason === "device disconnected",
                    validSamples,
                    patient_id: patientId,
                    sender: "executor",
                }));
            };

            const startTime = Date.now();
            let sampleIndex = 0;

            const handleNotification = () => {
                if (!isRecording) return;
                if (BLE_MANAGER.isRecording === false) { 
                    console.error("Recording stopped by BLE_MANAGER"); 
                    stopRecording("device disconnected");
                    return; 
                }

                if (!lastElectrodeStatus) {
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

                // Append dummy data
                for (let i = 0; i < 5; i++) {
                    totalSamples++;
                    const mv = ecgSampleData[sampleIndex % ecgSampleData.length];
                    sampleIndex++;
                    ecgData.push(mv);
                    validSamples++;
                }
                
                if (Date.now() - startTime >= duration) {
                    stopRecording("completed");
                } else {
                    setTimeout(handleNotification, 20); // 20ms = 50Hz updates of 5 samples each = 250Hz roughly
                }
            };

            // Start simulation loop
            setTimeout(handleNotification, 20);

        } catch (error) {
            console.error('ECG Recording Error:', error);
            showCustomAlert('Recording failed!', null, 5000);
            chatSocket.send(JSON.stringify({
                type: 'js_function_response',
                message: `Error: ${error.message}`,
                patient_id: patientId,
                sender: "executor",
            }));
        }

    """
    new_text = text[:start_idx] + replacement + text[end_idx:]
    with open('d:\\StartUp\\ClinicalCardioBot-main\\Clinical_Cardio_Bot\\chatbot\\static\\js\\executor.js', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print('Replaced successfully.')
else:
    print('Could not find start or end index.')
