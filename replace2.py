import sys
import re

with open('d:\\StartUp\\ClinicalCardioBot-main\\Clinical_Cardio_Bot\\chatbot\\static\\js\\executor.js', 'r', encoding='utf-8') as f:
    text = f.read()

match = re.search(r'    \} else if \(functionName === \'pairBluetoothDevice\'\) \{.+?\n    else if \(functionName === \'startECGRecording\'\) \{', text, re.DOTALL)

if match:
    replacement = """    } else if (functionName === 'pairBluetoothDevice') {
        try {
            if (bluetoothDevice) {
                console.log('Simulation device already connected');
                chatSocket.send(JSON.stringify({
                    type: 'js_function_response',
                    message: 'Paired and connected',
                    patient_id: patientId,
                    sender: "executor",
                }));
                return;
            }

            console.log('Bypassing UI - Auto Pairing Virtual Device');
            
            // Auto pair a virtual device immediately
            bluetoothDevice = { name: 'Virtual_ECG_Device' };
            
            chatSocket.send(JSON.stringify({
                type: 'js_function_response',
                message: 'Device paired successfully', // Matches what the agent expects when successful
                patient_id: patientId,
                sender: "executor",
                pairing_completed: true
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
    else if (functionName === 'startECGRecording') {"""

    new_text = text[:match.start()] + replacement + text[match.end():]
    with open('d:\\StartUp\\ClinicalCardioBot-main\\Clinical_Cardio_Bot\\chatbot\\static\\js\\executor.js', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print('Auto pair logic updated.')
else:
    print('Could not find match for auto pair.')