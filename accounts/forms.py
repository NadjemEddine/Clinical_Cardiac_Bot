from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Patient

class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'})  # Render as a date input
    )
    gender = forms.ChoiceField(choices=[('True', 'Male'), ('False', 'Female')], required=True)
    phone_number = forms.CharField(max_length=15, required=True)
    address = forms.CharField(widget=forms.Textarea, required=True)

    class Meta:
        model = Patient  # Use the Patient model
        fields = ['username', 'email', 'password1', 'password2',
                  'first_name', 'last_name', 'date_of_birth', 'gender', 'phone_number', 'address']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password1')
        password2 = cleaned_data.get('confirm_password')

        if password and password2 and password != password2:
            raise forms.ValidationError("Passwords do not match.")

        # Ensure email is unique
        email = cleaned_data.get('email')
        if Patient.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use.")

        return cleaned_data