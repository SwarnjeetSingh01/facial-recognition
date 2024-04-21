from django.shortcuts import render, redirect
from django.http import HttpResponse, StreamingHttpResponse
from django.urls import path
from django.core.files.storage import FileSystemStorage

import pandas as pd
import sqlite3

from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .forms import *
from .forms import ExtractStudentForm
from .models import Student, Attendence
from .filters import AttendenceFilter


from .recognizer import Recognizer
from datetime import date


def index(request):
    return render(request,'index.html')

def signin(request):
    return render(request,'signin.html')

@login_required(login_url = 'login')
def home(request):
    studentForm = CreateStudentForm()

    if request.method == 'POST':
        studentForm = CreateStudentForm(data = request.POST, files=request.FILES)
        # print(request.POST)
        stat = False 
        try:
            student = Student.objects.get(registration_id = request.POST['registration_id'])
            stat = True
        except:
            stat = False
        if studentForm.is_valid() and (stat == False):
            studentForm.save()
            name = studentForm.cleaned_data.get('firstname') +" " +studentForm.cleaned_data.get('lastname')
            messages.success(request, 'Student ' + name + ' was successfully added.')
            return redirect('home')
        else:
            messages.error(request, 'Student with Registration Id '+request.POST['registration_id']+' already exists.')
            return redirect('home')

    context = {'studentForm':studentForm}
    return render(request, 'attendence_sys/home.html', context)


def import_students(request):
    if request.method == 'POST':
        form = ExtractStudentForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            try:
                # Save the uploaded file
                with FileSystemStorage() as storage:
                    file_name = storage.save(excel_file.name, excel_file)
                    try:
                        # Read the Excel file into a pandas DataFrame
                        df = pd.read_excel(storage.path(file_name))

                        # Iterate through DataFrame rows and create Student objects
                        for index, row in df.iterrows():
                            Student.objects.create(
                                firstname=row['firstname'],
                                lastname=row['lastname'],
                                registration_id=row['registration_id'],
                                branch=row['branch'],
                                year=row['year'],
                                section=row['section'],
                                name=f"{row['firstname']} {row['lastname']}"
                            )

                        messages.success(request, 'Students imported successfully!')
                        return redirect('home')  # Redirect to desired URL after import
                    except pd.errors.ParserError as e:
                        messages.error(request, f'Error parsing Excel file: {e}')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {e}')
            finally:
                # Ensure file deletion even on exceptions
                if file_name:
                    storage.delete(file_name)
        else:
            messages.error(request, 'Please correct errors in the form.')
    else:
        # Handle GET requests explicitly
        form = ExtractStudentForm() 

    return render(request, 'upload_file.html', {'form': form})


def loginPage(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username = username, password = password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.info(request, 'Username or Password is incorrect')

    context = {}
    return render(request, 'attendence_sys/signin.html', context)

@login_required(login_url = 'login')
def logoutUser(request):
    logout(request)
    return redirect('login')

@login_required(login_url = 'login')
def updateStudentRedirect(request):
    context = {}
    if request.method == 'POST':
        try:
            reg_id = request.POST['reg_id']
            branch = request.POST['branch']
            student = Student.objects.get(registration_id = reg_id, branch = branch)
            updateStudentForm = CreateStudentForm(instance=student)
            context = {'form':updateStudentForm, 'prev_reg_id':reg_id, 'student':student}
        except:
            messages.error(request, 'Student Not Found')
            return redirect('home')
    return render(request, 'attendence_sys/student_update.html', context)

@login_required(login_url = 'login')
def updateStudent(request):
    if request.method == 'POST':
        context = {}
        try:
            student = Student.objects.get(registration_id = request.POST['prev_reg_id'])
            updateStudentForm = CreateStudentForm(data = request.POST, files=request.FILES, instance = student)
            if updateStudentForm.is_valid():
                updateStudentForm.save()
                messages.success(request, 'Updation Success')
                return redirect('home')
        except:
            messages.error(request, 'Updation Unsucessfull')
            return redirect('home')
    return render(request, 'attendence_sys/student_update.html', context)


@login_required(login_url = 'login')
def takeAttendence(request):
    if request.method == 'POST':
        details = {
            'branch':request.POST['branch'],
            'year': request.POST['year'],
            'section':request.POST['section'],
            'period':request.POST['period'],
            'faculty':request.user.faculty
            }
        if Attendence.objects.filter(date = str(date.today()),branch = details['branch'], year = details['year'], section = details['section'],period = details['period']).count() != 0 :
            messages.error(request, "Attendence already recorded.")
            return redirect('attendence_sys/home.html')
        else:
            students = Student.objects.filter(branch = details['branch'], year = details['year'], section = details['section'])
            names = Recognizer(details)
            for student in students:
                if str(student.registration_id) in names:
                    attendence = Attendence(Faculty_Name = request.user.faculty, 
                    Student_ID = str(student.registration_id), 
                    period = details['period'], 
                    branch = details['branch'], 
                    year = details['year'], 
                    section = details['section'],
                    status = 'Present')
                    attendence.save()
                else:
                    attendence = Attendence(Faculty_Name = request.user.faculty, 
                    Student_ID = str(student.registration_id), 
                    period = details['period'],
                    branch = details['branch'], 
                    year = details['year'], 
                    section = details['section'])
                    attendence.save()
            attendences = Attendence.objects.filter(date = str(date.today()),branch = details['branch'], year = details['year'], section = details['section'],period = details['period'])
            context = {"attendences":attendences, "ta":True}
            messages.success(request, "Attendence taking Success")
            return render(request, 'attendence_sys/attendence.html', context)        
    context = {}
    return render(request, 'attendence_sys/home.html', context)

def searchAttendence(request):
    attendences = Attendence.objects.all()
    myFilter = AttendenceFilter(request.GET, queryset=attendences)
    attendences = myFilter.qs
    context = {'myFilter':myFilter, 'attendences': attendences, 'ta':False}
    return render(request, 'attendence_sys/attendence.html', context)


def facultyProfile(request):
    faculty = request.user.faculty
    form = FacultyForm(instance = faculty)
    context = {'form':form}
    return render(request, 'attendence_sys/facultyForm.html', context)

# def upload_excel(excel_file_path, table_name, db_path):
#     """
#     Uploads data from an Excel file to a SQLite3 database table.

#     Args:
#         excel_file_path (str): Path to the Excel file.
#         table_name (str): Name of the table to create or insert data into.
#         db_path (str): Path to the SQLite3 database file.
#     """

#     # Read the Excel data using pandas
#     try:
#         df = pd.read_excel(excel_file_path)
#     except FileNotFoundError:
#         print(f"Error: Excel file '{excel_file_path}' not found.")
#         return

#     # Connect to the SQLite3 database
#     conn = sqlite3.connect(db_path)

#     # Create the table if it doesn't exist
#     cursor = conn.cursor()
#     create_table_query = f"""
#     CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(df.columns)})
#     """
#     cursor.execute(create_table_query)

#     # Convert pandas DataFrame to a list of tuples (suitable for bulk insertion)
#     data_tuples = df.to_records(index=False).tolist()

#     # Insert data into the table (using bulk insertion for efficiency)
#     try:
#         insert_query = f"""INSERT INTO {table_name} VALUES (?, ?, ...)"""
#         cursor.executemany(insert_query, data_tuples)
#         conn.commit()
#         print(f"Data uploaded successfully to table '{table_name}'.")
#     except sqlite3.Error as e:
#         print(f"Error uploading data: {e}")
#     finally:
#         conn.close()