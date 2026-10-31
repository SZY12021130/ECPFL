# This sample should be run after make libMKHE.a file in lib folder

#---------------------------------------------------
# All Target
all: clean TestMKHE3

# Tool invocations
TestMKHE3:
	@echo 'Building target: $@'
	@echo 'Invoking: GCC C++ Linker'
	g++ mkRun.cpp -o TestMKHE3 -L/usr/local/lib ../lib/libMKHE.a -lntl -lgmp -lm -std=c++11 -O2 -I/../src -pthread
	@echo 'Finished building target: $@'
	@echo ' '

# Other Targets
clean:
	rm -rf TestMKHE3

# run:
# 	./TestMKHE3