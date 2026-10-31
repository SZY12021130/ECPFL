//Python调用c++(类）动态链接库
#include <iostream>
#include "../src/MKPlaintext.h"
#include "cpp_called.h"

// using namespace std;
 
// class TestLib
// {
//   public:
//   // long logN=6; long logP=120; long logQ=150; long logq0=32; long logSlots=3; 
// 	// long slots2=1; long CLIENT=0; bool isComplex=true; long numAgg=1; long numClients=5;
//   // MKPlaintext msg = MKPlaintext(ZZX::zero(), logP, logQ, logq0, logSlots, slots2, isComplex, numAgg);

//   public:
//       void display();
//       void display(int a);
//       void display(long b);
//       void display(float c);
//       void display(double d);
//       // void displayPlaintext();
// };

// class TestLib2:public TestLib
// {
//   public:
//         TestLib2() {
//           cout << "class TestLib2!" << endl;
//         }
//         ~TestLib2() {}
//   public:
//         void displayClass1();
// };

void TestLib::display() {
    cout<<"First display"<<endl;
}
 
void TestLib::display(int a) {
    cout<<"Second display:"<<a<<endl;
}

void TestLib::display(long b) {
    cout<<"Third display:"<<b<<endl;
}

void TestLib::display(float c) {
    cout<<"Fourth display:"<<c<<endl;
}

void TestLib::display(double d) {
    cout<<"Double data display:"<<d<<endl;
}

// void TestLib::displayPlaintext() {
//   cout << "The plaintext is " << msg.mx << endl;
// } 

// void TestLib2::displayClass1() {
//   TestLib::display(100);
// }

extern "C" {
    TestLib obj;
    void display() {
        obj.display();
      }
    void display_int(int a) {
        obj.display(a);
      }
    void display_long(long a) {
        obj.display(a);
      }
    void display_float(float a) {
        obj.display(a);
      }
    void display_double(double a) {
        obj.display(a);
      }
    // void displayPlaintext() {
    //   obj.displayPlaintext();
    // }
    // TestLib2 obj2;
    // void displayClass1() {
    //   obj2.displayClass1();
    // }
}
