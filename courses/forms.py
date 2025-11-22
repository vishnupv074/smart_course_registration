from django import forms
from .models import Course, Section

class CourseForm(forms.ModelForm):
    """Form for creating and editing courses"""
    
    class Meta:
        model = Course
        fields = ['code', 'title', 'description', 'credits']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., CS101'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Introduction to Computer Science'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Course description...'}),
            'credits': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
        }

class SectionForm(forms.ModelForm):
    """Form for creating and editing sections"""
    
    # Use CharField with autocomplete instead of ModelChoiceField to avoid loading 100k courses
    course_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter course code (e.g., CS101)',
            'list': 'course-datalist'
        }),
        label='Course Code',
        help_text='Enter the exact course code'
    )
    
    class Meta:
        model = Section
        fields = ['semester', 'capacity', 'room_number', 'schedule']
        widgets = {
            'semester': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Fall 2025'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'e.g., 30'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Room 101'}),
            'schedule': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Mon/Wed 10:00-11:30'}),
        }
    
    def __init__(self, *args, **kwargs):
        """Customize form initialization"""
        super().__init__(*args, **kwargs)
        # If editing, populate course_code from instance
        if self.instance and self.instance.pk and self.instance.course:
            self.fields['course_code'].initial = self.instance.course.code
    
    def clean_course_code(self):
        """Validate that the course code exists"""
        from .models import Course
        code = self.cleaned_data['course_code'].strip()
        try:
            course = Course.objects.get(code=code)
            return course
        except Course.DoesNotExist:
            raise forms.ValidationError(f"Course with code '{code}' does not exist.")
    
    def save(self, commit=True):
        """Override save to set the course from course_code"""
        instance = super().save(commit=False)
        instance.course = self.cleaned_data['course_code']  # This is now a Course object from clean_course_code
        if commit:
            instance.save()
        return instance
