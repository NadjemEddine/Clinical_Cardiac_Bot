
from django.contrib import admin
from .models import CardiacCT, CardiacMRI, Conversation, EchoImaging, Message, ConversationRating, Clinical_Record, Static_Clinical_data, ECG_record, SPO_record, Tempurature

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['agent', 'patient', 'created_at', 'tokens_consumed']
    search_fields = ['patient__email']
    ordering = ['-created_at']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'source', 'sequence_number', 'created_at']
    search_fields = ['conversation__uid', 'content']
    ordering = ['conversation', 'sequence_number']

@admin.register(ConversationRating)
class ConversationRatingAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'rating', 'created_at']
    search_fields = ['conversation__uid', 'rating']
    ordering = ['-created_at']

@admin.register(Clinical_Record)
class Clinical_record_Admin(admin.ModelAdmin):
    list_display = ['patient__username','glucose_level', 'systolic_bp', 'diastolic_bp', 'created_at']
    ordering = ['-created_at']
    search_fields = ['patient__email']

admin.site.register(ECG_record)
admin.site.register(Static_Clinical_data)
admin.site.register(SPO_record)
admin.site.register(Tempurature)

@admin.register(EchoImaging)
class EchoImagingAdmin(admin.ModelAdmin):
    list_display = ('patient', 'view_type', 'upload_date', 'file_type')
    list_filter = ('view_type', 'file_type')
    search_fields = ('patient__full_name',)


@admin.register(CardiacMRI)
class CardiacMRIAdmin(admin.ModelAdmin):
    list_display = ('patient', 'sequence_type', 'upload_date', 'file_type')
    list_filter = ('sequence_type', 'file_type')
    search_fields = ('patient__full_name',)
    
@admin.register(CardiacCT)
class CardiacMRIAdmin(admin.ModelAdmin):
    list_display = ('patient', 'indication', 'upload_date', 'file_type')
    list_filter = ('indication', 'file_type')
    search_fields = ('patient__full_name',)