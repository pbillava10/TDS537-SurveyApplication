from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Survey, Question, Option

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=[('Creator', 'Survey Creator'), ('Taker', 'Survey Taker')])

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'role']

class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ['name', 'description', 'state']

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'question_type']

