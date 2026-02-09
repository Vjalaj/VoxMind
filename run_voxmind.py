"""
Run VoxMind
==================
Start the unified VoxMind assistant.

Usage:
    python run_voxmind.py                  # Interactive mode
    python run_voxmind.py --demo           # Batch demo
    python run_voxmind.py --ask "query"    # Single query
    python run_voxmind.py --status         # Check status
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_banner():
    """Print the VoxMind banner."""
    banner = r"""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   ██╗   ██╗ ██████╗ ██╗  ██╗███╗   ███╗██╗███╗   ██╗██████╗║
    ║   ██║   ██║██╔═══██╗╚██╗██╔╝████╗ ████║██║████╗  ██║██╔══██╗
    ║   ██║   ██║██║   ██║ ╚███╔╝ ██╔████╔██║██║██╔██╗ ██║██║  ██║
    ║   ╚██╗ ██╔╝██║   ██║ ██╔██╗ ██║╚██╔╝██║██║██║╚██╗██║██║  ██║
    ║    ╚████╔╝ ╚██████╔╝██╔╝ ██╗██║ ╚═╝ ██║██║██║ ╚████║██████╔╝
    ║     ╚═══╝   ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝ 
    ║                                                           ║
    ║              J . A . R . V . I . S                        ║
    ║     Just A Rather Very Intelligent System                 ║
    ║                                                           ║
    ║   Multi-Agent • Self-Aware • Always Learning             ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_dependencies():
    """Check required dependencies."""
    missing = []
    
    required = [
        ('aiohttp', 'pip install aiohttp'),
        ('psutil', 'pip install psutil'),
    ]
    
    optional = [
        ('pyttsx3', 'pip install pyttsx3'),
        ('speech_recognition', 'pip install SpeechRecognition'),
    ]
    
    for module, install in required:
        try:
            __import__(module)
        except ImportError:
            missing.append((module, install, 'REQUIRED'))
    
    for module, install in optional:
        try:
            __import__(module)
        except ImportError:
            missing.append((module, install, 'optional'))
    
    if missing:
        print("\n⚠️  Dependency Check:")
        for module, install, level in missing:
            icon = "❌" if level == 'REQUIRED' else "⚡"
            print(f"   {icon} {module} ({level}): {install}")
        
        required_missing = [m for m, _, l in missing if l == 'REQUIRED']
        if required_missing:
            print("\n   Install required dependencies with:")
            print("   pip install aiohttp psutil")
            return False
        print()
    
    return True


async def run_interactive():
    """Run interactive mode."""
    from core.voxmind import get_voxmind
    
    print_banner()
    
    if not check_dependencies():
        return
    
    print("\n  Welcome! I'm VoxMind, your intelligent assistant.")
    print("  Type your questions or commands. Type 'quit' to exit.")
    print("  Try: 'What can you do?' or 'What time is it?'\n")
    print("=" * 60)
    
    voxmind = get_voxmind()
    await voxmind.start()
    
    try:
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n")
                break
            
            if not user_input:
                continue
            
            if user_input.lower() in ('quit', 'exit', 'bye'):
                print("\n🤖 VoxMind: Goodbye! It was a pleasure assisting you.")
                break
            
            result = await voxmind.process(user_input)
            
            # Print response with formatting
            print(f"\n🤖 VoxMind: {result.text}")
            
            # Show metadata in debug mode
            if os.environ.get('VOXMIND_DEBUG'):
                print(f"   [Source: {result.source}, "
                      f"Duration: {result.duration:.2f}s, "
                      f"Tasks: {result.tasks_completed}]")
    
    finally:
        await voxmind.stop()


async def run_demo():
    """Run batch demo."""
    from core.voxmind import get_voxmind
    
    print_banner()
    print("\n  Running VoxMind Demo...\n")
    
    voxmind = get_voxmind()
    await voxmind.start()
    
    demos = [
        ("Self-Awareness", [
            "What are you?",
            "Are you conscious?",
        ]),
        ("Information Retrieval", [
            "What time is it?",
            "Calculate 42 * 17",
        ]),
        ("Capabilities", [
            "What can you do?",
            "Can you open applications?",
        ]),
    ]
    
    for category, queries in demos:
        print(f"\n{'='*40}")
        print(f"  {category}")
        print(f"{'='*40}")
        
        for query in queries:
            print(f"\n👤 User: {query}")
            result = await voxmind.process(query)
            print(f"🤖 VoxMind: {result.text}")
    
    # Show self-report
    print(f"\n{'='*40}")
    print("  Self-Report")
    print(f"{'='*40}\n")
    print(voxmind.get_self_report())
    
    await voxmind.stop()


async def run_single_query(query: str):
    """Run a single query."""
    from core.voxmind import ask
    response = await ask(query)
    print(response)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg == '--demo':
            asyncio.run(run_demo())
        elif arg == '--ask' and len(sys.argv) > 2:
            query = ' '.join(sys.argv[2:])
            asyncio.run(run_single_query(query))
        elif arg == '--status':
            from core.voxmind import get_status
            import json
            status = get_status()
            print(json.dumps(status, indent=2, default=str))
        elif arg in ('--help', '-h'):
            print(__doc__)
        else:
            print(f"Unknown option: {arg}")
            print("Use --help for usage information")
    else:
        asyncio.run(run_interactive())


if __name__ == "__main__":
    main()
