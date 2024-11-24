from django.contrib.auth.forms import AuthenticationForm
from django.forms import modelform_factory
from django.http import HttpResponseForbidden
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
            # Save user with username, email, and password
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.save()

            # Create the profile with role
            profile = Profile.objects.create(user=user, role=form.cleaned_data['role'])

            # Log the user in
            login(request, user)

            # Add the user to the SurveyTakerStatus table for all Published surveys if they are a Taker
            if profile.role == 'Taker':  # Only add to SurveyTakerStatus for Takers
                surveys = Survey.objects.filter(state='Published')  # Only Published surveys
                for survey in surveys:
                    SurveyTakerStatus.objects.get_or_create(
                        survey=survey,
                        user=user,
                        defaults={'status': 'Pending'}
                    )

            return redirect('dashboard')  # Redirect to the dashboard after registration
    else:
        form = UserRegistrationForm()

    return render(request, 'surveys/register.html', {'form': form})

@login_required
def dashboard(request):
    profile = Profile.objects.get(user=request.user)

    if profile.role == 'Creator':
        surveys = Survey.objects.filter(created_by=request.user)
        context = {'role': 'Creator', 'surveys': surveys}

    elif profile.role == 'Taker':
        surveys = Survey.objects.filter(state__in=["Published", "Republished"])

        for survey in surveys:
            # Fetch the survey taker's status
            taker_status = SurveyTakerStatus.objects.filter(survey=survey, user=request.user).first()

            if taker_status:
                # Update the status for the taker based on `results_available`
                if taker_status.results_available:
                    survey.user_status = 'Results Available'
                else:
                    survey.user_status = taker_status.survey_status
            else:
                survey.user_status = 'Pending'  # Default status if no record exists

            # Allow viewing results only if `results_available` is True
            survey.can_view_results = bool(
                taker_status and taker_status.results_available
            )

        context = {'role': 'Taker', 'surveys': surveys}
    else:
        return HttpResponseForbidden("Unauthorized access.")

    return render(request, 'surveys/dashboard.html', context)

def create_survey(request):
    SurveyForm = modelform_factory(Survey, fields=('name', 'description'))

    if request.method == 'POST':
        form = SurveyForm(request.POST)
        if form.is_valid():
            try:
                # Save the survey object first
                survey = form.save(commit=False)
                survey.created_by = request.user
                survey.save()

                # Get all the question texts and question types from the POST request
                question_texts = request.POST.getlist('question_text')
                question_types = request.POST.getlist('question_type')

                # Validate that at least 5 questions are added
                if len(question_texts) < 5:
                    messages.error(request, "You must add at least 5 questions to the survey.")
                    return render(request, 'surveys/create_survey.html', {'form': form})

                # Loop through each question text and create corresponding questions in the DB
                for i, question_text in enumerate(question_texts):
                    question_type = question_types[i]
                    question = Question.objects.create(
                        survey=survey,
                        text=question_text,
                        question_type=question_type
                    )

                    # If the question type is radio or checkbox, save options for it
                    if question_type in ['radio', 'checkbox']:
                        options_key = f'options_{i}[]'
                        option_texts = request.POST.getlist(options_key)
                        # Loop through and create options for this question
                        for option_text in option_texts:
                            if option_text.strip():  # Ensure non-empty options
                                Option.objects.create(question=question, text=option_text)

                # Redirect to dashboard after successful survey creation
                return redirect('dashboard')

            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
        else:
            messages.error(request, "Form submission failed. Please correct the errors.")
    else:
        form = SurveyForm()

    return render(request, 'surveys/create_survey.html', {'form': form})\

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
def publish_survey(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id, created_by=request.user)
    if survey.state == 'Draft':
        survey.state = 'Published'
        survey.save()
        return redirect('dashboard')
    else:
        return HttpResponseForbidden("Survey cannot be published.")

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
    questions = survey.questions.prefetch_related('options')

    # Preprocess existing user responses
    user_responses = Response.objects.filter(survey=survey, user=request.user)
    preprocessed_responses = {}
    for response in user_responses:
        question = response.question
        if question.question_type == "text":
            preprocessed_responses[question.id] = response.text_answer
        # elif question.question_type == "calendar":
        #     preprocessed_responses[question.id] = response.date_answer
        elif question.question_type in ["radio", "checkbox"]:
            preprocessed_responses[question.id] = set(
                response.selected_options.values_list("id", flat=True)
            )

    if request.method == "POST":
        try:
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


            # Update survey taker's status in SurveyTakerStatus table
            survey_taker_status, created = SurveyTakerStatus.objects.get_or_create(
                survey=survey, user=request.user
            )
            survey_taker_status.survey_status = "In Progress" if "save_draft" in request.POST else "Completed"
            survey_taker_status.save()

            # If the survey is republished, mark results as available if the status is completed
            if survey.state == "Republished" and survey_taker_status.survey_status == "Completed":
                survey_taker_status.results_available = True  # Set the results as available
            survey_taker_status.save()

            # Add success message for submission or draft
            if "save_draft" in request.POST:
                messages.success(request, "Your survey responses have been saved as a draft.")
            else:
                messages.success(request, "Thank you! Your survey has been successfully completed.")

            # Redirect to the dashboard
            return redirect("dashboard")

        except Exception as e:
            messages.error(request, f"An error occurred while saving your responses: {e}")

    context = {
        "survey": survey,
        "questions": questions,
        "preprocessed_responses": preprocessed_responses,
    }
    return render(request, "surveys/take_survey.html", context)

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
