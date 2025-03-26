import sqlite3
from werkzeug.security import generate_password_hash

# Создание базы данных и таблиц
def create_database_and_tables():
    try:
        # Подключение к SQLite (файл базы данных будет создан автоматически)
        connection = sqlite3.connect('auto_parts_store.db')
        cursor = connection.cursor()

        # SQL-запросы для создания таблиц
        queries = [
            """
            CREATE TABLE IF NOT EXISTS Users (
                UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                Login TEXT UNIQUE,
                PasswordHash TEXT,
                Role TEXT CHECK(Role IN ('client', 'admin')) DEFAULT 'client'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS Categories (
                CategoryID INTEGER PRIMARY KEY AUTOINCREMENT,
                CategoryName TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS Products (
                ProductID INTEGER PRIMARY KEY AUTOINCREMENT,
                ProductName TEXT,
                Description TEXT,
                Price REAL,
                CategoryID INTEGER,
                Manufacturer TEXT,
                StockQuantity INTEGER,
                Compatibility TEXT,
                FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS Orders (
                OrderID INTEGER PRIMARY KEY AUTOINCREMENT,
                UserID INTEGER,
                OrderDate DATETIME,
                Status TEXT CHECK(Status IN ('pending', 'processing', 'delivered')),
                TotalAmount REAL,
                PaymentMethod TEXT,
                DeliveryAddress TEXT,
                FOREIGN KEY (UserID) REFERENCES Users(UserID)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS OrderItems (
                OrderItemID INTEGER PRIMARY KEY AUTOINCREMENT,
                OrderID INTEGER,
                ProductID INTEGER,
                Quantity INTEGER,
                UnitPrice REAL,
                FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
                FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS Reviews (
                ReviewID INTEGER PRIMARY KEY AUTOINCREMENT,
                UserID INTEGER,
                ProductID INTEGER,
                ReviewText TEXT,
                Rating INTEGER CHECK(Rating BETWEEN 1 AND 5),
                ReviewDate DATETIME,
                FOREIGN KEY (UserID) REFERENCES Users(UserID),
                FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
            )
            """
        ]

        # Выполнение запросов для создания таблиц
        for query in queries:
            cursor.execute(query)
        print("Таблицы успешно созданы.")

        # Заполнение таблиц тестовыми данными
        populate_data(cursor)

        # Сохранение изменений и закрытие соединения
        connection.commit()

    except sqlite3.Error as e:
        print(f"Ошибка при работе с SQLite: {e}")

    finally:
        if connection:
            connection.close()
            print("Подключение к SQLite закрыто.")

# Заполнение таблиц тестовыми данными
def populate_data(cursor):
    # Добавление данных в таблицу Users
    users = [
        ("admin", generate_password_hash("admin_password")),  # Логин: admin, Пароль: admin_password
        ("user", generate_password_hash("user_password"))     # Логин: user, Пароль: user_password
    ]
    for login, password_hash in users:
        try:
            cursor.execute("INSERT INTO Users (Login, PasswordHash, Role) VALUES (?, ?, ?)",
                           (login, password_hash, "admin" if login == "admin" else "client"))
        except sqlite3.IntegrityError:
            print(f"Пользователь с логином '{login}' уже существует. Пропускаем добавление.")

    # Добавление данных в таблицу Categories
    categories = [("Тормозные системы",), ("Двигатели",), ("Подвеска",)]
    for category_name in categories:
        try:
            cursor.execute("INSERT INTO Categories (CategoryName) VALUES (?)", category_name)
        except sqlite3.IntegrityError:
            print(f"Категория '{category_name[0]}' уже существует. Пропускаем добавление.")

    # Добавление данных в таблицу Products
    products = [
        ("Тормозные колодки", "Описание тормозных колодок", 1500.00, 1, "Bosch", 50, "Совместимо с Toyota Camry"),
        ("Масляный фильтр", "Описание масляного фильтра", 300.00, 2, "Mann", 100, "Совместимо с BMW X5"),
        ("Стойки стабилизатора", "Описание стоек стабилизатора", 800.00, 3, "Lemforder", 30, "Совместимо с Mercedes E-Class")
    ]
    for product in products:
        try:
            cursor.execute("""
                INSERT INTO Products (ProductName, Description, Price, CategoryID, Manufacturer, StockQuantity, Compatibility)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, product)
        except sqlite3.IntegrityError:
            print(f"Товар '{product[0]}' уже существует. Пропускаем добавление.")

# Запуск функции создания базы данных и таблиц
if __name__ == "__main__":
    create_database_and_tables()