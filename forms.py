from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, EmailField
from wtforms.validators import DataRequired, URL, Email, Length


class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = EmailField("E-mail", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    submit = SubmitField("Sign up")


class LoginForm(FlaskForm):
    email = EmailField("E-mail", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


class NewTodoForm(FlaskForm):
    form_name = StringField("List Name:", validators=[DataRequired()])
    submit = SubmitField("Submit")


class TaskForm(FlaskForm):
    # the render_kw autofocus: True will make the browser window always focus on the form,
    # so when you add a new task it doesnt look like the page is reloading
    task_name = StringField("New task", validators=[DataRequired()], render_kw={'autofocus': True})
    submit = SubmitField("Add Task")