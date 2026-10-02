from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, SelectField, SelectMultipleField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from wtforms.widgets import ListWidget, CheckboxInput


class RegisterForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=150)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match")]
    )
    role = SelectField(
        "Role",
        choices=[("student", "Student"), ("lecturer", "Lecturer"), ("alumni", "Alumni")],
        validators=[Optional()],
    )

    # Student-specific fields
    matric_number = StringField("Matric Number", validators=[Optional()])
    department_id = SelectField("Department", coerce=int, validators=[Optional()])
    level_id = SelectField("Level", coerce=int, validators=[Optional()])
    preferred_resource_type = SelectField(
        "Preferred Resource Type",
        choices=[("pdf", "PDF"), ("video", "Video"), ("textbook", "Textbook"), ("notes", "Notes")],
        validators=[Optional()],
    )
   
    interest_tags = SelectMultipleField(
        "Learning Preferences",
        choices=[
            # Learning Goals
            ("Goal: Exam Preparation", "Exam Preparation"),
            ("Goal: Assignments", "Complete Assignments"),
            ("Goal: Projects", "Work on Projects"),
            ("Goal: Academic Performance", "Improve Academic Performance"),
            ("Goal: Research", "Conduct Research"),
            ("Goal: Practical Skills", "Learn Practical Skills"),
            ("Goal: Career Prep", "Prepare for Career Opportunities"),
            ("Goal: Deeper Understanding", "Gain Deeper Understanding"),
            # Learning Style
            ("Style: Reading Notes", "Reading Notes and PDFs"),
            ("Style: Video Tutorials", "Watching Video Tutorials"),
            ("Style: Practice Questions", "Solving Practice Questions"),
            ("Style: Hands-on", "Hands-on Practical Exercises"),
            ("Style: Group Discussion", "Group Discussions"),
            ("Style: Case Studies", "Case Studies"),
            ("Style: Research-based", "Research-based Learning"),
            ("Style: Step-by-step", "Step-by-step Tutorials"),
            # Resource Format
            ("Format: Lecture Slides", "Lecture Slides"),
            ("Format: Research Papers", "Research Papers"),
            ("Format: Past Questions", "Past Questions"),
            # Academic Interests
            ("Interest: Technology", "Technology & Computing"),
            ("Interest: Engineering", "Engineering"),
            ("Interest: Health Sciences", "Health Sciences"),
            ("Interest: Business", "Business & Entrepreneurship"),
            ("Interest: Social Sciences", "Social Sciences"),
            ("Interest: Arts & Humanities", "Arts & Humanities"),
            ("Interest: Education", "Education"),
            ("Interest: Environmental Studies", "Environmental Studies"),
        ],
        widget=ListWidget(prefix_label=False),
        option_widget=CheckboxInput(),
        validators=[Optional()],
    )
    # Lecturer-specific fields
    faculty_id = SelectField("Faculty", coerce=int, validators=[Optional()])
    specialization = StringField("Area of Specialization", validators=[Optional()])

    # Alumni-specific fields
    graduation_year = IntegerField("Graduation Year", validators=[Optional()])
    degree_class = StringField("Degree Class", validators=[Optional()])

    verification_document = FileField(
        "Verification Document (Certificate, ID, or Transcript)",
        validators=[Optional(), FileAllowed(["pdf", "jpg", "jpeg", "png"], "PDF or image files only!")]
    )
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = SelectField(
        "Remember Me", choices=[("yes", "Yes"), ("no", "No")], default="no"
    )
    submit = SubmitField("Login")


class ResourceUploadForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=250)])
    description = StringField("Description", validators=[Optional()])
    resource_type = SelectField(
        "Resource Type",
        choices=[("pdf", "PDF Document"), ("youtube", "YouTube Link"), ("textbook", "Textbook Reference")],
        validators=[DataRequired()],
    )

    university_id = SelectField("University", coerce=int, validators=[DataRequired()])
    faculty_id = SelectField("Faculty", coerce=int, validators=[DataRequired()])
    department_id = SelectField("Department", coerce=int, validators=[DataRequired()])
    level_id = SelectField("Level", coerce=int, validators=[DataRequired()])
    course_id = SelectField("Course", coerce=int, validators=[DataRequired()])

    file = FileField("Upload PDF", validators=[Optional(), FileAllowed(["pdf"], "PDF files only!")])
    external_link = StringField("Link / Reference", validators=[Optional(), Length(max=500)])

    submit = SubmitField("Submit for Review")


class FacultyForm(FlaskForm):
    name = StringField("Faculty Name", validators=[DataRequired(), Length(max=150)])
    university_id = SelectField("University", coerce=int, validators=[DataRequired()])
    submit_faculty = SubmitField("Add Faculty")


class DepartmentForm(FlaskForm):
    name = StringField("Department Name", validators=[DataRequired(), Length(max=150)])
    faculty_id = SelectField("Faculty", coerce=int, validators=[DataRequired()])
    submit_department = SubmitField("Add Department")


class CourseForm(FlaskForm):
    course_code = StringField("Course Code", validators=[DataRequired(), Length(max=20)])
    course_title = StringField("Course Title", validators=[DataRequired(), Length(max=200)])
    department_id = SelectField("Department", coerce=int, validators=[DataRequired()])
    level_id = SelectField("Level", coerce=int, validators=[DataRequired()])
    submit_course = SubmitField("Add Course")


class UniversityForm(FlaskForm):
    name = StringField("University Name", validators=[DataRequired(), Length(max=150)])
    submit_university = SubmitField("Add University")


class UniversityForm(FlaskForm):
    name = StringField("University Name", validators=[DataRequired(), Length(max=150)])
    submit_university = SubmitField("Add University")

class RecommendationSettingsForm(FlaskForm):
    content_weight = StringField("Content-Based Weight", validators=[DataRequired()])
    collaborative_weight = StringField("Collaborative Weight", validators=[DataRequired()])
    submit = SubmitField("Save Settings")

class ProfileForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=150)])
    email = StringField("Email", validators=[DataRequired(), Email()])

    # Student-specific
    department_id = SelectField("Department", coerce=int, validators=[Optional()])
    level_id = SelectField("Level", coerce=int, validators=[Optional()])
    preferred_resource_type = SelectField(
        "Preferred Resource Type",
        choices=[("pdf", "PDF"), ("video", "Video"), ("textbook", "Textbook"), ("notes", "Notes")],
        validators=[Optional()],
    )

    # Lecturer-specific
    faculty_id = SelectField("Faculty", coerce=int, validators=[Optional()])
    specialization = StringField("Area of Specialization", validators=[Optional()])

    # Alumni-specific
    degree_class = StringField("Degree Class", validators=[Optional()])

    submit_profile = SubmitField("Save Changes")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField(
        "Confirm New Password", validators=[DataRequired(), EqualTo("new_password", message="Passwords must match")]
    )
    submit_password = SubmitField("Change Password")