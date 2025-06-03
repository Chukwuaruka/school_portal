from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponseForbidden

from .models import User, Assignment, Grade, Resource, Announcement, Timetable, Submission, Teacher, Classroom
from .forms import UserEditForm, ResourceForm, AnnouncementForm
from .decorators import student_required, teacher_required
from django.utils import timezone
from collections import defaultdict
import datetime
from datetime import time, timedelta
from django.utils.timezone import now
from .models import RegistrationCode
from .models import SubjectGrade


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
    current_day = datetime.datetime.now().strftime("%A")

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
        'class_name': classroom.name,
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
@login_required
def teacher_dashboard(request):
    try:
        teacher = request.user.teacher
    except:
        return redirect('login')
    return render(request, 'portal/teacher_dashboard.html', {'teacher': teacher})

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
def teacher_upload_grades(request):
    students = User.objects.filter(role='student')
    grades = SubjectGrade.objects.filter(teacher=request.user).select_related('student')

    if request.method == 'POST':
        student_username = request.POST.get('student_username')
        subject = request.POST.get('subject')
        term = request.POST.get('term')
        session = request.POST.get('session')
        comment = request.POST.get('comment')

        first_test = request.POST.get('first_test')
        second_test = request.POST.get('second_test')
        exam = request.POST.get('exam')

        # New manual overrides
        manual_total = request.POST.get('manual_total')
        manual_grade = request.POST.get('manual_grade')

        # Convert scores to int if provided, else -
        first_test = int(first_test) if first_test else None 
        second_test = int(second_test) if second_test else None
        exam = int(exam) if exam else None
        manual_total = int(manual_total) if manual_total else None
        manual_grade = manual_grade.strip() if manual_grade else None

        if not all([student_username, subject, term, session]):
            messages.error(request, "All required fields (except scores) must be filled.")
            return redirect('teacher_upload_grades')

        student = get_object_or_404(User, username=student_username, role='student')

        grade, created = SubjectGrade.objects.get_or_create(
            student=student,
            subject=subject,
            term=term,
            session=session,
            defaults={
                'teacher': request.user,
                'first_test': first_test,
                'second_test': second_test,
                'exam': exam,
                'manual_total': manual_total,
                'manual_grade': manual_grade,
                'comment': comment
            }
        )

        if not created:
            # Update existing fields selectively
            if first_test is not None:
                grade.first_test = first_test
            if second_test is not None:
                grade.second_test = second_test
            if exam is not None:
                grade.exam = exam
            grade.manual_total = manual_total  # None or int
            grade.manual_grade = manual_grade  # None or string
            grade.comment = comment or grade.comment
            grade.save()
            messages.success(request, "Grade updated successfully.")
        else:
            messages.success(request, "Grade uploaded successfully.")

        return redirect('teacher_upload_grades')

    return render(request, 'portal/teacher_upload_grades.html', {'students': students, 'grades': grades})

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
    context = {
        'grades': grades,
        'student_name': request.user.get_full_name() or request.user.username,
    }
    return render(request, 'portal/student_test_examination_grades.html', context)

def edit_grade(request, grade_id):
    grade = get_object_or_404(SubjectGrade, id=grade_id)

    if request.method == 'POST':
        subject = request.POST.get('subject')
        first_test = request.POST.get('first_test')
        second_test = request.POST.get('second_test')
        exam = request.POST.get('exam')
        term = request.POST.get('term')
        session = request.POST.get('session')
        comment = request.POST.get('comment')

        # Safely parse values (set to 0 if empty)
        first_test = int(first_test) if first_test else 0
        second_test = int(second_test) if second_test else 0
        exam = int(exam) if exam else 0

        # Compute total
        total = first_test + second_test + exam

        # Compute grade
        if total >= 70:
            grade_letter = 'A'
        elif total >= 60:
            grade_letter = 'B'
        elif total >= 50:
            grade_letter = 'C'
        elif total >= 45:
            grade_letter = 'D'
        elif total >= 40:
            grade_letter = 'E'
        else:
            grade_letter = 'F'

        # Update grade object
        grade.subject = subject
        grade.first_test = first_test
        grade.second_test = second_test
        grade.exam = exam
        grade.manual_total = total       # <-- Use manual_total field
        grade.manual_grade = grade_letter  # <-- Use manual_grade field
        grade.term = term
        grade.session = session
        grade.comment = comment
        grade.save()


        messages.success(request, 'Grade updated successfully.')
        return redirect('teacher_upload_grades')

    return render(request, 'portal/edit_grade.html', {'grade': grade})

@login_required
@user_passes_test(is_admin)
def edit_student_grade(request, grade_id):
    grade = get_object_or_404(SubjectGrade, id=grade_id)

    if request.method == 'POST':
        grade.first_test = request.POST.get('first_test') or None
        grade.second_test = request.POST.get('second_test') or None
        grade.exam = request.POST.get('exam') or None
        grade.comment = request.POST.get('comment')
        grade.save()
        return redirect('admin_manage_grades')

    return render(request, 'portal/edit_student_grade.html', {'grade': grade})
