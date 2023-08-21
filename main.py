from flask import Flask, render_template, redirect, url_for, flash, abort, session
from flask_bootstrap import Bootstrap
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import forms
from flask_wtf.csrf import CSRFProtect
import os
import random
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)
csrf = CSRFProtect(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.execute(db.select(User).where(User.id == int(user_id))).scalar_one_or_none()


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todolists.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    todo_lists = relationship("TodoList")


class TodoList(db.Model):
    __tablename__ = "todo_lists"
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    list_name = db.Column(db.String(200), nullable=False)
    tasks = relationship("ListItem")


class ListItem(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey("todo_lists.id"))
    task_name = db.Column(db.String(200), nullable=False)
    task_status = db.Column(db.Boolean, nullable=False, default=False)


with app.app_context():
    db.create_all()


def generate_random_identifier(length=10):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


@app.route("/", methods=["GET", "POST"])
def home():
    if not current_user.is_authenticated:
        user_identifier = session.get("user_identifier")
        if user_identifier is None:
            user_identifier = generate_random_identifier()
            session["user_identifier"] = user_identifier
        todo_list = db.session.execute(db.select(TodoList).filter_by(owner_id=user_identifier)).scalar_one_or_none()
        if not todo_list:
            new_todo_list = TodoList(owner_id=user_identifier, list_name="My list")
            db.session.add(new_todo_list)
            db.session.commit()
            todo_list = new_todo_list
        form = forms.TaskForm()
        if form.validate_on_submit():
            new_task = ListItem(list_id=todo_list.id, task_name=form.task_name.data)
            db.session.add(new_task)
            db.session.commit()
            db.get_or_404(TodoList, todo_list.id)
            form.task_name.data = ""
            return render_template("edit_list.html", list=todo_list, form=form, list_id=todo_list.id)
        return render_template("edit_list.html", list=todo_list, form=form)
    else:
        todo_lists = db.session.execute(db.select(TodoList).filter_by(owner_id=current_user.id)).scalars().all()
        return render_template("index.html", all_todos=todo_lists)


@app.route("/register", methods=["GET", "POST"])
def register():
    form = forms.RegisterForm()
    if form.validate_on_submit():
        # for unregistered users
        user_identifier = session.get("user_identifier")
        if user_identifier is not None:
            hashed_password = generate_password_hash(form.password.data, method="pbkdf2:sha256", salt_length=6)
            new_user = User(name=form.name.data, email=form.email.data, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            todo_list = db.session.execute(db.select(TodoList).filter_by(owner_id=user_identifier)).scalar_one_or_none()
            todo_list.owner_id = new_user.id
            db.session.commit()
            return redirect(url_for("home"))
        if db.session.execute(db.select(User).where(User.email == form.email.data)).scalar_one_or_none():
            flash("You've already registered with this e-mail, log in instead!")
            return redirect(url_for("login"))
        else:
            hashed_password = generate_password_hash(form.password.data, method="pbkdf2:sha256", salt_length=6)
            new_user = User(name=form.name.data, email=form.email.data, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("home"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = forms.LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = db.session.execute(db.select(User).where(User.email == email)).scalar_one_or_none()
        if user:
            is_authenticated = check_password_hash(user.password, password)
            if is_authenticated:
                login_user(user)
                return redirect(url_for("home"))
            else:
                flash("Wrong password, please try again...")
        else:
            flash("Sorry, this e-mail was not found in our database")
    return render_template("login.html", form=form)


@login_required
@app.route("/new-list", methods=["GET", "POST"])
def new_list():
    if current_user.is_authenticated:
        form = forms.NewTodoForm()
        if form.validate_on_submit():
            new_todo_list = TodoList(list_name=form.form_name.data, owner_id=current_user.id)
            db.session.add(new_todo_list)
            db.session.commit()
            list_to_edit = db.get_or_404(TodoList, new_todo_list.id)
            return redirect(url_for("edit_list", list_id=list_to_edit.id))
        return render_template("create_list.html", form=form)


@app.route("/edit-list/<list_id>", methods=["GET", "POST"])
def edit_list(list_id):
    try:
        selected_list = db.get_or_404(TodoList, list_id)
        if selected_list:
            if current_user.id == selected_list.owner_id:
                form = forms.TaskForm()
                if form.validate_on_submit():
                    new_task = ListItem(list_id=list_id, task_name=form.task_name.data)
                    db.session.add(new_task)
                    db.session.commit()
                    selected_list = db.get_or_404(TodoList, list_id)
                    form.task_name.data = ""
                    return render_template("edit_list.html", list=selected_list, form=form)
                return render_template("edit_list.html", list=selected_list, form=form)
            else:
                abort(403)
    except AttributeError:
        abort(403)


@app.route('/update-task/<int:task_id>/<int:list_id>/', methods=['GET', 'POST'])
def update_task(task_id, list_id):
    task = db.get_or_404(ListItem, task_id)
    list_ = db.get_or_404(TodoList, list_id)
    if session["user_identifier"] == list_.owner_id:
        task.task_status = not task.task_status
        db.session.commit()
        return redirect(url_for('home'))
    elif current_user.id == list_.owner_id or session["user_identifier"] == list_.owner_id:
        task.task_status = not task.task_status
        db.session.commit()
        return redirect(url_for('edit_list', list_id=list_id))


@login_required
@app.route("/rename/<int:list_id>", methods=["GET", "POST"])
def rename(list_id):
    list_to_edit = db.get_or_404(TodoList, list_id)
    form = forms.NewTodoForm()
    if current_user.id == list_to_edit.owner_id:
        if form.validate_on_submit():
            list_to_edit.list_name = form.form_name.data
            db.session.commit()
            return redirect(url_for("edit_list", list_id=list_to_edit.id))
    else:
        abort(403)
    return render_template("create_list.html", form=form)


@app.route("/delete/<int:task_id>")
def delete_task(task_id):
    try:
        chosen_task = db.get_or_404(ListItem, task_id)
        associated_list = db.session.execute(db.select(TodoList).where(TodoList.id == chosen_task.list_id)).scalar_one_or_none()
        if associated_list:
            if current_user.id == associated_list.owner_id:
                db.session.delete(chosen_task)
                db.session.commit()
                return redirect(url_for('edit_list', list_id=associated_list.id))
            else:
                abort(403)
        else:
            abort(404)
    except AttributeError:
        # When not logged in, even though technically one should be able to check "current_user.is_anonymous",
        # Jinja kept giving me an attribute error, so I used an exception to achieve the desired functionality
        chosen_task = db.get_or_404(ListItem, task_id)
        db.session.delete(chosen_task)
        db.session.commit()
        return redirect(url_for('home'))


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))


if __name__ == '__main__':
    app.run()
