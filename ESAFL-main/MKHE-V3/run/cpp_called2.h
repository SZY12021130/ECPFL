#ifndef TEST2_MKTEST_H_
#define TEST2_MKTEST_H_

#include "cpp_called.h"
using namespace std;

class TestLib2:public TestLib
{
  public:
        TestLib2() {
          cout << "class TestLib2!" << endl;
        }
        ~TestLib2() {}
  public:
        void displayClass1();
};

#endif