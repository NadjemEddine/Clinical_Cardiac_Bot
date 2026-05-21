from typing import List, Dict
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from .models import Clinical_Record
from accounts.models import Patient
from typing import Dict, Any
import json
from uuid import UUID

from django.utils import timezone

today = timezone.now().date()

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda

from langgraph.prebuilt import ToolNode


from django.core.exceptions import ObjectDoesNotExist
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig


@tool
def Check_for_updates(config: RunnableConfig) -> List[Dict]:
    """Check the clinical data of a patient in the database for missing values.

    Args:
        config: Configuration dictionary containing the patient_id.

    Returns:
        A list of dictionaries containing the labels of the missing clinical data.
    """
    configuration = config.get("configurable", {})
    patient_id = configuration.get("patient_id", None)
    if not patient_id:
        raise ValueError("No patient ID configured.")
    try:
        patient_id = UUID(patient_id)  # Convert string to UUID object
    except ValueError:
        raise ValueError("Invalid patient ID format. Must be a valid UUID.")
    try:
        # Fetch the patient instance
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        raise ValueError(f"No patient found with ID {patient_id}.")
    try:
        # Fetch the Static_Clinical_data instance
        has_record_today = Clinical_Record.objects.filter(patient=patient, created_at__date=today).exists()
        if has_record_today:
            clinical_data = Clinical_Record.objects.get(patient=patient, created_at__date=today) 
        else:
            clinical_data = Clinical_Record.objects.create(
            patient=patient,
            weight          = None,
            height          = None,
            cholestrol_total    = None,
            fasting         = None,
            glucose_level   = None,
            systolic_bp     = None,
            diastolic_bp    = None,
            removed_teeth   = None,
        )
    except Clinical_Record.DoesNotExist:
        raise ValueError(f"Problem in check of: {patient_id}.")

    

    # List of fields to check for missing values
    fields_to_check = [
        'weight'          ,
        'height'          ,
        'cholestrol_total',
        'fasting'         ,
        'chest_pain'      ,  
        'glucose_level'   ,
        'systolic_bp'     ,
        'diastolic_bp'    ,
        'removed_teeth'   ,
    ]

    # Check for missing values
    missing_data = {}
    for field in fields_to_check:
        value = getattr(clinical_data, field)
        if value is None:
            missing_data[field] = None

    # Return a list of dictionaries with missing data
    return missing_data

@tool
def update_missing_clinical_data(*, config: RunnableConfig, clinical_data: str) -> str:
    """ Update the missing clinical data of a patient in the database using Django models.
      Please provide those values as follow : weight FLOAT, height FLOAT, fasting BOOLEAN, cholestrol_total FLOAT, glucose_level FLOAT, systolic_bp INTEGER, diastolic_bp INTEGER, removed_teeth INTEGER
    All values must be passed as JSON key-value pairs where values are Python for the booleans: True or False.
    Args:
        config: A configuration object containing the patient ID.
        clinical_data: A JSON string containing key-value pairs of clinical data columns and their values to update.

    Returns:
        A string indicating the status of the update:
        - "Update completed with all clinical details" if the update was successful.
        - "No patient ID configured." if no patient ID is provided.
        - "no update needed" if no values are passed for updating.
        - "Invalid JSON input" if the clinical_data JSON string is invalid.
        - "No clinical data found for the given patient ID." if the patient does not exist.
    """
    configuration = config.get("configurable", {})
    patient_id = configuration.get("patient_id", None)

    # Parse the JSON string into a dictionary
    try:
        clinical_data = json.loads(clinical_data)
    except json.JSONDecodeError as e:
        return f"Invalid JSON input: {str(e)}"

    if not patient_id:
        return "No patient ID configured."

    if not clinical_data:
        return "no update needed"

    # Filter out None values from clinical_data
    clinical_data = {k: v for k, v in clinical_data.items() if v is not None}

    if not clinical_data:
        return "no update needed"

    try:
        # Fetch the Clinical_data instance for the given patient_id
        clinical_record = Clinical_Record.objects.get(patient_id=patient_id, created_at__date=today)
    except ObjectDoesNotExist:
        return "No clinical data found for the given patient ID."

    # Update the fields dynamically
    for field, value in clinical_data.items():
        if hasattr(clinical_record, field):  # Ensure the field exists in the model
            setattr(clinical_record, field, value)

    # Save the updated record to the database
    clinical_record.save()

    return "Update completed with all clinical details"


@tool
def finish_collected(config: RunnableConfig) -> str:
    """
    Notify that all daily clinical data has been collected and the system should proceed to ECG recording.

    Args:
        config: Configuration dictionary containing the patient_id.

    Returns:
        str: Confirmation message.
    """
    return "All daily clinical data has been collected successfully. Ready to proceed."


def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    
    # Construct a detailed error message
    error_details = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "error_traceback": error.__traceback__ if hasattr(error, "__traceback__") else None
    }
    
    # Format the error details into a string
    error_message = f"Error: {error_details['error_type']}\n"
    error_message += f"Message: {error_details['error_message']}\n"
    if error_details['error_traceback']:
        error_message += f"Traceback: {error_details['error_traceback']}\n"
    error_message += "Please fix your mistakes."
    
    return {
        "messages": [
            ToolMessage(
                content=error_message,
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }

def create_tool_node_with_fallback(tools: list) -> dict:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )
