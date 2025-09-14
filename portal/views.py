# Django core imports
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from django.template.loader import get_template
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import now
from django.utils.dateparse import parse_date
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.templatetags.static import static
from django.db.models import Q
import mimetypes
from django.db.models import Max, Q
from io import BytesIO
from django.template.loader import render_to_string

import os
import base64
from collections import defaultdict
from datetime import datetime, time, timedelta

# Third-party imports
from xhtml2pdf import pisa

# Local app imports
from .models import (
    User, Assignment, Grade, SubjectGrade, GradeReport, Resource,
    Announcement, Timetable, Submission, Teacher, Classroom, RegistrationCode, BehaviouralSkill
)
from .forms import ResourceForm, AnnouncementForm
from .decorators import student_required, teacher_required


def welcome(request):
    return render(request, 'portal/welcome.html')

def is_admin(user):
    return user.role == 'admin'

def register_user(request):
    return redirect('student_register')

def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.role == 'student':
                return redirect('student_dashboard')
            elif user.role == 'teacher':
                return redirect('teacher_dashboard')
            elif user.role == 'admin':
                return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'portal/login.html')

def logout_user(request):
    logout(request)
    return redirect('login')

# --- Student Registration ---
def student_register(request):
    classrooms = Classroom.objects.all()

    if request.method == 'POST':
        data = request.POST
        files = request.FILES

        # --- Extract form data ---
        username = data.get('username', '').strip()
        password1 = data.get('password1', '')
        password2 = data.get('password2', '')
        first_name = data.get('first_name', '').strip()
        middle_name = data.get('middle_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip()
        gender = data.get('gender', '').strip()
        dob = data.get('dob', '').strip()
        phone = data.get('phone', '').strip()
        classroom_name = data.get('classroom', '')
        reg_code_input = data.get('registration_code', '').strip()
        profile_picture = files.get('profile_picture')
        address = data.get('address', '').strip()

        # --- Additional fields ---
        nationality = data.get('nationality', '').strip()
        state_of_origin = data.get('state_of_origin', '').strip()
        height = data.get('height', '').strip()
        weight = data.get('weight', '').strip()

        # --- Parent info ---
        parent_first_name = data.get('parent_first_name', '').strip()
        parent_last_name = data.get('parent_last_name', '').strip()
        parent_phone = data.get('parent_phone', '').strip()
        parent_email = data.get('parent_email', '').strip()
        parent_address = data.get('parent_address', '').strip()

        # --- Validation ---
        errors = []

        if not classroom_name:
            errors.append('Please select a classroom.')
        if not username:
            errors.append('Username is required.')
        if not password1:
            errors.append('Password is required.')
        if password1 != password2:
            errors.append('Passwords do not match.')
        if not reg_code_input:
            errors.append('Registration code is required.')
        if not first_name or not last_name:
            errors.append('First and last name are required.')
        if not gender:
            errors.append('Gender is required.')
        if not dob:
            errors.append('Date of birth is required.')
        if not phone:
            errors.append('Phone number is required.')
        if not address:
            errors.append('Address is required.')
        if not nationality:
            errors.append('Nationality is required.')
        if not state_of_origin:
            errors.append('State of Origin is required.')
        if not height:
            errors.append('Height is required.')
        if not weight:
            errors.append('Weight is required.')
        if not parent_first_name or not parent_last_name or not parent_phone or not parent_email or not parent_address:
            errors.append('All parent details are required.')

        # Check registration code
        try:
            reg_code_obj = RegistrationCode.objects.get(code=reg_code_input, is_active=True)
        except RegistrationCode.DoesNotExist:
            errors.append('Invalid or already used registration code.')

        # Check username duplicate
        if User.objects.filter(username=username).exists():
            errors.append('Username already exists.')

        # --- Handle errors ---
        if errors:
            for error in errors:
                messages.error(request, error)

            # Preserve submitted data in context
            context = {
                'classrooms': classrooms,
                'username': username,
                'first_name': first_name,
                'middle_name': middle_name,
                'last_name': last_name,
                'email': email,
                'gender': gender,
                'dob': dob,
                'phone': phone,
                'classroom': classroom_name,
                'registration_code': reg_code_input,
                'address': address,
                'nationality': nationality,
                'state_of_origin': state_of_origin,
                'height': height,
                'weight': weight,
                'parent_first_name': parent_first_name,
                'parent_last_name': parent_last_name,
                'parent_phone': parent_phone,
                'parent_email': parent_email,
                'parent_address': parent_address,
            }
            return render(request, 'portal/student_registration.html', context)

        # --- Create user ---
        user = User.objects.create_user(
            username=username,
            password=password1,
            email=email,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            gender=gender,
            dob=dob,
            phone=phone,
            profile_picture=profile_picture,
            address=address,
            nationality=nationality,
            state_of_origin=state_of_origin,
            height=height,
            weight=weight,
            parent_first_name=parent_first_name,
            parent_last_name=parent_last_name,
            parent_phone=parent_phone,
            parent_email=parent_email,
            parent_address=parent_address,
        )

        user.role = 'student'
        user.classroom = get_object_or_404(Classroom, name=classroom_name)
        user.save()

        # Mark registration code as used
        reg_code_obj.is_active = False
        reg_code_obj.used_by = user
        reg_code_obj.save()

        messages.success(request, 'Registration successful. You can now login.')
        return redirect('login')

    # --- GET request ---
    return render(request, 'portal/student_registration.html', {'classrooms': classrooms})



# --- Student Views ---
@login_required
@student_required
def student_dashboard(request):
    # The template uses `user.classroom.name` directly
    return render(request, 'portal/student_dashboard.html')

@login_required
@student_required
def student_timetable(request):
    student = request.user
    classroom = student.classroom
    current_day = datetime.now().strftime("%A")

    periods = Timetable.objects.filter(classroom=classroom).order_by('day', 'start_time')

    # Time slots (e.g., "09:00 - 10:00")
    time_slots = sorted(set([
        f"{p.start_time.strftime('%H:%M')} - {p.end_time.strftime('%H:%M')}"
        for p in periods
    ]))

    # Days (standard school days)
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    # Grid structure: day -> [subjects per time slot]
    timetable = {day: ['' for _ in time_slots] for day in days}

    for p in periods:
        time_label = f"{p.start_time.strftime('%H:%M')} - {p.end_time.strftime('%H:%M')}"
        if time_label in time_slots:
            col_index = time_slots.index(time_label)
            timetable[p.day][col_index] = p.subject

    return render(request, 'portal/student_timetable.html', {
        'class_name': classroom,
        'time_slots': time_slots,
        'timetable': timetable,
        'current_day': current_day
    })

@login_required
@student_required
def student_assignments(request):
    classroom = request.user.classroom  # ensure this is not None
    assignments = Assignment.objects.filter(classroom=classroom).order_by('-due_date')

    # Get IDs of assignments the student has submitted
    submissions = Submission.objects.filter(student=request.user)
    submitted_assignment_ids = submissions.values_list('assignment_id', flat=True)

    # For date comparison in template
    today = timezone.now().date()

    return render(request, 'portal/student_assignments.html', {
        'assignments': assignments,
        'submitted_assignment_ids': submitted_assignment_ids,
        'today': today
    })

@login_required
@student_required
def student_resources(request):
    user_classroom = request.user.classroom

    # Only show resources for the logged-in student's class
    resources = Resource.objects.filter(classroom=user_classroom).order_by('-uploaded_at')

    return render(request, 'portal/student_resources.html', {
        'resources': resources
    })

@login_required
@student_required
def student_announcements(request):
    user_classroom = request.user.classroom

    # Get announcements for the whole school (classroom=None) or for the student's class
    announcements = Announcement.objects.filter(
        target_audience__in=['student', 'all']
    ).filter(
        Q(classroom__isnull=True) | Q(classroom=user_classroom)
    ).order_by('-created_at')

    return render(request, 'portal/student_announcements.html', {
        'announcements': announcements
    })

@login_required
@student_required
def student_details(request):
    student = request.user  # logged-in student

    context = {
        'student': student
    }
    return render(request, 'portal/student_details.html', context)

@login_required
@student_required
def edit_student_profile(request):
    student = request.user
    classrooms = Classroom.objects.all()

    if request.method == 'POST':
        # Update basic info
        student.first_name = request.POST.get('first_name', student.first_name)
        student.middle_name = request.POST.get('middle_name', student.middle_name)
        student.last_name = request.POST.get('last_name', student.last_name)
        student.email = request.POST.get('email', student.email)
        student.phone = request.POST.get('phone', student.phone)
        student.address = request.POST.get('address', student.address)

        # Update classroom by name
        classroom_name = request.POST.get('classroom')
        if classroom_name:
            student.classroom = get_object_or_404(Classroom, name=classroom_name)

        # Update profile picture if uploaded
        if 'profile_picture' in request.FILES:
            student.profile_picture = request.FILES['profile_picture']

        student.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('student_details')

    return render(request, 'portal/edit_student_profile.html', {'student': student, 'classrooms': classrooms})

@login_required
@student_required
def student_submissions(request):
    # All submissions for the logged-in student
    submissions = Submission.objects.filter(student=request.user).order_by('-submitted_at')
    assignments = Assignment.objects.all().order_by('-due_date')

    # Pre-select assignment from GET parameter (from assignments page)
    preselected_assignment_id = request.GET.get('assignment')

    if request.method == 'POST':
        assignment_id = request.POST.get('assignment')
        uploaded_file = request.FILES.get('file')
        notes = request.POST.get('notes', '').strip()

        # Validate assignment exists
        assignment = get_object_or_404(Assignment, id=assignment_id)

        # Prevent submission if deadline passed (compare as dates)
        if assignment.due_date < timezone.now().date():
            messages.error(request, f"❌ Submission failed. The deadline for '{assignment.title}' has passed.")
            return redirect('student_submissions')

        if not uploaded_file:
            messages.error(request, "Please upload a file.")
            return redirect('student_submissions')

        # Allow resubmission (update existing submission or create new)
        submission, created = Submission.objects.update_or_create(
            student=request.user,
            assignment=assignment,
            defaults={
                'file': uploaded_file,
                'notes': notes,
                'submitted_at': timezone.now()
            }
        )

        if created:
            messages.success(request, f"✅ Your submission for '{assignment.title}' was successful!")
        else:
            messages.success(request, f"🔄 Your submission for '{assignment.title}' has been updated!")

        return redirect('student_submissions')

    # Attach grade info and calculate percentage/pass-fail
    for sub in submissions:
        try:
            grade = Grade.objects.get(student=request.user, assignment=sub.assignment)
            sub.grade = grade.score
            sub.total_marks = grade.total_marks
            sub.graded = True
            sub.feedback = grade.feedback

            # Compute percentage and pass/fail
            if sub.total_marks and sub.total_marks > 0:
                sub.percentage = round((sub.grade / sub.total_marks) * 100, 2)
                sub.pass_fail = 'Pass' if sub.percentage >= 50 else 'Fail'
            else:
                sub.percentage = None
                sub.pass_fail = None

        except Grade.DoesNotExist:
            sub.grade = None
            sub.total_marks = None
            sub.graded = False
            sub.feedback = None
            sub.percentage = None
            sub.pass_fail = None

    context = {
        'submissions': submissions,
        'assignments': assignments,
        'now': timezone.now(),
        'preselected_assignment_id': preselected_assignment_id,
    }
    return render(request, 'portal/student_submissions.html', context)

@login_required
@student_required
def student_grades_view(request):
    student = request.user

    # All reports for this student
    reports = GradeReport.objects.filter(student=student)
    # All grades for all reports
    grades = SubjectGrade.objects.filter(report__in=reports).order_by('report__term', 'subject')
    # Latest report for summary
    latest_report = reports.order_by('-date_uploaded').first()

    return render(request, 'portal/student_test_examination_grades.html', {
        'grades': grades,
        'report': latest_report,
        'student_name': student.get_full_name() or student.username,
    })

@login_required
def download_my_grade_report_pdf(request):
    student = request.user
    if student.role != 'student':
        return HttpResponse("Unauthorized", status=403)

    # Get the latest report
    report = GradeReport.objects.filter(student=student).order_by('-date_uploaded').first()
    if not report:
        return HttpResponse("No report available.", status=404)

    grades = report.subject_grades.all()
    behavioural_skills = report.behavioural_skills.all()

    student_profile = {
        "student_name": student.get_full_name(),
        "classroom": getattr(student.classroom, 'name', ''),
        "age": getattr(student, 'age', ''),
    }

    logo_url = getattr(student, 'school_logo', None)
    if logo_url:
        logo_url = logo_url.url

    context = {
        "student_name": student.get_full_name(),
        "student_profile": student_profile,
        "grades": grades,
        "report": report,
        "logo_url": logo_url,
        "behavioural_skills": behavioural_skills,
    }

    template_path = "portal/grades_pdf.html"
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{student.username}_report.pdf"'

    html = render(request, template_path, context).content.decode("UTF-8")
    result = BytesIO()
    pisa_status = pisa.CreatePDF(src=html, dest=result)
    if pisa_status.err:
        return HttpResponse("Error generating PDF <pre>" + html + "</pre>")

    response.write(result.getvalue())
    return response

def register_teacher(request):
    if request.method == 'POST':
        data = request.POST
        files = request.FILES

        username = data.get('username', '').strip()
        password1 = data.get('password1', '')
        password2 = data.get('password2', '')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip()
        subject = data.get('subject', '').strip()
        phone = data.get('phone', '').strip()
        profile_picture = files.get('profile_picture')

        errors = []

        # All fields required
        if not username:
            errors.append("Username is required.")
        if not password1 or not password2:
            errors.append("Password and confirmation are required.")
        if password1 != password2:
            errors.append("Passwords do not match.")
        if not first_name:
            errors.append("First name is required.")
        if not last_name:
            errors.append("Last name is required.")
        if not email:
            errors.append("Email is required.")
        if not subject:
            errors.append("Subject/Department is required.")
        if not phone:
            errors.append("Phone number is required.")
        if not profile_picture:
            errors.append("Profile picture is required.")
        if User.objects.filter(username=username).exists():
            errors.append("Username already exists.")

        if errors:
            for error in errors:
                messages.error(request, error)
            # Return form with previously entered data (except password & profile)
            context = {
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'subject': subject,
                'phone': phone,
            }
            return render(request, 'portal/teacher_registration.html', context)

        # Create user and teacher
        user = User.objects.create_user(
            username=username,
            password=password1,
            first_name=first_name,
            last_name=last_name,
            email=email,
            role='teacher'
        )
        Teacher.objects.create(
            user=user,
            subject=subject,
            phone=phone,
            profile_picture=profile_picture
        )
        messages.success(request, 'Registration successful. You can now login.')
        return redirect('login')

    return render(request, 'portal/teacher_registration.html')

# --- Teacher Views ---
@login_required(login_url='login')
def teacher_dashboard(request):
    if request.user.role != 'teacher':
        return redirect('login')  # Or a 403 page
    return render(request, 'portal/teacher_dashboard.html', {'teacher': request.user})

@login_required
@teacher_required
def teacher_assignments(request):
    user = request.user
    assignments = Assignment.objects.filter(teacher=user).order_by('-due_date')
    classrooms = Classroom.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        due_date = request.POST.get('due_date')
        classroom_name = request.POST.get('classroom')

        # Validate fields
        errors = []
        if not title:
            errors.append("Title is required.")
        if not due_date:
            errors.append("Due date is required.")
        if not classroom_name:
            errors.append("Please select a classroom.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            classroom = get_object_or_404(Classroom, name=classroom_name)

            Assignment.objects.create(
                teacher=user,
                title=title,
                description=description,
                due_date=due_date,
                classroom=classroom
            )
            messages.success(request, 'Assignment created successfully!')
            return redirect('teacher_assignments')

    return render(request, 'portal/teacher_assignments.html', {
        'assignments': assignments,
        'classrooms': classrooms
    })

@login_required
@teacher_required
def teacher_submissions(request):
    submissions = Submission.objects.filter(assignment__teacher=request.user)
    return render(request, 'portal/teacher_submissions.html', {'submissions': submissions})

@login_required
@teacher_required
def grade_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id, assignment__teacher=request.user)

    if request.method == 'POST':
        try:
            score = float(request.POST.get('score'))
            total_marks = float(request.POST.get('total_marks'))
        except (ValueError, TypeError):
            messages.error(request, 'Enter valid numeric values for score and total marks.')
            return redirect('teacher_submissions')

        feedback = request.POST.get('feedback', '')

        submission.score = score
        submission.total_marks = total_marks
        submission.feedback = feedback
        submission.graded = True
        submission.save()

        Grade.objects.update_or_create(
            student=submission.student,
            assignment=submission.assignment,
            defaults={
                'score': score,
                'total_marks': total_marks,
                'feedback': feedback
            }
        )

        messages.success(request, 'Submission graded successfully.')
        return redirect('teacher_submissions')

    return render(request, 'portal/grade_submission.html', {'submission': submission})

@login_required
@teacher_required
def teacher_resources(request):
    classrooms = Classroom.objects.all()  # Or filter by teacher if needed

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        subject = request.POST.get('subject')
        classroom_name = request.POST.get('classroom')
        uploaded_file = request.FILES.get('file')

        try:
            classroom = Classroom.objects.get(name=classroom_name)
        except Classroom.DoesNotExist:
            messages.error(request, "Selected classroom does not exist.")
            return redirect('teacher_resources')

        Resource.objects.create(
            title=title,
            description=description,
            subject=subject,
            classroom=classroom,
            file=uploaded_file,
            created_by=request.user
        )
        messages.success(request, "Resource uploaded successfully.")
        return redirect('teacher_resources')

    resources = Resource.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'portal/teacher_resources.html', {
        'resources': resources,
        'classrooms': classrooms
    })

@login_required
@teacher_required
def edit_teacher_profile(request):
    user = request.user
    teacher = get_object_or_404(Teacher, user=user)

    if request.method == "POST":
        # Update User model fields
        user.first_name = request.POST.get("first_name")
        user.last_name = request.POST.get("last_name")
        user.email = request.POST.get("email")

        # Update Teacher model fields
        teacher.phone = request.POST.get("phone")
        teacher.subject = request.POST.get("subject")
        teacher.gender = request.POST.get("gender")

        if "profile_picture" in request.FILES:
            teacher.profile_picture = request.FILES["profile_picture"]

        # Save both
        user.save()
        teacher.save()

        messages.success(request, "Profile updated successfully.")
        return redirect("teacher_profile")

    return render(request, "portal/edit_teacher_profile.html", {"teacher": teacher})

@login_required
@teacher_required
def edit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id, teacher=request.user)
    if request.method == 'POST':
        assignment.title = request.POST.get('title')
        assignment.description = request.POST.get('description')
        assignment.due_date = request.POST.get('due_date')
        assignment.save()
        messages.success(request, 'Assignment updated successfully.')
        return redirect('teacher_assignments')
    return render(request, 'portal/edit_assignment.html', {'assignment': assignment})

@login_required
@teacher_required
def delete_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id, teacher=request.user)
    if request.method == 'POST':
        assignment.delete()
        messages.success(request, 'Assignment deleted successfully.')
        return redirect('teacher_assignments')
    return render(request, 'portal/delete_assignment.html', {'assignment': assignment})

@login_required
def teacher_profile(request):
    teacher = get_object_or_404(Teacher, user=request.user)
    return render(request, 'portal/teacher_profile.html', {'teacher': teacher})

@login_required
@teacher_required
def teacher_grades(request):
    teacher = request.user
    classroom = teacher.classroom
    assignments = Assignment.objects.filter(teacher=teacher)
    submissions = Submission.objects.filter(assignment__in=assignments)
    return render(request, 'portal/teacher_grades.html', {
        'submissions': submissions,
    })

@login_required
def edit_student_grade(request, grade_id):
    # grade_id corresponds to submission id
    submission = get_object_or_404(Submission, id=grade_id)

    if request.method == 'POST':
        submission.score = request.POST.get('score') or 0
        submission.total_marks = request.POST.get('total_marks') or 0
        submission.feedback = request.POST.get('feedback') or ''
        submission.graded = True
        submission.save()
        return redirect('teacher_submissions')  # adjust if needed

    return render(request, 'portal/edit_student_grades.html', {
        'submission': submission
    })

BEHAVIOURAL_SKILLS = [
    "Punctuality", "Neatness", "Attentiveness", "Social Development", 
    "Assignment", "Class Participation", "Perseverance",
    "Responsibility", "Politeness", "Honesty", "Sport & Games",
    "Industry", "Club Participation", "Psychomotor"
]

@login_required
@teacher_required
def teacher_upload_grades(request):
    students = User.objects.filter(role='student')
    selected_classroom = request.GET.get('classroom')
    if selected_classroom:
        students = students.filter(classroom__name=selected_classroom)

    # Build student_grades dictionary
    grade_reports = GradeReport.objects.filter(student__in=students)
    if selected_classroom:
        grade_reports = grade_reports.filter(classroom__name=selected_classroom)

    student_grades = {}
    for report in grade_reports.prefetch_related('subject_grades','behavioural_skills').select_related('student'):
        student = report.student
        if student not in student_grades:
            student_grades[student] = []
        student_grades[student].extend(report.subject_grades.all())

    if request.method == 'POST':
        student_username = request.POST.get('student_username')
        subject = request.POST.get('subject')
        term = request.POST.get('term')
        session = request.POST.get('session')
        classroom_name = request.POST.get('classroom')

        if not all([student_username, subject, term, session, classroom_name]):
            messages.error(request, "Please fill in all required fields.")
            return redirect('teacher_upload_grades')

        student = get_object_or_404(User, username=student_username, role='student')
        classroom = get_object_or_404(Classroom, name=classroom_name)

        grade_report, created = GradeReport.objects.get_or_create(
            student=student, classroom=classroom, term=term, session=session
        )

        # Helpers
        def to_int(val): 
            try: return int(val)
            except: return None
        def to_float(val):
            try: return float(val)
            except: return None

        # SubjectGrade fields
        first_test = to_int(request.POST.get('first_test'))
        second_test = to_int(request.POST.get('second_test'))
        exam = to_int(request.POST.get('exam'))
        manual_total = to_int(request.POST.get('manual_total'))
        manual_grade = request.POST.get('manual_grade', '').strip()
        grade_comment = request.POST.get('grade_comment', '').strip()
        first_term_score = to_int(request.POST.get('first_term_score'))
        second_term_score = to_int(request.POST.get('second_term_score'))
        average_score = to_float(request.POST.get('average_score'))

        # Overall report fields
        total_available_score = to_int(request.POST.get('total_available_score'))
        overall_score = to_int(request.POST.get('overall_score'))
        overall_average = to_float(request.POST.get('overall_average'))
        overall_position = request.POST.get('overall_position','').strip()
        teacher_comment = request.POST.get('teacher_comment','').strip()
        admin_comment_report = request.POST.get('admin_comment_report','').strip()
        next_term_date_str = request.POST.get('next_term_date')
        next_term_date = None
        if next_term_date_str:
            try: next_term_date = datetime.strptime(next_term_date_str, '%Y-%m-%d').date()
            except: pass

        # Update GradeReport
        if total_available_score is not None: grade_report.total_available_score = total_available_score
        if overall_score is not None: grade_report.overall_score = overall_score
        if overall_average is not None: grade_report.overall_average = overall_average
        if overall_position: grade_report.overall_position = overall_position
        if teacher_comment: grade_report.teacher_comment = teacher_comment
        grade_report.admin_comment_report = admin_comment_report
        grade_report.date_uploaded = timezone.now()
        if next_term_date: grade_report.next_term_date = next_term_date
        grade_report.save()

        # Create or update SubjectGrade
        grade, created = SubjectGrade.objects.get_or_create(
            report=grade_report, subject=subject,
            defaults={
                'first_test': first_test, 'second_test': second_test, 'exam': exam,
                'manual_total': manual_total, 'manual_grade': manual_grade,
                'grade_comment': grade_comment, 'first_term_score': first_term_score,
                'second_term_score': second_term_score, 'average_score': average_score
            }
        )
        if not created:
            grade.first_test = first_test
            grade.second_test = second_test
            grade.exam = exam
            grade.manual_total = manual_total
            grade.manual_grade = manual_grade
            grade.grade_comment = grade_comment
            grade.first_term_score = first_term_score
            grade.second_term_score = second_term_score
            grade.average_score = average_score
            grade.save()

        # Behavioural skills
        for skill in BEHAVIOURAL_SKILLS:
            key_name = f'beh_{skill.replace(" ","_")}'
            rating = request.POST.get(key_name)
            if rating:
                BehaviouralSkill.objects.update_or_create(
                    student=student,
                    report=grade_report,
                    skill_name=skill,
                    defaults={'rating': int(rating)}
                )

        messages.success(request,"Grades uploaded successfully.")
        return redirect('teacher_upload_grades')

    classrooms = Classroom.objects.all()
    return render(request,'portal/teacher_upload_grades.html',{
        'students': students,
        'student_grades': student_grades,
        'selected_classroom': selected_classroom,
        'classrooms': classrooms,
        'behavioural_skills': BEHAVIOURAL_SKILLS
    })

@login_required
def edit_grade(request, grade_id):
    grade = get_object_or_404(SubjectGrade, id=grade_id)
    report = grade.report  # Linked GradeReport

    def parse_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def parse_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    if request.method == 'POST':
        # SUBJECT GRADE updates
        grade.subject = request.POST.get('subject', grade.subject)
        grade.first_test = parse_int(request.POST.get('first_test'))
        grade.second_test = parse_int(request.POST.get('second_test'))
        grade.exam = parse_int(request.POST.get('exam'))
        grade.manual_total = parse_int(request.POST.get('manual_total'))
        grade.manual_grade = request.POST.get('manual_grade', '').strip()
        grade.grade_comment = request.POST.get('grade_comment', '').strip()
        grade.first_term_score = parse_int(request.POST.get('first_term_score'))
        grade.second_term_score = parse_int(request.POST.get('second_term_score'))
        grade.average_score = parse_float(request.POST.get('average_score'))
        grade.term = request.POST.get('term') or grade.term
        grade.session = request.POST.get('session') or grade.session
        grade.comment = request.POST.get('comment', '').strip()
        grade.admin_comment = request.POST.get('admin_comment', '').strip()
        grade.save()

        # REPORT updates
        report.total_available_score = parse_int(request.POST.get('total_available_score')) or report.total_available_score
        report.overall_score = parse_int(request.POST.get('overall_score')) or report.overall_score
        report.overall_average = parse_float(request.POST.get('overall_average')) or report.overall_average
        report.overall_position = request.POST.get('overall_position', report.overall_position).strip()
        report.teacher_comment = request.POST.get('teacher_comment', report.teacher_comment).strip()
        report.admin_comment_report = request.POST.get('admin_comment_report', report.admin_comment_report).strip()

        next_term_date_str = request.POST.get('next_term_date')
        if next_term_date_str:
            try:
                report.next_term_date = datetime.strptime(next_term_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        report.date_uploaded = timezone.now()
        report.save()

        # BEHAVIOURAL SKILLS updates
        for skill in BEHAVIOURAL_SKILLS:
            key_name = f'beh_{skill.replace(" ", "_")}'
            rating = request.POST.get(key_name)
            if rating:
                BehaviouralSkill.objects.update_or_create(
                    student=report.student,
                    report=report,
                    skill_name=skill,
                    defaults={'rating': int(rating)}
                )

        messages.success(request, "Grade and behavioural skills updated successfully.")
        return redirect('teacher_upload_grades')

    # Prepare existing behavioural skill ratings for the form
    skills_data = {}
    for skill in BEHAVIOURAL_SKILLS:
        existing = report.behavioural_skills.filter(skill_name=skill).first()
        skills_data[skill] = existing.rating if existing else None

    context = {
        'grade': grade,
        'report': report,
        'behavioural_skills': BEHAVIOURAL_SKILLS,
        'skills_data': skills_data,
    }
    return render(request, 'portal/edit_grade.html', context)

# --- Admin Views ---
@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        return HttpResponseForbidden("You are not authorized to access this page.")
    return render(request, 'portal/admin_dashboard.html')

@login_required
@user_passes_test(is_admin)
def manage_registration_codes(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        if code:
            if RegistrationCode.objects.filter(code=code).exists():
                messages.error(request, "This code already exists.")
            else:
                RegistrationCode.objects.create(code=code)
                messages.success(request, f"Registration code '{code}' added successfully.")
        return redirect('manage_registration_codes')

    registration_codes = RegistrationCode.objects.all().order_by('-created_at')
    return render(request, 'portal/manage_registration_codes.html', {'registration_codes': registration_codes})

@login_required
@user_passes_test(is_admin)
def delete_registration_code(request, code_id):
    if request.method == 'POST':
        code = get_object_or_404(RegistrationCode, id=code_id)
        code.delete()
        messages.success(request, f"Registration code '{code.code}' deleted.")
    return redirect('manage_registration_codes')

@login_required
@user_passes_test(is_admin)
def create_announcement(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('manage_announcements')
    else:
        form = AnnouncementForm()
    return render(request, 'portal/create_announcement.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def manage_announcements(request):
    announcements = Announcement.objects.all().order_by('-created_at')
    return render(request, 'portal/manage_announcements.html', {'announcements': announcements})

@login_required
@user_passes_test(is_admin)
def edit_announcement(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, "Announcement updated.")
            return redirect('manage_announcements')
    else:
        form = AnnouncementForm(instance=announcement)
    return render(request, 'portal/edit_announcement.html', {'form': form, 'announcement': announcement})

@login_required
@user_passes_test(is_admin)
def delete_announcement(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    if request.method == 'POST':
        announcement.delete()
        return redirect('manage_announcements')
    return render(request, 'portal/delete_announcement.html', {'announcement': announcement})

@login_required
@user_passes_test(is_admin)
def admin_resources(request):
    resources = Resource.objects.all().order_by('-created_at')
    return render(request, 'portal/admin_resources.html', {'resources': resources})

@login_required
@user_passes_test(is_admin)
def add_resource(request):
    classrooms = Classroom.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        subject = request.POST.get('subject')
        classroom_name = request.POST.get('classroom')
        uploaded_file = request.FILES.get('file')

        if not all([title, subject, classroom_name, uploaded_file]):
            messages.error(request, "All fields are required.")
            return redirect('add_resource')

        try:
            classroom = Classroom.objects.get(name=classroom_name)
        except Classroom.DoesNotExist:
            messages.error(request, "Selected classroom does not exist.")
            return redirect('add_resource')

        Resource.objects.create(
            title=title,
            subject=subject,
            classroom=classroom,
            file=uploaded_file,
            created_by=request.user
        )
        messages.success(request, "Resource uploaded successfully.")
        return redirect('admin_resources')

    return render(request, 'portal/add_resource.html', {
        'classrooms': classrooms
    })

@login_required
@user_passes_test(is_admin)
def edit_resource(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES, instance=resource)
        if form.is_valid():
            form.save()
            return redirect('admin_resources')
    else:
        form = ResourceForm(instance=resource)
    return render(request, 'portal/edit_resource.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def delete_resource(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)
    if request.method == 'POST':
        resource.delete()
        return redirect('admin_resources')
    return render(request, 'portal/delete_resource.html', {'resource': resource})

def generate_time_slots(start="08:00", end="16:00", interval=30):
    start_time = datetime.datetime.strptime(start, "%H:%M")
    end_time = datetime.datetime.strptime(end, "%H:%M")
    slots = []
    while start_time <= end_time:
        label = start_time.strftime("%H:%M")
        slots.append(label)
        start_time += timedelta(minutes=interval)
    return slots

@login_required
@user_passes_test(is_admin)
def manage_timetables(request):
    classrooms = Classroom.objects.all()
    selected_class = request.GET.get('classroom')

    if selected_class:
        timetable_qs = Timetable.objects.filter(classroom__name=selected_class)
    else:
        timetable_qs = Timetable.objects.all()

    timetable_data = {}
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    # Group by classroom
    for classroom in classrooms:
        periods = timetable_qs.filter(classroom=classroom).order_by('day', 'start_time')
        if not periods:
            continue

        # Build time slots
        time_slots = sorted(set(
            f"{p.start_time.strftime('%H:%M')} - {p.end_time.strftime('%H:%M')}"
            for p in periods
        ))

        # Initialize empty grid
        grid = {day: ['' for _ in time_slots] for day in days}

        for p in periods:
            slot_label = f"{p.start_time.strftime('%H:%M')} - {p.end_time.strftime('%H:%M')}"
            if slot_label in time_slots:
                index = time_slots.index(slot_label)
                grid[p.day][index] = f"{p.subject}<br><small>{p.teacher.get_full_name}</small>"

        timetable_data[classroom.name] = {
            'time_slots': time_slots,
            'timetable': grid
        }

    return render(request, 'portal/admin_timetables.html', {
        'classrooms': classrooms,
        'selected_class': selected_class,
        'timetable_data': timetable_data,
        'days': days,
        'current_day': now().strftime("%A")
    })



def add_timetable_period(request):
    if request.method == 'POST':
        classroom_name = request.POST.get('classroom')
        subject = request.POST.get('subject')
        day = request.POST.get('day')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        teacher_username = request.POST.get('teacher')

        classroom = get_object_or_404(Classroom, name=classroom_name)
        teacher = get_object_or_404(User, username=teacher_username, role='teacher')

        Timetable.objects.create(
            classroom=classroom,
            subject=subject,
            day=day,
            start_time=start_time,
            end_time=end_time,
            teacher=teacher
        )
        messages.success(request, 'Timetable period added successfully.')
        return redirect('manage_timetables')

    classrooms = Classroom.objects.all()
    teachers = User.objects.filter(role='teacher')
    return render(request, 'portal/add_timetable_period.html', {
        'classrooms': classrooms,
        'teachers': teachers
    })

@login_required
@user_passes_test(is_admin)
def admin_manage_grades(request):
    student_id = request.GET.get('student_id')
    students = User.objects.filter(role='student').order_by('last_name', 'first_name')

    if student_id:
        student = get_object_or_404(User, id=student_id)
        
        # Get all reports for the student
        reports = GradeReport.objects.filter(student=student).order_by('-date_uploaded')
        
        if not reports.exists():
            return render(request, 'portal/admin_manage_grades.html', {
                'student_selected': student,
                'no_grades': True,
                'students': students,
            })

        # Get all grades across all reports for this student, ordered by report date & subject
        grades = SubjectGrade.objects.filter(report__in=reports).order_by('report__date_uploaded', 'subject')

        latest_report = reports.first()  # For summary data

        return render(request, 'portal/admin_manage_grades.html', {
            'student_selected': student,
            'grades': grades,
            'reports': reports,
            'report': latest_report,  # latest report for summary
            'students': students,
        })

    else:
        # All grades (filterable list)
        grades = SubjectGrade.objects.select_related('report__student', 'report').all()

        student_query = request.GET.get('student')
        term_query = request.GET.get('term')
        session_query = request.GET.get('session')

        if student_query:
            grades = grades.filter(
                Q(report__student__first_name__icontains=student_query) |
                Q(report__student__last_name__icontains=student_query) |
                Q(report__student__username__icontains=student_query)
            )
        if term_query:
            grades = grades.filter(report__term=term_query)
        if session_query:
            grades = grades.filter(report__session__icontains=session_query)

        grades = grades.order_by('report__student__last_name', 'report__student__first_name', 'subject')

        return render(request, 'portal/admin_manage_grades.html', {
            'grades_list': grades,
            'students': students,
        })

@login_required
def delete_final_grade(request, grade_id):
    grade = get_object_or_404(SubjectGrade, id=grade_id)

    if request.method == 'POST':
        grade.delete()
        messages.success(request, "Grade deleted successfully.")
        return redirect('teacher_upload_grades')

    messages.error(request, "Invalid request method.")
    return redirect('teacher_upload_grades')

@login_required
def delete_student_grade(request, grade_id):
    grade = get_object_or_404(SubjectGrade, id=grade_id)
    grade.delete()
    messages.success(request, "Grade deleted successfully.")
    return redirect('admin_manage_grades')



@login_required
@user_passes_test(is_admin)
def admin_download_grade_report_pdf(request, student_id):
    # Get the student object
    student = User.objects.filter(id=student_id, role='student').first()
    if not student:
        return HttpResponse("Student not found.", status=404)

    # Get all reports and related subject grades for this student
    reports = GradeReport.objects.filter(student=student)
    grades = SubjectGrade.objects.filter(report__in=reports).order_by('report__term', 'subject')

    latest_report = reports.order_by('-date_uploaded').first()

    if not latest_report:
        return HttpResponse("No report found.", status=404)

    # Encode logo for PDF header
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'portal', 'images', 'logo.jpg')
    logo_data_uri = ''
    if os.path.exists(logo_path):
        mime_type, _ = mimetypes.guess_type(logo_path)
        with open(logo_path, "rb") as image_file:
            encoded_logo = base64.b64encode(image_file.read()).decode('utf-8')
            logo_data_uri = f"data:{mime_type};base64,{encoded_logo}"

    context = {
        'grades': grades,
        'reports': reports,
        'report': latest_report,
        'student_name': student.get_full_name() or student.username,
        'logo_url': logo_data_uri,
    }

    template = get_template('portal/grades_pdf.html')
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{student.username}_report.pdf"'

    from io import BytesIO
    result = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=result)

    if pisa_status.err:
        return HttpResponse('Error generating PDF. <pre>' + html + '</pre>')

    response.write(result.getvalue())
    return response
