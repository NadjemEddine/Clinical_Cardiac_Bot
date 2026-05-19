from typing import List, Dict
from django.core.exceptions import ObjectDoesNotExist
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from .models import (
    Static_Clinical_data,
    Patient,
)  # Ensure you import the Clinical_data model correctly
from typing import Dict, Any
import json
from uuid import UUID

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda

from langgraph.prebuilt import ToolNode


@tool
def Check_static_clinical_data(config: RunnableConfig) -> List[Dict]:
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
        clinical_data = Static_Clinical_data.objects.get(patient=patient)
    except Static_Clinical_data.DoesNotExist:
        # Create a new instance with all fields set to null (None)
        clinical_data = Static_Clinical_data.objects.create(
            patient=patient,
            diabetes=None,
            hypertension=None,
            smoke=None,
            kidney_disease=None,
            hypertension_medicales=None,
            physical_activity=None,
            astheme=None,
            pulmonary_disease=None,
            alcoholic=None,
            walking_problem=None,
            e_cigarette=None,
            covid_19=None,
            prevouis_stroke=None,
        )

        return clinical_data

    # Full list of fields to check for missing values
    fields_to_check = [
        "diabetes",
        "hypertension",
        "smoke",
        "kidney_disease",
        "hypertension_medicales",
        "physical_activity",
        "astheme",
        "pulmonary_disease",
        "alcoholic",
        "walking_problem",
        "e_cigarette",
        "covid_19",
        "prevouis_stroke",
    ]

    # Check for missing values
    missing_data = {}
    for field in fields_to_check:
        value = getattr(clinical_data, field)
        if value is None:
            missing_data[field] = None

    # Return a dictionary of missing data
    return missing_data


@tool
def Update_static_clinical_data(*, config: RunnableConfig, clinical_data: str) -> str:
    """
    Update the missing static clinical data of a patient in the database using Django models.

    This tool updates the following fields: 
    diabetes, hypertension, smoke, kidney_disease, hypertension_medicales, physical_activity,
    astheme, pulmonary_disease, alcoholic, walking_problem, e_cigarette, covid_19, prevouis_stroke.

    All values must be passed as JSON key-value pairs where values are Python booleans: True or False.
    (For example: {"diabetes": true, "alcoholic": false})

    Args:
        config: A configuration object that must include the patient ID.
        clinical_data: A JSON string containing key-value pairs of clinical fields and their boolean values to update.

    Returns:
        - "Update completed with all clinical details" if the update was successful.
        - "No patient ID configured." if the patient ID is missing from the config.
        - "No update needed" if no valid update values are provided.
        - "Invalid JSON input" if the clinical_data string is malformed or cannot be parsed.
        - "No clinical data found for the given patient ID." if no matching record exists.
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
        clinical_record = Static_Clinical_data.objects.get(patient_id=patient_id)
    except ObjectDoesNotExist:
        return "No clinical data found for the given patient ID."

    # Update the fields dynamically
    for field, value in clinical_data.items():
        if hasattr(clinical_record, field):  # Ensure the field exists in the model
            setattr(clinical_record, field, value)

    # Save the updated record to the database
    clinical_record.save()

    return "Update completed with all clinical details"
