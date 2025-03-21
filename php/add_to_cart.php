<?php
session_start(); // Начинаем сессию
include 'db_connect.php';

$productId = $_POST['productId'];

// Если корзина не существует, создаем её
if (!isset($_SESSION['cart'])) {
    $_SESSION['cart'] = [];
}

// Добавляем товар в корзину
if (!in_array($productId, $_SESSION['cart'])) {
    $_SESSION['cart'][] = $productId;
    echo json_encode(['success' => true]);
} else {
    echo json_encode(['success' => false, 'message' => 'Товар уже в корзине']);
}

$conn = null; // Закрываем соединение
?>