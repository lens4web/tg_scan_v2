<?php
session_start();
if (!isset($_SESSION['logged_in']) || $_SESSION['logged_in'] !== true) {
    http_response_code(403);
    echo json_encode(["error" => "Access denied. Please log in."]);
    exit;
}

// Отключаем стандартный вывод ошибок в браузер (чтобы они не ломали JSON)
ini_set('display_errors', 0);
error_reporting(E_ALL);

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

// Абсолютный путь к файлу
$file_path = '/home/adminamin2/tg_monitor/words.json';

try {
    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        if (!file_exists($file_path)) {
            echo json_encode(["error" => "Файл конфигурации не найден по пути: " . $file_path]);
            exit;
        }
        $content = file_get_contents($file_path);
        if ($content === false) {
            echo json_encode(["error" => "Нет прав на чтение файла. Проверьте chmod."]);
            exit;
        }
        echo $content;
        exit;
    }

    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $raw_data = file_get_contents('php://input');
        $decoded = json_decode($raw_data, true);
        
        if (json_last_error() !== JSON_ERROR_NONE) {
            echo json_encode(["success" => false, "error" => "Неверный формат входящего JSON"]);
            exit;
        }

        $result = file_put_contents($file_path, json_encode($decoded, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
        
        if ($result !== false) {
            echo json_encode(["success" => true, "message" => "Настройки успешно сохранены"]);
        } else {
            echo json_encode(["success" => false, "error" => "Ошибка записи файла. Выполните: sudo chmod 666 " . $file_path]);
        }
        exit;
    }

    echo json_encode(["error" => "Метод не поддерживается"]);
} catch (Exception $e) {
    echo json_encode(["error" => "Внутренняя ошибка сервера: " . $e->getMessage()]);
}
?>