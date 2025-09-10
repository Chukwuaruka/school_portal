# portal/forms.py

from django import forms
from .models import Announcement
from .models import Resource
from .models import User

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'created_by']  # Adjust based on your model

class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ['title', 'subject', 'file']
