"""
VoxMind Assistant - Unified Entry Point
=====================================
The complete VoxMind experience combining all systems.

This is what makes VoxMind feel like the intelligent assistant:
- Multi-agent parallel task execution
- Long-term memory across sessions
- Extensible plugin system for any data source
- Self-monitoring and introspection
- Learning from user interactions
- Proactive monitoring and alerts
- Natural conversation with context

Usage:
    # Simple usage
    from core.voxmind import voxmind
    
    response = await vm.ask("Research AI while checking my calendar")
    print(response)
    
    # Full control
    vm = get_voxmind()
    await voxmind.start()
    
    result = await voxmind.process("Open Chrome and search for Python")
    print(result.text)
    
    # Ask about itself
    print(await voxmind.ask("What can you do?"))
    
    await voxmind.stop()
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

# Import all components
from core.voxmind_core import (
    VoxMindCore, VoxMindResponse, get_voxmind as get_voxmind_core,
    MemoryStore, Memory, MemoryType
)
from core.voxmind_plugins import (
    PluginRegistry, PluginExecutor, VoxMindPlugin
)
from core.self_awareness import (
    SelfAwareVoxMind, CapabilityRegistry, PerformanceTracker, LearningEngine
)

logger = logging.getLogger('VoxMind.Unified')


# ============================================================================
# UNIFIED VOXMIND
# ============================================================================

@dataclass
class UnifiedResponse:
    """Complete response from Unified VoxMind."""
    text: str
    spoken_text: str  # May be different (shorter) for TTS
    source: str  # Which system answered
    confidence: float
    duration: float
    tasks_completed: int = 0
    learned_from: bool = False
    context: Dict[str, Any] = field(default_factory=dict)


class UnifiedVoxMind:
    """
    The complete VoxMind experience.
    
    Combines:
    - VoxMindCore (multi-agent orchestration)
    - Plugin system (extensible data sources)
    - Self-awareness (introspection, learning)
    - VoxMind Daemon (if running)
    """
    
    def __init__(self):
        # Core systems
        self.core = VoxMindCore()
        self.plugins = PluginExecutor()
        self.awareness = SelfAwareVoxMind()
        
        # State
        self._running = False
        self._personality = {
            'name': 'VoxMind',
            'formal': True,
            'proactive': True
        }
        
        # Conversation context
        self._conversation_history: List[Dict] = []
        self._max_history = 10
    
    async def start(self):
        """Start all VoxMind systems."""
        logger.info("Starting Unified VoxMind...")
        
        await self.core.start()
        self._running = True
        
        logger.info("Unified VoxMind is ready")
        return True
    
    async def stop(self):
        """Stop all systems."""
        logger.info("Stopping Unified VoxMind...")
        
        await self.core.stop()
        self._running = False
        
        logger.info("Unified VoxMind stopped")
    
    async def process(self, text: str, 
                      context: Dict = None) -> UnifiedResponse:
        """
        Process a user request through all systems.
        
        This is the main entry point for all user interactions.
        """
        start_time = time.time()
        context = context or {}
        
        # Add conversation history to context
        context['conversation_history'] = self._conversation_history[-5:]
        
        # 1. Check if this is a self-introspection question
        if self._is_about_voxmind(text):
            response = self.awareness.reflection.introspect(text)
            result = UnifiedResponse(
                text=response,
                spoken_text=self._shorten_for_speech(response),
                source='self-awareness',
                confidence=1.0,
                duration=time.time() - start_time
            )
            self._record_conversation(text, response)
            return result
        
        # 2. Try plugins first (they handle specific domains well)
        plugin_results = await self.plugins.execute(text)
        if plugin_results and any(r.success for r in plugin_results):
            formatted = self.plugins.format_results(plugin_results)
            if formatted:
                result = UnifiedResponse(
                    text=formatted,
                    spoken_text=self._shorten_for_speech(formatted),
                    source='plugins',
                    confidence=0.9,
                    duration=time.time() - start_time,
                    context={'plugins_used': [r.source for r in plugin_results]}
                )
                self._record_conversation(text, formatted)
                
                # Learn from this interaction
                self.awareness.learning.learn_from_interaction(
                    text, 'plugin_query', True, context
                )
                return result
        
        # 3. Use core multi-agent system for complex tasks
        core_response = await self.core.process(text)
        
        # 4. Record performance metrics
        self.awareness.performance.record(
            'response_time', 
            (time.time() - start_time) * 1000, 
            'ms'
        )
        
        # 5. Learn from interaction
        self.awareness.learning.learn_from_interaction(
            text,
            'core_query',
            core_response.tasks_completed > 0,
            context
        )
        
        result = UnifiedResponse(
            text=core_response.text,
            spoken_text=self._shorten_for_speech(core_response.text),
            source='core',
            confidence=0.8,
            duration=core_response.duration,
            tasks_completed=core_response.tasks_completed,
            learned_from=True
        )
        
        self._record_conversation(text, core_response.text)
        return result
    
    async def ask(self, text: str) -> str:
        """
        Simple ask interface - just returns text response.
        
        Usage:
            answer = await vm.ask("What's the weather?")
            print(answer)
        """
        result = await self.process(text)
        return result.text
    
    def remember(self, fact: str, importance: float = 0.6):
        """Make VoxMind remember a fact."""
        self.core.memory.remember_fact(fact, importance=importance)
    
    def recall(self, query: str, limit: int = 5) -> List[Memory]:
        """Recall memories related to a query."""
        return self.core.recall_memory(query, limit)
    
    def set_preference(self, key: str, value: Any):
        """Set a user preference."""
        self.core.set_preference(key, value)
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get all user preferences."""
        return self.core.get_preferences()
    
    def register_plugin(self, plugin: VoxMindPlugin):
        """Register a custom plugin."""
        self.plugins.registry.register(plugin)
    
    def can_do(self, task: str) -> tuple:
        """Check if VoxMind can do something."""
        return self.awareness.capabilities.can_do(task)
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status."""
        return self.awareness.reflection.get_status()
    
    def get_self_report(self) -> str:
        """Get a full self-report."""
        return self.awareness.get_self_report()
    
    def _is_about_voxmind(self, text: str) -> bool:
        """Check if query is about VoxMind itself."""
        keywords = [
            'what are you', 'who are you', 'about yourself',
            'what can you do', 'your capabilities', 'your features',
            'are you conscious', 'are you alive', 'are you real',
            'how are you', 'your status', 'your health',
            'your limitations', "can't you do", "cannot you do"
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)
    
    def _shorten_for_speech(self, text: str, max_length: int = 200) -> str:
        """Shorten text for speech output."""
        if len(text) <= max_length:
            return text
        
        # Try to break at sentence boundary
        sentences = text.split('. ')
        result = sentences[0]
        
        for sentence in sentences[1:]:
            if len(result) + len(sentence) + 2 <= max_length:
                result += '. ' + sentence
            else:
                break
        
        if not result.endswith('.'):
            result += '.'
        
        return result
    
    def _record_conversation(self, user_input: str, response: str):
        """Record conversation turn."""
        self._conversation_history.append({
            'user': user_input,
            'VoxMind': response,
            'timestamp': time.time()
        })
        
        # Trim history
        if len(self._conversation_history) > self._max_history:
            self._conversation_history = \
                self._conversation_history[-self._max_history:]


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_unified_voxmind: Optional[UnifiedVoxMind] = None


def get_voxmind() -> UnifiedVoxMind:
    """Get the global Unified VoxMind instance."""
    global _unified_voxmind
    if _unified_voxmind is None:
        _unified_voxmind = UnifiedVoxMind()
    return _unified_voxmind


# Convenience alias
vm = property(lambda self: get_voxmind())


# ============================================================================
# SIMPLE INTERFACE FUNCTIONS
# ============================================================================

async def ask(query: str) -> str:
    """
    Simple function to ask VoxMind something.
    
    Usage:
        from core.voxmind import ask
        
        answer = await ask("What's the weather in London?")
        print(answer)
    """
    j = get_voxmind()
    if not j._running:
        await j.start()
    return await j.ask(query)


def ask_sync(query: str) -> str:
    """
    Synchronous version of ask.
    
    Usage:
        from core.voxmind import ask_sync
        
        answer = ask_sync("What time is it?")
        print(answer)
    """
    return asyncio.run(ask(query))


async def can_do(task: str) -> str:
    """Check if VoxMind can do something."""
    j = get_voxmind()
    can, explanation = j.can_do(task)
    return explanation


def get_status() -> Dict[str, Any]:
    """Get VoxMind status."""
    return get_voxmind().get_status()


# ============================================================================
# DEMO & CLI
# ============================================================================

async def interactive_demo():
    """Run an interactive demo session."""
    print("=" * 60)
    print("  VoxMind Assistant - UNIFIED ASSISTANT")
    print("=" * 60)
    print()
    print("Type your questions or commands. Type 'quit' to exit.")
    print("Special commands:")
    print("  status   - Get VoxMind status")
    print("  report   - Get full self-report")
    print("  help     - What can VoxMind do")
    print()
    
    j = get_voxmind()
    await j.start()
    
    try:
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
            except EOFError:
                break
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("\n🤖 VoxMind: Goodbye!")
                break
            
            if user_input.lower() == 'status':
                status = j.get_status()
                print(f"\n🤖 VoxMind: I'm {status['health']['status']}. "
                      f"Uptime: {status['uptime']['formatted']}")
                continue
            
            if user_input.lower() == 'report':
                print(f"\n{j.get_self_report()}")
                continue
            
            if user_input.lower() == 'help':
                user_input = "What can you do?"
            
            result = await j.process(user_input)
            print(f"\n🤖 VoxMind: {result.text}")
            print(f"   [Source: {result.source}, Duration: {result.duration:.2f}s]")
    
    finally:
        await j.stop()


async def batch_demo():
    """Run a batch demo with predefined queries."""
    print("=" * 60)
    print("  VoxMind Assistant - BATCH DEMO")
    print("=" * 60)
    
    j = get_voxmind()
    await j.start()
    
    queries = [
        # Self-awareness
        "What are you?",
        "What can you do?",
        "Can you feel emotions?",
        
        # Information
        "What time is it?",
        "Calculate 25 * 17 + 100",
        "What's the weather in Tokyo?",
        
        # Multi-tasking
        "Check my system status and tell me the time",
        
        # Learning
        "Remember that I prefer dark mode",
    ]
    
    for query in queries:
        print(f"\n👤 User: {query}")
        result = await j.process(query)
        print(f"🤖 VoxMind: {result.text}")
        print(f"   [Source: {result.source}]")
    
    # Show what was learned
    print("\n--- Learning Summary ---")
    insights = j.awareness.learning.get_user_insight()
    print(f"Patterns learned: {insights['patterns_learned']}")
    print(f"Interactions: {insights['total_interactions']}")
    
    await j.stop()


def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--batch':
            asyncio.run(batch_demo())
        elif sys.argv[1] == '--ask':
            query = ' '.join(sys.argv[2:])
            print(ask_sync(query))
        else:
            print("Usage:")
            print("  python -m core.voxmind              # Interactive mode")
            print("  python -m core.voxmind --batch      # Batch demo")
            print("  python -m core.voxmind --ask <q>    # Single query")
    else:
        asyncio.run(interactive_demo())


if __name__ == "__main__":
    main()
