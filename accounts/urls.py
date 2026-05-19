from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import DoctorAdmin, LogoutView, PatientRegistrationView, main_view, profile_view, custom_login_view, patient_register_view, login ,patient_detail

# API routes
urlpatterns = [
    path('api/register/', PatientRegistrationView.as_view(), name='api_register'),
    path('api/logout/', LogoutView.as_view(), name='logout'),



    
    path('profile/', profile_view, name='profile'),
    path('login/', custom_login_view, name='login'),
    path('register/', patient_register_view, name='patient_register'),
    path('doctor/', DoctorAdmin , name='DoctorAdmin'),
    path('doctor/patient/<uuid:patient_id>/', patient_detail, name='patient_detail'),

]

