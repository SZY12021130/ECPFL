#include <iostream>
#include "../src/MKPlaintext.h"
#include "cpp_called2.h"

// 命令行输入 g++ -o libpycallcpp.so -shared -fPIC cpp_called.cpp cpp_called2.cpp
// 将cpp_called.cpp 和 cpp_called2.cpp 两个文件打包为一个动态链接库 libpycallcpp.so
// 头文件放在cpp_called.h 和 cpp_called2.h

void TestLib2::displayClass1() {
  TestLib::display(100);
}

extern "C" {
    TestLib2 obj2;
    void displayClass1() {
      obj2.displayClass1();
    }
}