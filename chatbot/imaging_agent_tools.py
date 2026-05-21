from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig


@tool
def request_EchoImaging(config: RunnableConfig) -> str:
    """
    Request the patient to upload their echocardiogram (heart ultrasound) imaging.
    The patient will be shown an upload dialog to submit their files.

    Args:
        config: Configuration dictionary containing the patient_id.

    Returns:
        str: Status of the request.
    """
    return "I've asked the patient to upload their echocardiogram. The upload dialog has been shown."


@tool
def request_CardiacMRI(config: RunnableConfig) -> str:
    """
    Request the patient to upload their Cardiac MRI imaging.
    The patient will be shown an upload dialog to submit their files.

    Args:
        config: Configuration dictionary containing the patient_id.

    Returns:
        str: Status of the request.
    """
    return "I've asked the patient to upload their Cardiac MRI. The upload dialog has been shown."


@tool
def request_CardiacCT(config: RunnableConfig) -> str:
    """
    Request the patient to upload their Cardiac CT scan imaging.
    The patient will be shown an upload dialog to submit their files.

    Args:
        config: Configuration dictionary containing the patient_id.

    Returns:
        str: Status of the request.
    """
    return "I've asked the patient to upload their Cardiac CT. The upload dialog has been shown."
