from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = (('Creator', 'Survey Creator'), ('Taker', 'Survey Taker'))
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    class Meta:
        db_table = 'profile'


class Survey(models.Model):
    STATE_CHOICES = [
        ('Draft', 'Draft'),
        ('Published', 'Published'),
        ('Closed', 'Closed'),
        ("REPUBLISHED", 'Republished'),
    ]
    name = models.CharField(max_length=200)
    description = models.TextField()
    state = models.CharField(max_length=100, choices=STATE_CHOICES, default='Draft')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    republished_date = models.DateTimeField(null=True, blank=True)  # Track republished date

    class Meta:
        db_table = 'survey'

    def __str__(self):
        return self.name

    def get_taker_status(self, user):
        """
        Determines the status of the survey for a specific user.
        - Returns 'Completed' if all responses are marked as completed.
        - Returns 'In Progress' if at least one response exists but is not completed.
        - Returns 'Pending' if no responses exist.
        """
        responses = Response.objects.filter(survey=self, user=user)

        if not responses.exists():
            return 'Pending'

        if responses.filter(status='Completed').count() == responses.count():
            return 'Completed'

        return 'In Progress'


class Question(models.Model):
    QUESTION_TYPES = [
        ('text', 'Text Input'),
        ('radio', 'Single Choice'),
        ('checkbox', 'Multiple Choice'),
        # ('calendar', 'Calendar'),  # New question type
    ]
    text = models.CharField(max_length=255)
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES)
    survey = models.ForeignKey(Survey, related_name='questions', on_delete=models.CASCADE)

    class Meta:
        db_table = 'question'


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=255)

    class Meta:
        db_table = 'option'


class Response(models.Model):
    SURVEY_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_options = models.ManyToManyField(Option, blank=True)  # For radio/checkbox questions
    text_answer = models.TextField(blank=True, null=True)  # For text-based questions
    date_answer = models.DateField(blank=True, null=True)  # For calendar questions
    status = models.CharField(max_length=15, choices=SURVEY_STATUS_CHOICES, default='Pending')

    class Meta:
        db_table = 'response'


class OptionEdit(models.Model):
    option = models.ForeignKey(Option, related_name='edits', on_delete=models.CASCADE)
    old_text = models.TextField()  # Store the old value of the option text
    edited_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)  # The user who made the edit
    edited_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the edit occurred

    def __str__(self):
        return f"Edit to Option: {self.option.id} - {self.old_text}"

class SurveyTakerStatus(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # The survey taker
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)  # The survey they are taking
    survey_status = models.CharField(max_length=100, choices=STATUS_CHOICES, default='Pending')  # Survey status for the user
    results_available = models.BooleanField(default=False)  # Indicates if results are available for this survey-taker

    class Meta:
        db_table = 'survey_taker_status'
        unique_together = ('user', 'survey')  # Ensure that a user can only have one status per survey

    def __str__(self):
        return f"User: {self.user.username}, Survey: {self.survey.name}, Status: {self.survey_status}, Results Available: {self.results_available}"

