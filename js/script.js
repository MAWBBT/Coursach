document.addEventListener('DOMContentLoaded', function() {
    // Загрузка товаров на странице каталога
    if (window.location.pathname.includes('catalog.html')) {
        fetch('php/get_products.php')
            .then(response => response.json())
            .then(data => {
                const productsContainer = document.getElementById('products');
                data.forEach(product => {
                    const productElement = document.createElement('div');
                    productElement.className = 'product';
                    productElement.innerHTML = `
                        <img src="images/${product.image}" alt="${product.name}">
                        <h2>${product.name}</h2>
                        <p>${product.description}</p>
                        <p>Цена: ${product.price} руб.</p>
                        <button onclick="addToCart(${product.id})">Добавить в корзину</button>
                    `;
                    productsContainer.appendChild(productElement);
                });
            });
    }

    // Загрузка товаров в корзине
    if (window.location.pathname.includes('cart.html')) {
        fetch('php/get_cart.php')
            .then(response => response.json())
            .then(data => {
                const cartItemsContainer = document.getElementById('cart-items');
                data.forEach(item => {
                    const itemElement = document.createElement('div');
                    itemElement.className = 'cart-item';
                    itemElement.innerHTML = `
                        <h2>${item.name}</h2>
                        <p>Цена: ${item.price} руб.</p>
                    `;
                    cartItemsContainer.appendChild(itemElement);
                });
            });
    }
});

function addToCart(productId) {
    fetch('php/add_to_cart.php', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ productId: productId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Товар добавлен в корзину');
        } else {
            alert(data.message || 'Ошибка при добавлении товара в корзину');
        }
    });
}

function checkout() {
    fetch('php/checkout.php', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Оплата прошла успешно');
            window.location.reload(); // Обновляем страницу корзины
        } else {
            alert('Ошибка при оплате');
        }
    });
}

fetch('php/get_products.php')
    .then(response => response.json())
    .then(data => {
        console.log(data); // Вывод данных в консоль
        const productsContainer = document.getElementById('products');
        data.forEach(product => {
            const productElement = document.createElement('div');
            productElement.className = 'product';
            productElement.innerHTML = `
                <img src="images/${product.image}" alt="${product.name}">
                <h2>${product.name}</h2>
                <p>${product.description}</p>
                <p>Цена: ${product.price} руб.</p>
                <button onclick="addToCart(${product.id})">Добавить в корзину</button>
            `;
            productsContainer.appendChild(productElement);
        });
    })
    .catch(error => console.error('Error:', error));