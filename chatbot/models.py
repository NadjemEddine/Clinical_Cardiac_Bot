import json
import uuid
from django.utils import timezone

today = timezone.now()

from django.db import models
from accounts.models import Patient  # Import the Patient model

# Choices for message source
MESSAGE_SOURCE_CHOICES = [
    ('human', 'Human'),
    ('ai', 'AI'),
]

# Choices for conversation rating
RATING_CHOICES = [
    ('norate', 'Norate'),
    ('useless', 'Useless'),
    ('helpful', 'Helpful'),
    ('grateful', 'Grateful'),
]


class Conversation(models.Model):
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    tokens_consumed = models.PositiveIntegerField(default=0)  # Tracks LLM tokens consumed
    state = models.JSONField(default=dict , null=True , blank=True)  # To store conversation state if needed
    thread_id = models.CharField(max_length=255, null=True , blank=True )
    agent = models.CharField(max_length=255, null=True , blank=True )
    
    def __str__(self):
        return f"Conversation {self.uid} with {self.patient.email}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    source = models.CharField(max_length=5, choices=MESSAGE_SOURCE_CHOICES)
    content = models.TextField(max_length=2000)  # Limit the message content length
    created_at = models.DateTimeField(auto_now_add=True)
    sequence_number = models.PositiveIntegerField()  # Sequence order for the messages

    def __str__(self):
        return f"Message {self.sequence_number} in Conversation {self.conversation.uid}"


class ConversationRating(models.Model):
    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name='rating')
    rating = models.CharField(max_length=10, choices=RATING_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Assuming Conversation has a patient field
        patient_name = self.conversation.patient.name if hasattr(self.conversation, 'patient') else "Unknown Patient"
        date_str = self.created_at.strftime("%d_%m_%Y")
        return f"{patient_name} - {date_str} - Rating: {self.rating}"


class Static_Clinical_data(models.Model):
    patient                 = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='historical_data')
    diabetes                = models.BooleanField(null=True, blank=True)
    hypertension            = models.BooleanField(null=True, blank=True)
    smoke                   = models.BooleanField(null=True, blank=True)
    kidney_disease          = models.BooleanField(null=True, blank=True)
    hypertension_medicales  = models.BooleanField(null= True, blank=True)
    physical_activity       = models.BooleanField(null= True, blank=True)
    astheme                 = models.BooleanField(null= True, blank=True)
    pulmonary_disease       = models.BooleanField(null= True, blank=True)
    alcoholic               = models.BooleanField(null= True, blank=True)
    walking_problem         = models.BooleanField(null= True, blank=True)
    e_cigarette             = models.BooleanField(null= True, blank=True)
    covid_19                = models.BooleanField(null= True, blank=True)
    prevouis_stroke         = models.BooleanField(null= True, blank=True)
    
    created_at              = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.patient.username


class Clinical_Record(models.Model):
    patient             = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='dayly_data')
    weight              = models.FloatField(null=True, blank=True)
    height              = models.FloatField(null=True, blank=True)
    cholestrol_total    = models.FloatField(null=True, blank=True)
    fasting             = models.BooleanField(null= True, blank=True)
    chest_pain          = models.BooleanField(null= True, blank=True)
    glucose_level       = models.FloatField(null=True, blank=True)
    systolic_bp         = models.FloatField(null=True, blank=True)
    diastolic_bp        = models.FloatField(null=True, blank=True)
    removed_teeth       = models.SmallIntegerField(null=True, blank=True)
    
    created_at      = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.patient.username
    
class ECG_record(models.Model):
    record          = models.ForeignKey(Clinical_Record, on_delete=models.CASCADE, related_name='ECG_record')
    ECG             = models.TextField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.record.patient.username
    
    def save(self, *args, **kwargs):
        """Log ECG data before and after saving."""
        print(f"Before save - ECG: {self.ECG}")
        super().save(*args, **kwargs)
        print(f"After save - ECG: {self.ECG}")
class SPO_record(models.Model):
    record          = models.ForeignKey(Clinical_Record, on_delete=models.CASCADE, related_name='SPO_record')
    SPO             = models.IntegerField(null=True , blank= True)
    created_at      = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.record.patient.username
    
class Tempurature(models.Model):
    record          = models.ForeignKey(Clinical_Record, on_delete=models.CASCADE, related_name='tempurater_record')
    Temp             = models.IntegerField(null=True , blank= True)
    created_at      = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.record.patient.username


def patient_directory_path(instance, filename):
    # Format date as YYYY-MM-DD without time components
    date_formatted = instance.upload_date.strftime('%Y-%m-%d')
    
    # Files will be uploaded to MEDIA_ROOT/patient_<id>/<imaging_type>/<YYYY-MM-DD>/<filename>
    return f'patient_{instance.patient.id}/{instance.__class__.__name__.lower()}/{date_formatted}/{filename}'


# files based model
class BaseImaging(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    upload_date = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to=patient_directory_path)
    file_type = models.CharField(max_length=10, choices=[
        ('DICOM', 'DICOM (.dcm)'),
        ('PDF', 'Report (.pdf)'),
        ('MP4', 'Video (.mp4)'),
        ('PNG', 'Image (.png)'),
        ('JPG', 'Image (.jpg)'),
        ('OTHER', 'Other'),
    ])
    notes = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True
        
# Echo Image         
class EchoImaging(BaseImaging):
    view_type = models.CharField(max_length=50, choices=[
        ('PLAX', 'Parasternal Long Axis'),
        ('A4C', 'Apical 4 Chamber'),
        ('PSAX', 'Parasternal Short Axis'),
        ('SUBC', 'Subcostal'),
        ('OTHER', 'Other'),
    ])
    ejection_fraction = models.FloatField(null=True, blank=True)

# MRI
class CardiacMRI(BaseImaging):
    sequence_type = models.CharField(max_length=50, choices=[
        ('LGE', 'Late Gadolinium Enhancement'),
        ('CINE', 'Cine MRI'),
        ('T1', 'T1 Mapping'),
        ('T2', 'T2 Mapping'),
        ('OTHER', 'Other'),
    ])
    slice_thickness = models.FloatField(null=True, blank=True)


#CT cardiac
class CardiacCT(BaseImaging):
    indication = models.CharField(max_length=100, choices=[
        ('CALCIUM', 'Calcium Scoring'),
        ('CTA', 'Coronary CTA'),
        ('ANATOMY', 'Cardiac Anatomy'),
        ('OTHER', 'Other'),
    ])
    radiation_dose = models.FloatField(null=True, blank=True)

