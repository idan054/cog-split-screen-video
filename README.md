# Video Split-Screen Combiner

A high-performance Replicate Cog model that combines two videos into a single split-screen layout with hardware acceleration support.

## 🎬 What it does

This model takes two video files and combines them into a single video with either:
- **Side-by-side** (left and right) layout
- **Top and bottom** (stacked) layout

Perfect for creating comparison videos, reaction videos, or any content requiring multiple video streams in one frame.

## ⚡ Performance Features

### Smart Optimizations
- **Intelligent scaling**: Only scales when necessary to maintain quality
- **Even dimension enforcement**: Ensures H.264 compatibility
- **Quality presets**: Balance between speed and output quality
- **Efficient filter chains**: Minimized processing operations
- **Threading optimization**: Multi-core CPU utilization

## 📥 Inputs

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `video_1` | File | Required | First video file |
| `video_2` | File | Required | Second video file |
| `layout` | Choice | "left and right" | Layout style: "left and right" or "top and bottom" |
| `duration_source` | Choice | "video 1" | Which video's duration to use: "video 1" or "video 2" |
| `loop_videos` | Boolean | `true` | Loop shorter video to match target duration |
| `audio_source` | Choice | "video 1" | Which video's audio to use: "video 1" or "video 2" |
| `quality_preset` | Choice | "fast" | Speed vs quality: "fastest", "fast", or "balanced" |

## 🔧 Technical Details

### Supported Formats
- **Input**: MP4, MOV, AVI, MKV, and most common video formats
- **Output**: MP4 (H.264 + AAC)
- **Audio**: Stereo AAC at 128kbps

### Resolution Handling
- **Maximum output**: 1920x1080 (Full HD)
- **Smart scaling**: Preserves aspect ratios
- **H.264 compliance**: Ensures even dimensions for compatibility

### Duration & Looping
- Choose which video's duration to use as the target
- Shorter video can loop to match longer video's duration
- Audio from selected source video is preserved

## 📄 License

This project is available under the MIT License. See LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
