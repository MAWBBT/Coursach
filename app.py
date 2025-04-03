from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import traceback

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Секретный ключ для работы с Flask

UPLOAD_FOLDER = 'static/images/products'  # Папка для хранения изображений
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Настройка подключения к базе данных SQLite
DATABASE = 'auto_parts_store.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Главная страница
@app.route('/')
def home():
    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM Categories LIMIT 6").fetchall()
    conn.close()
    user = None
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute(
            "SELECT Login FROM Users WHERE UserID = ?", (session['user_id'],)
        ).fetchone()
        conn.close()

    return render_template('index.html', categories=categories, user=user)

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
    if 'user_id' not in session:
        flash('Для обновления корзины необходимо войти в систему.', 'error')
        return redirect(url_for('login'))

    try:
        new_quantity = int(request.form.get('quantity'))
        user_id = session['user_id']

        conn = get_db_connection()
        cart_item = conn.execute(
            "SELECT ProductID, Quantity FROM Cart WHERE CartID = ? AND UserID = ?", (cart_id, user_id)
        ).fetchone()

        if not cart_item:
            flash('Товар не найден в корзине!', 'error')
            return redirect(url_for('cart'))

        product = conn.execute(
            "SELECT StockQuantity FROM Products WHERE ProductID = ?", (cart_item['ProductID'],)
        ).fetchone()

        # Проверка, что новое количество не превышает доступное
        if new_quantity > product['StockQuantity']:
            new_quantity = product['StockQuantity']
            flash(f'Максимальное количество для этого товара: {new_quantity} шт.', 'warning')

        # Обновление корзины
        conn.execute(
            "UPDATE Cart SET Quantity = ? WHERE CartID = ?", 
            (new_quantity, cart_id)
        )
        conn.commit()

    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
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

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').strip()  # Получаем поисковый запрос
    if not query:
        flash('Введите поисковый запрос.', 'error')
        return redirect(url_for('catalog'))

    conn = get_db_connection()
    products = conn.execute(
        """
        SELECT * FROM Products 
        WHERE ProductName LIKE ? OR Description LIKE ?
        """,
        (f'%{query}%', f'%{query}%')
    ).fetchall()

    conn.close()

    if not products:
        flash('Товары не найдены.', 'info')

    return render_template('catalog.html', products=products, query=query)

@app.route('/product/<int:product_id>')
def product_details(product_id):
    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM Products WHERE ProductID = ?", (product_id,)
    ).fetchone()
    conn.close()

    if not product:
        flash('Товар не найден!', 'error')
        return redirect(url_for('catalog'))

    return render_template('product_details.html', product=product)

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

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    if 'user_id' not in session:
        flash('Для удаления заказа необходимо войти в систему.', 'error')
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверка, принадлежит ли заказ текущему пользователю
        order = conn.execute(
            "SELECT * FROM Orders WHERE OrderID = ? AND UserID = ?", 
            (order_id, session['user_id'])
        ).fetchone()

        if not order:
            flash('Заказ не найден или доступ запрещен!', 'error')
            return redirect(url_for('orders'))

        # Удаление элементов заказа из OrderItems
        conn.execute("DELETE FROM OrderItems WHERE OrderID = ?", (order_id,))
        # Удаление самого заказа
        conn.execute("DELETE FROM Orders WHERE OrderID = ?", (order_id,))
        conn.commit()
        flash('Заказ успешно удален!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении заказа: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('orders'))

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
    if 'user_id' not in session:
        flash('Для добавления товара в корзину необходимо войти в систему.', 'error')
        return redirect(url_for('login'))

    quantity = int(request.form.get('quantity', 1))
    user_id = session['user_id']

    try:
        conn = get_db_connection()
        product = conn.execute(
            "SELECT StockQuantity FROM Products WHERE ProductID = ?", (product_id,)
        ).fetchone()

        if not product:
            flash('Товар не найден!', 'error')
            return redirect(url_for('catalog'))

        # Проверка, что запрашиваемое количество не превышает доступное
        if quantity > product['StockQuantity']:
            flash(f'Максимальное количество: {product["StockQuantity"]} шт.', 'error')
            return redirect(url_for('catalog'))

        # Проверка, есть ли товар уже в корзине
        cart_item = conn.execute(
            "SELECT * FROM Cart WHERE UserID = ? AND ProductID = ?", (user_id, product_id)
        ).fetchone()

        if cart_item:
            new_quantity = cart_item['Quantity'] + quantity
            if new_quantity > product['StockQuantity']:
                flash(f'Недостаточно товара на складе!', 'error')
                return redirect(url_for('catalog'))
            conn.execute(
                "UPDATE Cart SET Quantity = ? WHERE CartID = ?", (new_quantity, cart_item['CartID'])
            )
        else:
            conn.execute(
                "INSERT INTO Cart (UserID, ProductID, Quantity) VALUES (?, ?, ?)",
                (user_id, product_id, quantity)
            )

        conn.commit()
        flash('Товар добавлен в корзину!', 'success')
        return redirect(url_for('catalog'))

    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
        return redirect(url_for('catalog'))
    finally:
        conn.close()

# Корзина
@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cart_items = conn.execute(
        """
        SELECT Cart.CartID, Products.ProductID, Products.ProductName, 
               Products.Price, Cart.Quantity, Products.StockQuantity
        FROM Cart
        JOIN Products ON Cart.ProductID = Products.ProductID
        WHERE Cart.UserID = ?
        """,
        (user_id,)
    ).fetchall()
    conn.close()

    total_price = sum(item['Price'] * item['Quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/orders')
def orders():
    # Проверка авторизации пользователя
    if 'user_id' not in session:
        flash('Для просмотра заказов необходимо войти в систему.', 'error')
        return redirect(url_for('login'))

    try:
        user_id = session['user_id']

        # Подключение к базе данных
        conn = get_db_connection()

        # Получение всех заказов пользователя
        orders = conn.execute(
            """
            SELECT OrderID, OrderDate, Status, TotalAmount, PaymentMethod, DeliveryAddress
            FROM Orders
            WHERE UserID = ?
            ORDER BY OrderDate DESC
            """,
            (user_id,)
        ).fetchall()

        # Получение элементов каждого заказа
        order_details = {}
        for order in orders:
            order_id = order['OrderID']
            items = conn.execute(
                """
                SELECT Products.ProductName, OrderItems.Quantity, OrderItems.UnitPrice
                FROM OrderItems
                JOIN Products ON OrderItems.ProductID = Products.ProductID
                WHERE OrderItems.OrderID = ?
                """,
                (order_id,)
            ).fetchall()
            order_details[order_id] = items

        conn.close()

        return render_template('orders.html', orders=orders, order_details=order_details)

    except Exception as e:
        flash(f'Ошибка при загрузке заказов: {e}', 'error')
        return redirect(url_for('home'))

# Оформление заказа
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('Для оформления заказа необходимо войти в систему.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            user_id = session['user_id']

            # Получение товаров из корзины
            conn = get_db_connection()
            cart_items = conn.execute(
                """
                SELECT Cart.CartID, Products.ProductID, Products.ProductName, Products.Price, Cart.Quantity, Products.StockQuantity
                FROM Cart
                JOIN Products ON Cart.ProductID = Products.ProductID
                WHERE Cart.UserID = ?
                """,
                (user_id,)
            ).fetchall()

            if not cart_items:
                flash('Ваша корзина пуста!', 'error')
                return redirect(url_for('cart'))

            # Проверка наличия товаров на складе
            for item in cart_items:
                if item['StockQuantity'] < item['Quantity']:
                    flash(f'Товар "{item["ProductName"]}" недоступен в нужном количестве!', 'error')
                    return redirect(url_for('cart'))

            # Создание заказа
            total_price = sum(item['Price'] * item['Quantity'] for item in cart_items)
            delivery_address = request.form['delivery_address']
            payment_method = request.form['payment_method']

            conn.execute(
                "INSERT INTO Orders (UserID, OrderDate, Status, TotalAmount, PaymentMethod, DeliveryAddress) VALUES (?, datetime('now'), ?, ?, ?, ?)",
                (user_id, 'pending', total_price, payment_method, delivery_address)
            )
            order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Сохранение элементов заказа и уменьшение количества товаров на складе
            for item in cart_items:
                conn.execute(
                    "INSERT INTO OrderItems (OrderID, ProductID, Quantity, UnitPrice) VALUES (?, ?, ?, ?)",
                    (order_id, item['ProductID'], item['Quantity'], item['Price'])
                )
                conn.execute(
                    "UPDATE Products SET StockQuantity = StockQuantity - ? WHERE ProductID = ?",
                    (item['Quantity'], item['ProductID'])
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
    if session.get('role') != 'admin':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('home'))

    try:
        product_name = request.form['product_name']
        price = request.form['price']
        category_id = request.form['category_id']
        manufacturer = request.form['manufacturer']
        stock_quantity = request.form['stock_quantity']
        compatibility = request.form['compatibility']
        description = request.form['description']
        image = request.files.get('image')  # Получаем файл изображения

        # Сохранение изображения
        filename = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO Products 
            (ProductName, Price, CategoryID, Manufacturer, StockQuantity, Compatibility, Description, Image) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (product_name, price, category_id, manufacturer, stock_quantity, compatibility, description, filename)
        )
        conn.commit()
        flash('Товар успешно добавлен!', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('admin_panel'))

# Редактирование товара
@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    # Проверка прав доступа
    if session.get('role') != 'admin':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('home'))

    try:
        conn = get_db_connection()
        product = conn.execute(
            "SELECT * FROM Products WHERE ProductID = ?", (product_id,)
        ).fetchone()

        if not product:
            flash('Товар не найден!', 'error')
            return redirect(url_for('admin_panel'))

        if request.method == 'POST':
            # Обработка данных формы (POST)
            product_name = request.form['product_name']
            price = request.form['price']
            category_id = request.form['category_id']
            manufacturer = request.form['manufacturer']
            stock_quantity = request.form['stock_quantity']
            compatibility = request.form['compatibility']
            description = request.form['description']
            image = request.files.get('image')

            # Логика сохранения нового изображения (если загружено)
            filename = product['Image']  # По умолчанию оставляем старое изображение
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Обновление данных товара в базе данных
            conn.execute(
                """
                UPDATE Products 
                SET ProductName = ?, Price = ?, CategoryID = ?, Manufacturer = ?, 
                    StockQuantity = ?, Compatibility = ?, Description = ?, Image = ?
                WHERE ProductID = ?
                """,
                (product_name, price, category_id, manufacturer, stock_quantity, 
                 compatibility, description, filename, product_id)
            )
            conn.commit()

            flash('Товар успешно обновлен!', 'success')
            return redirect(url_for('admin_panel'))

        # Для GET-запроса: отображение формы редактирования
        categories = conn.execute("SELECT * FROM Categories").fetchall()
        conn.close()

        return render_template('edit_product.html', product=product, categories=categories)

    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
        return redirect(url_for('admin_panel'))

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