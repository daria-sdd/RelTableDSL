#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

// Реализация strdup, так как Zig может не видеть её в string.h на Windows
char* my_strdup(const char* s) {
    size_t len = strlen(s) + 1;
    char* d = (char*)malloc(len);
    if (d) memcpy(d, s, len);
    return d;
}

// --- Структуры данных ---

typedef struct {
    char* name;
    char* type;
} Column;

typedef struct {
    int* data; 
} Row;

typedef struct {
    char* name;
    Column* columns;
    int col_count;
    Row* rows;
    int row_count;
    int row_capacity;
} Table;

typedef struct {
    int (*fn_ptr)(void* env, void* row);
    void* env_ptr;
} Closure;

// --- API ---

void* rt_create_table(const char* name) {
    Table* t = (Table*)malloc(sizeof(Table));
    t->name = my_strdup(name);
    t->columns = NULL;
    t->col_count = 0;
    t->rows = (Row*)malloc(sizeof(Row) * 10);
    t->row_count = 0;
    t->row_capacity = 10;
    return (void*)t;
}

void rt_add_column(void* table, const char* col_name, const char* type) {
    Table* t = (Table*)table;
    t->col_count++;
    t->columns = (Column*)realloc(t->columns, sizeof(Column) * t->col_count);
    t->columns[t->col_count - 1].name = my_strdup(col_name);
    t->columns[t->col_count - 1].type = my_strdup(type);
}

void rt_add_row(void* table) {
    Table* t = (Table*)table;
    if (t->row_count >= t->row_capacity) {
        t->row_capacity *= 2;
        t->rows = (Row*)realloc(t->rows, sizeof(Row) * t->row_capacity);
    }
    Row* r = &t->rows[t->row_count];
    r->data = (int*)malloc(sizeof(int) * (t->col_count + 1));
    memset(r->data, 0, sizeof(int) * (t->col_count + 1));
    t->row_count++;
}

int rt_get_int(void* row_ptr, const char* col_name) {
    // В упрощенном рантайме возвращаем 42 или значение из данных,
    // если бы мы хранили соответствие колонок строке
    return 42; 
}

void* rt_table_select(void* table, Closure closure) {
    Table* src = (Table*)table;
    Table* res = (Table*)rt_create_table("QueryResult");
    
    for (int i = 0; i < src->col_count; i++) {
        rt_add_column(res, src->columns[i].name, src->columns[i].type);
    }

    for (int i = 0; i < src->row_count; i++) {
        Row* current_row = &src->rows[i];
        // Вызов LLVM функции через указатель
        if (closure.fn_ptr(closure.env_ptr, (void*)current_row)) {
            rt_add_row(res);
            memcpy(res->rows[res->row_count-1].data, current_row->data, sizeof(int) * src->col_count);
        }
    }
    return (void*)res;
}

void rt_write_int(int i) { printf("%d\n", i); }
void rt_write_string(const char* s) { printf("%s\n", s); }
void rt_write_bool(bool b) { printf("%s\n", b ? "true" : "false"); }
void rt_write_float(double d) { printf("%f\n", d); }