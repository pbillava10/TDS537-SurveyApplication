from logging import Logger

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.db.models import Q
from django.forms import modelform_factory
from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from .models import Survey, Profile, Question, Option, OptionEdit, Response, SurveyTakerStatus
from .forms import UserRegistrationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def home(request):
    return render(request, 'surveys/home.html')

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Saving user with username, email, and password
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.save()

            # Create the profile with role
            profile = Profile.objects.create(user=user, role=form.cleaned_data['role'])

            # Log the user in
            login(request, user)

            # Add the user to the SurveyTakerStatus table for all Published surveys if they are a Taker
            if profile.role == 'Taker':  
                surveys = Survey.objects.filter(state='Published')  # Only Published surveys
                for survey in surveys:
                    SurveyTakerStatus.objects.get_or_create(
                        survey=survey,
                        user=user,
                        defaults={'survey_status': 'Pending'}
                    )

            return redirect('dashboard')  # Redirect to the dashboard after registration
    else:
        form = UserRegistrationForm()

    return render(request, 'surveys/register.html', {'form': form})

def create_survey(request):
    """
    Allows survey creators to create a new survey with questions and options.
    """
    SurveyForm = modelform_factory(Survey, fields=('name', 'description'))

    if request.method == 'POST':
        form = SurveyForm(request.POST)
        if form.is_valid():
            try:
                # Create the survey
                survey = form.save(commit=False)
                survey.created_by = request.user
                survey.save()

                # Extract questions from POST data
                questions_data = {}
                for key, value in request.POST.items():
                    if key.startswith('questions['):
                        question_index = key.split('[')[1].split(']')[0]
                        if question_index not in questions_data:
                            questions_data[question_index] = {}
                        field_name = key.split('][')[-1].replace(']', '')
                        questions_data[question_index][field_name] = value

                # Loop through each question and create it in the database
                for question_index, question_fields in questions_data.items():
                    question_text = question_fields.get('text', '').strip()
                    question_type = question_fields.get('type', '').strip()

                    # Skip invalid questions
                    if not question_text or not question_type:
                        continue

                    # Create the question
                    question = Question.objects.create(
                        survey=survey,
                        text=question_text,
                        question_type=question_type
                    )

                    # Process options if applicable
                    if question_type in ['radio', 'checkbox']:
                        options = request.POST.getlist(f"questions[{question_index}][options][]")
                        for option_text in options:
                            if option_text.strip():
                                Option.objects.create(question=question, text=option_text.strip())

                messages.success(request, "Survey created successfully!")
                return redirect('dashboard')

            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
        else:
            messages.error(request, "Form submission failed. Please correct the errors.")
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
                return redirect('dashboard')
            else:
                form.add_error(None, 'Invalid username or password')
    else:
        form = AuthenticationForm()

    return render(request, 'surveys/login.html', {'form': form})

def delete_question(request, survey_id, question_id):
    survey = get_object_or_404(Survey, id=survey_id)
    question = get_object_or_404(Question, id=question_id, survey=survey)

    question.delete()

    messages.success(request, "Question deleted successfully.")
    return redirect('edit_survey', survey_id=survey.id)

@login_required
def close_survey(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id, created_by=request.user)
    if survey.state == 'Published':
        survey.state = 'Closed'
        survey.save()
        return redirect('dashboard')
    else:
        return HttpResponseForbidden("Survey cannot be closed.")

@login_required
def survey_detail(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    questions = survey.questions.prefetch_related('options')

    context = {
        'survey': survey,
        'questions': questions,
    }

    return render(request, 'surveys/survey_detail.html', context)

@login_required
def edit_survey(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)

    if request.method == "POST":
        try:
            # Update survey details
            survey.name = request.POST.get('survey_name', survey.name)
            survey.description = request.POST.get('survey_description', survey.description)
            survey.save()

            # Handle existing questions
            for question in survey.questions.prefetch_related('options'):
                question_text = request.POST.get(f'question_text_{question.id}')
                question_type = request.POST.get(f'question_type_{question.id}')

                if question_text and question_type:
                    # Update question details
                    question.text = question_text
                    question.question_type = question_type
                    question.save()

                    # Process options for radio/checkbox questions
                    if question_type in ['radio', 'checkbox']:
                        submitted_option_ids = request.POST.getlist(f'option_id_{question.id}')
                        print(f'submitted_option_ids: {submitted_option_ids}')
                        submitted_option_texts = request.POST.getlist(f'option_text_{question.id}')
                        print(f'submitted_option_texts: {submitted_option_texts}')

                        existing_options = {
                            str(option.id): option for option in question.options.all()
                        }

                        # Update or delete existing options
                        for option_id, option_text in zip(submitted_option_ids, submitted_option_texts):
                            if option_id in existing_options:
                                option = existing_options[option_id]
                                if option.text != option_text:
                                    OptionEdit.objects.create(
                                        option=option,
                                        old_text=option.text,
                                        edited_by=request.user
                                    )
                                    option.text = option_text
                                    option.save()
                                existing_options.pop(option_id)

                        # Delete options not submitted
                        for option in existing_options.values():
                            option.delete()

                        # Add new options
                        new_option_count = int(request.POST.get(f'new_option_count_{question.id}', 0))
                        print(f'new_option_count for question {question.id}: {new_option_count}')
                        for i in range(1, new_option_count + 1):
                            new_option_text = request.POST.get(f'new_option_text_{question.id}_{i}')
                            print(f'Adding new option: {new_option_text} for question {question.id}')
                            if new_option_text:
                                Option.objects.create(question=question, text=new_option_text)

            # Handle newly added questions
            new_question_counter = int(request.POST.get('new_question_counter', 0))
            for i in range(1, new_question_counter + 1):
                new_question_text = request.POST.get(f'new_question_text_{i}')
                new_question_type = request.POST.get(f'new_question_type_{i}')

                if new_question_text and new_question_type:
                    new_question = Question.objects.create(
                        survey=survey,
                        text=new_question_text,
                        question_type=new_question_type
                    )

                    if new_question_type in ['radio', 'checkbox']:
                        new_option_count = int(request.POST.get(f'new_option_count_{i}', 0))
                        for j in range(1, new_option_count + 1):
                            new_option_text = request.POST.get(f'new_option_text_{i}_{j}')
                            if new_option_text:
                                Option.objects.create(question=new_question, text=new_option_text)

            messages.success(request, "Survey updated successfully.")
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")

        return redirect('survey_detail', survey_id=survey.id)

    # Prepare data for rendering
    questions = survey.questions.prefetch_related('options')
    return render(request, 'surveys/edit_survey.html', {
        'survey': survey,
        'questions': questions,
        'new_question_counter': 0,
    })

@login_required
def take_survey(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    is_retake = request.GET.get("retake") == "true"

    if is_retake:
        # Clear previous responses for a retake
        Response.objects.filter(survey=survey, user=request.user).delete()
        SurveyTakerStatus.objects.filter(survey=survey, user=request.user).update(
            survey_status="In Progress", results_available=False
        )

    questions = survey.questions.prefetch_related('options')
    user_responses = Response.objects.filter(survey=survey, user=request.user) if not is_retake else []

    preprocessed_responses = {}
    for response in user_responses:
        question = response.question
        if question.question_type == "text":
            preprocessed_responses[question.id] = response.text_answer
        elif question.question_type in ["radio", "checkbox"]:
            preprocessed_responses[question.id] = set(response.selected_options.values_list("id", flat=True))

    if request.method == "POST":
        try:
            # Handle survey response saving logic
            for question in questions:
                # Handle radio questions
                if question.question_type == "radio":
                    selected_option_id = request.POST.get(f"question_{question.id}")
                    response, created = Response.objects.get_or_create(
                        survey=survey, user=request.user, question=question
                    )
                    if selected_option_id:
                        response.selected_options.set([selected_option_id])
                    else:
                        response.selected_options.clear()
                    response.status = "In Progress" if "save_draft" in request.POST else "Completed"
                    response.save()

                # Handle checkbox questions
                elif question.question_type == "checkbox":
                    selected_option_ids = request.POST.getlist(f"question_{question.id}[]")
                    response, created = Response.objects.get_or_create(
                        survey=survey, user=request.user, question=question
                    )
                    if selected_option_ids:
                        response.selected_options.set(selected_option_ids)  # Save selected options
                    else:
                        response.selected_options.clear()  # Clear all options if none are selected
                    response.status = "In Progress" if "save_draft" in request.POST else "Completed"
                    response.save()

                # Handle text questions
                elif question.question_type == "text":
                    text_answer = request.POST.get(f"question_{question.id}")
                    response, created = Response.objects.get_or_create(
                        survey=survey, user=request.user, question=question
                    )
                    response.text_answer = text_answer or ""  # Save empty string if no text provided
                    response.status = "In Progress" if "save_draft" in request.POST else "Completed"
                    response.save()

            survey_taker_status, created = SurveyTakerStatus.objects.get_or_create(
                survey=survey, user=request.user
            )
            survey_taker_status.survey_status = "In Progress" if "save_draft" in request.POST else "Completed"
            if survey.state == "Republished" and survey_taker_status.survey_status == "Completed":
                survey_taker_status.results_available = True
            survey_taker_status.save()

            messages.success(request, "Survey retaken successfully!" if is_retake else "Survey completed successfully!")
            return redirect("dashboard")
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")

    return render(request, "surveys/take_survey.html", {
        "survey": survey,
        "questions": questions,
        "preprocessed_responses": preprocessed_responses,
    })

@login_required
def view_results(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)

    # Allow only the creator or eligible takers to view results
    if survey.created_by != request.user:
        taker_status = SurveyTakerStatus.objects.filter(
            survey=survey, user=request.user, results_available=True
        ).first()
        if not taker_status:
            return HttpResponseForbidden("You are not authorized to view these results.")

    questions = survey.questions.all()

    # Get total number of users the survey was published to
    total_takers = SurveyTakerStatus.objects.filter(survey=survey).count()

    # Calculate the total number of completed responses
    total_responses = SurveyTakerStatus.objects.filter(survey=survey, survey_status="Completed").count()

    # Initialize a dictionary to store aggregated results
    results = {}

    # Aggregate answers for each question
    for question in questions:
        answers = {}
        responses = Response.objects.filter(survey=survey, question=question)

        for response in responses:
            if question.question_type in ['radio', 'checkbox']:
                for option in response.selected_options.all():
                    answers[option.text] = answers.get(option.text, 0) + 1
            elif question.question_type == 'text':
                text_answer = response.text_answer
                answers[text_answer] = answers.get(text_answer, 0) + 1

        # Calculate the percentage for each answer
        for answer, count in answers.items():
            percentage = (count / total_responses) * 100 if total_responses > 0 else 0
            answers[answer] = {'count': count, 'percentage': percentage}

        results[question.text] = answers

    return render(request, 'surveys/view_results.html', {
        'survey': survey,
        'total_takers':total_takers,
        'total_responses': total_responses,
        'results': results,
    })

@login_required
def update_survey_status(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id, created_by=request.user)
    new_status = request.POST.get("new_status")

    if new_status not in ["Draft", "Published", "Closed", "Republished"]:
        messages.error(request, "Invalid status update.")
        return redirect("dashboard")

    # Update the survey state
    survey.state = new_status
    survey.save()
    messages.success(request, f"Survey status updated to {new_status}.")

    # Handle "Republished" status
    if new_status == "Republished":
        # Update `results_available` for all takers with 'Completed' status
        SurveyTakerStatus.objects.filter(survey=survey, survey_status="Completed").update(results_available=True)

    # Handle "Published" status
    elif new_status == "Published":
        taker_profiles = Profile.objects.filter(role="Taker")
        for profile in taker_profiles:
            SurveyTakerStatus.objects.get_or_create(
                survey=survey,
                user=profile.user,
                defaults={"survey_status": "Pending"}
            )

    return redirect("dashboard")


@login_required
def dashboard(request):
    profile = Profile.objects.get(user=request.user)

    if profile.role == 'Creator':
        surveys = Survey.objects.filter(created_by=request.user)
        taker_status = SurveyTakerStatus.objects.filter(survey__in=surveys).select_related('taker__user')

        # Fetch all users who can be invited except the current user (creator)
        available_takers = Profile.objects.exclude(user=request.user)

        context = {
            'role': 'Creator',
            'surveys': surveys,
            'taker_status': taker_status,
            'available_takers': available_takers
        }


    elif profile.role == 'Taker':
        # Get surveys where the user is invited or the survey is in published or republished state
        surveys = Survey.objects.filter(
            Q(state__in=["Published", "Republished"]) &
            Q(invited_users=request.user)  
        ).distinct()

        taker_surveys = []
        for survey in surveys:
            taker_status = SurveyTakerStatus.objects.filter(survey=survey, user=request.user).first()
            if taker_status:
                survey.user_status = 'Results Available' if taker_status.results_available else taker_status.survey_status
                survey.can_view_results = taker_status.results_available
                survey.can_retake = survey.state == 'Republished' and taker_status.results_available
            else:
                survey.user_status = 'Pending'
                survey.can_view_results = False
                survey.can_retake = False

            taker_surveys.append(survey)

        context = {'role': 'Taker', 'surveys': taker_surveys}

    else:
        return HttpResponseForbidden("Unauthorized access.")

    return render(request, 'surveys/dashboard.html', context)

@login_required
def publish_survey(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)

    if survey.created_by != request.user:
        return HttpResponseForbidden("You are not authorized to publish this survey.")

    if request.method == 'POST':
        selected_users = request.POST.getlist('selected_users')  # Extract only checked users
        select_all = request.POST.get('select_all')  # Handle Select All
        new_status = request.POST.get('new_status', '').strip()
        print(request)
        print(new_status)

        # Ensure select all is handled correctly without inviting unintended users
        if select_all:
            selected_users = list(Profile.objects.exclude(user=survey.created_by).values_list('user_id', flat=True))

        if new_status == 'Published' and not selected_users:
            messages.error(request, "Please select at least one user to publish.")
            return redirect('dashboard')

        # Only selected users should be invited
        try:
            if new_status == 'Published':
                for user_id in selected_users:
                    user = User.objects.get(id=user_id)
                    SurveyTakerStatus.objects.update_or_create(
                        survey=survey, user=user, defaults={'survey_status': 'Pending'}
                    )
                    survey.invited_users.add(user)

            survey.state = new_status
            survey.save()
            messages.success(request, f"Survey '{survey.name}' successfully updated to {new_status}.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

        return redirect('dashboard')

    return HttpResponseForbidden("Invalid request.")

@login_required
def send_invites(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)

    if request.user != survey.created_by:
        messages.error(request, "You are not authorized to send invites for this survey.")
        return redirect('dashboard')

    if request.method == 'POST':
        selected_users = request.POST.getlist('selected_users')
        select_all = request.POST.get('select_all')

        if select_all:  # If "Select All" is checked, invite all users
            selected_profiles = Profile.objects.exclude(user=request.user)
            selected_users = [profile.user.id for profile in selected_profiles]

        for user_id in selected_users:
            try:
                user = User.objects.get(id=user_id)
                SurveyTakerStatus.objects.get_or_create(survey=survey, user=user, survey_status='Pending')
                if not survey.invited_users.filter(id=user.id).exists():
                    survey.invited_users.add(user)
            except User.DoesNotExist:
                continue

        survey.save()
        messages.success(request, "Invites have been sent successfully.")
        return redirect('dashboard')

    return redirect('dashboard')

def retake_survey(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    user = request.user

    # Check if the user has already taken the survey
    taker_status = SurveyTakerStatus.objects.filter(survey=survey, user=user).first()
    if not taker_status:
        return HttpResponseForbidden("You are not authorized to retake this survey.")

    # Retrieve the previous responses for the logged-in user
    previous_responses = Response.objects.filter(survey=survey, user=user)

    # Calculate total takers and total responses
    total_takers = SurveyTakerStatus.objects.filter(survey=survey).count()
    total_responses = SurveyTakerStatus.objects.filter(survey=survey, survey_status="Completed").count()

    # Calculate response counts and percentages for each question
    previous_responses_percentages = {}
    for question in survey.questions.all():
        responses_count = Response.objects.filter(survey=survey, question=question).count()
        options_count = {}
        for option in question.options.all():
            option_count = Response.objects.filter(survey=survey, question=question, selected_options=option).count()
            option_percentage = (option_count / responses_count) * 100 if responses_count > 0 else 0
            options_count[option.id] = {
                'count': option_count,
                'percentage': option_percentage
            }
        previous_responses_percentages[question.id] = {
            'options_count': options_count,
        }

    # Prepare preprocessed_responses for template
    preprocessed_responses = {}
    for response in previous_responses:
        if response.selected_options.exists():
            preprocessed_responses[response.question.id] = [option.id for option in response.selected_options.all()]
        if response.text_answer:
            preprocessed_responses[response.question.id] = response.text_answer
        if response.others_input:
            preprocessed_responses[f"others_input_{response.question.id}"] = response.others_input

    # Handle form submission to update or create responses
    if request.method == 'POST':
        for question in survey.questions.all():
            # Handle radio questions
            if question.question_type == 'radio':
                selected_option_id = request.POST.get(f"question_{question.id}")  # Get selected option ID
                response, created = Response.objects.update_or_create(
                    survey=survey,
                    question=question,
                    user=user,
                )

                # Update the selected option for radio buttons
                if selected_option_id:
                    try:
                        selected_option = question.options.get(id=selected_option_id)
                        response.selected_options.set([selected_option])
                    except question.options.model.DoesNotExist:
                        pass  # Handle the case where the option doesn't exist

                # Handle the "Others" input for radio questions (if applicable)
                others_input = request.POST.get(f"others_input_{question.id}")
                if others_input:
                    response.others_input = others_input
                response.save()

            # Handle checkbox questions
            elif question.question_type == 'checkbox':
                selected_option_ids = request.POST.getlist(f"question_{question.id}[]")  # List of selected option IDs
                others_input = request.POST.get(f"others_input_{question.id}")

                response, created = Response.objects.update_or_create(
                    survey=survey,
                    question=question,
                    user=user,
                )

                # Clear previous selected options
                response.selected_options.clear()

                # Add new selected options
                for option_id in selected_option_ids:
                    try:
                        option = question.options.get(id=option_id)
                        response.selected_options.add(option)
                    except question.options.model.DoesNotExist:
                        pass  # Handle case where option doesn't exist

                # Handle the "Others" input if provided
                if others_input:
                    response.others_input = others_input
                response.save()

            # Handle text questions
            elif question.question_type == 'text':
                text_answer = request.POST.get(f"question_{question.id}")
                response, created = Response.objects.update_or_create(
                    survey=survey,
                    question=question,
                    user=user,
                    defaults={'text_answer': text_answer}
                )

        # Once responses are saved, update the taker status to 'Completed'
        taker_status.survey_status = "Completed"
        taker_status.save()

        # Redirect to the dashboard after saving the responses
        return redirect('dashboard')  # Adjust this to your actual dashboard URL name

    return render(request, 'surveys/retake_survey.html', {
        'survey': survey,
        'questions': survey.questions.all(),
        'preprocessed_responses': preprocessed_responses,
        'previous_responses_percentages': previous_responses_percentages,
        'total_takers': total_takers,
        'total_responses': total_responses,
    })