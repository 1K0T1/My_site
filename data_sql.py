import sqlite3
from pathlib import Path
import uuid
from time import time, ctime
from flask import current_app
#для токенов
from itsdangerous import (
Serializer,
URLSafeSerializer,
TimedSerializer,
URLSafeTimedSerializer,
Signer,
BadSignature,
SignatureExpired,
)

db_path = Path(__file__).parent / "data_base" / "users_data.db"

#декоратор что бы автоматом был конект к бд
def sql_request(func):
    def wrapper(self, *args, **kwargs):
        try:
            users_sql = sqlite3.connect(db_path, timeout=10)
            cursor = users_sql.cursor()
            result = func(self, cursor, *args, **kwargs)
            users_sql.commit()
            return result
        except Exception as e:
            users_sql.rollback()
            raise e
        finally:
            users_sql.close()
    return wrapper

#каждому юзеру уникальный токен
def _get_serializer(secret=None, salt='password-reset'):
    secret = secret or current_app.config['SECRET_KEY']
    return URLSafeTimedSerializer(secret, salt=salt)

def verify_reset_token(token, max_age=3600):
    s = _get_serializer()
    try:
        data = s.loads(token, max_age=max_age)
        return data  # вернёт {uid:__, jti:__}
    except Exception:
        return None

class Data_base:
    def __init__(self):
        self._init_table()

    #data base
    @sql_request
    def _init_table(self, cursor):
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,     -- Уникальный ID пользователя
            login TEXT NOT NULL,         -- Имя
            password TEXT NOT NULL,       -- Пароль
            email TEXT NOT NULL,        -- Почта
            date TEXT NOT NULL,         -- Дата регистрации
            token TEXT,           -- Идентификатор токена
            reset_token TEXT        -- Время запроса в сек.
            )
        """)
        
    @sql_request
    def generate_reset_token(self, cursor, user_id):
        jti = uuid.uuid4().hex
        cursor.execute("UPDATE users SET token = ?, reset_token = ? WHERE id = ?",
                    (jti, int(time()), user_id))
        #cоздаем токен user_id + jti
        s = _get_serializer()
        token = s.dumps({"uid": user_id, "jti": jti})
        return token

    @sql_request
    def registr(self, cursor, login, email):
        cursor.execute("SELECT login, password, email from users WHERE login = ? OR email = ?", (login, email,))
        regis = cursor.fetchone()
        return regis
    
    @sql_request
    def add_users(self, cursor, login, hash_password, email, data_time):
        cursor.execute("INSERT INTO users (login, password, email, date) VALUES (?, ?, ?, ?)",
                           (login, hash_password, email, data_time))
    
    @sql_request
    def login(self, cursor, login):
        cursor.execute("SELECT password FROM users WHERE login = ?", (login,))
        pas = cursor.fetchone()
        return pas
    
    @sql_request
    def restore_gmail(self, cursor, email):
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        pas = cursor.fetchone()
        user_id = pas[0]
        token = self.generate_reset_token(user_id)
        return token
    
    @sql_request
    def restore_password(self, cursor, token, hash_password):
        data = verify_reset_token(token)
        if not data:
            return 'ссылка устарела'
        user_id = data['uid']
        token_jti = data['jti']
        cursor.execute("SELECT token FROM users WHERE id = ?", (user_id,))
        tok = cursor.fetchone()
        if not tok or tok[0] != token_jti:
            return "Токен недействителен"
        cursor.execute("UPDATE users SET password = ?, token = NULL WHERE id = ?", (hash_password ,user_id))
        return "Пороль изменен"