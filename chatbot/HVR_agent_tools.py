from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
import json
from uuid import UUID
from django.utils import timezone
from .models import Patient, Clinical_Record, ECG_record
import neurokit2 as nk


@tool
def check_connect(config: RunnableConfig) -> str:
    """
    Ask the patient to check if Bluetooth is connected on their device.
    The patient will confirm whether Bluetooth is on or off.

    Args:
        config: Configuration dictionary containing the patient_id.

    Returns:
        str: Status of the Bluetooth check request.
    """
    return "I've asked the patient to check their Bluetooth. Please wait for their response."


@tool
def pair_device(config: RunnableConfig) -> str:
    """
    Ask the patient to pair their ECG Bluetooth device.
    The patient will attempt to pair and confirm the result.

    Args:
        config: Configuration dictionary containing the patient_id.

    Returns:
        str: Status of the pairing request.
    """
    return "I've asked the patient to pair their ECG device. Waiting for their confirmation."


@tool
def recording_request(config: RunnableConfig) -> str:
    """
    Request the patient to start a 60-second ECG recording.
    The patient will record and the data will be saved automatically.

    Args:
        config: Configuration dictionary containing the patient_id.

    Returns:
        str: Status of the recording request.
    """
    return "I've asked the patient to start the ECG recording. The data will be saved automatically when complete."


@tool
def check_record_ECG_correctly(config: RunnableConfig) -> str:
    """
    Verify whether the ECG record has been saved correctly in the database.
    Checks for missing, corrupted, or invalid data.
    If valid, returns confirmation. If missing, reports the issue.

    Args:
        config: Configuration dictionary containing the patient_id.

    Returns:
        str: A message indicating the ECG save status.
    """
    today = timezone.now().date()
    configuration = config.get("configurable", {})
    patient_id = configuration.get("patient_id", None)
    if not patient_id:
        raise ValueError("No patient ID configured.")
    try:
        patient_id = UUID(patient_id)
    except ValueError:
        error = f"Invalid patient ID format. Must be a valid UUID.{patient_id}"
        raise ValueError(error)
    try:
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
                try:
                    ecg_record = ECG_record.objects.get(record=clinical_data)
                    ecg_data = "[" + ecg_record.ECG + "]"
                    ecg_data = json.loads(ecg_data)
                except json.JSONDecodeError:
                    print("Invalid ECG data format")
                    return "ECG data is corrupted or invalid."
                sampling_rate = len(ecg_data) / 60
                ecg_signals, info = nk.ecg_process(
                    ecg_data, sampling_rate=sampling_rate
                )

                if len(info["ECG_R_Peaks"]) == 0:
                    return "ECG validation failed: No R-peaks detected. The recording may be invalid."

                print(f"ECG record for {clinical_data} cleaned and saved successfully")
                return "ECG record validated and saved successfully in the database."
            else:
                return "No ECG record found in the database for today. The recording may not have been saved."
        else:
            return "No clinical record found for today. The patient needs to record their clinical data first."
    except Exception as e:
        print(f"Tool: Error checking ECG record: {str(e)}")
        return f"Error checking ECG record: {str(e)}"


@tool
def finish_recording(config: RunnableConfig) -> str:
    """
    Notify that the ECG recording process is complete and the system should proceed to imaging collection.

    Args:
        config: Configuration dictionary containing the patient_id.

    Returns:
        str: Confirmation message.
    """
    return "ECG recording process completed successfully. Ready to proceed to imaging."
