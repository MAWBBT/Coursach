from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Секретный ключ для работы с Flask

# Настройка подключения к базе данных SQLite
DATABASE = 'auto_parts_store.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Главная страница
@app.route('/')
def home():
    return render_template('index.html')

# Страница регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']

        # Хеширование пароля
        password_hash = generate_password_hash(password)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Проверка на уникальность логина
            cursor.execute("SELECT * FROM Users WHERE Login = ?", (login,))
            existing_user = cursor.fetchone()

            if existing_user:
                flash('Пользователь с таким логином уже существует!', 'error')
                return redirect(url_for('register'))

            # Добавление нового пользователя
            cursor.execute("INSERT INTO Users (Login, PasswordHash) VALUES (?, ?)", (login, password_hash))
            conn.commit()
            flash('Регистрация прошла успешно!', 'success')
            return redirect(url_for('login'))

        except sqlite3.Error as e:
            flash(f'Ошибка базы данных: {e}', 'error')

        finally:
            if conn:
                conn.close()

    return render_template('register.html')

# Страница авторизации
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Поиск пользователя по логину
            cursor.execute("SELECT * FROM Users WHERE Login = ?", (login,))
            user = cursor.fetchone()

            if user and check_password_hash(user['PasswordHash'], password):  # Проверка хеша пароля
                session['user_id'] = user['UserID']
                session['role'] = user['Role']  # Сохраняем роль пользователя в сессии
                flash('Вы успешно вошли!', 'success')

                # Перенаправление в зависимости от роли
                if user['Role'] == 'admin':
                    return redirect(url_for('admin_panel'))  # Админская панель
                else:
                    return redirect(url_for('home'))  # Главная страница для клиентов

            else:
                flash('Неверный логин или пароль!', 'error')

        except sqlite3.Error as e:
            flash(f'Ошибка базы данных: {e}', 'error')

        finally:
            if conn:
                conn.close()

    return render_template('login.html')

# Страница каталога товаров
@app.route('/catalog')
def catalog():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM Products").fetchall()
    conn.close()
    return render_template('catalog.html', products=products)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    # Получение данных о товаре из базы данных
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM Products WHERE ProductID = ?", (product_id,)).fetchone()
    conn.close()

    if not product:
        flash('Товар не найден!', 'error')
        return redirect(url_for('catalog'))

    # Инициализация корзины в сессии
    if 'cart' not in session:
        session['cart'] = []

    # Проверка, есть ли товар уже в корзине
    cart = session['cart']
    for item in cart:
        if item['ProductID'] == product['ProductID']:
            item['Quantity'] += 1
            session.modified = True
            flash('Товар добавлен в корзину!', 'success')
            return redirect(url_for('catalog'))

    # Добавление нового товара в корзину
    cart.append({
        'ProductID': product['ProductID'],
        'ProductName': product['ProductName'],
        'UnitPrice': product['Price'],
        'Quantity': 1
    })
    session.modified = True
    flash('Товар добавлен в корзину!', 'success')
    return redirect(url_for('catalog'))

# Корзина
@app.route('/cart')
def cart():
    if 'cart' not in session or not session['cart']:
        return render_template('cart.html', cart=None, total_amount=0)

    cart = session['cart']
    total_amount = sum(item['UnitPrice'] * item['Quantity'] for item in cart)
    return render_template('cart.html', cart=cart, total_amount=total_amount)

@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    if 'cart' not in session or not session['cart']:
        flash('Корзина пуста!', 'error')
        return redirect(url_for('cart'))

    # Поиск товара в корзине
    cart = session['cart']
    for item in cart:
        if item['ProductID'] == product_id:
            cart.remove(item)
            session.modified = True
            flash('Товар удален из корзины!', 'success')
            return redirect(url_for('cart'))

    flash('Товар не найден в корзине!', 'error')
    return redirect(url_for('cart'))

# Оформление заказа
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        # Логика сохранения заказа в базу данных
        flash('Заказ успешно оформлен!', 'success')
        return redirect(url_for('home'))
    return render_template('checkout.html')

# Административная панель
@app.route('/admin')
def admin_panel():
    # Проверка, является ли пользователь администратором
    if session.get('role') != 'admin':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('home'))

    # Получение данных о товарах для отображения в админской панели
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM Products").fetchall()
    conn.close()

    return render_template('admin_panel.html', products=products)

# Добавление нового товара
@app.route('/add_product', methods=['POST'])
def add_product():
    # Проверка роли пользователя
    if session.get('role') != 'admin':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('home'))

    product_name = request.form['product_name']
    price = request.form['price']
    description = request.form['description']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Products (ProductName, Price, Description, CategoryID, Manufacturer, StockQuantity, Compatibility) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (product_name, price, description, 1, 'Unknown', 10, 'Compatible with all cars')
        )
        conn.commit()
        flash('Товар успешно добавлен!', 'success')
    except sqlite3.Error as e:
        flash(f'Ошибка базы данных: {e}', 'error')
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin_panel'))

# Редактирование товара
@app.route('/edit_product/<int:product_id>', methods=['POST'])
def edit_product(product_id):
    # Проверка роли пользователя
    if session.get('role') != 'admin':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('home'))

    new_price = request.form['new_price']
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Products SET Price = ? WHERE ProductID = ?", (new_price, product_id))
        conn.commit()
        flash('Товар успешно обновлен!', 'success')
    except sqlite3.Error as e:
        flash(f'Ошибка базы данных: {e}', 'error')
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin_panel'))

# Удаление товара
@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    # Проверка роли пользователя
    if session.get('role') != 'admin':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('home'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Products WHERE ProductID = ?", (product_id,))
        conn.commit()
        flash('Товар успешно удален!', 'success')
    except sqlite3.Error as e:
        flash(f'Ошибка базы данных: {e}', 'error')
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin_panel'))

# Выход из аккаунта
@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из аккаунта!', 'success')
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)