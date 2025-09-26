from flask import ( 
    Flask,             # основной класс приложения
    render_template,   # для рендеринга HTML-шаблонов
    request,           # доступ к данным запроса (GET/POST)
    redirect,          # перенаправление на другие маршруты
    url_for,           # генерация URL по имени функции
    jsonify,           # для возврата JSON-ответов
    make_response,     # для создания объектов ответа вручную
    session,           # хранение данных между запросами
    flash,             # временные сообщения для пользователя
    get_flashed_messages,  # получение flash-сообщений
    g                  # специальный объект для хранения данных в течение одного запроса (например, соединение с БД).
)
from pathlib import Path
import requests
from argon2 import PasswordHasher, exceptions
from time import time, ctime
#отдельные функции
from gmail_restore import Restore_account
from data_sql import Data_base
#для токенов
from dotenv import load_dotenv
import os
    
env_key = Path(__file__).parent / "key" / ".env"

load_dotenv(dotenv_path=env_key)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
ph = PasswordHasher()

@app.route("/")
def index():
    # render_template рендерит старницу
    return render_template("index.html")

@app.route("/register", methods=['POST', 'GET'])
def register():
    data_time = ctime() #дада регистрации
    answer = "" #что бы код не ломался
    login = None
    password = None
    email = None
    hash_password = None
    if request.method == "POST":
        login  = request.form.get("username")
        password = request.form.get("password")
        hash_password = ph.hash(password) #хешируем пароль
        email = request.form.get("email")
    print(f"Регистр{login, hash_password , email}")
    
    # если введен логин пароль и эмайл
    if login and password and email:
        regis = Data_base().registr(login, email)

        #проверка на такой же логин и почту в бд
        if regis is not None:
            if login == regis[0] or email == regis[2]:
                print("Такой пользователь уже есть")
                answer = "Такой пользователь уже есть"
        else:
            Data_base().add_users(login, hash_password, email, data_time)
            print("Зарегистрирован")
            answer = "Вы зарегистрированы"
    return render_template("register.html", name=login, password=password, email=email, message=answer)

@app.route("/login", methods=['POST', 'GET'])
def login():
    answer = "" #что бы код не ломался
    name = None
    password = None
    if request.method == "POST":
        name = request.form.get("username")
        password = request.form.get("password")
    print(f"Вход{name, password}")
    # если пароль и логин введены
    if name and password:
        pas = Data_base().login(name)
        print(pas)
        # проверка если пароль и логин введены правильно
        try:
            if pas is not None:
                passwords = pas[0]
                if ph.verify(passwords, password):
                    print(f'Авторизация')
                    answer = "Вы авторизированы"
                    session["name"] = name
                    return redirect(url_for("catsphoto", username=name))
            else:
                print("Не авторизация")
                answer = "Вы не авторизированы"
        except exceptions.VerificationError:
            answer = "Не верный пароль"
    return render_template("login.html", name=name, password=password, message=answer)

#отправка письма на почту
@app.route("/restore", methods=['POST', 'GET'])
def restore_gmail():
    email = None
    if request.method == "POST":
        email = request.form.get("email")
        if not email:
            print("Почта не введена")
        else:
            token = Data_base().restore_gmail(email)
            reset_link = url_for("restore_password", token=token, _external=True)
            #отправка на почту
            send_to_gmail = Restore_account(email, reset_link)
            send_to_gmail.restore_password()
    return render_template("restore_gmail.html", email=email)

#для тех кто забыл пароль :<
@app.route("/restore/password/<token>", methods=['POST', 'GET'])
def restore_password(token):
    password1 = None
    password2 = None
    hash_password = None
    if request.method == "POST":
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")
        print(f"Пароль 1: {password1} \nПароль 2: {password2}")
        if password1 == password2:
            hash_password = ph.hash(password1)
            tok = Data_base().restore_password(token, hash_password)
            print(tok)
    return render_template("restore_password.html", password1=password1, password2=password2, token=token)

#страница с котиками
@app.route("/catsphoto", methods=["GET", "POST"])
def catsphoto():
    name = f'Вы вошли как: {session.get("name")}'
    # берем api с котами
    url_cat = "https://api.thecatapi.com/v1/images/search"
    cat = requests.get(url_cat).json()
    photo=cat[0]["url"]
    return render_template("catsphoto.html", cat_url=photo, message=name)

if __name__ == "__main__":
    cert_path = Path(__file__).parent / "pem" / r"localhost+2.pem" 
    key_path = Path(__file__).parent / "pem" / r"localhost+2-key.pem"
    app.run(debug=True, ssl_context=(cert_path, key_path)) #лог и самоподписанный сертификат 
