from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 🔐 Authentication
    path('', views.welcome, name='welcome'),
    path('register/student/', views.student_register, name='student_register'),
    path('register/teacher/', views.register_teacher, name='teacher_register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),

    # 🧑‍🎓 Student Dashboard & Features
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/timetable/', views.student_timetable, name='student_timetable'),
    path('student/assignments/', views.student_assignments, name='student_assignments'),
    path('student/assignments/<int:assignment_id>/submit/', views.submit_assignment, name='submit_assignment'),
    path('student/submissions/', views.student_submissions, name='student_submissions'),
    path('student/grades/', views.student_grades, name='student_grades'),
    path('student/resources/', views.student_resources, name='student_resources'),
    path('student/announcements/', views.student_announcements, name='student_announcements'),
    path('student/details/', views.student_details, name='student_details'),
    path('student/details/edit/', views.edit_student_profile, name='edit_student_profile'),

    # 🧑‍🏫 Teacher Dashboard & Features
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/timetable/', views.teacher_timetable, name='teacher_timetable'),
    path('teacher/assignments/', views.teacher_assignments, name='teacher_assignments'),
    path('teacher/assignments/edit/<int:assignment_id>/', views.edit_assignment, name='edit_assignment'),
    path('teacher/assignments/delete/<int:assignment_id>/', views.delete_assignment, name='delete_assignment'),
    path('teacher/resources/', views.teacher_resources, name='teacher_resources'),
    path('teacher/submissions/', views.teacher_submissions, name='teacher_submissions'),
    path('teacher/submissions/<int:submission_id>/grade/', views.grade_submission, name='grade_submission'),
    path('teacher/details/edit/', views.edit_teacher_profile, name='edit_teacher_profile'),
    path('teacher/profile/', views.teacher_profile, name='teacher_profile'),
    path('teacher/grades/', views.teacher_grades, name='teacher_grades'),

    # 🛠 Admin Dashboard & Management
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard-admin/registration-codes/', views.manage_registration_codes, name='manage_registration_codes'),
    path('dashboard-admin/resources/', views.admin_resources, name='admin_resources'),
    path('dashboard-admin/resources/add/', views.add_resource, name='add_resource'),
    path('dashboard-admin/resources/edit/<int:resource_id>/', views.edit_resource, name='edit_resource'),
    path('dashboard-admin/resources/delete/<int:resource_id>/', views.delete_resource, name='delete_resource'),
    path('dashboard-admin/timetables/', views.manage_timetables, name='manage_timetables'),
    path('timetables/add/', views.add_timetable_period, name='add_timetable_period'),
    path('dashboard-admin/registration-codes/delete/<int:code_id>/', views.delete_registration_code, name='delete_registration_code'),
    path('admin/grades/delete/<int:grade_id>/', views.delete_student_grade, name='delete_student_grade'),

    # 📣 Announcements (Admin)
    path('dashboard-admin/announcements/', views.manage_announcements, name='manage_announcements'),
    path('announcements/create/', views.create_announcement, name='create_announcement'),
    path('announcements/edit/<int:announcement_id>/', views.edit_announcement, name='edit_announcement'),
    path('announcements/delete/<int:announcement_id>/', views.delete_announcement, name='delete_announcement'),

    path('teacher/upload-grades/', views.teacher_upload_grades, name='teacher_upload_grades'),
    path('dashboard-admin/manage-grades/', views.admin_manage_grades, name='admin_manage_grades'),
    path('student/test-examination-grades/', views.student_grades_view, name='student_test_examination_grades'),
    path('teacher/edit-grade/<int:grade_id>/', views.edit_grade, name='edit_grade'),
    path('dashboard-admin/grades/<int:grade_id>/edit/', views.edit_student_grade, name='edit_student_grade'),


    # 🔑 Password Reset
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='portal/password_reset_form.html',
        email_template_name='portal/password_reset_email.html',
        subject_template_name='portal/password_reset_subject.txt',
        success_url='/password_reset/done/',
    ), name='password_reset'),

    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='portal/password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='portal/password_reset_confirm.html',
        success_url='/reset/done/',
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='portal/password_reset_complete.html'
    ), name='password_reset_complete'),
]

# 📁 Static & Media Files (Dev Only)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
