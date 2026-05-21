from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CardiacCTListView,
    CardiacCTUploadView,
    CardiacMRIListView,
    CardiacMRIUploadView,
    ConversationCreateView,
    ConversationListView,
    ConversationDetailView,
    ECGRecordViewSet,
    EchoImagingListView,
    EchoImagingUploadView,
    MessageListCreateView,
    FirstMeeting,
    patient_dashboard,
    chat_room,
    HVR_record_chat,
    ECG_report,
    recordsHistory,
    risk_scores_view,
    daily_agent_api,
    welcome_agent_api,
    hvr_agent_api,
    imaging_agent_api,
)


router = DefaultRouter()
router.register(r'ecg-records', ECGRecordViewSet, basename='ecg-record')

urlpatterns = [
    path('', include(router.urls)),
    path('api/conversations/', ConversationListView.as_view(), name='conversation_list'),
    path('api/conversations/create/', ConversationCreateView.as_view(), name='conversation_create'),
    path('api/conversations/<uuid:uid>/', ConversationDetailView.as_view(), name='conversation_detail'),
    # path('api/conversations/<uuid:conversation_uid>/messages/', MessageListCreateView.as_view(), name='conversation_messages'),
    # path('api/conversations/<uuid:conversation_uid>/messages/', process_user_message, name='process_user_message'),
    # path('api/conversations/<uuid:conversation_uid>/complete-collection/', complete_clinical_data_collection, name='complete_clinical_data_collection'),
    
    path('api/echo/upload/', EchoImagingUploadView.as_view(), name='echo-upload'),
    path('api/echo/list/', EchoImagingListView.as_view(), name='echo-list'),
    
    path('api/mri/upload/', CardiacMRIUploadView.as_view(), name='mri-upload'),
    path('api/mri/list/', CardiacMRIListView.as_view(), name='mri-list'),
    
    path('api/ct/upload/', CardiacCTUploadView.as_view(), name='ct-upload'),
    path('api/ct/list/', CardiacCTListView.as_view(), name='ct-list'),
    
    path('Welcome/', FirstMeeting , name='welcome_page'),
    path('Dashboard/', patient_dashboard , name='dashboard_page'),
    path('HVRChat/', HVR_record_chat , name='HVRchat'),
    path('ecg-reporting/<int:recordID>/', ECG_report , name = 'ecg_reporting'),
    path('scores/<int:recordID>/', risk_scores_view, name='medical_scores' ),

    path("api/agent/daily/", daily_agent_api, name='daily_agent_api'),
    path("api/agent/welcome/", welcome_agent_api, name='welcome_agent_api'),
    path("api/agent/hvr/", hvr_agent_api, name='hvr_agent_api'),
    path("api/agent/imaging/", imaging_agent_api, name='imaging_agent_api'),

    path("chat/", chat_room, name="chat_room"),
    path("chat/<str:room_name>/", chat_room, name="chat_room_with_name"),
    path("history/", recordsHistory, name="records_history"),

]
