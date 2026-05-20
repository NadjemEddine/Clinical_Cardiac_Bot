from datetime import date
import traceback
import math
import os
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view, permission_classes
from rest_framework import viewsets, status 
from django.utils import timezone

from .Medical_Scores import ascvd_risk, cha2ds2_vasc_score, chads2_score, framingham_risk_score, has_bled_score, qrisk3_score
from .Medical_Scores import estimate_hdl

from .models import CardiacCT, CardiacMRI, Conversation, EchoImaging, Message, Patient , Clinical_Record
from django.conf import settings

from chatbot.models import Static_Clinical_data , Clinical_Record , ECG_record , SPO_record , Tempurature
from .serializers import CardiacCTSerializer, CardiacMRISerializer, ConversationSerializer, ECGRecordSerializer, EchoImagingSerializer, MessageSerializer
from .FuzzyFraminghamRisk import FuzzyFraminghamRisk
from .FuzzyASCVD import FuzzyASCVDRisk
from .FuzzyQriskScore import FuzzyQRISK3Risk
from .FuzzyCHADs2Score import FuzzyCHADS2Risk
from .FuzzyCHA2DS2Score import FuzzyCHA2DS2VAScRisk
from .FuzzyHASBLEDScore import FuzzyHASBLEDRisk

# from .agent import create_agent, llm


from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist

import neurokit2 as nk
import json
import numpy as np
from scipy import signal
import tensorflow as tf
from sklearn.preprocessing import StandardScaler
from scipy.signal import resample

import matplotlib.pyplot as plt
from langgraph.graph import StateGraph

import uuid

# Create a new conversation
class ConversationCreateView(generics.CreateAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Automatically associate the conversation with the authenticated patient
        serializer.save(patient=self.request.user)

# Retrieve all conversations for the logged-in user
class ConversationListView(generics.ListAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(patient=self.request.user)

# Retrieve a specific conversation and its messages
class ConversationDetailView(generics.RetrieveAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    queryset = Conversation.objects.all()
    lookup_field = 'uid'

# Add a message to a conversation
class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Retrieve the conversation based on the UID
        conversation_uid = self.kwargs['conversation_uid']
        conversation = get_object_or_404(Conversation, uid=conversation_uid)

        # Ensure the authenticated user is the patient in the conversation
        if self.request.user != conversation.patient:
            raise PermissionDenied("You do not have permission to view these messages.")

        return conversation.messages.all().order_by('sequence_number')

    def perform_create(self, serializer):
        conversation_uid = self.kwargs['conversation_uid']
        conversation = get_object_or_404(Conversation, uid=conversation_uid)

        # Ensure the authenticated user is the patient in the conversation
        if self.request.user != conversation.patient:
            raise PermissionDenied("You do not have permission to send messages in this conversation.")

        # Automatically set the conversation and sequence number
        latest_message = conversation.messages.order_by('-sequence_number').first()
        next_sequence_number = latest_message.sequence_number + 1 if latest_message else 1

        serializer.save(conversation=conversation, sequence_number=next_sequence_number)

# ECG REcord API view
class ECGRecordViewSet(viewsets.ModelViewSet):
    queryset = ECG_record.objects.all()
    serializer_class = ECGRecordSerializer
    http_method_names = ['get', 'post', 'patch']  # Restrict to GET, POST, PATCH

    def create(self, request, *args, **kwargs):
        print("-------------------ECG CREATE VIEW -------------------")
        print(request.data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        print("Response data: ")
        print(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)  # Support PATCH
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()


class EchoImagingUploadView(generics.CreateAPIView):
    queryset = EchoImaging.objects.all()
    serializer_class = EchoImagingSerializer

class EchoImagingListView(generics.ListAPIView):
    serializer_class = EchoImagingSerializer

    def get_queryset(self):
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            return EchoImaging.objects.filter(patient__id=patient_id)
        return EchoImaging.objects.all()

class CardiacMRIUploadView(generics.CreateAPIView):
    queryset = CardiacMRI.objects.all()
    serializer_class = CardiacMRISerializer

class CardiacMRIListView(generics.ListAPIView):
    serializer_class = CardiacMRISerializer

    def get_queryset(self):
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            return CardiacMRI.objects.filter(patient__id=patient_id)
        return CardiacMRI.objects.all()

class CardiacCTUploadView(generics.CreateAPIView):
    queryset = CardiacCT.objects.all()
    serializer_class = CardiacCTSerializer

class CardiacCTListView(generics.ListAPIView):
    serializer_class = CardiacCTSerializer

    def get_queryset(self):
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            return CardiacCT.objects.filter(patient__id=patient_id)
        return CardiacCT.objects.all()


# import uuid
@login_required
def FirstMeeting(request):
    # Get the logged-in patient
    patient = request.user

    try:
        # Get the Static_Clinical_data for the patient
        clinical_data = Static_Clinical_data.objects.get(patient=patient)

        # Check if any required fields are empty
        if (clinical_data.diabetes is None or 
            clinical_data.hypertension is None or 
            clinical_data.prevouis_stroke is None or 
            clinical_data.kidney_disease is None):
            # Redirect to the Welcome page to complete the clinical data
            return render(request, 'chatbot/Welcome.html')
        else:
            # Redirect to the Dashboard view
            return redirect('dashboard')  # Replace 'dashboard' with the actual name of your dashboard URL

    except Static_Clinical_data.DoesNotExist:
        # If Static_Clinical_data does not exist for the patient, redirect to the Welcome page
        return render(request, 'chatbot/Welcome.html')

def chat_room(request, room_name=None):
    if not room_name:
        room_name = str(uuid.uuid4())
    return render(request, "chatbot/daily_chat.html", {"room_name": room_name})

@login_required
def patient_dashboard(request):
    patient = request.user
    today = timezone.now().date()
    has_record_today = Clinical_Record.objects.filter(
            patient=patient, created_at__date=today
        ).exists()
    
    try:
        static_data = Static_Clinical_data.objects.get(patient=patient)
        clinical_records = Clinical_Record.objects.filter(patient=patient)
        ecg_records = ECG_record.objects.filter(record__in=clinical_records)
        spo_records = SPO_record.objects.filter(record__in=clinical_records)
        temp_records = Tempurature.objects.filter(record__in=clinical_records)
        static_data = {
        'diabetes': static_data.diabetes,
        'hypertension': static_data.hypertension,
        'smoke': static_data.smoke,
        'kidney_disease': static_data.kidney_disease,
        'hypertension_medicales': static_data.hypertension_medicales,
        'physical_activity': static_data.physical_activity,
        'astheme': static_data.astheme,
        'pulmonary_disease': static_data.pulmonary_disease,
        'alcoholic': static_data.alcoholic,
        'walking_problem': static_data.walking_problem,
        'e_cigarette': static_data.e_cigarette,
        'covid_19': static_data.covid_19,
        'prevouis_stroke': static_data.prevouis_stroke,
    }
       
        context = {
            'patient': patient,
            'static_data': static_data,
            'clinical_records': clinical_records,
            'ecg_records': ecg_records,
            'spo_records': spo_records,
            'temp_records': temp_records,
            'record':has_record_today,
        }

        return render(request, 'chatbot/Dashboard.html', context)
    except ObjectDoesNotExist:
        return render(request, 'chatbot/Welcome.html')


def recordsHistory(request):
    patient = request.user
    today = timezone.now().date()
    has_record_today = Clinical_Record.objects.filter(
            patient=patient, created_at__date=today
        ).exists()
    
    try:
        clinical_records = Clinical_Record.objects.filter(patient=patient)  
        context = {
            'patient': patient,
            'clinical_records': clinical_records,
            'record':has_record_today,
        }

        return render(request, 'chatbot/records_history.html', context)
    except ObjectDoesNotExist:
        return render(request, 'chatbot/Welcome.html')


#HVR Chat based on Bluetooth

@login_required
def HVR_record_chat(request):
    today = timezone.now().date()
    patient = request.user
    has_record_today = Clinical_Record.objects.filter(patient=patient, created_at__date=today).exists()
    print("**********************************************************")
    print(has_record_today)
    print("**********************************************************")
    if has_record_today:
        clinical_data = Clinical_Record.objects.get(patient=patient, created_at__date=today)
        has_ecg_today = ECG_record.objects.filter(record = clinical_data, created_at__date=today).exists()
        if has_ecg_today:
            return redirect("patient_dashboard")
    # Check actual fields from your model
        fields_to_check = [
            'chest_pain', 'cholestrol_total', 'diastolic_bp', 
            'fasting', 'glucose_level', 'height', 'systolic_bp', 
            'weight', 'removed_teeth'
        ]
        
        null_fields = []
        for field_name in fields_to_check:
            if getattr(clinical_data, field_name) is None:
                null_fields.append(field_name)
        
        if null_fields:
            print(f"Null fields: {null_fields}")
        else:
            print("All checked fields have values")

        context = {'recordID':clinical_data.id, 'NullFields': len(null_fields) == 0,}
        return render(request, 'chatbot/HVR_chat.html', context)
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
        context = {'recordID':clinical_data.id,}
        return render(request, 'chatbot/HVR_chat.html', context)
    
def clean_peaks(peaks):
                return [p if isinstance(p, (int, float)) and not math.isnan(p) else None for p in peaks]


def generate_ecg_figure(raw_ecg, sampling_rate, patient_id, record_date):
    """
    Generate ECG figure using NeuroKit2 and save it under:
    MEDIA_ROOT/patientID/dd_mm_yyyy/ecg_overview.png
    """
    # Format date as dd_mm_yyyy
    date_str = record_date.strftime("%d_%m_%Y")

    # Build folder path MEDIA_ROOT/patientID/dd_mm_yyyy
    folder_path = os.path.join(settings.MEDIA_ROOT, str(patient_id), date_str)
    os.makedirs(folder_path, exist_ok=True)

    # File path
    file_name = "ecg_overview.png"
    file_path = os.path.join(folder_path, file_name)

    # If already exists, return directly
    if os.path.exists(file_path):
        return file_path

    # NeuroKit processing
    signals, info = nk.ecg_process(raw_ecg, sampling_rate=sampling_rate)

    # Grab the current figure
    fig = plt.gcf()
    fig.set_size_inches(14, 10)   # Resize
    fig.tight_layout()

    # Save the figure
    fig.savefig(file_path, dpi=300)
    plt.close(fig)

    return file_path

  
@login_required
def ECG_report(request, recordID=None):
    """View to process ECG data and generate a report.
    This view retrieves the ECG data for the logged-in patient, processes it using Neurokit2,
    """
    
    today = timezone.now().date()
    patient = request.user
    has_record_today = Clinical_Record.objects.filter(patient=patient, id=recordID).exists()
    context = {}
    if has_record_today:
        clinical_data = Clinical_Record.objects.get(patient=patient, id=recordID)
        has_ecg_today = ECG_record.objects.filter(record=clinical_data).exists()
        if has_ecg_today:
            ecg_record = ECG_record.objects.get(record=clinical_data)
            # Process ECG with Neurokit2
            ecg_pre_record = "[" + ecg_record.ECG+ "]"  # Ensure the ECG data is a valid JSON array
            ecg_signal = json.loads(ecg_pre_record)  # Convert JSON string to list
            print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
            print(ecg_signal)
            print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
            sampling_rate = len(ecg_signal) / 60  # Adjust if you know the actual rate (e.g., 1000 Hz)

            # # Step 1: Filter Design
            # # High-pass filter to remove baseline wander (<0.5 Hz)
            # highpass_cutoff = 0.5  # Hz
            # b_high, a_high = signal.butter(4, highpass_cutoff / (sampling_rate / 2), btype='highpass')
            # ecg_highpass = signal.filtfilt(b_high, a_high, ecg_signal)

            # # Low-pass filter to remove high-frequency noise (>40 Hz)
            # lowpass_cutoff = 40  # Hz
            # b_low, a_low = signal.butter(4, lowpass_cutoff / (sampling_rate / 2), btype='lowpass')
            ecg_filtered = ecg_signal

            # Optional: Notch filter for 50 Hz powerline interference
            notch_freq = 50  # Hz
            quality_factor = 30
            
            sampling_rate = len(ecg_filtered) / 60  # Adjust if you know the actual rate (e.g., 1000 Hz)
            ecg_signals, info = nk.ecg_process(ecg_filtered, sampling_rate=sampling_rate)
            
            cleaned_signal = ecg_signals["ECG_Clean"]
            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
            print(type(info["ECG_Q_Peaks"]))
            signal_length = len(ecg_filtered)
            #arrhyhtmia classification.
            # Calculate the original frequency
            duration = 60  # seconds
            
            original_freq = signal_length / duration  # e.g., 18,000 / 60 = 300 Hz
            print(f"Original Frequency: {original_freq:.2f} Hz")

            # Target frequency for the model
            target_freq = 250  # Hz
            target_samples = int(target_freq * duration)  # 250 * 60 = 15,000 samples
            signal_length = int(original_freq * duration)
            # Resample the signal to 250 Hz
            ecg_resampled = resample(ecg_filtered, target_samples)  # Shape: (15,000,)

            # Step 2: Segment the Resampled Signal
            # Segment the 60-second signal into 10-second windows (6 segments)
            segment_length = int(target_freq * (duration/6))
            n_segments = int(len(ecg_resampled) / segment_length)  # 6 segments
            # Reshape into segments
            segments = ecg_resampled.reshape(n_segments, segment_length)  # Shape: (6, 2500)
            print(f"segement len: {len(segments[0]):.2f} Hz")
            # Step 3: Standardize the Segments
            scaler = StandardScaler()
            segments_scaled = scaler.fit_transform(segments)  # Shape: (6, 2500)

            # Reshape for the model (GRU expects shape: (n_samples, timesteps, features))
            X_input = segments_scaled.reshape(n_segments, segment_length, 1)  # Shape: (6, 2500, 1)
            # Print the shapes of the resulting datasets
            print(f"X_shape: {X_input.shape}")
            # Step 4: Load the Pre-trained Model
            model = tf.keras.models.load_model('DSC-GRU.h5')

            # Step 5: Make Predictions
            predictions = model.predict(X_input)  # Shape: (6, n_classes)

            # Step 6: Decode Predictions
            # Convert one-hot predictions to class indices
            predicted_classes = np.argmax(predictions, axis=1)  # Shape: (6,)

            # Map back to arrhythmia labels (replace with your actual encoder dictionary)
            encoder_dict = {0: 'AF1', 1: 'AF2', 2: 'AF3', 3: 'AF4', 4:'AFib', 5:'AT', 6:'SNR'}  # Example; use your actual dictionary
            predicted_labels = [encoder_dict[cls] for cls in predicted_classes]

            # Step 7: Display Results
            print("Predictions for each 10-second segment:")
            for i, label in enumerate(predicted_labels):
                print(f"Segment {i + 1} (seconds {i * 10}-{(i + 1) * 10}): {label}")
            
            # Step 5: Prepare Data for the Template
            # Full ECG signal for plotting
            full_signal = ecg_resampled.tolist()  # Convert to list for JSON serialization

            # Segment metadata (start/end indices and labels)
            segment_metadata = []
            for i in range(n_segments):
                start_idx = i * segment_length
                end_idx = (i + 1) * segment_length
                segment_metadata.append({
                    'start_idx': start_idx,
                    'end_idx': end_idx,
                    'label': predicted_labels[i],
                    'time_range': f"Seconds {i * 10}-{(i + 1) * 10}"
                })
            #generate the ECG report url image
              # as you said: record length = SR
            record_date = ecg_record.created_at

            file_path = generate_ecg_figure(ecg_filtered, sampling_rate, patient.id, record_date)
            # Prepare data for the frontend
            relative_url = file_path.replace(settings.MEDIA_ROOT, settings.MEDIA_URL)
            
            context = {
                'ecg_record': cleaned_signal,
                'ecg_data': json.dumps(ecg_signals["ECG_Clean"].tolist()),  # Raw ECG signal
                'sampling_rate': sampling_rate,
                'r_peaks': json.dumps(clean_peaks(info["ECG_R_Peaks"].tolist())),  # R-peak indices
                'p_peaks': json.dumps(clean_peaks(info["ECG_P_Peaks"])),  # P-peak indices
                't_peaks': json.dumps(clean_peaks(info["ECG_T_Peaks"])),  # T-peak indices
                'q_peaks': json.dumps(clean_peaks(info["ECG_Q_Peaks"])),  # Q-peak indices
                's_peaks': json.dumps(clean_peaks(info["ECG_S_Peaks"])),  # S-peak indices
                'heart_rate': json.dumps(ecg_signals["ECG_Rate"].tolist()),  # Heart rate over time
                'full_signal': full_signal,
                'segment_metadata': segment_metadata,
                'ecg_url': relative_url
            }
            return render(request, "chatbot/ECG_reporting.html", context)
        else:
            context = {'recordID': clinical_data.id}
            return render(request, 'chatbot/HVR_chat.html', context)
    else:
        return render(request, 'chatbot/Dashboard.html', context)


def risk_scores_view(request, recordID):
    user = request.user
    today = timezone.now().date()
    
    clinical = get_object_or_404(Static_Clinical_data, patient=user)
    try: 
        record = Clinical_Record.objects.get( patient=user, id= recordID)
    except:
        return render(request, 'chatbot/error.html', {'message': 'No clinical record found for the user.'})
    # Age calculation
    today = date.today()
    dob = user.date_of_birth
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    sex = 'female' if user.gender is False else 'male'
    race =  'white'  # Default race if missing

    # Extract shared values
    total_chol = record.cholestrol_total or 200
    systolic_bp = record.systolic_bp or 120
    diastolic_bp = record.diastolic_bp or 80
    on_bp_meds = clinical.hypertension_medicales or False
    weight = record.weight or 75
    height = record.height or 170
    kidney_disease = clinical.kidney_disease or False
    prevouis_stroke = clinical.prevouis_stroke or False
    e_cigarette = clinical.e_cigarette or False
    hypertension = clinical.hypertension or False
    alcoholic = clinical.alcoholic or False
    ## Framingham Score
    framingham = FuzzyFraminghamRisk()
    framingham_results = framingham.calculate_risk(
            age=age,
            sex=sex,
            total_chol=total_chol,
            systolic_bp=systolic_bp,
            smoker=clinical.smoke,
            diabetes=clinical.diabetes,
            on_bp_meds=on_bp_meds,
            hdl=estimate_hdl(chol_total=total_chol, sex = sex))
    
    ## ASCVD score
    ascvd = FuzzyASCVDRisk()

    ascvd_results = ascvd.calculate_risk(
            age=age,
            sex=sex,
            total_chol=total_chol,
            systolic_bp=systolic_bp,
            smoker=clinical.smoke,
            diabetes=clinical.diabetes,
            on_bp_meds=on_bp_meds,
            race_black=False
        )
    
    ## QRISK3 score
    qrisk = FuzzyQRISK3Risk()
    qrisk_results = qrisk.calculate_risk(
        age=age,
        sex=sex,
        total_chol=total_chol,
        smoker=clinical.smoke,
        diabetes=clinical.diabetes,
        on_bp_meds=on_bp_meds,
        weight=weight, height=height,             # -> BMI estimated
        kidney_disease=kidney_disease, previous_stroke=prevouis_stroke,
        e_cigarette=e_cigarette,                 # -> smoking category estimated
        recent_sbps = systolic_bp,        # -> SBP SD estimated; optional
    )
    ## CHADs2Score
    chads2_score = FuzzyCHADS2Risk()
    chads2result = chads2_score.calculate_risk(
        age=age,
        sex=sex,
        hypertension=hypertension,
        diabetes=clinical.diabetes,
        heart_failure=False,
        prior_stroke_tia=prevouis_stroke
)

## cha2ds2_vasc_score
    cha2ds2_vasc_score = FuzzyCHA2DS2VAScRisk()
    chad2ds2_results = cha2ds2_vasc_score.calculate_risk(
        age=age,
        sex=sex,
        hypertension=hypertension,
        diabetes=clinical.diabetes,
        heart_failure=False,
        stroke_tia_te=prevouis_stroke,
        vascular_disease=False
)
    
## HasBled score
    hasbled = FuzzyHASBLEDRisk()
    hasbledresult = hasbled.calculate_risk(
        age=age,
        sex=sex,
        systolic_bp = systolic_bp,
        hypertension=hypertension,           # not used directly for a point; SBP≥160 is
        kidney_disease=kidney_disease,
        liver_disease=False,                              # set if you track it
        prior_stroke=prevouis_stroke,
        prior_bleeding=False,                             # set if you track it
        labile_inr=False, inr_ttr=None,                   # if on warfarin, pass TTR<60% or labile flag
        on_antiplatelet_or_nsaid=False,                   # set True if known
        alcohol_excess=alcoholic
)


    context = {
        'ascvd_score': ascvd_results,
        'qrisk3_score': qrisk_results,
        'chads2_score': chads2result,
        'cha2ds2_vasc_score': chad2ds2_results,
        'has_bled_score': hasbledresult,
        'framingham_score': framingham_results ,
    }

    return render(request, 'chatbot/medical_scores.html', context)