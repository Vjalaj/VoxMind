CXX = g++
CXXFLAGS = -I./include -std=c++17 -O2 -Wall

SRC = src/main.cpp
OBJ = $(SRC:.cpp=.o)
TARGET = voxmind.exe

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(OBJ)

clean:
	rm -f $(TARGET) src/*.o

.PHONY: all clean
