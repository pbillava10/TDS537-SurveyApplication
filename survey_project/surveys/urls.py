from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_login, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.create_survey, name='create_survey'),
    # path('survey/<int:survey_id>/invite_new_takers/', views.invite_new_takers, name='invite_new_takers'),
    path('survey/<int:survey_id>/publish/', views.publish_survey, name='publish_survey'),
    path('survey/<int:survey_id>/close/', views.close_survey, name='close_survey'),
    path('survey/<int:survey_id>/edit/', views.edit_survey, name='edit_survey'),
    path('view_results/<int:survey_id>/', views.view_results, name='view_results'),
    path('survey/<int:survey_id>/', views.survey_detail, name='survey_detail'),
    path("update_survey_status/<int:survey_id>/", views.update_survey_status, name="update_survey_status"),
    path("take_survey/<int:survey_id>/", views.take_survey, name="take_survey"),
    path("view_survey/<int:survey_id>/", views.survey_detail, name="view_survey"),
    path('survey/<int:survey_id>/invite/', views.send_invites, name='send_invites'),
    path('survey/<int:survey_id>/retake/', views.retake_survey, name='retake_survey'),
]
