// 1. Инициализация таблицы
write("--- [1] Создание таблицы сотрудников ---");
employees = create_table("CompanyDB");

add_column(employees, "id", int);
add_column(employees, "name", string);
add_column(employees, "age", int);
add_column(employees, "salary", int);

// 2. Наполнение данными
add_row(employees, 1, "Alice", 28, 5000);
add_row(employees, 2, "Bob", 17, 1500); // Несовершеннолетний
add_row(employees, 3, "Charlie", 35, 7000);
add_row(employees, 4, "Dave", 16, 1200);  // Несовершеннолетний
add_row(employees, 5, "Eve", 42, 9000);

write("Данные успешно загружены.");

// 3. Тест ЗАМЫКАНИЯ (Closure)
// Мы захватываем переменную 'age_limit' из внешнего скоупа внутрь лямбды
age_limit = 18;
write("--- [2] Фильтрация (Замыкание) ---");
write("Ищем сотрудников старше:");
write(age_limit);

// select использует лямбду, которая обращается к внешней переменной age_limit
adults = select(employees) where (\r => r.age >= age_limit);

write("Фильтрация завершена.");

// 4. Тест ЦИКЛА и УСЛОВИЙ (Арифметика)
write("--- [3] Расчет налогов (Циклы и IF) ---");
total_tax = 0;
tax_rate = 13;

for i = 1 to 3 {
    // Просто имитация расчетов для первых 3 сотрудников
    bonus = i * 100;
    if bonus > 150 {
        write("Высокий бонус для ID:", i);
    }
    total_tax = total_tax + bonus;
}

write("Общая сумма бонусов:");
write(total_tax);

// 5. Тест SWITCH с диапазонами
write("--- [4] Классификация статуса ---");
test_age = 25;

switch test_age {
    case 0 to 17:
        write("Статус: Стажер (Minor)");
    case 18 to 60:
        write("Статус: Специалист (Adult)");
    default:
        write("Статус: Ветеран");
}

// 6. Вызов именованной функции
func calculate_discount(int price, int percent) {
    res = (price * percent) / 100;
    return res;
}

discount = calculate_discount(1000, 10);
write("--- [5] Именованная функция ---");
write("Скидка 10% от 1000:");
write(discount);

write("--- ТЕСТ ЗАВЕРШЕН УСПЕШНО ---");