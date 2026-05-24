# Code Style Guide

This document outlines the code style and naming conventions for the CoronaEngine project. The rules are enforced by `.clang-format` and `.clang-tidy`.

## Formatting

Our formatting rules are based on the **Google C++ Style Guide** with a few modifications. The configuration is defined in the `.clang-format` file.

- **Base Style**: Google
- **Indentation**: 4 spaces.
- **Tabs**: Never use tabs for indentation.
- **Column Limit**: There is no hard column limit.

## Naming Conventions

Naming conventions are enforced by `.clang-tidy`. The goal is to ensure consistency and readability across the codebase.

| Category                  | Convention      | Example                               |
| ------------------------- | --------------- | ------------------------------------- |
| **Types**                 | `CamelCase`     | `class MyClass;`, `struct MyStruct;`  |
| (Classes, Structs, Enums) |                 |                                       |
| **Functions / Methods**   | `snake_case`    | `void my_function();`                 |
| **Variables**             | `snake_case`    | `int local_variable;`                 |
| **Class/Struct Members**  | `snake_case_`   | `int member_variable_;`               |
| (Private or Protected)    |                 |                                       |
| **Constants**             | `kCamelCase`    | `const int kMyConstant = 10;`         |
| (const, constexpr)        |                 |                                       |
| **Enum Members**          | `kCamelCase`    | `enum MyEnum { kEnumValue1, kEnumValue2 };` |
