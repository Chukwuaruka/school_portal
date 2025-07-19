from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.conf import settings


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
    profile_picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.jpg', blank=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.CharField(max_length=255, default='N/A', blank=True)

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

# 🧮 Subject Grade
class SubjectGrade(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='grades'
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_grades'
    )
    classroom = models.ForeignKey(
        'Classroom',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    subject = models.CharField(max_length=100)
    first_test = models.IntegerField(null=True, blank=True)
    second_test = models.IntegerField(null=True, blank=True)
    exam = models.IntegerField(null=True, blank=True)

    term = models.CharField(max_length=20)
    session = models.CharField(max_length=20)

    comment = models.TextField(blank=True, null=True)
    date_uploaded = models.DateTimeField(auto_now_add=True)

    # Additional Score/Grade Fields
    manual_total = models.PositiveIntegerField(blank=True, null=True)
    manual_grade = models.CharField(max_length=20, blank=True, null=True)
    first_term_score = models.IntegerField(null=True, blank=True)
    second_term_score = models.IntegerField(null=True, blank=True)
    average_score = models.FloatField(null=True, blank=True)
    grade_comment = models.CharField(max_length=255, blank=True, null=True)

    # 🆕 NEW fields for comments and next term
    teacher_comment = models.TextField(blank=True, null=True)
    admin_comment = models.TextField(blank=True, null=True)
    next_term_date = models.DateField(blank=True, null=True)

    @property
    def total_score(self):
        if self.manual_total is not None:
            return self.manual_total
        return (self.first_test or 0) + (self.second_test or 0) + (self.exam or 0)

    def __str__(self):
        return f"{self.student.username} - {self.subject} ({self.term}, {self.session})"



# 📄 Student Report
class StudentReport(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    term = models.CharField(max_length=20)
    session = models.CharField(max_length=20)
    total_available_score = models.IntegerField(null=True, blank=True)
    overall_score = models.IntegerField(null=True, blank=True)
    overall_average = models.FloatField(null=True, blank=True)
    overall_position = models.CharField(max_length=10, blank=True, null=True)
    teacher_comment = models.TextField(blank=True, null=True)
    admin_comment = models.TextField(blank=True, null=True)
    next_term_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'term', 'session']

    def __str__(self):
        return f"{self.student.username} - {self.term} {self.session}"
