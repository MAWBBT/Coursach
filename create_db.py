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
                ProductName TEXT NOT NULL,
                Description TEXT,
                Price DECIMAL(10, 2) NOT NULL,
                CategoryID INTEGER,
                Manufacturer TEXT,
                StockQuantity INTEGER DEFAULT 0,
                Compatibility TEXT,
                Image TEXT,
                FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS Orders (
                OrderID INTEGER PRIMARY KEY AUTOINCREMENT,
                UserID INTEGER,
                OrderDate DATETIME,
                Status TEXT DEFAULT 'pending',
                TotalAmount DECIMAL(10, 2),
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
                UnitPrice DECIMAL(10, 2),
                FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
                FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS Cart (
                CartID INTEGER PRIMARY KEY AUTOINCREMENT,
                UserID INTEGER,
                ProductID INTEGER,
                Quantity INTEGER,
                FOREIGN KEY (UserID) REFERENCES Users(UserID),
                FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
            );
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
    ]
    for login, password_hash in users:
        try:
            cursor.execute("INSERT INTO Users (Login, PasswordHash, Role) VALUES (?, ?, ?)",
                           (login, password_hash, "admin" if login == "admin" else "client"))
        except sqlite3.IntegrityError:
            print(f"Пользователь с логином '{login}' уже существует. Пропускаем добавление.")

# Запуск функции создания базы данных и таблиц
if __name__ == "__main__":
    create_database_and_tables()