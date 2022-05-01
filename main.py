import flask
from flask import Flask, render_template, redirect, request, abort, jsonify
from flask import make_response, session
from flask_restful import reqparse, abort, Api, Resource
import datetime
from data import db_session, news_api
from data.users import User
from data.news import News
from forms.news import NewsForm
from forms.user import RegisterForm, LoginForm
from flask_login import LoginManager, login_required, logout_user, login_user, current_user

app = Flask(__name__)
api = Api(app)
app.config['SECRET_KEY'] = 'my_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(
    days=365
)

login_manager = LoginManager()
login_manager.init_app(app)


@app.route("/profile=<nickname>")
def show_profile(nickname=None):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.nickname == nickname).first()
    news = db_sess.query(News).filter(News.user == user).all()
    return render_template('profile.html', title='Профиль', user=user, news=news)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/')
def events():
    name_news = request.args.get('name')
    db_sess = db_session.create_session()
    if name_news is None:
        news = db_sess.query(News).filter(~News.is_private).all()
    else:
        news = db_sess.query(News).filter(News.is_private != True and
                                          News.title.like(f'%{name_news}%'))
    news = news[::-1]
    if len(news) > 50:
        news = news[:50]
    top_news = db_sess.query(News).all()
    top_users = {}
    for i in top_news:
        if i.user_id not in top_users:
            top_users[i.user_id] = 0
        top_users[i.user_id] += 1
    users = db_sess.query(User).filter(User.id.in_(top_users.keys())).all()
    top_users_with_nickname = {}
    for i in users:
        top_users_with_nickname[i.nickname] = top_users[i.id]
    top_users_with_nickname = sorted(top_users_with_nickname.items(), key=lambda x: x[1], reverse=True)
    if len(top_users_with_nickname) > 10:
        top_users_with_nickname = top_users_with_nickname[:10]
    return render_template('event_page.html', news=news, top=top_users_with_nickname)


@app.route('/news', methods=['GET', 'POST'])
@login_required
def add_news():
    form = NewsForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        news = News()
        news.title = form.title.data
        news.content = form.content.data
        news.is_private = form.is_private.data
        current_user.news.append(news)
        db_sess.merge(current_user)
        db_sess.commit()
        return redirect(f'/profile={current_user.nickname}')
    return render_template('news.html', title='Добавление новости',
                           form=form)


@app.route('/news=<int:id>', methods=['GET', 'POST'])
@login_required
def edit_news(id):
    form = NewsForm()
    if request.method == "GET":
        db_sess = db_session.create_session()
        news = db_sess.query(News).filter(News.id == id,
                                          News.user == current_user
                                          ).first()
        if news:
            form.title.data = news.title
            form.content.data = news.content
            form.is_private.data = news.is_private
        else:
            abort(404)
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        news = db_sess.query(News).filter(News.id == id,
                                          News.user == current_user
                                          ).first()
        if news:
            news.title = form.title.data
            news.content = form.content.data
            news.is_private = form.is_private.data
            db_sess.commit()
            return redirect(f'/profile={current_user.nickname}')
        else:
            abort(404)
    return render_template('news.html',
                           title='Редактирование новости',
                           form=form
                           )


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            nickname=form.nickname.data,
            name=form.name.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/news_delete/<int:id>', methods=['GET', 'POST'])
@login_required
def news_delete(id):
    db_sess = db_session.create_session()
    news = db_sess.query(News).filter(News.id == id,
                                      News.user == current_user
                                      ).first()
    if news:
        db_sess.delete(news)
        db_sess.commit()
    else:
        abort(404)
    return redirect(f'/profile={current_user.nickname}')


def main():
    db_session.global_init("db/blogs.db")
    app.register_blueprint(news_api.blueprint)
    app.run(port=8000, host='127.0.0.1')


if __name__ == '__main__':
    main()
