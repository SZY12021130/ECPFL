
#ifndef TEST_MKTEST_H_
#define TEST_MKTEST_H_

using namespace std;

class TestLib
{
  public:
  // long logN=6; long logP=120; long logQ=150; long logq0=32; long logSlots=3; 
	// long slots2=1; long CLIENT=0; bool isComplex=true; long numAgg=1; long numClients=5;
  // MKPlaintext msg = MKPlaintext(ZZX::zero(), logP, logQ, logq0, logSlots, slots2, isComplex, numAgg);

  public:
      void display();
      void display(int a);
      void display(long b);
      void display(float c);
      void display(double d);
      // void displayPlaintext();
};

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

#endif