#!/usr/bin/env python3
"""
Test the new layout names: "16:9 Side by side" and "9:16 Top & Bottom"
"""

import sys
import os

sys.path.append(os.path.dirname(__file__))

# Mock the cog module
class MockInput:
    def __init__(self, **kwargs):
        pass

class MockPath:
    def __init__(self, path):
        self.path = path
    
    def __str__(self):
        return self.path

import types
cog = types.ModuleType('cog')
cog.BasePredictor = object
cog.Input = MockInput
cog.Path = MockPath
sys.modules['cog'] = cog

from predict import VideoProcessor

def test_new_layout_names():
    """Test the new layout names"""
    processor = VideoProcessor()
    
    print("=== Testing New Layout Names ===\n")
    
    # Mock video info
    video_info = {
        'width': 1280,
        'height': 720,
        'duration': 5.0,
        'fps': 24.0,
        'has_audio': True
    }
    
    # Test 1: 16:9 Side by side
    print("Test 1: '16:9 Side by side' layout")
    try:
        dimensions = processor._calculate_layout_dimensions(video_info, video_info, '16:9 Side by side')
        print(f"  Output dimensions: {dimensions['output_width']}x{dimensions['output_height']}")
        print(f"  Each video target: {dimensions['video_width']}x{dimensions['video_height']}")
        print(f"  Layout type: {dimensions['layout_type']}")
        print(f"  Aspect ratio: {dimensions['output_width'] / dimensions['output_height']:.3f} (should be 1.778 for 16:9)")
        print("  ✅ Success!")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print()
    
    # Test 2: 9:16 Top & Bottom
    print("Test 2: '9:16 Top & Bottom' layout")
    try:
        dimensions = processor._calculate_layout_dimensions(video_info, video_info, '9:16 Top & Bottom')
        print(f"  Output dimensions: {dimensions['output_width']}x{dimensions['output_height']}")
        print(f"  Each video target: {dimensions['video_width']}x{dimensions['video_height']}")
        print(f"  Layout type: {dimensions['layout_type']}")
        print(f"  Aspect ratio: {dimensions['output_width'] / dimensions['output_height']:.3f} (should be 0.562 for 9:16)")
        print("  ✅ Success!")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print()
    
    # Test 3: Filter complex generation
    print("Test 3: Filter complex generation")
    try:
        filter_complex_horizontal = processor.build_filter_complex(
            video_info, video_info, '16:9 Side by side', False, 5.0
        )
        print("  16:9 Side by side filter contains 'hstack':", 'hstack' in filter_complex_horizontal)
        
        filter_complex_vertical = processor.build_filter_complex(
            video_info, video_info, '9:16 Top & Bottom', False, 5.0
        )
        print("  9:16 Top & Bottom filter contains 'vstack':", 'vstack' in filter_complex_vertical)
        print("  ✅ Filter generation works!")
    except Exception as e:
        print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    test_new_layout_names()
    print("\n🎬 New layout names test completed!")