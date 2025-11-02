#!/usr/bin/env python3
"""
Test the new layout names with real video processing
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

def test_new_names_real_video():
    """Test new layout names with real video"""
    processor = VideoProcessor()
    
    # Path to test video
    test_video = "/Users/biton/Downloads/cog-split-screen-video/footage-for-test.mp4"
    
    if not os.path.exists(test_video):
        print(f"❌ Test video not found: {test_video}")
        return
    
    print("=== Testing New Layout Names with Real Video ===\n")
    
    # Get video info
    try:
        video_info = processor.get_video_info(test_video)
        print(f"Input video: {video_info['width']}x{video_info['height']} ({video_info['duration']:.2f}s)")
        print()
    except Exception as e:
        print(f"❌ Failed to get video info: {e}")
        return
    
    # Test: 16:9 Side by side
    print("Test: Creating '16:9 Side by side' split-screen")
    output_path = Path("test_16_9_side_by_side.mp4")
    
    try:
        # Build FFmpeg command
        cmd = ["ffmpeg", "-y", "-threads", "4"]
        cmd.extend(["-i", test_video, "-i", test_video])
        
        # Generate filter complex for new layout name
        filter_complex = processor.build_filter_complex(
            video_info, video_info, '16:9 Side by side', False, video_info['duration']
        )
        
        print("Filter complex preview:")
        print(f"  {filter_complex[:100]}...")
        print()
        
        cmd.extend(["-filter_complex", filter_complex])
        cmd.extend(["-map", "[output]"])
        if video_info.get('has_audio', False):
            cmd.extend(["-map", "0:a:0"])
        
        cmd.extend(["-t", str(video_info['duration'])])
        cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "23"])
        if video_info.get('has_audio', False):
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
        cmd.extend(["-movflags", "+faststart"])
        cmd.append(str(output_path))
        
        print("Running FFmpeg...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"✅ '16:9 Side by side' video created successfully!")
            print(f"   Output file: {output_path}")
            print(f"   File size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
            
            # Check output dimensions
            check_cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(output_path)]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            if check_result.returncode == 0:
                dimensions = check_result.stdout.strip()
                print(f"   Output dimensions: {dimensions} (should be 1920,1080)")
                
                if dimensions == "1920,1080":
                    print("   ✅ Perfect! Output is exactly 1920x1080 (16:9)")
                else:
                    print(f"   ⚠️  Expected 1920x1080, got {dimensions}")
        else:
            print(f"❌ Failed to create video: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_new_names_real_video()
    print("\n🎬 New layout names real video test completed!")