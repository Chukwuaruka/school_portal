from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError

# 🏫 Classroom Model
class Classroom(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


# 🔧 Custom User Manager
class CustomUserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, email, password, **extra_fields)


# 🔐 Custom User Model
class User(AbstractUser):
    email = models.EmailField(blank=True, null=True)
    middle_name = models.CharField(max_length=50, default='Not specified', blank=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=50, default='Not specified', blank=True)
    phone = models.CharField(max_length=20, default='Not specified', blank=True)
    profile_picture = models.ImageField(
        upload_to='profile_pics/', 
        default='profile_pics/default.jpg', 
        blank=True
    )
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.CharField(max_length=255, default='N/A', blank=True)

    # ✅ New fields
    nationality = models.CharField(max_length=100, blank=True, null=True)
    state_of_origin = models.CharField(max_length=100, blank=True, null=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # e.g., 170.50 cm
    weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # e.g., 65.25 kg

    # Parent Info
    parent_first_name = models.CharField(max_length=50, blank=True)
    parent_last_name = models.CharField(max_length=50, blank=True)
    parent_phone = models.CharField(max_length=20, blank=True)
    parent_email = models.EmailField(blank=True)
    parent_address = models.TextField(blank=True)

    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')

    objects = CustomUserManager()

    def __str__(self):
        return self.username

# 🔐 Registration Code
class RegistrationCode(models.Model):
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    used_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.code

    @property
    def used(self):
        return self.used_by is not None


# 📅 Timetable
class Timetable(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, default=1)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'}, null=True, blank=True, related_name='teacher_timetables')
    subject = models.CharField(max_length=100)
    day = models.CharField(max_length=20)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.subject} - {self.day} ({self.classroom.name})"


# 📝 Assignment
class Assignment(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    created_at = models.DateTimeField(default=timezone.now)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'}, related_name='teacher_assignments', null=True)
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'}, related_name='student_assignments', null=True, blank=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.title} (Due {self.due_date})"


# 📤 Submission
class Submission(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    file = models.FileField(upload_to='submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)  
    graded = models.BooleanField(default=False)
    feedback = models.TextField(blank=True, null=True)
    score = models.FloatField(null=True, blank=True)
    total_marks = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"

# 📊 Grade
class Grade(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    score = models.FloatField()
    total_marks = models.FloatField()
    feedback = models.TextField(blank=True, null=True)
    graded_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.assignment.title} - {self.student.username}"


# 📁 Resource
class Resource(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='resources/')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(default=timezone.now)
    subject = models.CharField(max_length=100, blank=True, null=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.title


# 📢 Announcement
class Announcement(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    target_audience = models.CharField(
        max_length=20,
        choices=[('student', 'Student'), ('teacher', 'Teacher'), ('all', 'All')],
        default='all'
    )
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.title


# 👨‍🏫 Teacher Profile
class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    subject = models.CharField(max_length=100)
    gender = models.CharField(max_length=50)
    profile_picture = models.ImageField(upload_to='teacher_profiles/', blank=True, null=True)

    def __str__(self):
        return self.user.get_full_name()

class GradeReport(models.Model):
    SESSION_CHOICES = [
        ('2023/2024', '2023/2024'),
        ('2024/2025', '2024/2025'),
        # Add more sessions as needed
    ]
    TERM_CHOICES = [
        ('1st Term', '1st Term'),
        ('2nd Term', '2nd Term'),
        ('3rd Term', '3rd Term'),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,  # allow null for existing data or if student unknown
        blank=True
    )
    classroom = models.ForeignKey('Classroom', on_delete=models.SET_NULL, null=True, blank=True)
    session = models.CharField(max_length=20, choices=SESSION_CHOICES, null=True, blank=True)
    term = models.CharField(max_length=20, choices=TERM_CHOICES, null=True, blank=True)
    date_uploaded = models.DateField(null=True, blank=True)

    total_available_score = models.PositiveIntegerField(null=True, blank=True)
    overall_score = models.PositiveIntegerField(null=True, blank=True)
    overall_average = models.FloatField(null=True, blank=True)
    overall_position = models.CharField(max_length=10, blank=True)

    teacher_comment = models.TextField(blank=True)
    admin_comment_report = models.TextField(blank=True)
    next_term_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.username if self.student else 'Unknown Student'} - {self.term} {self.session}"


class SubjectGrade(models.Model):
    MAX_FIRST_TEST = 20
    MAX_SECOND_TEST = 20
    MAX_EXAM = 60

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    report = models.ForeignKey(
        GradeReport,
        on_delete=models.CASCADE,
        related_name='subject_grades',
        null=True,
        blank=True
    )
    subject = models.CharField(max_length=100, null=False, blank=True)

    first_test = models.PositiveIntegerField(default=0)
    second_test = models.PositiveIntegerField(default=0)
    exam = models.PositiveIntegerField(default=0)

    manual_total = models.PositiveIntegerField(null=True, blank=True)
    manual_grade = models.CharField(max_length=10, blank=True)

    grade_comment = models.TextField(blank=True)

    first_term_score = models.PositiveIntegerField(null=True, blank=True)
    second_term_score = models.PositiveIntegerField(null=True, blank=True)
    average_score = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.username if self.student else 'Unknown Student'} - {self.subject or 'Unknown Subject'}"

    @property
    def total_score(self):
        if self.manual_total is not None:
            return self.manual_total
        return self.first_test + self.second_test + self.exam

    @property
    def grade(self):
        if self.manual_grade:
            return self.manual_grade.upper()
        total = self.total_score
        if total >= 70:
            return 'A'
        elif total >= 60:
            return 'B'
        elif total >= 50:
            return 'C'
        elif total >= 45:
            return 'D'
        else:
            return 'F'

    def clean(self):
        # Validate that test scores are within max limits
        if not (0 <= self.first_test <= self.MAX_FIRST_TEST):
            raise ValidationError({'first_test': f'First Test score must be between 0 and {self.MAX_FIRST_TEST}'})
        if not (0 <= self.second_test <= self.MAX_SECOND_TEST):
            raise ValidationError({'second_test': f'Second Test score must be between 0 and {self.MAX_SECOND_TEST}'})
        if not (0 <= self.exam <= self.MAX_EXAM):
            raise ValidationError({'exam': f'Exam score must be between 0 and {self.MAX_EXAM}'})

        # If manual_total is set, it must not exceed 100
        if self.manual_total is not None and not (0 <= self.manual_total <= 100):
            raise ValidationError({'manual_total': 'Manual total must be between 0 and 100'})

        # Scores cannot be negative
        for field in ['first_term_score', 'second_term_score', 'average_score']:
            val = getattr(self, field)
            if val is not None and val < 0:
                raise ValidationError({field: f'{field.replace("_", " ").capitalize()} cannot be negative.'})

    class Meta:
        ordering = ['subject']