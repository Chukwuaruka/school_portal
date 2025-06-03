from django.contrib import admin
from .models import User
from .models import RegistrationCode
from .models import Teacher

# Register your models here.
admin.site.register(User)

admin.site.register(RegistrationCode)

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'phone')

from django.contrib import admin
from .models import Timetable

@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'subject', 'day', 'start_time', 'end_time', 'teacher')
    list_filter = ('classroom', 'day', 'teacher')
    search_fields = ('subject', 'classroom__name', 'teacher__first_name', 'teacher__last_name')
