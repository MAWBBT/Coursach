<?php
session_start(); // Начинаем сессию

// Очищаем корзину
unset($_SESSION['cart']);

echo json_encode(['success' => true]);
?>