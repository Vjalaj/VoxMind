"""
Test suite for Process Mapper Module
=====================================
Tests the app/icon mapping functionality.

Author: Swadhin
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Swadhin.process_mapper import (
    ProcessMapper, 
    ProcessInfo, 
    ProcessCategory,
    PROCESS_FRIENDLY_NAMES,
    SYSTEM_PROCESSES,
    list_running_apps,
    find_app,
    get_process_mapper
)


class TestProcessMapper:
    """Test the ProcessMapper class"""
    
    @pytest.fixture
    def mapper(self):
        """Create a ProcessMapper instance"""
        return ProcessMapper()
    
    def test_mapper_initialization(self, mapper):
        """Test that mapper initializes correctly"""
        assert mapper is not None
        assert mapper.cache_dir.exists()
    
    def test_get_running_processes(self, mapper):
        """Test getting running processes"""
        processes = mapper.get_running_processes()
        
        assert isinstance(processes, list)
        assert len(processes) > 0
        
        # Check that each process has required fields
        for proc in processes[:5]:
            assert isinstance(proc, ProcessInfo)
            assert proc.pid >= 0  # PID 0 is valid (System Idle Process)
            assert proc.name
            assert proc.friendly_name
            assert isinstance(proc.category, ProcessCategory)
    
    def test_get_running_processes_include_system(self, mapper):
        """Test that system processes are included when requested"""
        with_system = mapper.get_running_processes(include_system=True)
        without_system = mapper.get_running_processes(include_system=False)
        
        # Should have more processes when including system
        assert len(with_system) >= len(without_system)
    
    def test_find_process_by_name(self, mapper):
        """Test finding processes by name"""
        # Get some running processes first
        processes = mapper.get_running_processes(include_system=True)
        
        if processes:
            # Try to find the first process by name
            test_proc = processes[0]
            found = mapper.find_process_by_name(test_proc.name)
            
            # Should find the process
            assert found is not None
            assert found.name == test_proc.name
    
    def test_resolve_problematic_mapping(self, mapper):
        """Test resolving problematic app mappings"""
        # Test with a common app that should be running on most systems
        result = mapper.resolve_problematic_mapping("explorer")
        
        # Explorer should be found on Windows
        if result:
            assert "explorer" in result.name.lower() or "explorer" in result.friendly_name.lower()
    
    def test_get_process_summary(self, mapper):
        """Test process summary generation"""
        summary = mapper.get_process_summary()
        
        assert isinstance(summary, dict)
        assert 'total_processes' in summary
        assert 'total_memory_mb' in summary
        assert 'category_counts' in summary
        assert 'top_memory' in summary
        assert 'top_cpu' in summary
        
        assert summary['total_processes'] > 0
        assert summary['total_memory_mb'] > 0
    
    def test_process_cache(self, mapper):
        """Test that process caching works"""
        # First call populates cache
        processes1 = mapper.get_running_processes()
        
        # Second call should use cache (faster)
        processes2 = mapper.get_running_processes()
        
        # Should return similar data
        assert len(processes1) == len(processes2)
    
    def test_cache_refresh(self, mapper):
        """Test cache refresh functionality"""
        # Populate cache
        mapper.get_running_processes()
        
        # Force refresh
        mapper.refresh()
        
        # Cache should be cleared
        assert len(mapper._process_cache) == 0
        assert mapper._last_refresh == 0


class TestProcessFriendlyNames:
    """Test the friendly name mappings"""
    
    def test_friendly_names_not_empty(self):
        """Test that friendly names dictionary is populated"""
        assert len(PROCESS_FRIENDLY_NAMES) > 50
    
    def test_common_apps_mapped(self):
        """Test that common apps are in the mapping"""
        common_apps = [
            "chrome.exe", "msedge.exe", "firefox.exe",
            "code.exe", "notepad.exe", "explorer.exe"
        ]
        
        for app in common_apps:
            assert app in PROCESS_FRIENDLY_NAMES, f"{app} should be in friendly names"
    
    def test_friendly_names_are_strings(self):
        """Test that all friendly names are valid strings"""
        for key, value in PROCESS_FRIENDLY_NAMES.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
            assert len(value) > 0


class TestSystemProcesses:
    """Test system process filtering"""
    
    def test_system_processes_not_empty(self):
        """Test that system processes set is populated"""
        assert len(SYSTEM_PROCESSES) > 20
    
    def test_common_system_processes(self):
        """Test that common system processes are included"""
        common_system = ["svchost.exe", "csrss.exe", "dwm.exe"]
        
        for proc in common_system:
            assert proc in SYSTEM_PROCESSES


class TestConvenienceFunctions:
    """Test the convenience functions"""
    
    def test_list_running_apps(self):
        """Test listing running apps"""
        apps = list_running_apps()
        
        assert isinstance(apps, list)
        
        # Check format of returned data
        for app in apps[:5]:
            assert 'name' in app
            assert 'process' in app
            assert 'pid' in app
            assert 'category' in app
    
    def test_find_app(self):
        """Test finding an app"""
        # Explorer should always be running
        result = find_app("explorer")
        
        if result:
            assert 'name' in result
            assert 'process' in result
            assert 'pid' in result
    
    def test_get_process_mapper_singleton(self):
        """Test that get_process_mapper returns singleton"""
        mapper1 = get_process_mapper()
        mapper2 = get_process_mapper()
        
        assert mapper1 is mapper2


class TestProcessCategories:
    """Test process categorization"""
    
    @pytest.fixture
    def mapper(self):
        return ProcessMapper()
    
    def test_browser_categorization(self, mapper):
        """Test that browsers are categorized correctly"""
        chrome = mapper.find_process_by_name("chrome.exe")
        
        if chrome:
            assert chrome.category == ProcessCategory.BROWSER
    
    def test_category_enum_values(self):
        """Test that all categories have valid values"""
        categories = list(ProcessCategory)
        
        assert len(categories) > 5
        assert ProcessCategory.BROWSER in categories
        assert ProcessCategory.SYSTEM in categories
        assert ProcessCategory.UNKNOWN in categories


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
