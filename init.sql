USE `flowerstore`;

CREATE TABLE `users` (
    `user_id` int PRIMARY KEY AUTO_INCREMENT,
    `username` varchar(255),
    `email` varchar(255),
    `first_name` varchar(255),
    `last_name` varchar(255),
    `phone_number` varchar(255),
    `date_of_birth` date,
    `created_at` datetime,
    `updated_at` datetime,
    `role` varchar(255),
    `password_hash` varchar(255),
    `disabled` boolean
);

CREATE TABLE `addresses` (
    `address_id` int PRIMARY KEY AUTO_INCREMENT,
    `user_id` int,
    `address` varchar(255),
    `city` varchar(255),
    `state` varchar(255),
    `zip_code` varchar(255),
    `country` varchar(255),
    `is_current` boolean
);

CREATE TABLE `categories` (
    `category_id` int PRIMARY KEY AUTO_INCREMENT,
    `name` varchar(255)
);

CREATE TABLE `products` (
    `product_id` int PRIMARY KEY AUTO_INCREMENT,
    `category_id` int,
    `name` varchar(255),
    `description` text,
    `price` decimal,
    `stock_quantity` int,
    `product_image` varchar(255)
);

CREATE TABLE `cart` (
    `cart_id` int PRIMARY KEY AUTO_INCREMENT,
    `user_id` int
);

CREATE TABLE `cart_items` (
    `cart_item_id` int PRIMARY KEY AUTO_INCREMENT,
    `cart_id` int,
    `product_id` int,
    `quantity` int
);

CREATE TABLE `orders` (
    `order_id` int PRIMARY KEY AUTO_INCREMENT,
    `user_id` int,
    `address_id` int,
    `order_date` datetime,
    `status` varchar(255),
    `total_price` decimal
);

CREATE TABLE `order_items` (
    `order_item_id` int PRIMARY KEY AUTO_INCREMENT,
    `order_id` int,
    `product_id` int,
    `quantity` int,
    `price_per_unit` decimal
);

ALTER TABLE
    `addresses`
ADD
    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`);

ALTER TABLE
    `products`
ADD
    FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`);

ALTER TABLE
    `cart`
ADD
    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`);

ALTER TABLE
    `cart_items`
ADD
    FOREIGN KEY (`cart_id`) REFERENCES `cart` (`cart_id`);

ALTER TABLE
    `cart_items`
ADD
    FOREIGN KEY (`product_id`) REFERENCES `products` (`product_id`);

ALTER TABLE
    `orders`
ADD
    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`);

ALTER TABLE
    `orders`
ADD
    FOREIGN KEY (`address_id`) REFERENCES `addresses` (`address_id`);

ALTER TABLE
    `order_items`
ADD
    FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`);

ALTER TABLE
    `order_items`
ADD
    FOREIGN KEY (`product_id`) REFERENCES `products` (`product_id`);