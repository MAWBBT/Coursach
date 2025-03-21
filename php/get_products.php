<?php
include 'db_connect.php';

$sql = "SELECT * FROM products";
$stmt = $conn->query($sql);

$products = $stmt->fetchAll(PDO::FETCH_ASSOC);

echo json_encode($products);

$conn = null; // Закрываем соединение
?>