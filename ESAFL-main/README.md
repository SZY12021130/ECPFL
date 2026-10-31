# MKHE
MKHE is software library that implements multi-key additively homomorphic encryption (AHE) that supports fixed point arithmetics.
This library supports approximate operations between rational numbers.
The approximate error depends on some parameters and almost same with floating point operation errors.
This library is written refering to the code of HEAAN on the paper "Homomorphic Encryption for Arithmetic of Approximate Numbers" (https://eprint.iacr.org/2016/421.pdf).
The scheme in this library is 

This library does not contain bootstrapping

This library is written by c++ and using NTL library (http://www.shoup.net/ntl/) and GMP library (https://gmplib.org/).

## How to use this library uniquely?
### 1. Build a static library/Running test functions
You can make a static library by typing "make all" in the /lib directory. After successful compilation you can find a static library libMKHE.a in the /lib directory.

After you build libMKHE.a, you can run a test program in the /run directory. In run.cpp, you need uncomment tests you need and type "make" in the /run directory. This command will run exe file "MKHE".

We checked the program was working well on Ubuntu 18.04.2 LTS. You need to install NTL (with GMP), pThread, libraries.

## How to be called by third-party languages such as Python
### 1. Build a dynamic library/calling the dynamic library
You can first make static libraries with "pic" attribute (".o" files) of all cpp files in MKHE library by typing "g++ -c -fPIC InferenceFun.cpp MKScheme.cpp MKSecretKey.cpp EvaluatorUtils.cpp MKCiphertext.cpp MKey.cpp MKPlaintext.cpp NumUtils.cpp Ring2Utils.cpp StringUtils.cpp TimeUtils.cpp" in the /src directory, and the generated static libraries are InferenceFun.o MKScheme.o MKSecretKey.o EvaluatorUtils.o MKCiphertext.o MKey.o MKPlaintext.o NumUtils.o Ring2Utils.o StringUtils.o TimeUtils.o; 

You should then make static libraries with "pic" attribute of NTL and GMP libraries to generate ".o" files (We have put all these static libraries in the /so/build directory);

Finally, you can make a integrated dynamic library of MKHE, NTL, and GMP libraries by typing "g++ -o libMKHE.so -shared -fPIC *.o" in the /so/build directory.
After successful compilation you can call the dynamic library "libMKHE.so" in a python file as follows 
"dll = ctypes.cdll.LoadLibrary
lib = dll('/xxx/libMKHE.so')
lib.mkUnpkEncryptADD_doubleArray_longSize(double* mvec1, double* mvec2, double* mvec3, double* mvec4, double* mvec5, long vsize)"

## License
Copyright (c) by CryptoLab inc.

Copyright (c) 2022 Pengcheng Lab.

Modified extensively by Jiahui Wu, Pengcheng Laboratory, Aug. 2022

This program is licensed under a Creative Commons Attribution-NonCommercial 3.0 Unported License.

You should have received a copy of the license along with this work.  If not, see <http://creativecommons.org/licenses/by-nc/3.0/>.
