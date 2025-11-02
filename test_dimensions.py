#!/usr/bin/env python3
"""
Test script for the updated video processing logic
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

# Mock the cog module since it's not available in local testing
class MockInput:
    def __init__(self, **kwargs):
        pass

class MockPath:
    def __init__(self, path):
        self.path = path
    
    def __str__(self):
        return self.path

# Create mock cog module
import types
cog = types.ModuleType('cog')
cog.BasePredictor = object
cog.Input = MockInput
cog.Path = MockPath
sys.modules['cog'] = cog

# Now import our VideoProcessor
from predict import VideoProcessor

def test_dimension_calculations():
    """Test the new dimension calculation logic"""
    processor = VideoProcessor()
    
    print("=== Testing Dimension Calculations ===\n")
    
    # Test case 1: Two 16:9 videos (1280x720) in left/right layout
    video_info = {'width': 1280, 'height': 720, 'duration': 5.0, 'fps': 24, 'has_audio': True}
    
    print("Test 1: Two 16:9 videos (1280x720) in left/right layout")
    dimensions = processor._calculate_layout_dimensions(video_info, video_info, 'left and right')
    print(f"  Output dimensions: {dimensions['output_width']}x{dimensions['output_height']}")
    print(f"  Each video target: {dimensions['video_width']}x{dimensions['video_height']}")
    print(f"  Output aspect ratio: {dimensions['output_width']/dimensions['output_height']:.3f} (should be 1.778 for 16:9)")
    print()
    
    # Test case 2: Two 16:9 videos in top/bottom layout
    print("Test 2: Two 16:9 videos (1280x720) in top/bottom layout")
    dimensions = processor._calculate_layout_dimensions(video_info, video_info, 'top and bottom')
    print(f"  Output dimensions: {dimensions['output_width']}x{dimensions['output_height']}")
    print(f"  Each video target: {dimensions['video_width']}x{dimensions['video_height']}")
    print(f"  Output aspect ratio: {dimensions['output_width']/dimensions['output_height']:.3f} (should be 0.562 for 9:16)")
    print()
    
    # Test case 3: Vertical videos (9:16) in top/bottom layout
    vertical_video = {'width': 1080, 'height': 1920, 'duration': 5.0, 'fps': 30, 'has_audio': True}
    print("Test 3: Two 9:16 videos (1080x1920) in top/bottom layout")
    dimensions = processor._calculate_layout_dimensions(vertical_video, vertical_video, 'top and bottom')
    print(f"  Output dimensions: {dimensions['output_width']}x{dimensions['output_height']}")
    print(f"  Each video target: {dimensions['video_width']}x{dimensions['video_height']}")
    print(f"  Output aspect ratio: {dimensions['output_width']/dimensions['output_height']:.3f} (should be 0.562 for 9:16)")
    print()

def test_crop_filters():
    """Test the crop filter generation"""
    processor = VideoProcessor()
    
    print("=== Testing Crop Filter Generation ===\n")
    
    # Test case 1: 16:9 video to fit in half of 16:9 output (left/right)
    video_info = {'width': 1280, 'height': 720, 'duration': 5.0, 'fps': 24, 'has_audio': True}
    target_width, target_height = 960, 1080  # Half of 1920x1080
    
    print("Test 1: 16:9 video (1280x720) to fit 960x1080 target")
    crop_filter = processor._build_crop_scale_filter('[0:v]', video_info, target_width, target_height, 'test_output')
    print(f"  Filter: {crop_filter}")
    print()
    
    # Test case 2: 9:16 video to fit in half of 9:16 output (top/bottom)
    vertical_video = {'width': 1080, 'height': 1920, 'duration': 5.0, 'fps': 30, 'has_audio': True}
    target_width, target_height = 1080, 960  # Half of 1080x1920
    
    print("Test 2: 9:16 video (1080x1920) to fit 1080x960 target")
    crop_filter = processor._build_crop_scale_filter('[0:v]', vertical_video, target_width, target_height, 'test_output')
    print(f"  Filter: {crop_filter}")
    print()

def test_filter_complex():
    """Test the complete filter complex generation"""
    processor = VideoProcessor()
    
    print("=== Testing Complete Filter Complex ===\n")
    
    # Test with our actual test video
    video_info = {'width': 1280, 'height': 720, 'duration': 5.0, 'fps': 24, 'has_audio': True}
    
    print("Test: Two 16:9 videos in left/right layout (should output 1920x1080)")
    filter_complex = processor.build_filter_complex(video_info, video_info, 'left and right', False, 5.0)
    print(f"  Filter complex: {filter_complex}")
    print()
    
    print("Test: Two 16:9 videos in top/bottom layout (should output 1080x1920)")
    filter_complex = processor.build_filter_complex(video_info, video_info, 'top and bottom', False, 5.0)
    print(f"  Filter complex: {filter_complex}")
    print()

if __name__ == "__main__":
    test_dimension_calculations()
    test_crop_filters()
    test_filter_complex()
    print("✅ All tests completed!")