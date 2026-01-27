#include <iostream>
#include <string>
#include <memory>
#include "TextClassifier.h"
#include "CommandExecutor.h"

int main() {
    std::cout << "Initializing VoxMind Core..." << std::endl;

    // 1. Initialize NLU
    TextClassifier classifier;
    std::string training_file = "training_data.txt";
    if (!classifier.train(training_file)) {
        std::cerr << "Error: Could not load training data from " << training_file << std::endl;
        std::cerr << "Please ensure training_data.txt is in the current directory." << std::endl;
        return 1;
    }

    // 2. Initialize Executor
    std::unique_ptr<CommandExecutor> executor;
    #ifdef _WIN32
        executor = std::make_unique<WindowsExecutor>();
        std::cout << "Platform: Windows Detected" << std::endl;
    #else
        executor = std::make_unique<LinuxExecutor>();
        std::cout << "Platform: Linux/Unix Detected (Simulation Mode)" << std::endl;
    #endif

    std::cout << "\n=== VoxMind CLI (C++ Rewrite) ===" << std::endl;
    std::cout << "Type a command to simulate voice input (or 'exit' to quit)." << std::endl;
    std::cout << "Examples: 'open browser', 'what time is it', 'mute volume'" << std::endl;

    std::string input;
    while (true) {
        std::cout << "\n> ";
        std::getline(std::cin, input);

        if (input == "exit" || input == "quit") {
            break;
        }

        if (input.empty()) continue;

        // 3. Classify
        std::string intent = classifier.predict(input);
        std::cout << "Detected Intent: " << intent << std::endl;

        // 4. Execute
        if (intent != "unknown") {
            executor->execute(intent, input);
        } else {
            executor->speak("I did not understand that command.");
        }
    }

    return 0;
}
