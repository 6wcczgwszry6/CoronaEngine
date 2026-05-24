# 代码风格指南

本文档概述了 CoronaEngine 项目的代码风格和命名约定。这些规则由 `.clang-format` 和 `.clang-tidy` 强制执行。

## 格式化

我们的格式化规则基于 **Google C++ 风格指南**，并进行了一些调整。相关配置定义在 `.clang-format` 文件中。

- **基础风格**: Google
- **缩进**: 4个空格。
- **制表符**: 禁止使用制表符进行缩进。
- **列宽限制**: 没有硬性的列宽限制。

## 命名约定

命名约定由 `.clang-tidy` 强制执行，旨在确保整个代码库的一致性和可读性。

| 类别                              | 约定            | 示例                                  |
| --------------------------------- | --------------- | ------------------------------------- |
| **类型**                          | `CamelCase`     | `class MyClass;`, `struct MyStruct;`  |
| (类, 结构体, 枚举)                | (大驼峰)        |                                       |
| **函数 / 方法**                   | `snake_case`    | `void my_function();`                 |
|                                   | (下划线命名)    |                                       |
| **变量**                          | `snake_case`    | `int local_variable;`                 |
|                                   | (下划线命名)    |                                       |
| **类/结构体成员**                 | `snake_case_`   | `int member_variable_;`               |
| (私有或保护)                      | (下划线结尾)    |                                       |
| **常量**                          | `kCamelCase`    | `const int kMyConstant = 10;`         |
| (const, constexpr)                | (k+大驼峰)      |                                       |
| **枚举成员**                      | `kCamelCase`    | `enum MyEnum { kEnumValue1, kEnumValue2 };` |
|                                   | (k+大驼峰)      |                                       |
