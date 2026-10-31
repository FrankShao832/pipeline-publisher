#!/usr/bin/env python
"""
Test script for Pipeline Publisher main entry point.

Demonstrates different usage patterns for the unified entry point.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from publisher.main import PublisherLauncher, launch


def test_standalone_mode():
    """Test standalone mode - standard desktop application."""
    print("=" * 50)
    print("Test 1: Standalone Mode")
    print("=" * 50)
    
    try:
        launcher = PublisherLauncher(standalone_mode=True)
        app, window = launcher.launch()
        
        print("✓ Standalone mode launched successfully")
        print(f"✓ Window title: {window.windowTitle()}")
        print(f"✓ Window size: {window.size().width()}x{window.size().height()}")
        
        # Run application (this will block until window is closed)
        exit_code = app.exec()
        print(f"✓ Application exited with code: {exit_code}")
        
        return exit_code
        
    except Exception as e:
        print(f"✗ Standalone mode failed: {e}")
        return 1


def test_convenience_functions():
    """Test convenience functions."""
    print("\n" + "=" * 50)
    print("Test 2: Convenience Functions")
    print("=" * 50)
    
    try:
        # Test launch function
        print("Testing launch() function...")
        app, window = launch(standalone_mode=True)
        print("✓ launch() function works")
        
        # Test launch_standalone function
        print("Testing launch_standalone() function...")
        app2, window2 = launch_standalone()
        print("✓ launch_standalone() function works")
        
        # Clean up windows
        window.close()
        window2.close()
        
        return 0
        
    except Exception as e:
        print(f"✗ Convenience functions failed: {e}")
        return 1


def test_dcc_detection():
    """Test DCC detection."""
    print("\n" + "=" * 50)
    print("Test 3: DCC Detection")
    print("=" * 50)
    
    try:
        from publisher.dcc.dcc_detector import DCCDetector, DCCType
        
        # Detect current environment
        dcc_type = DCCDetector.detect()
        print(f"✓ Detected environment: {dcc_type.value}")
        
        # Get detailed info
        info = DCCDetector.get_dcc_info(dcc_type)
        print(f"✓ DCC name: {info['name']}")
        print(f"✓ Available: {info['available']}")
        print(f"✓ Version: {info['version']}")
        
        return 0
        
    except Exception as e:
        print(f"✗ DCC detection failed: {e}")
        return 1


def test_launcher_methods():
    """Test PublisherLauncher methods and module integration."""
    print("\n" + "=" * 50)
    print("Test 4: Launcher & Module Integration")
    print("=" * 50)
    
    try:
        # Test DCC detection via DCCDetector (decoupled from Launcher)
        from publisher.dcc.dcc_detector import DCCDetector, DCCType
        dcc_type = DCCDetector.detect()
        print(f"✓ DCC type: {dcc_type.value}")
        
        dcc_info = DCCDetector.get_dcc_info(dcc_type)
        print(f"✓ DCC info: {dcc_info['name']} - {dcc_info['version']}")
        
        # Test version info via version module
        from publisher.core.version import get_version_info
        version_info = get_version_info()
        print(f"✓ Publisher version: {version_info['publisher_version']}")
        print(f"✓ Python version: {version_info['python_version']}")
        
        # Test launcher lifecycle methods
        launcher = PublisherLauncher(standalone_mode=True)
        version_info = launcher.get_version_info()
        print(f"✓ Launcher version info: {version_info['publisher_version']}")
        
        return 0
        
    except Exception as e:
        print(f"✗ Launcher methods failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def test_import_usage():
    """Test different import patterns."""
    print("\n" + "=" * 50)
    print("Test 5: Import Patterns")
    print("=" * 50)
    
    try:
        # Test direct import
        import publisher.main
        print("✓ Direct import works")
        
        # Test function import
        from publisher.main import launch, PublisherLauncher
        print("✓ Function import works")
        
        # Test class usage
        launcher = PublisherLauncher(standalone_mode=True)
        print("✓ Class instantiation works")
        
        return 0
        
    except Exception as e:
        print(f"✗ Import patterns failed: {e}")
        return 1


def main():
    """Run all tests."""
    print("🚀 Pipeline Publisher - Main Entry Point Tests")
    print("=" * 50)
    
    results = []
    
    # Run tests
    # Note: We skip the actual UI launch test to keep the script non-interactive
    # test_standalone_mode()  # This would show the actual UI
    
    results.append(("DCC Detection", test_dcc_detection()))
    results.append(("Launcher Methods", test_launcher_methods()))
    results.append(("Import Patterns", test_import_usage()))
    
    # Print summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    for test_name, result in results:
        status = "✓ PASS" if result == 0 else "✗ FAIL"
        print(f"{test_name:30} {status}")
    
    # Calculate overall result
    overall_success = all(result == 0 for _, result in results)
    
    if overall_success:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())