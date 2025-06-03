from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings

# 🏫 Classroom Model
class Classroom(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


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
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students'
    )
    address = models.CharField(max_length=255, default='N/A', blank=True)

    # Parent information
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

    def __str__(self):
        return self.username


# 🔐 Registration Code Model
class RegistrationCode(models.Model):
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    used_by = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.code

    @property
    def used(self):
        return self.used_by is not None


# 📅 Timetable Model
class Timetable(models.Model):
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        default=1,
        help_text="Select the class this timetable belongs to"
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'teacher'},
        null=True,
        blank=True,
        related_name='teacher_timetables'
    )
    subject = models.CharField(max_length=100)
    day = models.CharField(max_length=20)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.subject} - {self.day} ({self.classroom.name})"


# 📝 Assignment Model
class Assignment(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    created_at = models.DateTimeField(default=timezone.now)

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'teacher'},
        related_name='teacher_assignments',
        null=True,
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        limit_choices_to={'role': 'student'},
        related_name='student_assignments'
    )

    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Class this assignment is for (optional if assigned to individual student)"
    )

    def __str__(self):
        return f"{self.title} (Due {self.due_date})"


# 📤 Submission Model
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


# 📊 Grade Model
class Grade(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'}
    )
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    score = models.FloatField()
    total_marks = models.FloatField()
    feedback = models.TextField(blank=True, null=True)
    graded_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.assignment.title} - {self.student.username}"


# 📁 Resource Model
class Resource(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='resources/')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(default=timezone.now)
    subject = models.CharField(max_length=100, blank=True, null=True)

    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Class this resource is for"
    )

    def __str__(self):
        return self.title


# 📢 Announcement Model
class Announcement(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    target_audience = models.CharField(
        max_length=20,
        choices=[
            ('student', 'Student'),
            ('teacher', 'Teacher'),
            ('all', 'All'),
        ],
        default='all'
    )
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Optional – only needed if this announcement is class-specific"
    )

    def __str__(self):
        return self.title


# 👨‍🏫 Teacher Profile Model
class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    subject = models.CharField(max_length=100)
    gender = models.CharField(max_length=50)
    profile_picture = models.ImageField(upload_to='teacher_profiles/', blank=True, null=True)

    def __str__(self):
        return self.user.get_full_name()

class SubjectGrade(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='grades')
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='uploaded_grades')
    subject = models.CharField(max_length=100)
    first_test = models.IntegerField(null=True, blank=True)
    second_test = models.IntegerField(null=True, blank=True)
    exam = models.IntegerField(null=True, blank=True)
    term = models.CharField(max_length=20)
    session = models.CharField(max_length=20)
    comment = models.TextField(blank=True, null=True)
    date_uploaded = models.DateTimeField(auto_now_add=True)

    # New manual override fields
    manual_total = models.PositiveIntegerField(blank=True, null=True)
    manual_grade = models.CharField(max_length=20, blank=True, null=True)

    @property
    def total_score(self):
        # Use manual_total if set, else calculate
        if self.manual_total is not None:
            return self.manual_total
        return (self.first_test or 0) + (self.second_test or 0) + (self.exam or 0)

    def __str__(self):
        return f"{self.student.username} - {self.subject} ({self.term}, {self.session})"