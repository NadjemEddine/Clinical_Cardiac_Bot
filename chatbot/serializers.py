from rest_framework import serializers
from .models import CardiacCT, CardiacMRI, Conversation, EchoImaging, Message 
from rest_framework import serializers
from .models import ECG_record, Clinical_Record


class ConversationSerializer(serializers.ModelSerializer):
    tokens_consumed = serializers.IntegerField(required=False)



    class Meta:
        model = Conversation
        fields = ['uid', 'patient', 'created_at', 'tokens_consumed',]

   
    

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'source', 'content', 'created_at', 'sequence_number']
        read_only_fields = ['id', 'conversation', 'created_at', 'sequence_number']






class ECGRecordSerializer(serializers.ModelSerializer):
    record_id = serializers.PrimaryKeyRelatedField(
        queryset=Clinical_Record.objects.all(), source='record', write_only=True
    )

    class Meta:
        model = ECG_record
        fields = ['id', 'record_id', 'ECG', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_record_id(self, value):
        """Ensure the Clinical_Record exists."""
        if not Clinical_Record.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("Clinical record with this ID does not exist.")
        return value


class EchoImagingSerializer(serializers.ModelSerializer):
    class Meta:
        model = EchoImaging
        fields = ['id', 'patient', 'view_type', 'ejection_fraction' , 'file', 'upload_date']


class CardiacMRISerializer(serializers.ModelSerializer):
    class Meta:
        model = CardiacMRI
        fields = ['id', 'patient', 'slice_thickness', 'sequence_type', 'file', 'upload_date']

class CardiacCTSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardiacCT
        fields = ['id', 'patient', 'indication', 'radiation_dose' , 'file', 'upload_date']

