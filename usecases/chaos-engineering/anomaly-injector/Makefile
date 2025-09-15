default:
	g++ -fopenmp -o cpu cpu.cpp
	g++ -fopenmp -o cpu-all-cores cpu-all-cores.cpp
	g++ -fopenmp -o cpu-all-cores-with-affinity cpu-all-cores-with-affinity.cpp
	g++ -fopenmp -o mem mem.c
	g++ -o l3 l3.c -lrt

clean:
	rm mem
	rm cpu
	rm l3
	rm cpu-all-cores
	rm cpu-all-cores-with-affinity
