#ifndef COMMAND_EXECUTOR_H
#define COMMAND_EXECUTOR_H

#include <string>
#include <iostream>
#include <cstdlib>

class CommandExecutor {
public:
    virtual void execute(const std::string& intent, const std::string& original_query) = 0;
    virtual void speak(const std::string& text) = 0;
    virtual ~CommandExecutor() {}
};

class WindowsExecutor : public CommandExecutor {
public:
    void execute(const std::string& intent, const std::string& original_query) override {
        std::cout << "[Windows Action] Intent: " << intent << std::endl;
        
        if (intent == "browser_open") {
            system("start https://www.google.com");
            speak("Opening Google Chrome");
        }
        else if (intent == "search_web") {
            // Find search query (everything after the first few words)
            std::string query = original_query;
            size_t pos = query.find("for ");
            if (pos != std::string::npos) query = query.substr(pos + 4);
            
            std::string cmd = "start https://www.google.com/search?q=\"" + query + "\"";
            system(cmd.c_str());
            speak("Searching for " + query);
        }
        else if (intent == "time_check") {
             system("powershell -c \"Get-Date -Format 'HH:mm'\"");
             speak("The time is displayed");
        }
        else if (intent == "volume_mute") {
            system("powershell -c \"(New-Object -ComObject WScript.Shell).SendKeys([char]173)\"");
            speak("Muting volume");
        }
        else if (intent == "volume_up") {
             system("powershell -c \"(New-Object -ComObject WScript.Shell).SendKeys([char]175)\"");
             speak("Volume up");
        }
        else if (intent == "volume_down") {
             system("powershell -c \"(New-Object -ComObject WScript.Shell).SendKeys([char]174)\"");
             speak("Volume down");
        }
        else if (intent == "mouse_click") {
            system("powershell -c \"Add-Type -MemberDefinition '[DllImport(\\\"user32.dll\\\")] public static extern void mouse_event(int dwFlags, int dx, int dy, int cButtons, int dwExtraInfo);' -Name MouseUtils -Namespace User32; [User32.MouseUtils]::mouse_event(0x0002, 0, 0, 0, 0); [User32.MouseUtils]::mouse_event(0x0004, 0, 0, 0, 0);\"");
            speak("Clicked");
        }
        else if (intent == "mouse_right_click") {
            system("powershell -c \"Add-Type -MemberDefinition '[DllImport(\\\"user32.dll\\\")] public static extern void mouse_event(int dwFlags, int dx, int dy, int cButtons, int dwExtraInfo);' -Name MouseUtils -Namespace User32; [User32.MouseUtils]::mouse_event(0x0008, 0, 0, 0, 0); [User32.MouseUtils]::mouse_event(0x0010, 0, 0, 0, 0);\"");
            speak("Right clicked");
        }
        else if (intent == "mouse_move_up") {
            system("powershell -c \"[Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point([Windows.Forms.Cursor]::Position.X, [Windows.Forms.Cursor]::Position.Y - 50)\"");
        }
        else if (intent == "mouse_move_down") {
            system("powershell -c \"[Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point([Windows.Forms.Cursor]::Position.X, [Windows.Forms.Cursor]::Position.Y + 50)\"");
        }
        else if (intent == "mouse_move_left") {
            system("powershell -c \"[Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point([Windows.Forms.Cursor]::Position.X - 50, [Windows.Forms.Cursor]::Position.Y)\"");
        }
        else if (intent == "mouse_move_right") {
            system("powershell -c \"[Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point([Windows.Forms.Cursor]::Position.X + 50, [Windows.Forms.Cursor]::Position.Y)\"");
        }
        else if (intent == "window_close") {
            system("powershell -c \"(New-Object -ComObject WScript.Shell).SendKeys('%{F4}')\"");
            speak("Closing window");
        }
        else if (intent == "window_minimize") {
            system("powershell -c \"(New-Object -ComObject WScript.Shell).SendKeys('#m')\"");
            speak("Minimizing all windows");
        }
        else if (intent == "notepad_open") {
            system("start notepad");
            speak("Opening Notepad");
        }
        else if (intent == "calculator_open") {
            system("start calc");
            speak("Opening Calculator");
        }
        else if (intent == "shutdown_system") {
            speak("Goodbye");
            system("shutdown /s /t 10");
        }
        else {
            speak("I am not sure how to do that yet.");
        }
    }

    void speak(const std::string& text) override {
        // PowerShell TTS
        std::string cmd = "powershell -c \"Add-Type -AssemblyName System.Speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.Speak('" + text + "')\"";
        // On Linux/Cross-compile this won't run, but this is the code for Windows.
        // We use system() which blocks, so it might pause execution. Ideally use a thread.
        // For CLI prototype, blocking is acceptable.
        #ifdef _WIN32
        system(cmd.c_str());
        #else
        std::cout << "[TTS] " << text << std::endl;
        #endif
    }
};

class LinuxExecutor : public CommandExecutor {
public:
    void execute(const std::string& intent, const std::string& original_query) override {
        std::cout << "[Linux Simulation] Action: " << intent << std::endl;
        
        if (intent == "browser_open") {
            std::cout << ">> Opening Default Browser..." << std::endl;
            speak("Opening browser");
        }
        else if (intent == "time_check") {
            system("date");
            speak("Here is the time");
        }
        else if (intent.find("mouse_move") == 0) {
            std::cout << ">> Moving Cursor " << intent.substr(11) << "..." << std::endl;
        }
        else if (intent == "mouse_click") {
            std::cout << ">> Left Click!" << std::endl;
            speak("Clicked");
        }
        else if (intent == "window_close") {
            std::cout << ">> Closing current window (Alt+F4)..." << std::endl;
            speak("Closing window");
        }
        else {
            std::cout << ">> Executing: " << intent << " (Simulated)" << std::endl;
            speak("Executing command");
        }
    }

    void speak(const std::string& text) override {
        std::cout << "[Speaker] " << text << std::endl;
    }
};

#endif
