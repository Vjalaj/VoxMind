"""
VoxMind Knowledge Engine Demo
=============================
Demonstrates the multi-source knowledge aggregation system.

Run this to see VoxMind gather information from multiple sources.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_aiohttp():
    """Check if aiohttp is available."""
    try:
        import aiohttp
        return True
    except ImportError:
        print("⚠️  aiohttp not installed. Install it for full functionality:")
        print("   pip install aiohttp")
        print()
        return False


async def demo_brief():
    """Demo brief answers."""
    from core.knowledge_engine import ask_knowledge
    
    print("=" * 60)
    print("BRIEF KNOWLEDGE QUERIES")
    print("=" * 60)
    
    queries = [
        "What is quantum computing?",
        "Who is Elon Musk?",
        "What is Python programming?",
    ]
    
    for query in queries:
        print(f"\n❓ {query}")
        try:
            result = await ask_knowledge(query, detail_level="brief")
            print(f"💡 {result}")
        except Exception as e:
            print(f"❌ Error: {e}")


async def demo_detailed():
    """Demo detailed answers."""
    from core.knowledge_engine import ask_knowledge
    
    print("\n" + "=" * 60)
    print("DETAILED KNOWLEDGE QUERY")
    print("=" * 60)
    
    query = "How do I learn machine learning?"
    print(f"\n❓ {query}")
    
    try:
        result = await ask_knowledge(query, detail_level="detailed", include_videos=True)
        # Limit output
        if len(result) > 1500:
            print(f"💡 {result[:1500]}...")
            print(f"\n[Response truncated - full response is {len(result)} chars]")
        else:
            print(f"💡 {result}")
    except Exception as e:
        print(f"❌ Error: {e}")


async def demo_research():
    """Demo comprehensive research."""
    from core.knowledge_engine import research
    
    print("\n" + "=" * 60)
    print("COMPREHENSIVE RESEARCH")
    print("=" * 60)
    
    query = "Artificial Intelligence"
    print(f"\n🔍 Researching: {query}")
    
    try:
        response = await research(query)
        
        print(f"\n📊 Research Results:")
        print(f"   Sources found: {response.source_count}")
        print(f"   Videos found: {len(response.videos)}")
        print(f"   Confidence: {response.confidence:.0%}")
        print(f"   Time taken: {response.retrieval_time:.2f}s")
        
        if response.related_topics:
            print(f"   Related topics: {', '.join(response.related_topics[:5])}")
        
        print(f"\n📝 Summary:")
        print(f"   {response.summary}")
        
        print(f"\n📚 Sources used:")
        for s in response.sources[:5]:
            print(f"   • [{s.source}] {s.title[:50]}")
        
        if response.videos:
            print(f"\n🎥 Videos found:")
            for v in response.videos[:3]:
                print(f"   • {v.title} ({v.duration})")
                print(f"     {v.url}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def demo_with_voxmind():
    """Demo through VoxMind interface."""
    from core.voxmind import get_voxmind
    
    print("\n" + "=" * 60)
    print("THROUGH VOXMIND INTERFACE")
    print("=" * 60)
    
    voxmind = get_voxmind()
    await voxmind.start()
    
    queries = [
        "Tell me about quantum computing",
        "Research artificial intelligence",
        "Tell me everything about Python programming",
    ]
    
    for query in queries:
        print(f"\n👤 User: {query}")
        result = await voxmind.process(query)
        
        # Limit output
        text = result.text
        if len(text) > 500:
            text = text[:500] + "..."
        
        print(f"🤖 VoxMind: {text}")
        print(f"   [Source: {result.source}]")
    
    await voxmind.stop()


async def main():
    """Main demo function."""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║     VOXMIND KNOWLEDGE AGGREGATION ENGINE DEMO             ║
    ║                                                           ║
    ║  Gathering information from:                              ║
    ║  • Wikipedia & Wikidata                                   ║
    ║  • DuckDuckGo                                             ║
    ║  • Reddit & Stack Overflow                                ║
    ║  • YouTube (with transcripts)                             ║
    ║  • Academic sources (ArXiv, Semantic Scholar)            ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    has_aiohttp = check_aiohttp()
    
    if not has_aiohttp:
        print("Running with limited functionality...\n")
    
    await demo_brief()
    await demo_detailed()
    await demo_research()
    await demo_with_voxmind()
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
