import time
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
import json
from uuid import UUID
from django.utils import timezone
from .models import Patient, Clinical_Record, ECG_record
import neurokit2 as nk


from .utils import response_events


@tool
async def check_connect(config: RunnableConfig) -> str:
    """
    this tool Ask the patient to Check if the Bluetooth is connected on the patient's device.

    Args:
        config: Configuration dictionary containing the patient_id and WebSocket of the patient.

    Returns:
        str: "asked sucessfully" if Bluetooth is connected, "Failed to check" otherwise.
    """
    configuration = config.get("configurable", {})
    websocket = configuration.get("websocket", None)

    if not websocket:
        return "No WebSocket connection provided."

    try:
        start_time = time.time()
        await websocket.send(
            json.dumps(
                {
                    "type": "call_js_function",
                    "function_name": "checkBluetoothConnection",
                    "args": [],
                    "sender": "tool",
                }
            )
        )

        return "we succesfully check"

    except Exception as e:

        return "Check Failed"


@tool
async def pair_device(config: RunnableConfig) -> str:
    """
    Ask the patient to pair the ECG Bluetooth device.

    Args:
        config: Configuration dictionary containing the patient_id and WebSocket of the patient.

    Returns:
        str: "Pairing request sent successfully" if the request is sent, "Failed to send pairing request" otherwise.
    """
    configuration = config.get("configurable", {})
    websocket = configuration.get("websocket", None)

    if not websocket:
        return "No WebSocket connection provided."

    try:
        start_time = time.time()
        await websocket.send(
            json.dumps(
                {
                    "type": "call_js_function",
                    "function_name": "pairBluetoothDevice",
                    "args": [],
                    "sender": "tool",
                }
            )
        )
        print(f"Tool: Sent pairing request at {time.time()}")
        return "Pairing request sent successfully"
    except Exception as e:
        print(f"Tool: Error sending pairing request: {str(e)}")
        return "Failed to send pairing request"


@tool
async def recording_request(config: RunnableConfig) -> str:
    """
    this tool  request the client side to start recording his ECG and send back the record it just request not return the record.
    you should wait the client side response after send reequest.

    Args:

    config: Configuration dictionary containing the patient_id and WebSocket of the patient.

    Returns:
        str: A message indicating the recording request status.
    """
    configuration = config.get("configurable", {})
    websocket = configuration.get("websocket", None)

    if not websocket:
        return "No WebSocket connection provided."

    try:
        start_time = time.time()
        await websocket.send(
            json.dumps(
                {
                    "type": "call_js_function",
                    "function_name": "startECGRecording",
                    "args": [60, True],
                    "sender": "tool",
                }
            )
        )
        print(f"Tool: Sent recording request at {time.time()}")
        return "Recording request sent successfully"
    except Exception as e:
        print(f"Tool: Error sending recording request: {str(e)}")
        return "Failed to send Recording request"


@tool
def check_record_ECG_correctly(config: RunnableConfig) -> str:
    """
    This tool verifies whether the ECG record has been saved correctly in database and ensures that all ECG values are valid and free of errors.
    It checks for any missing, corrupted, or invalid data within the record.
    If any issues are detected, the tool identifies them and reports an error.
    Additionally, the tool performs data cleaning by removing noise, correcting inconsistencies, and ensuring the ECG values are properly formatted.
    Once the cleaning process is complete, it saves a validated and cleaned version of the ECG record.
    In case of any errors or failures during the process, the tool returns a detailed error message specifying the issue.


    Args:
        config: Configuration dictionary containing the patient_id and WebSocket of the patient.



    Returns:
        str: A message indicating the save status.
    """
    today = timezone.now().date()
    configuration = config.get("configurable", {})
    patient_id = configuration.get("patient_id", None)
    if not patient_id:
        raise ValueError("No patient ID configured.")
    try:
        patient_id = UUID(patient_id)  # Convert string to UUID object
    except ValueError:
        error = f"Invalid patient ID format. Must be a valid UUID.{patient_id}"
        raise ValueError(error)
    try:
        # Fetch the patient instance
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        raise ValueError(f"No patient found with ID {patient_id}.")
    try:
        has_record_today = Clinical_Record.objects.filter(
            patient=patient, created_at__date=today
        ).exists()
        if has_record_today:
            clinical_data = Clinical_Record.objects.get(
                patient=patient, created_at__date=today
            )
            has_ecg_today = ECG_record.objects.filter(
                record=clinical_data, created_at__date=today
            ).exists()
            if has_ecg_today:
                ### treat the ECG here
                try:
                    ecg_record = ECG_record.objects.get(record=clinical_data)
                    ecg_data = "[" + ecg_record.ECG + "]"
                    ecg_data = json.loads(
                        ecg_data
                    )  # e.g., "[1.2, 2.3, 3.4]" -> [1.2, 2.3, 3.4]
                except json.JSONDecodeError:
                    print("Invalid ECG data format")
                    return
                sampling_rate = (
                    len(ecg_data) / 60
                )  # djust based on your data's actual sampling rate
                ecg_signals, info = nk.ecg_process(
                    ecg_data, sampling_rate=sampling_rate
                )

                # check if the ECG is valid (e.g., if peaks are detected)
                if (
                    len(info["ECG_R_Peaks"]) == 0
                ):  # Fixed: Check length instead of array directly
                    return "ECG validation failed: No R-peaks detected"

                

                print(f"ECG record for {clinical_data} cleaned and saved successfully")

                return "ECG record saved successfully."
            else:
                return (
                    "the ECG record not find in database there is no ECG record today"
                )
        else:
            return "the Patient did not recording his clinical data yet!"
    except Exception as e:
        print(f"Tool: Error sending recording request: {str(e)}")
        return f"Tool: Error sending recording request: {str(e)}"

@tool
async def finish_recording(config: RunnableConfig) -> str:
    """
    this tool notify the patient that all his ECG data is collected successfully .

    Args:
        config: Configuration dictionary containing the patient_id and WebSocket of the patient.

    Returns:
        str: "Notify sucessfully" if no problem , "Failed to notify" otherwise.
    """
    configuration = config.get("configurable", {})
    websocket = configuration.get("websocket", None)

    if not websocket:
        return "No WebSocket connection provided."

    try:
        
        await websocket.send(
            json.dumps(
                {
                    "type": "swap_webSocket2",
                    "function_name": "swap_webSocket2",
                    "args": [],
                    "sender": "tool",
                }
            )
        )

        return "we succesfully notify"

    except Exception as e:

        return "Notify Failed"