################################################################################
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
CPP_SRCS += \
../src/MKCiphertext.cpp \
../src/EvaluatorUtils.cpp \
../src/MKey.cpp \
../src/NumUtils.cpp \
../src/MKPlaintext.cpp \
../src/Ring2Utils.cpp \
../src/MKScheme.cpp \
../src/MKSecretKey.cpp \
../src/StringUtils.cpp \
../src/MKTestScheme.cpp \
../src/InferenceFun.cpp \
../src/TimeUtils.cpp 

OBJS += \
./src/MKCiphertext.o \
./src/EvaluatorUtils.o \
./src/MKey.o \
./src/NumUtils.o \
./src/MKPlaintext.o \
./src/Ring2Utils.o \
./src/MKScheme.o \
./src/MKSecretKey.o \
./src/StringUtils.o \
./src/MKTestScheme.o \
./src/InferenceFun.o \
./src/TimeUtils.o 

CPP_DEPS += \
./src/MKCiphertext.d \
./src/EvaluatorUtils.d \
./src/MKey.d \
./src/NumUtils.d \
./src/MKPlaintext.d \
./src/Ring2Utils.d \
./src/MKScheme.d \
./src/MKSecretKey.d \
./src/StringUtils.d \
./src/MKTestScheme.d \
./src/InferenceFun.d \
./src/TimeUtils.d 


# Each subdirectory must supply rules for building sources it contributes
src/%.o: ../src/%.cpp
	@echo 'Building file: $<'
	@echo 'Invoking: GCC C++ Compiler'
	g++ -I/usr/local/include -O3 -c -std=c++11 -pthread -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -o "$@" "$<"
	@echo 'Finished building: $<'
	@echo ' '


