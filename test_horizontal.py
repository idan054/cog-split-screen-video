#!/usr/bin/env python3
"""
Test horizontal (left and right) split-screen layout
"""

import sys
import os
import subprocess
from pathlib import Path

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

def test_horizontal_layout():
    """Test horizontal split-screen layout"""
    processor = VideoProcessor()
    
    # Path to test video
    test_video = "/Users/biton/Downloads/cog-split-screen-video/footage-for-test.mp4"
    
    if not os.path.exists(test_video):
        print(f"❌ Test video not found: {test_video}")
        return
    
    print("=== Testing Horizontal Split-Screen Layout ===\n")
    
    # Get video info
    try:
        video_info = processor.get_video_info(test_video)
        print(f"Input video: {video_info['width']}x{video_info['height']} ({video_info['duration']:.2f}s)")
        print()
    except Exception as e:
        print(f"❌ Failed to get video info: {e}")
        return
    
    # Output file
    output_path = Path("horizontal_split_test.mp4")
    
    try:
        # Build FFmpeg command for horizontal layout
        cmd = ["ffmpeg", "-y", "-threads", "4"]
        cmd.extend(["-i", test_video, "-i", test_video])
        
        # Generate filter complex for left and right layout
        filter_complex = processor.build_filter_complex(
            video_info, video_info, 'left and right', False, video_info['duration']
        )
        
        print("Filter complex:")
        print(filter_complex)
        print()
        
        cmd.extend(["-filter_complex", filter_complex])
        
        # Map outputs
        cmd.extend(["-map", "[output]"])
        if video_info.get('has_audio', False):
            cmd.extend(["-map", "0:a:0"])
        
        # Set duration and encoding
        cmd.extend(["-t", str(video_info['duration'])])
        cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "23"])
        if video_info.get('has_audio', False):
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
        cmd.extend(["-movflags", "+faststart"])
        cmd.append(str(output_path))
        
        print("Running FFmpeg command...")
        print(f"Command: {' '.join(cmd[:15])}...")
        print()
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"✅ Horizontal split-screen video created successfully!")
            print(f"   Output file: {output_path}")
            print(f"   File size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
            
            # Check output dimensions
            check_cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(output_path)]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            if check_result.returncode == 0:
                dimensions = check_result.stdout.strip()
                width, height = dimensions.split(',')
                aspect_ratio = int(width) / int(height)
                print(f"   Output dimensions: {width}x{height}")
                print(f"   Aspect ratio: {aspect_ratio:.3f} (16:9 = 1.778)")
                
                if dimensions == "1920,1080":
                    print("   ✅ Perfect! Output is exactly 1920x1080 (16:9)")
                else:
                    print(f"   ⚠️  Expected 1920x1080, got {dimensions}")
        else:
            print(f"❌ Failed to create horizontal video:")
            print(f"   Error: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error in horizontal test: {e}")

if __name__ == "__main__":
    test_horizontal_layout()
    print("\n🎬 Horizontal layout test completed!")