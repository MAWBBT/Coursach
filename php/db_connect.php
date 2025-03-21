<?php
$dsn = "odbc:store_access"; // Имя источника данных ODBC
$user = ""; // Пользователь (обычно не требуется для Access)
$password = ""; // Пароль (обычно не требуется для Access)

try {
    $conn = new PDO($dsn, $user, $password);
    $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    die("Connection failed: " . $e->getMessage());
}
?>