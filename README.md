
*************Meeting Room Reservation System*************

A comprehensive Django web application for managing and booking meeting rooms within an organization. This system allows users to reserve meeting rooms, send invitations to participants, and manage room resources efficiently.

**Features**

* **User Authentication:** Registration, login, and user management
* **Room Management:** Create, update, and delete meeting rooms
* **Room Details:** View room capacity, amenities (projector, whiteboard, video conferencing)
* **Reservation System:** Book rooms for specific time slots
* **Calendar View:** See room availability on a weekly calendar
* **Email Notifications:** Send meeting invites and reminders to participants
* **Admin Dashboard:** Monitor room usage and manage reservations
* **Responsive Design:** Works on desktop and mobile devices


    ![Screenshot From 2025-03-14 21-00-45](https://github.com/user-attachments/assets/f5269610-231a-4e50-bdec-2bb5b9067dd6)
    

**Technologies Used**

* **Django 4.2:** Web framework for backend
* **Bootstrap:** Frontend styling and components
* **SQLite:** Database (default)
* **Django Template Language:** Frontend rendering
* **SMTP:** Email notifications

**Installation**

* Clone the repository:
    * `git clone https://github.com/hajmoha/payam-pardaz.git`
    * `cd payam-pardaz`
* Create and activate a virtual environment:
    * `python -m venv venv`
    * `source venv/bin/activate` # On Windows: venv\Scripts\activate
* Install dependencies:
    * `pip install -r requirements.txt`
* Run migrations:
    * `python manage.py migrate`
* Create a superuser:
    * `python manage.py createsuperuser`
* Update email settings in myproject/settings.py with your SMTP credentials:
    * `EMAIL_HOST_USER = 'your-email@example.com'`
    * `EMAIL_HOST_PASSWORD = 'your-password'`
    * `DEFAULT_FROM_EMAIL = 'your-email@example.com'`
* Run the development server:
    * `python manage.py runserver`
* Access the application at [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

**Usage**

* **Regular Users:**
    * Register a new account or login
    * Browse available meeting rooms
    * View room details and availability
    * Make a reservation by selecting date and time slot
    * Add participants by email addresses
    * View and manage your reservations
* **Admin Users:**
    * Access the admin dashboard
    * Create and manage meeting rooms
    * View all reservations
    * Generate reports on room usage
    * Manage users and permissions

**Project Structure**

* `base/`: Main application containing models, views, and templates
    * `models.py`: Defines Room and Reservation data models
    * `views.py`: Contains all view functions
    * `forms.py`: Defines forms for user input
    * `urls.py`: URL routing configuration
* `myproject/`: Project configuration files
    * `settings.py`: Project settings including database and email config
    * `urls.py`: Project-level URL configuration

**Email Notifications**

The system sends two types of email notifications:

* Meeting invitations: When a user creates a new reservation
* Meeting reminders: Sent one day before scheduled meetings

To enable this functionality, configure the email settings in `settings.py`.

**Future Enhancements**

* **API Integration:** Build REST API for mobile app integration
* **Google Calendar Sync:** Allow users to sync with their Google Calendar
* **Resource Management:** Add equipment booking along with rooms
* **Advanced Reporting:** Generate usage statistics and reports
* **Recurring Meetings:** Allow scheduling recurring meetings




