# Сервер та База Даних (pi_server)

Документація модулів, що розгортаються на Raspberry Pi для забезпечення обчислень та зберігання сигнатур.

---

## PiServerService

Основний TCP сервер для передачі результатів аналізу клієнтам.
::: pi_server.pi_server_service

---

## DatabaseService

Взаємодія з базою даних SQLite через SQLAlchemy ORM.
::: pi_server.database_service

---

## PopulateDbUtil

Скрипт для початкового наповнення бази даних тестовими сигнатурами.
::: pi_server.populate_db_util

---

## RunServer

Точка входу для запуску серверного модуля.
::: pi_server.run_server
