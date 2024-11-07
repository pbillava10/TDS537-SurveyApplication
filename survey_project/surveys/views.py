from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from .models import Survey, Profile, Question, Option, Response
from .forms import UserRegistrationForm, SurveyForm, QuestionForm

def home(request):
    # This view simply renders the home page with links to register or login.
    return render(request, 'surveys/home.html')

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Save user with username, email, and password
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.save()

            # Create the profile with role
            Profile.objects.create(user=user, role=form.cleaned_data['role'])

            # Log the user in
            login(request, user)

            return redirect('dashboard')  # Redirect to dashboard or desired page
        else:
            print(form.errors)  # Debug: Print form errors in the console
    else:
        form = UserRegistrationForm()

    return render(request, 'surveys/register.html', {'form': form})


def dashboard(request):
    # Get the user's role
    profile = Profile.objects.get(user=request.user)

    if profile.role == 'Creator':
        # Show surveys created by the Survey Creator
        surveys = Survey.objects.filter(created_by=request.user)
        context = {
            'role': 'Creator',
            'surveys': surveys
        }
    else:
        # Show published surveys for Survey Takers
        surveys = Survey.objects.filter(state='Published')
        context = {
            'role': 'Taker',
            'surveys': surveys
        }

    return render(request, 'surveys/dashboard.html', context)


def create_survey(request):
    if request.method == 'POST':
        form = SurveyForm(request.POST)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.created_by = request.user
            survey.save()
            return redirect('manage_surveys')
    else:
        form = SurveyForm()
    return render(request, 'surveys/create_survey.html', {'form': form})


def custom_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')  # Redirect to the dashboard after login
            else:
                form.add_error(None, 'Invalid username or password')  # Error message
    else:
        form = AuthenticationForm()

    return render(request, 'surveys/login.html', {'form': form})