from rest_framework import generics
from .models import Patient
from .serializers import PatientSerializer
from rest_framework.permissions import AllowAny

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view

from django.shortcuts import get_object_or_404, render , redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password

from django.contrib.auth.decorators import login_required
from django.views import View
from .forms import SignupForm


import requests


class PatientRegistrationView(generics.CreateAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [AllowAny]


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        # Log out the user by clearing the session
        logout(request)
        return Response({"message": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)




## Pages Views
# Main page view
def main_view(request):
    return render(request, 'accounts/main.html')

# Profile page view (requires login)
@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')

def custom_login_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(request, email=email, password=password)
        # Authenticate using the API (replace with your actual API endpoint)
        
            
        if user:
            login(request, user)
            print(f"User {user} logged in successfully.")
            print(f"Session data: {request.session.items()}")  # Check session
            return redirect('/accounts/profile/')
        else:
                messages.error(request, 'Invalid username or password')
    else:
        messages.error(request, 'Login failed. Please check your credentials.')

    return render(request, 'accounts/login.html')



#Rigsteration "Sign UP"


def patient_register_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            # Save the Patient instance (which extends AbstractUser)
            patient = form.save()

            # Log the user in
            login(request, patient)

            # Redirect to the welcome page
            return redirect('welcome_page')  # Replace 'welcome_page' with the actual name of your welcome page URL
    else:
        form = SignupForm()
    return render(request, 'accounts/register.html', {'form': form})


def DoctorAdmin(request):
    all_patient = Patient.objects.all()
    context = {"patients": all_patient}
    return render(request, "accounts/DoctorPage.html", context=context)

def patient_detail(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    static_data = getattr(patient, 'historical_data', None)
    daily_records = patient.dayly_data.all().order_by('-id')  # latest first
    print(patient)
    print("-------------------")
    print(static_data)
    return render(request, 'accounts/patient_detail.html', {
        'patient': patient,
        'static_data': static_data,
        'daily_records': daily_records,
    })

