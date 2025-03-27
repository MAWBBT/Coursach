from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import traceback

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

@app.route('/manage_users')
def manage_users():
    # Проверка роли пользователя
    if session.get('role') != 'admin':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('home'))

    try:
        conn = get_db_connection()

        # Получение списка пользователей из базы данных
        users = conn.execute("SELECT * FROM Users").fetchall()
        conn.close()

        return render_template('manage_users.html', users=users)

    except sqlite3.Error as e:
        flash(f'Ошибка базы данных: {e}', 'error')
        return redirect(url_for('home'))

@app.route('/update_cart/<int:cart_id>', methods=['POST'])
def update_cart(cart_id):
    try:
        new_quantity = int(request.form['quantity'])

        if new_quantity <= 0:
            flash('Количество должно быть больше 0!', 'error')
            return redirect(url_for('cart'))

        conn = get_db_connection()
        conn.execute(
            "UPDATE Cart SET Quantity = ? WHERE CartID = ?",
            (new_quantity, cart_id)
        )
        conn.commit()
        flash('Количество товара успешно обновлено!', 'success')
    except Exception as e:
        flash(f'Ошибка при обновлении количества товара: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('cart'))


@app.route('/remove_from_cart/<int:cart_id>', methods=['POST'])
def remove_from_cart(cart_id):
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM Cart WHERE CartID = ?", (cart_id,))
        conn.commit()
        flash('Товар успешно удален из корзины!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении товара из корзины: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('cart'))

@app.route('/update_user_role/<int:user_id>', methods=['POST'])
def update_user_role(user_id):
    # Проверка роли пользователя
    if session.get('role') != 'admin':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('home'))

    new_role = request.form['role']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET Role = ? WHERE UserID = ?", (new_role, user_id))
        conn.commit()
        flash('Роль пользователя успешно обновлена!', 'success')
    except sqlite3.Error as e:
        flash(f'Ошибка базы данных: {e}', 'error')
    finally:
        if conn:
            conn.close()

    return redirect(url_for('manage_users'))

# Страница авторизации
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Если пользователь уже авторизован, перенаправляем его на домашнюю страницу
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Получение данных из формы
        login = request.form.get('login')
        password = request.form.get('password')

        if not login or not password:
            flash('Пожалуйста, заполните все поля!', 'error')
            return redirect(url_for('login'))

        try:
            # Подключение к базе данных
            conn = get_db_connection()
            cursor = conn.cursor()

            # Поиск пользователя в базе данных
            user = cursor.execute(
                "SELECT * FROM Users WHERE Login = ?", (login,)
            ).fetchone()

            if user and check_password_hash(user['PasswordHash'], password):
                # Сохранение данных пользователя в сессии
                session['user_id'] = user['UserID']
                session['role'] = user['Role']
                flash('Вы успешно вошли!', 'success')

                # Перенаправление в зависимости от роли пользователя
                if user['Role'] == 'admin':
                    return redirect(url_for('admin_panel'))
                else:
                    return redirect(url_for('home'))
            else:
                flash('Неверный логин или пароль!', 'error')
                return redirect(url_for('login'))

        except Exception as e:
            flash(f'Ошибка при входе: {e}', 'error')
            return redirect(url_for('login'))

        finally:
            conn.close()

    # Если метод GET, отображаем форму входа
    return render_template('login.html')

# Страница каталога товаров
@app.route('/catalog')
def catalog():
    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM Categories").fetchall()
    products = conn.execute("SELECT * FROM Products").fetchall()
    conn.close()
    return render_template('catalog.html', products=products, categories=categories)

@app.route('/catalog/<int:category_id>')
def catalog_by_category(category_id):
    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM Categories").fetchall()
    products = conn.execute(
        "SELECT * FROM Products WHERE CategoryID = ?", (category_id,)
    ).fetchall()
    conn.close()
    return render_template('catalog.html', products=products, categories=categories)

@app.route('/edit_category/<int:category_id>', methods=['POST'])
def edit_category(category_id):
    # Проверка роли пользователя
    if session.get('role') != 'admin':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('home'))

    new_name = request.form['new_name']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Categories SET CategoryName = ? WHERE CategoryID = ?", (new_name, category_id))
        conn.commit()
        flash('Категория успешно обновлена!', 'success')
    except sqlite3.Error as e:
        flash(f'Ошибка базы данных: {e}', 'error')
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin_panel'))

@app.route('/delete_category/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    # Проверка роли пользователя
    if session.get('role') != 'admin':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('home'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Удаление категории из таблицы Categories
        cursor.execute("DELETE FROM Categories WHERE CategoryID = ?", (category_id,))
        conn.commit()
        flash('Категория успешно удалена!', 'success')
    except sqlite3.Error as e:
        flash(f'Ошибка базы данных: {e}', 'error')
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin_panel'))

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    try:
        if 'user_id' not in session:
            flash('Для добавления товара в корзину необходимо войти в систему.', 'error')
            return redirect(url_for('login'))

        conn = get_db_connection()
        cursor = conn.cursor()

        product = conn.execute("SELECT * FROM Products WHERE ProductID = ?", (product_id,)).fetchone()
        if not product:
            flash('Товар не найден!', 'error')
            return redirect(url_for('catalog'))

        user_id = session['user_id']
        cart_item = conn.execute(
            "SELECT * FROM Cart WHERE UserID = ? AND ProductID = ?", (user_id, product_id)
        ).fetchone()

        if cart_item:
            new_quantity = cart_item['Quantity'] + 1
            conn.execute(
                "UPDATE Cart SET Quantity = ? WHERE CartID = ?", (new_quantity, cart_item['CartID'])
            )
        else:
            conn.execute(
                "INSERT INTO Cart (UserID, ProductID, Quantity) VALUES (?, ?, 1)",
                (user_id, product_id)
            )

        conn.commit()
        flash('Товар успешно добавлен в корзину!', 'success')
    except Exception as e:
        traceback.print_exc()  # Выводит трассировку ошибки
        flash('Произошла ошибка при добавлении товара в корзину.', 'error')
    finally:
        if conn:
            conn.close()

    return redirect(url_for('catalog'))

# Корзина
@app.route('/cart')
def cart():
    # Проверка авторизации пользователя
    if 'user_id' not in session:
        flash('Для просмотра корзины необходимо войти в систему.', 'error')
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        user_id = session['user_id']

        # Получение товаров из корзины
        cart_items = conn.execute(
            """
            SELECT Cart.CartID, Products.ProductID, Products.ProductName, Products.Price, Cart.Quantity
            FROM Cart
            JOIN Products ON Cart.ProductID = Products.ProductID
            WHERE Cart.UserID = ?
            """,
            (user_id,)
        ).fetchall()

        # Вычисление общей стоимости
        total_price = sum(item['Price'] * item['Quantity'] for item in cart_items)

        conn.close()

        # Передача данных в шаблон
        return render_template('cart.html', cart_items=cart_items, total_price=total_price)

    except Exception as e:
        flash(f'Ошибка при загрузке корзины: {e}', 'error')
        return redirect(url_for('home'))

# Оформление заказа
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('Для оформления заказа необходимо войти в систему.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            # Получение данных из формы
            delivery_address = request.form.get('delivery_address')
            payment_method = request.form.get('payment_method')

            # Проверка обязательных полей
            if not delivery_address or not payment_method:
                flash('Пожалуйста, заполните все обязательные поля.', 'error')
                return redirect(url_for('checkout'))

            user_id = session['user_id']

            # Получение товаров из корзины
            conn = get_db_connection()
            cart_items = conn.execute(
                """
                SELECT Cart.CartID, Products.ProductID, Products.ProductName, Products.Price, Cart.Quantity
                FROM Cart
                JOIN Products ON Cart.ProductID = Products.ProductID
                WHERE Cart.UserID = ?
                """,
                (user_id,)
            ).fetchall()

            if not cart_items:
                flash('Ваша корзина пуста!', 'error')
                return redirect(url_for('cart'))

            # Создание заказа
            total_price = sum(item['Price'] * item['Quantity'] for item in cart_items)

            conn.execute(
                "INSERT INTO Orders (UserID, OrderDate, Status, TotalAmount, PaymentMethod, DeliveryAddress) VALUES (?, datetime('now'), ?, ?, ?, ?)",
                (user_id, 'pending', total_price, payment_method, delivery_address)
            )
            order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Сохранение элементов заказа
            for item in cart_items:
                conn.execute(
                    "INSERT INTO OrderItems (OrderID, ProductID, Quantity, UnitPrice) VALUES (?, ?, ?, ?)",
                    (order_id, item['ProductID'], item['Quantity'], item['Price'])
                )

            # Очистка корзины
            conn.execute("DELETE FROM Cart WHERE UserID = ?", (user_id,))
            conn.commit()

            flash('Заказ успешно оформлен!', 'success')
            return redirect(url_for('order_confirmation', order_id=order_id))

        except Exception as e:
            flash(f'Ошибка при оформлении заказа: {e}', 'error')
            return redirect(url_for('cart'))
        finally:
            conn.close()

    # Если метод GET, отображаем форму оформления заказа
    return render_template('checkout.html')

@app.route('/order_confirmation/<int:order_id>')
def order_confirmation(order_id):
    try:
        # Получение данных о заказе из базы данных
        conn = get_db_connection()
        order = conn.execute(
            """
            SELECT * FROM Orders
            WHERE OrderID = ?
            """,
            (order_id,)
        ).fetchone()

        if not order:
            flash('Заказ не найден!', 'error')
            return redirect(url_for('home'))

        # Получение элементов заказа
        order_items = conn.execute(
            """
            SELECT OrderItems.Quantity, Products.ProductName, Products.Price
            FROM OrderItems
            JOIN Products ON OrderItems.ProductID = Products.ProductID
            WHERE OrderItems.OrderID = ?
            """,
            (order_id,)
        ).fetchall()

        conn.close()

        return render_template('order_confirmation.html', order=order, order_items=order_items)

    except Exception as e:
        flash(f'Ошибка при загрузке данных о заказе: {e}', 'error')
        return redirect(url_for('home'))

# Административная панель
@app.route('/admin')
def admin_panel():
    # Проверка роли пользователя
    if session.get('role') != 'admin':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('home'))

    try:
        conn = get_db_connection()

        # Получение данных о товарах
        products = conn.execute("SELECT * FROM Products").fetchall()

        # Получение данных о категориях
        categories = conn.execute("SELECT * FROM Categories").fetchall()

        conn.close()

        # Передача данных в шаблон
        return render_template('admin_panel.html', products=products, categories=categories)

    except sqlite3.Error as e:
        flash(f'Ошибка базы данных: {e}', 'error')
        return redirect(url_for('home'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    # Проверка роли пользователя
    if session.get('role') != 'admin':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('home'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Удаление пользователя из таблицы Users
        cursor.execute("DELETE FROM Users WHERE UserID = ?", (user_id,))
        conn.commit()
        flash('Пользователь успешно удален!', 'success')
    except sqlite3.Error as e:
        flash(f'Ошибка базы данных: {e}', 'error')
    finally:
        if conn:
            conn.close()

    return redirect(url_for('manage_users'))

# Добавление нового товара
@app.route('/add_product', methods=['POST'])
def add_product():
    # Проверка роли пользователя
    if session.get('role') != 'admin':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('home'))

    product_name = request.form['product_name']
    price = request.form['price']
    category_id = request.form['category_id']
    manufacturer = request.form['manufacturer']
    stock_quantity = request.form['stock_quantity']
    compatibility = request.form['compatibility']
    description = request.form['description']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Products (ProductName, Price, CategoryID, Manufacturer, StockQuantity, Compatibility, Description) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (product_name, price, category_id, manufacturer, stock_quantity, compatibility, description)
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
@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    # Проверка роли пользователя
    if session.get('role') != 'admin':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('home'))

    conn = get_db_connection()
    product = conn.execute("SELECT * FROM Products WHERE ProductID = ?", (product_id,)).fetchone()

    if not product:
        flash('Товар не найден!', 'error')
        return redirect(url_for('admin_panel'))

    if request.method == 'POST':
        # Получение данных из формы
        product_name = request.form['product_name']
        price = request.form['price']
        category_id = request.form['category_id']
        manufacturer = request.form['manufacturer']
        stock_quantity = request.form['stock_quantity']
        compatibility = request.form['compatibility']
        description = request.form['description']

        try:
            # Обновление данных о товаре
            conn.execute(
                """
                UPDATE Products
                SET ProductName = ?, Price = ?, CategoryID = ?, Manufacturer = ?,
                    StockQuantity = ?, Compatibility = ?, Description = ?
                WHERE ProductID = ?
                """,
                (product_name, price, category_id, manufacturer, stock_quantity, compatibility, description, product_id)
            )
            conn.commit()
            flash('Товар успешно обновлен!', 'success')
            return redirect(url_for('admin_panel'))
        except sqlite3.Error as e:
            flash(f'Ошибка базы данных: {e}', 'error')
        finally:
            conn.close()

    # Получение списка категорий для выпадающего списка
    categories = conn.execute("SELECT * FROM Categories").fetchall()
    conn.close()

    return render_template('edit_product.html', product=product, categories=categories)

@app.route('/add_category', methods=['POST'])
def add_category():
    # Проверка роли пользователя
    if session.get('role') != 'admin':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('home'))

    category_name = request.form['category_name']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Categories (CategoryName) VALUES (?)", (category_name,))
        conn.commit()
        flash('Категория успешно добавлена!', 'success')
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