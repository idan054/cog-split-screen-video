#!/usr/bin/env python3
"""
Practical test using real video footage
"""

import sys
import os
import subprocess
import tempfile
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

def test_real_video_processing():
    """Test with actual video file"""
    processor = VideoProcessor()
    
    # Path to test video
    test_video = "/Users/biton/Downloads/cog-split-screen-video/footage-for-test.mp4"
    
    if not os.path.exists(test_video):
        print(f"❌ Test video not found: {test_video}")
        return
    
    print("=== Testing Real Video Processing ===\n")
    
    # Get video info
    try:
        video_info = processor.get_video_info(test_video)
        print(f"Video info: {video_info}")
        print()
    except Exception as e:
        print(f"❌ Failed to get video info: {e}")
        return
    
    # Test 1: Left/Right layout (should output 1920x1080)
    print("Test 1: Creating left/right split-screen (16:9 output)")
    output_file1 = tempfile.NamedTemporaryFile(suffix="_left_right.mp4", delete=False)
    output_path1 = Path(output_file1.name)
    output_file1.close()
    
    try:
        # Build FFmpeg command manually for testing
        cmd = ["ffmpeg", "-y", "-threads", "4"]
        cmd.extend(["-i", test_video, "-i", test_video])
        
        # Generate filter complex
        filter_complex = processor.build_filter_complex(video_info, video_info, 'left and right', False, video_info['duration'])
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
        cmd.append(str(output_path1))
        
        print(f"Running: {' '.join(cmd[:10])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"✅ Left/Right video created: {output_path1}")
            print(f"   File size: {output_path1.stat().st_size / 1024 / 1024:.1f} MB")
            
            # Check output dimensions
            check_cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(output_path1)]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            if check_result.returncode == 0:
                dimensions = check_result.stdout.strip()
                print(f"   Output dimensions: {dimensions} (should be 1920,1080)")
        else:
            print(f"❌ Failed to create left/right video: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error in left/right test: {e}")
    finally:
        if output_path1.exists():
            print(f"   Output saved to: {output_path1}")
    
    print()
    
    # Test 2: Top/Bottom layout (should output 1080x1920)
    print("Test 2: Creating top/bottom split-screen (9:16 output)")
    output_file2 = tempfile.NamedTemporaryFile(suffix="_top_bottom.mp4", delete=False)
    output_path2 = Path(output_file2.name)
    output_file2.close()
    
    try:
        # Build FFmpeg command for top/bottom
        cmd = ["ffmpeg", "-y", "-threads", "4"]
        cmd.extend(["-i", test_video, "-i", test_video])
        
        # Generate filter complex
        filter_complex = processor.build_filter_complex(video_info, video_info, 'top and bottom', False, video_info['duration'])
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
        cmd.append(str(output_path2))
        
        print(f"Running: {' '.join(cmd[:10])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"✅ Top/Bottom video created: {output_path2}")
            print(f"   File size: {output_path2.stat().st_size / 1024 / 1024:.1f} MB")
            
            # Check output dimensions
            check_cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(output_path2)]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            if check_result.returncode == 0:
                dimensions = check_result.stdout.strip()
                print(f"   Output dimensions: {dimensions} (should be 1080,1920)")
        else:
            print(f"❌ Failed to create top/bottom video: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error in top/bottom test: {e}")
    finally:
        if output_path2.exists():
            print(f"   Output saved to: {output_path2}")

if __name__ == "__main__":
    test_real_video_processing()
    print("\n🎬 Real video processing test completed!")