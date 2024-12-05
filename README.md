# Survey Application

### Contributors:
- **Viranchi More** (Backend)
- **Pallavi Billava** (Backend)
- **Rajiv Thorbole** (Frontend)
- **Anish Vichare** (Frontend)

School of Computing, Binghamton University  
INFO-537: Tools for Data Science  
Instructor: Dr. Hafiz Mansub Ali  

---

## Table of Contents
1. [Introduction](#introduction)
2. [Features](#features)
3. [Tools and Technologies](#tools-and-technologies)
4. [Workflow](#workflow)
    - [Home Page](#home-page)
    - [Login and Registration](#login-and-registration)
    - [Dashboard](#dashboard)
    - [Create Survey Workflow](#create-survey-workflow)
    - [Take Survey Workflow](#take-survey-workflow)
    - [Logout](#logout)
5. [Database Overview](#database-overview)
6. [Challenges Faced](#challenges-faced)
7. [Roles and Responsibilities](#roles-and-responsibilities)
8. [Conclusion](#conclusion)
9. [Git Repository](#git-repository)

---

## Introduction

The Survey Application is a web-based platform that allows users to create, manage, and participate in surveys. The application supports two user roles:
1. **Survey Creators**: Users who can design and manage surveys.
2. **Survey Takers**: Users who can participate in surveys and view results.

Built with Django as the backend framework and PostgreSQL for database management, the app ensures seamless integration of survey functionality with a dynamic frontend powered by HTML, CSS, and JavaScript.

---

## Features

- **User Authentication**: Login and Registration functionality.
- **Role Management**: Distinct roles for Survey Creators and Takers.
- **Survey Creation**: Dynamic form handling for adding questions and options.
- **Survey Participation**: Ability to take, retake, and view survey results.
- **Survey Management**: State transitions (Draft, Published, Closed) and editing options.
- **Dashboard**: A centralized interface for survey creators and takers.
- **Responsive Design**: Interactive and user-friendly frontend.

---

## Tools and Technologies

- **Backend**: Django
- **Frontend**: HTML, CSS, JavaScript
- **Database**: PostgreSQL
- **Version Control**: Git & GitHub

---

## Workflow

### Home Page
The starting point of the application, accessible at `http://127.0.0.1:8000/`, provides options to log in or register.

### Login and Registration
- **Login**: Existing users can log in to access their dashboard.
- **Register**: New users can sign up for an account.

### Dashboard
After logging in, users are redirected to their respective dashboards:
- **Survey Creator Dashboard**: Manage surveys (create, edit, publish, close, and republish).
- **Survey Taker Dashboard**: Participate in available surveys and view results.

### Create Survey Workflow
1. Survey creators can design surveys with customizable questions and options.
2. Actions include:
    - **View Results**: Display survey responses and percentages.
    - **Invite Users**: Send survey invitations.
    - **Edit Survey**: Modify survey questions or options.
    - **Change Status**: Toggle survey states (Draft, Published, Closed).

### Take Survey Workflow
1. Survey takers can select available surveys and submit responses.
2. Actions include:
    - **Retake Survey**: Modify previous responses if allowed.
    - **View Results**: Access aggregated survey statistics.

### Logout
Redirects users to a thank-you page upon logging out.

---

## Database Overview

The application uses PostgreSQL to manage survey-related data through the following models:

- **Auth_user**: Django's built-in user authentication system.
- **Profile**: Manages user roles (Creator/Taker).
- **Survey**: Stores survey details and states (Draft, Published, Closed).
- **Question**: Defines survey questions (Text, Single, Multiple Choice).
- **Option**: Stores possible answers to survey questions.
- **Response**: Captures user responses.
- **Response_selected_options**: Records multiple-choice answers.
- **Survey_invited_users**: Tracks invited users for specific surveys.
- **Survey_taker_status**: Manages user participation status.

---

## Challenges Faced

1. **Frontend-Backend Integration**: Synchronizing dynamic functionality like question addition without page refreshes.
2. **State Management**: Ensuring correct transitions between survey states while maintaining data integrity.
3. **Dynamic Form Handling**: Enabling real-time addition/removal of survey components through JavaScript.

---

## Roles and Responsibilities

| Name           | Responsibilities         |
|----------------|--------------------------|
| **Viranchi More** | Backend Development / Report |
| **Pallavi Billava** | Backend Development / Report |
| **Rajiv Thorbole** | Frontend Development |
| **Anish Vichare** | Frontend Development |

---

## Conclusion

The Survey Application combines Django's robust backend with a dynamic frontend built using HTML, CSS, and JavaScript to deliver a seamless survey experience. PostgreSQL ensures efficient data management for large-scale survey responses. The application is scalable, maintainable, and user-friendly, designed to cater to diverse survey needs.

---

## Git Repository

- gh repo clone pbillava10/TDS537-SurveyApplication (for cloning the folder)
- https://github.com/pbillava10/TDS537-SurveyApplication
