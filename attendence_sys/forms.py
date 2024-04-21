from django.forms import ModelForm
from django import forms
from .models import *

class CreateStudentForm(ModelForm):
    class Meta:
        model = Student
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super(CreateStudentForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

class ExtractStudentForm(ModelForm):
    excel_file = forms.FileField(label='Select Excel File (XLSX, XLS)')

    def clean_excel_file(self):
        excel_file = self.cleaned_data['excel_file']

        # Validate allowed file types (e.g., XLSX, XLS)
        if not excel_file.name.endswith('.xlsx') and not excel_file.name.endswith('.xls'):
            raise forms.ValidationError('Invalid file format. Please upload an Excel file (.xlsx or .xls).')

        return excel_file
    
    def your_view(request):
        form = ExtractStudentForm()  # Create an instance of the form
        import_students_url = 'import_students'  # URL name for the import_students view
        return render(request, 'upload_file.html', {'form': form, 'import_students_url': import_students_url})

    def save(self):
        excel_file = self.cleaned_data['excel_file']

        # Read excel file using pandas
        try:
            df = pd.read_excel(excel_file)
            student_data = df.to_dict(orient='records')

            # Create Student objects in bulk for efficiency
            Student.objects.bulk_create([Student(**data) for data in student_data])
            return student_data  # Optional: Return created student data
        except pd.errors.ParserError as e:
            raise forms.ValidationError(f'Error parsing Excel file: {e}')
        except Exception as e:
            raise forms.ValidationError(f'An error occurred: {e}')


class FacultyForm(ModelForm):
    class Meta:
        model = Faculty
        fields = '__all__'
        exclude = ['user']
    def __init__(self, *args, **kwargs):
        super(FacultyForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'    