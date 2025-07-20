# Django core
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.template.loader import get_template
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import now
from django.utils.dateparse import parse_date
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import SubjectGrade, Classroom

# Models
from .models import (
    User, Assignment, Grade, SubjectGrade, Resource,
    Announcement, Timetable, Submission, Teacher, Classroom, RegistrationCode
)

# Forms
from .forms import UserEditForm, ResourceForm, AnnouncementForm

# Decorators
from .decorators import student_required, teacher_required

# Third-party
from xhtml2pdf import pisa

# Python standard
from collections import defaultdict
from datetime import datetime, time, timedelta
import os
from django.db.models import Q

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
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        gender = request.POST.get('gender')
        classroom_name = request.POST.get('classroom')
        reg_code_input = request.POST.get('registration_code')  # new input for code

        if not classroom_name:
            messages.error(request, 'Please select a classroom.')
            return render(request, 'portal/student_registration.html', {'classrooms': classrooms})

        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'portal/student_registration.html', {'classrooms': classrooms})

        if not reg_code_input:
            messages.error(request, 'Registration code is required.')
            return render(request, 'portal/student_registration.html', {'classrooms': classrooms})

        # Validate registration code
        try:
            reg_code_obj = RegistrationCode.objects.get(code=reg_code_input, is_active=True)
        except RegistrationCode.DoesNotExist:
            messages.error(request, 'Invalid or already used registration code.')
            return render(request, 'portal/student_registration.html', {'classrooms': classrooms})

        classroom = get_object_or_404(Classroom, name=classroom_name)

        if not username or not password1:
            messages.error(request, 'Username and password are required.')
            return render(request, 'portal/student_registration.html', {'classrooms': classrooms})

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'portal/student_registration.html', {'classrooms': classrooms})

        # Create the user
        user = User.objects.create_user(
            username=username,
            password=password1,  # hashed automatically
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        user.gender = gender
        user.role = 'student'
        user.classroom = classroom
        user.save()

        # Mark registration code as used
        reg_code_obj.is_active = False
        reg_code_obj.used_by = user
        reg_code_obj.save()

        messages.success(request, 'Registration successful. You can now login.')
        return redirect('login')

    return render(request, 'portal/student_registration.html', {'classrooms': classrooms})

# --- Teacher Registration ---
def register_teacher(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        phone = request.POST.get('phone')
        profile_picture = request.FILES.get('profile_picture')

        if not username or not password1:
            messages.error(request, 'Username and password are required.')
            return redirect('teacher_register')

        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return redirect('teacher_register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        else:
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

# --- Student Views ---
@login_required
@student_required
def student_dashboard(request):
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
def student_grades(request):
    grades = Grade.objects.filter(student=request.user)
    return render(request, 'portal/student_grades.html', {'grades': grades})

@login_required
@student_required
def student_resources(request):
    resources = Resource.objects.all().order_by('-uploaded_at')
    return render(request, 'portal/student_resources.html', {'resources': resources})

@login_required
@student_required
def student_announcements(request):
    announcements = Announcement.objects.order_by('-created_at')
    return render(request, 'portal/student_announcements.html', {'announcements': announcements})

@login_required
def student_details(request):
    return render(request, 'portal/student_details.html', {'student': request.user})

@login_required
@student_required
def edit_student_profile(request):
    user = request.user
    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('student_details')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'portal/edit_student_profile.html', {'form': form})

@login_required
@student_required
def student_submissions(request):
    submissions = Submission.objects.filter(student=request.user).order_by('-submitted_at')
    return render(request, 'portal/student_submissions.html', {'submissions': submissions})

@login_required
@student_required
def submit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            messages.error(request, 'No file uploaded.')
            return redirect('submit_assignment', assignment_id=assignment.id)

        Submission.objects.create(
            student=request.user,
            assignment=assignment,
            file=uploaded_file
        )
        messages.success(request, 'Assignment submitted successfully.')
        return redirect('student_assignments')
    return render(request, 'portal/submit_assignment.html', {'assignment': assignment})


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
    assignments = Assignment.objects.filter(teacher=user)

    # This is what is probably missing:
    classrooms = Classroom.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        due_date = request.POST.get('due_date')
        classroom_name = request.POST.get('classroom')

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
            messages.error(request, 'Please enter valid numeric values for score and total marks.')
            return redirect('teacher_submissions')

        feedback = request.POST.get('feedback', '')

        submission.score = score
        submission.feedback = feedback
        submission.total_marks = total_marks
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
    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('teacher_dashboard')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'portal/edit_teacher_profile.html', {'form': form})

@login_required
@teacher_required
def teacher_timetable(request):
    teacher = request.user
    current_day = now().strftime("%A")

    periods = Timetable.objects.filter(teacher=teacher).select_related('classroom')
    timetable_data = {}
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    if not periods.exists():
        messages.info(request, "No timetable assigned yet.")
    else:
        class_names = periods.values_list('classroom__name', flat=True).distinct()

        for class_name in class_names:
            class_periods = periods.filter(classroom__name=class_name).order_by('day', 'start_time')

            # Create unique time slots (sorted)
            time_slots = sorted(set(
                f"{p.start_time.strftime('%H:%M')} - {p.end_time.strftime('%H:%M')}"
                for p in class_periods
            ))

            # Build grid: {day: [subjects for each time slot]}
            grid = {day: ['' for _ in time_slots] for day in days}
            for p in class_periods:
                time_label = f"{p.start_time.strftime('%H:%M')} - {p.end_time.strftime('%H:%M')}"
                col_index = time_slots.index(time_label)
                grid[p.day][col_index] = f"{p.subject}<br><small>{p.classroom.name}</small>"

            timetable_data[class_name] = {
                'time_slots': time_slots,
                'timetable': grid
            }

    return render(request, 'portal/teacher_timetable.html', {
        'timetable_data': timetable_data,
        'current_day': current_day,
        'days': days
    })

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
@teacher_required
@user_passes_test(is_admin)
def edit_student_grade(request, grade_id):
    # Here grade_id corresponds to submission id
    submission = get_object_or_404(Submission, id=grade_id)

    if request.method == 'POST':
        submission.score = request.POST.get('score') or 0
        submission.total_marks = request.POST.get('total_marks') or 0
        submission.feedback = request.POST.get('feedback') or ''
        submission.graded = True
        submission.save()
        return redirect('teacher_submissions')  # or admin_manage_grades or wherever you want

    return render(request, 'portal/edit_student_grades.html', {'submission': submission})

@login_required
@teacher_required
def teacher_upload_grades(request):
    students = User.objects.filter(role='student')
    selected_classroom = request.GET.get('classroom')

    if selected_classroom:
        students = students.filter(classroom__name=selected_classroom)

    all_grades = SubjectGrade.objects.filter(student__in=students)
    if selected_classroom:
        all_grades = all_grades.filter(student__classroom__name=selected_classroom)

    # Organize grades by student
    student_grades = {}
    for grade in all_grades.select_related('student'):
        student = grade.student
        if student not in student_grades:
            student_grades[student] = []
        student_grades[student].append(grade)

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

        def to_int(val):
            try:
                return int(val)
            except (TypeError, ValueError):
                return None

        def to_float(val):
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

        first_test = to_int(request.POST.get('first_test'))
        second_test = to_int(request.POST.get('second_test'))
        exam = to_int(request.POST.get('exam'))
        manual_total = to_int(request.POST.get('manual_total'))
        manual_grade = request.POST.get('manual_grade', '').strip()

        first_term_score = to_int(request.POST.get('first_term_score'))
        second_term_score = to_int(request.POST.get('second_term_score'))
        average_score = to_float(request.POST.get('average_score'))

        grade_comment = request.POST.get('grade_comment')
        comment = request.POST.get('comment')
        admin_comment = request.POST.get('admin_comment')
        teacher_comment = request.POST.get('teacher_comment')
        next_term_date = parse_date(request.POST.get('next_term_date')) if request.POST.get('next_term_date') else None

        # Create or update SubjectGrade
        grade, created = SubjectGrade.objects.get_or_create(
            student=student,
            subject=subject,
            term=term,
            session=session,
            defaults={
                'first_test': first_test,
                'second_test': second_test,
                'exam': exam,
                'manual_total': manual_total,
                'manual_grade': manual_grade,
                'first_term_score': first_term_score,
                'second_term_score': second_term_score,
                'average_score': average_score,
                'grade_comment': grade_comment,
                'comment': comment,
                'admin_comment': admin_comment,
                'next_term_date': next_term_date,
            }
        )

        if not created:
            grade.first_test = first_test
            grade.second_test = second_test
            grade.exam = exam
            grade.manual_total = manual_total
            grade.manual_grade = manual_grade
            grade.first_term_score = first_term_score
            grade.second_term_score = second_term_score
            grade.average_score = average_score
            grade.grade_comment = grade_comment
            grade.comment = comment
            grade.admin_comment = admin_comment
            grade.next_term_date = next_term_date
            grade.save()
            messages.success(request, "Grade updated successfully.")
        else:
            messages.success(request, "Grade uploaded successfully.")

        return redirect('teacher_upload_grades')

    classrooms = Classroom.objects.all()
    return render(request, 'portal/teacher_upload_grades.html', {
        'students': students,
        'student_grades': student_grades,
        'selected_classroom': selected_classroom,
        'classrooms': classrooms,
    })


@login_required
@user_passes_test(is_admin)
def admin_manage_grades(request):
    grades = SubjectGrade.objects.all().select_related('student', 'teacher')

    student_query = request.GET.get('student')
    term_query = request.GET.get('term')
    session_query = request.GET.get('session')

    if student_query:
        grades = grades.filter(
            Q(student__first_name__icontains=student_query) |
            Q(student__last_name__icontains=student_query) |
            Q(student__username__icontains=student_query)
        )
    if term_query:
        grades = grades.filter(term=term_query)
    if session_query:
        grades = grades.filter(session__icontains=session_query)

    grades = grades.order_by('student__last_name', 'subject')
    return render(request, 'portal/admin_manage_grades.html', {'grades': grades})

@login_required
@student_required
def student_grades_view(request):
    grades = SubjectGrade.objects.filter(student=request.user).order_by('subject')

    # Fetch these from your database or set default if missing
    # For example, assuming you store them in a Report model or in user profile
    total_available_score = request.user.profile.total_available_score if hasattr(request.user, 'profile') else None
    overall_score = request.user.profile.overall_score if hasattr(request.user, 'profile') else None
    overall_average = request.user.profile.overall_average if hasattr(request.user, 'profile') else None
    overall_position = request.user.profile.overall_position if hasattr(request.user, 'profile') else None
    teacher_comment = request.user.profile.teacher_comment if hasattr(request.user, 'profile') else ''
    report_date = request.user.profile.report_date if hasattr(request.user, 'profile') else ''
    admin_comment = request.user.profile.admin_comment if hasattr(request.user, 'profile') else ''
    next_term_date = request.user.profile.next_term_date if hasattr(request.user, 'profile') else ''

    context = {
        'grades': grades,
        'student_name': request.user.get_full_name() or request.user.username,
        'total_available_score': total_available_score,
        'overall_score': overall_score,
        'overall_average': overall_average,
        'overall_position': overall_position,
        'teacher_comment': teacher_comment,
        'report_date': report_date,
        'admin_comment': admin_comment,
        'next_term_date': next_term_date,
    }
    return render(request, 'portal/student_test_examination_grades.html', context)


@login_required
def edit_grade(request, grade_id):
    grade = get_object_or_404(SubjectGrade, id=grade_id)

    if request.method == 'POST':
        # Grade-level fields
        grade.subject = request.POST.get('subject')
        grade.first_test = int(request.POST.get('first_test') or 0)
        grade.second_test = int(request.POST.get('second_test') or 0)
        grade.exam = int(request.POST.get('exam') or 0)
        grade.term = request.POST.get('term')
        grade.session = request.POST.get('session')
        grade.comment = request.POST.get('comment')
        grade.admin_comment = request.POST.get('admin_comment')
        grade.grade_comment = request.POST.get('grade_comment')

        # Optional term scores and average
        grade.first_term_score = int(request.POST.get('first_term_score') or 0)
        grade.second_term_score = int(request.POST.get('second_term_score') or 0)
        grade.average_score = float(request.POST.get('average_score') or 0)

        # Manual override (optional)
        manual_total = request.POST.get('manual_total')
        manual_grade = request.POST.get('manual_grade')

        grade.manual_total = int(manual_total) if manual_total else (
            grade.first_test + grade.second_test + grade.exam
        )

        grade.manual_grade = manual_grade if manual_grade else (
            'A++' if grade.manual_total >= 90 else
            'A+' if grade.manual_total >= 80 else
            'B++' if grade.manual_total >= 70 else
            'B+' if grade.manual_total >= 60 else
            'C' if grade.manual_total >= 50 else
            'D' if grade.manual_total >= 40 else 'F'
        )

        # Report-level fields (stored in SubjectGrade now)
        grade.total_available_score = int(request.POST.get('total_available_score') or 0)
        grade.overall_score = int(request.POST.get('overall_score') or 0)
        grade.overall_average = float(request.POST.get('overall_average') or 0)
        grade.overall_position = request.POST.get('overall_position')
        grade.teacher_comment = request.POST.get('teacher_comment')
        grade.admin_comment_report = request.POST.get('admin_comment_report')
        grade.next_term_date = request.POST.get('next_term_date') or None

        grade.save()
        messages.success(request, 'Grade and report info updated successfully.')
        return redirect('teacher_upload_grades')

    return render(request, 'portal/edit_grade.html', {
        'grade': grade,
        'report': grade,  # since report fields are in SubjectGrade now
    })

@login_required
@user_passes_test(is_admin)
def delete_student_grade(request, grade_id):
    grade = get_object_or_404(Grade, id=grade_id)
    grade.delete()
    messages.success(request, "Grade deleted successfully.")
    return redirect('admin_manage_grades')

@login_required
def download_grade_report_pdf(request):
    student = request.user
    term = "First Term"
    session = "2024/2025"

    classroom = student.classroom

    # Get subject grades
    subject_grades = SubjectGrade.objects.filter(
        student=student,
        term=term,
        session=session
    )

    # Pick one SubjectGrade entry to pull report-level data
    report_grade = subject_grades.first()

    context = {
        'student': student,
        'classroom': classroom,
        'term': term,
        'session': session,
        'subject_grades': subject_grades,
        'total_available_score': report_grade.manual_total if report_grade else None,
        'overall_score': report_grade.manual_total if report_grade else None,
        'overall_average': report_grade.average_score if report_grade else None,
        'overall_position': report_grade.manual_grade if report_grade else None,
        'teacher_comment': report_grade.teacher_comment if report_grade and hasattr(report_grade, 'teacher_comment') else "No comment",
        'admin_comment': report_grade.admin_comment if report_grade else "No comment",
        'next_term_date': report_grade.next_term_date if report_grade else None,
    }

    template = get_template('portal/grades_pdf.html')
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{student.username}_report.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors generating the PDF <pre>' + html + '</pre>')
    return response
