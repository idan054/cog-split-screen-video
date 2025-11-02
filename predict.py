# Prediction interface for Cog ⚙️
# https://github.com/replicate/cog/blob/main/docs/python.md

# Test:
# python3 predict.py

# DEPLOY: 
# ⚠️ VERSIONS NOT WORKS ON REPLICATE!!! 
# ⚠️ DEPLOY AS A NEW MODEL - Updated with new layout names!
# 1. Create New model on Replicate.com Called "sarra-split-screen-v1"
# 2. cog push r8.im/idan054/sarra-split-screen-v1
# 3. Don't forget to update the usage Like "version:idan054/sarra-split-screen-v1:5cc24e000096bd3590c5b5b2e95ea7c0c229d7f5bca912890780184041ab74ed"
# 📱 New Features: "16:9 Side by side" & "9:16 Top & Bottom" layouts with smart cropping!


from cog import BasePredictor, Input, Path as CogPath
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import os

# Constants
DEFAULT_FPS = 30
# Standard output dimensions
LANDSCAPE_WIDTH = 1920
LANDSCAPE_HEIGHT = 1080
PORTRAIT_WIDTH = 1080
PORTRAIT_HEIGHT = 1920
DEFAULT_AUDIO_BITRATE = "128k"
FFMPEG_TIMEOUT = 600

class VideoProcessor:
    """Handles video processing operations"""
    
    def __init__(self, hw_accel: Optional[str] = None):
        self.hw_accel = hw_accel
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Get essential video information using ffprobe"""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height,r_frame_rate,codec_type:format=duration",
            "-of", "json", video_path
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            data = json.loads(result.stdout)
            
            video_stream = None
            has_audio = False
            
            # Find video stream and check for audio
            for stream in data['streams']:
                if stream['codec_type'] == 'video' and video_stream is None:
                    video_stream = stream
                elif stream['codec_type'] == 'audio':
                    has_audio = True
            
            if not video_stream:
                raise RuntimeError("No video stream found")
            
            return {
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'duration': float(data['format']['duration']),
                'fps': self._parse_fps(video_stream.get('r_frame_rate', f'{DEFAULT_FPS}/1')),
                'has_audio': has_audio
            }
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, IndexError) as e:
            raise RuntimeError(f"Failed to get video info: {e}")
    
    def _parse_fps(self, fps_string: str) -> float:
        """Safely parse FPS from ratio string"""
        try:
            if '/' in fps_string:
                num, den = fps_string.split('/')
                return float(num) / float(den)
            return float(fps_string)
        except (ValueError, ZeroDivisionError):
            return DEFAULT_FPS
    
    def _make_even(self, value: int) -> int:
        """Ensure dimension is even (required for H.264)"""
        return value if value % 2 == 0 else value - 1
    
    def _calculate_layout_dimensions(self, video1_info: Dict, video2_info: Dict, 
                                   layout: str) -> Dict[str, Any]:
        """Calculate optimal dimensions for the given layout with standard aspect ratios"""
        if layout == "16:9 Side by side":
            # For side-by-side, output should be 16:9 (landscape)
            output_width = LANDSCAPE_WIDTH
            output_height = LANDSCAPE_HEIGHT
            
            # Each video gets half the width
            target_width = output_width // 2
            target_height = output_height
            
            return {
                'output_width': output_width,
                'output_height': output_height,
                'video_width': self._make_even(target_width),
                'video_height': self._make_even(target_height),
                'layout_type': 'horizontal'
            }
        else:  # 9:16 Top & Bottom
            # For top/bottom, output should be 9:16 (portrait)
            output_width = PORTRAIT_WIDTH
            output_height = PORTRAIT_HEIGHT
            
            # Each video gets half the height
            target_width = output_width
            target_height = output_height // 2
            
            return {
                'output_width': output_width,
                'output_height': output_height,
                'video_width': self._make_even(target_width),
                'video_height': self._make_even(target_height),
                'layout_type': 'vertical'
            }
    
    def build_filter_complex(self, video1_info: Dict, video2_info: Dict,
                           layout: str, loop_videos: bool, target_duration: float) -> str:
        """Build complete filter complex for combining videos with smart cropping"""
        dimensions = self._calculate_layout_dimensions(video1_info, video2_info, layout)
        
        filters = []
        
        # Check if looping is needed
        loop1_needed = loop_videos and video1_info['duration'] < target_duration
        loop2_needed = loop_videos and video2_info['duration'] < target_duration
        
        print(f"Video 1 duration: {video1_info['duration']:.2f}s, needs loop: {loop1_needed}")
        print(f"Video 2 duration: {video2_info['duration']:.2f}s, needs loop: {loop2_needed}")
        print(f"Target duration: {target_duration:.2f}s")
        print(f"Output dimensions: {dimensions['output_width']}x{dimensions['output_height']}")
        print(f"Each video target: {dimensions['video_width']}x{dimensions['video_height']}")
        
        # Process video 1 - with looping if needed
        if loop1_needed:
            filters.append("[0:v]loop=loop=-1:size=32767:start=0[v1_looped]")
            v1_source = "[v1_looped]"
        else:
            v1_source = "[0:v]"
        
        # Process video 2 - with looping if needed
        if loop2_needed:
            filters.append("[1:v]loop=loop=-1:size=32767:start=0[v2_looped]")
            v2_source = "[v2_looped]"
        else:
            v2_source = "[1:v]"
        
        # Smart crop and scale for video 1
        v1_filter = self._build_crop_scale_filter(
            v1_source, video1_info, 
            dimensions['video_width'], dimensions['video_height'], 
            "v1_final"
        )
        filters.append(v1_filter)
        
        # Smart crop and scale for video 2
        v2_filter = self._build_crop_scale_filter(
            v2_source, video2_info, 
            dimensions['video_width'], dimensions['video_height'], 
            "v2_final"
        )
        filters.append(v2_filter)
        
        # Combine videos based on layout
        if layout == "16:9 Side by side":
            filters.append("[v1_final][v2_final]hstack=inputs=2[output]")
        else:  # 9:16 Top & Bottom
            filters.append("[v1_final][v2_final]vstack=inputs=2[output]")
        
        return ";".join(filters)
    
    def _build_crop_scale_filter(self, source: str, video_info: Dict, 
                               target_width: int, target_height: int, 
                               output_label: str) -> str:
        """Build a smart crop and scale filter for a video"""
        input_width = video_info['width']
        input_height = video_info['height']
        
        # Calculate aspect ratios
        input_aspect = input_width / input_height
        target_aspect = target_width / target_height
        
        if abs(input_aspect - target_aspect) < 0.01:
            # Aspect ratios are very close, just scale
            return f"{source}scale={target_width}:{target_height}:flags=fast_bilinear,fps={DEFAULT_FPS}[{output_label}]"
        
        if input_aspect > target_aspect:
            # Input is wider, crop width (center crop)
            crop_width = int(input_height * target_aspect)
            crop_height = input_height
            crop_x = (input_width - crop_width) // 2
            crop_y = 0
        else:
            # Input is taller, crop height (center crop)
            crop_width = input_width
            crop_height = int(input_width / target_aspect)
            crop_x = 0
            crop_y = (input_height - crop_height) // 2
        
        # Ensure crop dimensions are even
        crop_width = self._make_even(crop_width)
        crop_height = self._make_even(crop_height)
        crop_x = self._make_even(crop_x)
        crop_y = self._make_even(crop_y)
        
        # Build the filter: crop first, then scale, then set fps
        return f"{source}crop={crop_width}:{crop_height}:{crop_x}:{crop_y},scale={target_width}:{target_height}:flags=fast_bilinear,fps={DEFAULT_FPS}[{output_label}]"
    
    def build_encoding_args(self, quality_preset: str, hw_accel: Optional[str] = None) -> List[str]:
        """Build encoding arguments based on hardware acceleration and quality"""
        args = []
        
        if hw_accel == "nvenc":
            args.extend(["-c:v", "h264_nvenc", "-rc", "vbr", "-gpu", "0"])
            if quality_preset == "fastest":
                args.extend(["-preset", "p1", "-cq", "28"])
            elif quality_preset == "fast":
                args.extend(["-preset", "p3", "-cq", "25"])
            else:  # balanced
                args.extend(["-preset", "p4", "-cq", "23"])
                
        elif hw_accel == "qsv":
            args.extend(["-c:v", "h264_qsv"])
            quality_map = {"fastest": ("veryfast", "28"), "fast": ("faster", "25"), "balanced": ("fast", "23")}
            preset, quality = quality_map[quality_preset]
            args.extend(["-preset", preset, "-global_quality", quality])
            
        elif hw_accel == "videotoolbox":
            args.extend(["-c:v", "h264_videotoolbox", "-realtime", "1"])
            quality_map = {"fastest": "80", "fast": "65", "balanced": "50"}
            args.extend(["-q:v", quality_map[quality_preset]])
            
        else:  # Software encoding
            args.extend(["-c:v", "libx264"])
            if quality_preset == "fastest":
                args.extend(["-preset", "ultrafast", "-crf", "28"])
            elif quality_preset == "fast":
                args.extend(["-preset", "veryfast", "-crf", "25"])
            else:  # balanced
                args.extend(["-preset", "fast", "-crf", "23"])
            args.extend(["-x264-params", "scenecut=0:bframes=2:b-adapt=1:ref=1"])
        
        # Audio encoding
        args.extend(["-c:a", "aac", "-b:a", DEFAULT_AUDIO_BITRATE, "-ac", "2"])
        
        # Container optimizations
        args.extend(["-movflags", "+faststart", "-fflags", "+genpts"])
        
        return args
    
    def process_videos(self, video_1: Path, video_2: Path, output_path: Path,
                      layout: str, video1_info: Dict, video2_info: Dict,
                      loop_videos: bool, target_duration: float,
                      audio_source: str, quality_preset: str) -> bool:
        """Process videos with automatic fallback from hardware to software encoding"""
        
        for attempt, hw_accel in enumerate([self.hw_accel, None]):
            if attempt > 0:
                print(f"Hardware acceleration failed, trying software encoding...")
            
            try:
                cmd = self._build_ffmpeg_command(
                    video_1, video_2, output_path, layout,
                    video1_info, video2_info, loop_videos,
                    target_duration, audio_source, quality_preset, hw_accel
                )
                
                result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
                print(f"FFmpeg completed successfully using {'hardware' if hw_accel else 'software'} acceleration")
                return True
                
            except subprocess.CalledProcessError as e:
                if attempt == 0 and hw_accel:
                    continue  # Try software encoding
                print(f"FFmpeg error: {e}")
                print(f"Command: {' '.join(cmd)}")
                raise RuntimeError(f"Video processing failed: {e.stderr}")
            except subprocess.TimeoutExpired:
                if attempt == 0 and hw_accel:
                    continue  # Try software encoding
                raise RuntimeError("Video processing timed out")
        
        return False
    
    def _build_ffmpeg_command(self, video_1: Path, video_2: Path, output_path: Path,
                            layout: str, video1_info: Dict, video2_info: Dict,
                            loop_videos: bool, target_duration: float,
                            audio_source: str, quality_preset: str,
                            hw_accel: Optional[str]) -> List[str]:
        """Build complete FFmpeg command"""
        cmd = ["ffmpeg", "-y", "-threads", str(min(os.cpu_count() or 4, 8))]
        
        # Input files  
        cmd.extend(["-i", str(video_1), "-i", str(video_2)])
        
        # Filter complex
        filter_complex = self.build_filter_complex(video1_info, video2_info, layout, loop_videos, target_duration)
        print(f"Generated filter complex: {filter_complex}")
        cmd.extend(["-filter_complex", filter_complex])
        
        # Determine audio mapping strategy
        video1_has_audio = video1_info.get('has_audio', False)
        video2_has_audio = video2_info.get('has_audio', False)
        
        # Map audio if available
        if audio_source == "video 1" and video1_has_audio:
            cmd.extend(["-map", "0:a:0"])
        elif audio_source == "video 2" and video2_has_audio:
            cmd.extend(["-map", "1:a:0"])
        elif video1_has_audio:  # Fallback to video 1 audio if available
            cmd.extend(["-map", "0:a:0"])
        elif video2_has_audio:  # Fallback to video 2 audio if available
            cmd.extend(["-map", "1:a:0"])
        else:
            # No audio available - create silent audio track
            print("No audio streams found in either video, creating silent audio track")
            cmd.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"])
            cmd.extend(["-map", "2:a:0"])
        
        # Map video output
        cmd.extend(["-map", "[output]"])
        
        # Set exact duration
        cmd.extend(["-t", str(target_duration)])
        
        # Add timing options to ensure smooth playback and proper synchronization
        cmd.extend(["-vsync", "cfr"])  # Constant frame rate
        cmd.extend(["-r", str(DEFAULT_FPS)])  # Set output frame rate
        cmd.extend(["-avoid_negative_ts", "make_zero"])  # Handle timing issues
        
        # Encoding settings
        cmd.extend(self.build_encoding_args(quality_preset, hw_accel))
        cmd.append(str(output_path))
        
        print(f"Full FFmpeg command: {' '.join(cmd)}")
        return cmd


class HardwareDetector:
    """Detects available hardware acceleration"""
    
    @staticmethod
    def detect_acceleration() -> Optional[str]:
        """Test actual hardware acceleration availability"""
        test_cmd_base = [
            "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-f", "null", "-"
        ]
        
        # Test in order of preference
        for hw_type, codec in [("nvenc", "h264_nvenc"), ("qsv", "h264_qsv"), ("videotoolbox", "h264_videotoolbox")]:
            try:
                # Special check for NVIDIA
                if hw_type == "nvenc":
                    subprocess.run(["nvidia-smi"], check=True, capture_output=True)
                
                # Test actual encoding
                cmd = test_cmd_base.copy()
                cmd.insert(-2, "-c:v")
                cmd.insert(-2, codec)
                
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                if result.returncode == 0:
                    return hw_type
                    
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        return None


class Predictor(BasePredictor):
    def setup(self) -> None:
        """Initialize the predictor"""
        # Verify FFmpeg availability
        try:
            subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            raise RuntimeError("FFmpeg is not available")
        
        # Detect hardware acceleration
        self.hw_accel = HardwareDetector.detect_acceleration()
        print(f"Hardware acceleration available: {self.hw_accel or 'None'}")
        
        # Initialize video processor
        self.processor = VideoProcessor(self.hw_accel)

    def predict(
        self,
        video_1: CogPath = Input(description="First video file"),
        video_2: CogPath = Input(description="Second video file"),
        layout: str = Input(
            description="Layout for combining videos",
            choices=["16:9 Side by side", "9:16 Top & Bottom"],
            default="16:9 Side by side"
        ),
        duration_source: str = Input(
            description="Which video's duration to use",
            choices=["video 1", "video 2"],
            default="video 1"
        ),
        loop_videos: bool = Input(
            description="Loop shorter video to match duration",
            default=True
        ),
        audio_source: str = Input(
            description="Which video's audio to use",
            choices=["video 1", "video 2"],
            default="video 1"
        ),
        quality_preset: str = Input(
            description="Speed vs quality tradeoff",
            choices=["fastest", "fast", "balanced"],
            default="fast"
        ),
    ) -> CogPath:
        """Combine two videos into a split-screen layout"""
        
        # Create output file in a safe location
        output_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        output_path = Path(output_file.name)
        output_file.close()
        
        try:
            # Get video information
            video1_info = self.processor.get_video_info(str(video_1))
            video2_info = self.processor.get_video_info(str(video_2))
            
            # Determine target duration
            target_duration = video1_info['duration'] if duration_source == "video 1" else video2_info['duration']
            
            # Process videos
            success = self.processor.process_videos(
                video_1, video_2, output_path, layout,
                video1_info, video2_info, loop_videos,
                target_duration, audio_source, quality_preset
            )
            
            if not success or not output_path.exists():
                raise RuntimeError("Video processing failed")
            
            return CogPath(output_path)
            
        except Exception as e:
            # Clean up on error
            if output_path.exists():
                output_path.unlink()
            raise e
