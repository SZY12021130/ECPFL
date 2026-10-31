/*
* Copyright (c) by CryptoLab inc.
* Copyright (c) 2022 Your Pengcheng Lab.
* Modified extensively by Jiahui Wu, Pengcheng Laboratory, Aug. 2022
* This program is licensed under a
* Creative Commons Attribution-NonCommercial 3.0 Unported License.
* You should have received a copy of the license along with this
* work.  If not, see <http://creativecommons.org/licenses/by-nc/3.0/>.
*/

#include "../src/MKHE.h"
#include "../src/InferenceFun.h"

using namespace std;
using namespace NTL;

int main() {

	// long logN=6; long logP=110; long logQ=120; long logq0=32; long logSlots=3; 
	// long logN=6000; long logP=240; long logQ=256; long logq0=32; long logSlots=5998;
	// long CLIENT=0; bool isComplex=true; long numAgg=1; long numClients=5;
	// long pad = log2(numClients) + 1 + 1;
	// long slots2 = logP / (logq0 + pad) - 1; // -1 表示空余1 slot 用于打包过程中额外打包一个系数为0的多项式
	// MKTestScheme::testMKHETimeWithPack(logN, logP, logQ, logq0, logSlots, slots2, isComplex, numAgg, numClients);
	// MKTestScheme::testMKHETimeWithoutPack(logN, logP, logQ, logq0, logSlots, slots2, isComplex, numAgg, numClients);	
	// MKTestScheme::testMKPackEncryptADD(logN, logP, logQ, logq0, logSlots, slots2, isComplex, numAgg, numClients);	
	
	/*
	 * Params: (long logN, long logP, long logQ, long logq0, long logSlots, long slots2, long CLIENT, bool isComplex, long numAgg, long numClients)
	 * test result: pass
	 * cx = Enc(mx) = (mx + ex*Px + bx) % Q, where mkEncode(mx)\in R_q0, (ex,bx)\in R_Q^2, and P < Q.
	 * m'(x) = Dec(cx) = ((cx - bx) % Q) % P.
	 * slots: the number of complexes in a integral coefficient (encoded) polynomial
	 * slots2: the number of polynomials in a packed polynomial
	 * numClients: utilized in packing and unpacking processes, to determine 0-pad bits.
	 * numAgg: utilized in encoding and decoding processes, to determine the number of q0 that added to a encoded polynomial to change its coefficients to positive integers.
	 */		
	// long logN=6; long logP=120; long logQ=150; long logq0=32; long logSlots=3; 
	// long slots2=1; long CLIENT=0; bool isComplex=true; long numAgg=1; long numClients=5; // numClients: 打包多项式个数
	// MKTestScheme::testMKPackEncrypt(logN, logP, logQ, logq0, logSlots, slots2, CLIENT, isComplex, numAgg, numClients);

	// // long logN=6; long logP=110; long logQ=120; long logq0=32; long logSlots=3; 
	// long logN=6000; long logP=240; long logQ=256; long logq0=32; long logSlots=5998;
	// long CLIENT=0; bool isComplex=true; long numAgg=1; long numClients=5;
	// long pad = log2(numClients) + 1 + 1;
	// long slots2 = logP / (logq0 + pad) - 1; // -1 表示空余1 slot 用于打包过程中额外打包一个系数为0的多项式
	// cout << "---------"<<endl;
	// MKTestScheme::testMKPackEncryptADD();

	/*
	cout << "---------"<< endl;
	double eta = 0.001;
	map<long,complex<double>*> mvecs1; // clienti的原始消息
	map<long,complex<double>*> mvecs2;
	map<long,complex<double>*> mvecs3;
	map<long,complex<double>*> mvecs4;
	map<long,complex<double>*> mvecs5;
	InferenceFun inferenceFun;
	for (long i = 0; i < inferenceFun.slots2; i++) {
		mvecs1[i] = EvaluatorUtils::randomComplexArray(inferenceFun.slots);
		mvecs2[i] = EvaluatorUtils::randomComplexArray(inferenceFun.slots);
		mvecs3[i] = EvaluatorUtils::randomComplexArray(inferenceFun.slots);
		mvecs4[i] = EvaluatorUtils::randomComplexArray(inferenceFun.slots);
		mvecs5[i] = EvaluatorUtils::randomComplexArray(inferenceFun.slots);
	}	
	inferenceFun.mkPackEncryptADD_complexMap(mvecs1, mvecs2, mvecs3, mvecs4, mvecs5);
	// */

	// // test PRF running time
	// TimeUtils timeutils;
	// long logN=15; // logrithm number of polynomial coefficients
	// long logQ=478; // Binary size of a ciphertext
	// double sigma = 3.2;
	// long N = 1 << logN;
	// ZZ Q = power2_ZZ(logQ);
	// ZZX px, ex, pex; 
	// timeutils.start("Test polynomial multiplication with 1300 times!");

	// NumUtils::sampleGauss(ex, N, sigma);
	// NumUtils::sampleGauss(px, N, sigma);
	// for (long i = 0; i < 1300; i++) {
	// 	Ring2Utils::mult(pex, px, ex, Q, N);
	// }
	// timeutils.stop("Test polynomial multiplication with 1300 times!");

	// timeutils.start("Test polynomial multiplication with 1500 times!");
	// for (long i = 0; i < 1500; i++) {
	// 	// NumUtils::sampleGauss(ex, N, sigma);
	// 	// NumUtils::sampleGauss(px, N, sigma);
	// 	Ring2Utils::mult(pex, px, ex, Q, N);
	// }
	// timeutils.stop("Test polynomial multiplication with 1500 times!");



	// /* encrypt gradients, aggregate them, and decrypt the aggregation gradient
	double eta = 1;
	long vsize = 101770;
	// long vsize = 1250000;
	// long vsize = 4020000;
	double* rmvec1 = new double[vsize];
	double* rmvec2 = new double[vsize];
	double* rmvec3 = new double[vsize];
	double* rmvec4 = new double[vsize];
	double* rmvec5 = new double[vsize];
	for (long i = 0; i < vsize; i++) {
		rmvec1[i] = EvaluatorUtils::randomReal()*eta;
		rmvec2[i] = EvaluatorUtils::randomReal()*eta;
		rmvec3[i] = EvaluatorUtils::randomReal()*eta;
		rmvec4[i] = EvaluatorUtils::randomReal()*eta;
		rmvec5[i] = EvaluatorUtils::randomReal()*eta;
	}
	// 存原始double型数组的聚合, original mvec ==> rmvec
	double* longsize_rmvecAdd = new double[vsize];
	for (long i = 0; i < vsize; i++) {
		longsize_rmvecAdd[i] = rmvec1[i] + rmvec2[i] + rmvec3[i] + rmvec4[i] + rmvec5[i];
	}	
	double * longsize_dmvecAdd = InferenceFun::mkPackEncryptADD_doubleArray_longSize(rmvec1, rmvec2, rmvec3, rmvec4, rmvec5, vsize);
	// double * longsize_dmvecAdd = InferenceFun::mkUnpkEncryptADD_doubleArray_longSize(rmvec1, rmvec2, rmvec3, rmvec4, rmvec5, vsize);
	// StringUtils::showcompare(longsize_rmvecAdd, longsize_dmvecAdd, vsize, "val");
	// */	

	/*
	cout << "---------"<< endl;
	complex<double>* mvec1; // clienti的原始消息
	complex<double>* mvec2;
	complex<double>* mvec3;
	complex<double>* mvec4;
	complex<double>* mvec5;
	long logSlots = 13;
	long slots = (1 << logSlots);
	mvec1 = EvaluatorUtils::randomComplexArray(slots);
	mvec2 = EvaluatorUtils::randomComplexArray(slots);
	mvec3 = EvaluatorUtils::randomComplexArray(slots);
	mvec4 = EvaluatorUtils::randomComplexArray(slots);
	mvec5 = EvaluatorUtils::randomComplexArray(slots);
	InferenceFun::testMKPackEncryptADD(mvec1, mvec2, mvec3, mvec4, mvec5);
	*/

	/*
	long logSlots = 13;
	long slots = (1 << logSlots);
	double* mvec1 = new double[2*slots];
	double* mvec2 = new double[2*slots];
	double* mvec3 = new double[2*slots];
	double* mvec4 = new double[2*slots];
	double* mvec5 = new double[2*slots];
	for (long i = 0; i < 2*slots; i++) {
		mvec1[i] = EvaluatorUtils::randomReal();
		mvec2[i] = EvaluatorUtils::randomReal();
		mvec3[i] = EvaluatorUtils::randomReal();
		mvec4[i] = EvaluatorUtils::randomReal();
		mvec5[i] = EvaluatorUtils::randomReal();
	}
	InferenceFun::mkUnpkEncryptADD_doubleArray(mvec1, mvec2, mvec3, mvec4, mvec5);
	*/

	/*
	double eta = 0.001;
	long vsize = 105214;
	double* rmvec1 = new double[vsize];
	double* rmvec2 = new double[vsize];
	double* rmvec3 = new double[vsize];
	double* rmvec4 = new double[vsize];
	double* rmvec5 = new double[vsize];
	for (long i = 0; i < vsize; i++) {
		rmvec1[i] = EvaluatorUtils::randomReal()*eta;
		rmvec2[i] = EvaluatorUtils::randomReal()*eta;
		rmvec3[i] = EvaluatorUtils::randomReal()*eta;
		rmvec4[i] = EvaluatorUtils::randomReal()*eta;
		rmvec5[i] = EvaluatorUtils::randomReal()*eta;
	}
	double* longsize_rmvecAdd = new double[vsize];
	for (long i = 0; i < vsize; i++) {
		longsize_rmvecAdd[i] = rmvec1[i] + rmvec2[i] + rmvec3[i] + rmvec4[i] + rmvec5[i];
	}	
	double* longsize_dmvecAdd = InferenceFun::mkUnpkEncryptADD_doubleArray_longSize(rmvec1, rmvec2, rmvec3, rmvec4, rmvec5, vsize);
	StringUtils::showcompare(longsize_mvecAdd, longsize_dmvecAdd, vsize, "val");
	*/

	/*
	 * Params: (long logN, long logP, long logQ, long logq0, long logSlots, long slots2, long CLIENT, bool isComplex, long numAgg)
	 * Suggested: 13, 30, 65, 15, 3, 1, 1, 0
	 */	
	// MKTestScheme::testMKEncryptBatch(6, 80, 100, 32, 3, 2, 0, true, 1);
	// MKTestScheme::testMKEncryptBatch(6, 20, 30, 10, 3, 1, 0, true, 1);
	// MKTestScheme::testMKEncryptBatch(6000, 200, 256, 32, 5998, 1, 0, true, 1);

	/*
	 * Params: (long logN, long logP, long logQ, long logq0, long logSlots, long slots2, long CLIENT, bool isComplex, long numAgg)
	 * Suggested: 13, 65, 30, 15, 3, 0, true, 1
	 * test result: pass (只针对实数的实部进行了加解密)
	 */	
	// MKTestScheme::testMKEncryptIntegers(6, 20, 30, 10, 3, 1, 0, true, 1);
	// MKTestScheme::testMKEncryptIntegersADD(6, 50, 65, 10, 3, 1, 0, true, 1); // XXX

	/*
	 * Params: (long logN, long logp, long logq, long logq0, long logSlots, long slots2, bool isComplex, long numAgg)
	 * Suggested: 13, 65, 30, 15, 3, 1, true, 1
	 * text result: double pass
	 */	
	// MKTestScheme::testMKEncodeAndDecode(6, 10, 30, 10, 3, 1, true, 1);
	// MKTestScheme::testMKEncodeAndDecodeADD(6, 10, 30, 10, 3, 1, true, 1);
	// MKTestScheme::testMKEncodeAndDecode2(6, 20, 30, 10, 3, 1, true, 1);

	/*
	 * Params: (long logN, long logP, long logQ, long logq0, long logSlots, long slots2, long isComplex, long numAgg)
	 * 可最多编码slots=N-1个real numbers 到环Z_Q/(X^N+1)。
	 * Suggested: 13, 65, 30, 15, 3, 1, true, 5
	 */		
	// MKTestScheme::testMKadd(6, 20, 30, 10, 3, 1, true, 1);
	// MKTestScheme::testMKadd(6, 110, 256, 32, 3, 1, true, 1);
	// MKTestScheme::testMKadd(6000, 220, 256, 100, 5998, 1, true, 1);

	// long logN=6; long logP=150; long logQ=300; long logq0=32; long logSlots=3; 
	// long slots2=1; long CLIENT=0; bool isComplex=true; long numAgg=1; long numClients=5;

	// long logN=6; long logP=120; long logQ=150; long logq0=32; long logSlots=3; 
	// long slots2=1; long CLIENT=0; bool isComplex=true; long numAgg=1; long numClients=5;
	// MKTestScheme::testMKadd(logN, logP, logQ, logq0, logSlots, slots2, isComplex, numAgg);


	return 0;
}
