# Prediction interface for Cog ⚙️
# https://cog.run/python

from cog import BasePredictor, Input, Path as CogPath
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import os

# Constants
DEFAULT_FPS = 30
MAX_OUTPUT_WIDTH = 1920
MAX_OUTPUT_HEIGHT = 1080
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
                                   layout: str) -> Dict[str, int]:
        """Calculate optimal dimensions for the given layout"""
        if layout == "left and right":
            total_width = video1_info['width'] + video2_info['width']
            max_height = max(video1_info['height'], video2_info['height'])
            
            if total_width <= MAX_OUTPUT_WIDTH:
                return {
                    'width1': self._make_even(video1_info['width']),
                    'width2': self._make_even(video2_info['width']),
                    'height': self._make_even(max_height)
                }
            else:
                scale_factor = MAX_OUTPUT_WIDTH / total_width
                return {
                    'width1': self._make_even(int(video1_info['width'] * scale_factor)),
                    'width2': self._make_even(int(video2_info['width'] * scale_factor)),
                    'height': self._make_even(int(max_height * scale_factor))
                }
        else:  # top and bottom
            max_width = max(video1_info['width'], video2_info['width'])
            total_height = video1_info['height'] + video2_info['height']
            
            if total_height <= MAX_OUTPUT_HEIGHT:
                return {
                    'width': self._make_even(max_width),
                    'height1': self._make_even(video1_info['height']),
                    'height2': self._make_even(video2_info['height'])
                }
            else:
                scale_factor = MAX_OUTPUT_HEIGHT / total_height
                return {
                    'width': self._make_even(int(max_width * scale_factor)),
                    'height1': self._make_even(int(video1_info['height'] * scale_factor)),
                    'height2': self._make_even(int(video2_info['height'] * scale_factor))
                }
    
    def build_filter_complex(self, video1_info: Dict, video2_info: Dict,
                           layout: str, loop_videos: bool, target_duration: float) -> str:
        """Build complete filter complex for combining videos"""
        dimensions = self._calculate_layout_dimensions(video1_info, video2_info, layout)
        
        filters = []
        
        # Check if looping is needed
        loop1_needed = loop_videos and video1_info['duration'] < target_duration
        loop2_needed = loop_videos and video2_info['duration'] < target_duration
        
        print(f"Video 1 duration: {video1_info['duration']:.2f}s, needs loop: {loop1_needed}")
        print(f"Video 2 duration: {video2_info['duration']:.2f}s, needs loop: {loop2_needed}")
        print(f"Target duration: {target_duration:.2f}s")
        
        # Process video 1 - simple approach
        if loop1_needed:
            filters.append("[0:v]loop=loop=-1:size=32767:start=0[v1_looped]")
            v1_source = "[v1_looped]"
        else:
            v1_source = "[0:v]"
        
        # Process video 2 - simple approach  
        if loop2_needed:
            filters.append("[1:v]loop=loop=-1:size=32767:start=0[v2_looped]")
            v2_source = "[v2_looped]"
        else:
            v2_source = "[1:v]"
        
        # Scale and set framerate for both videos
        if layout == "left and right":
            v1_width, v1_height = dimensions['width1'], dimensions['height']
            v2_width, v2_height = dimensions['width2'], dimensions['height']
        else:  # top and bottom
            v1_width, v1_height = dimensions['width'], dimensions['height1']
            v2_width, v2_height = dimensions['width'], dimensions['height2']
        
        # Scale video 1
        filters.append(f"{v1_source}scale={v1_width}:{v1_height}:flags=fast_bilinear,fps={DEFAULT_FPS}[v1_final]")
        
        # Scale video 2  
        filters.append(f"{v2_source}scale={v2_width}:{v2_height}:flags=fast_bilinear,fps={DEFAULT_FPS}[v2_final]")
        
        # Combine videos
        if layout == "left and right":
            filters.append("[v1_final][v2_final]hstack=inputs=2[output]")
        else:  # top and bottom
            filters.append("[v1_final][v2_final]vstack=inputs=2[output]")
        
        return ";".join(filters)
    
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
            choices=["left and right", "top and bottom"],
            default="left and right"
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
