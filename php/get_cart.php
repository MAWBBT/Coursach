<?php
session_start(); // Начинаем сессию
include 'db_connect.php';

$cartItems = [];

if (isset($_SESSION['cart']) && !empty($_SESSION['cart'])) {
    // Преобразуем массив ID товаров в строку для SQL-запроса
    $cartIds = implode(",", $_SESSION['cart']);
    $sql = "SELECT * FROM products WHERE id IN ($cartIds)";
    $stmt = $conn->query($sql);
    $cartItems = $stmt->fetchAll(PDO::FETCH_ASSOC);
}

echo json_encode($cartItems);

$conn = null; // Закрываем соединение
?>