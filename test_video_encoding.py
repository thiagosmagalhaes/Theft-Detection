"""
Test script for video encoding validation
Tests the browser-compatible MP4 encoding with H.264
"""

import os
import subprocess
import sys


def check_ffmpeg():
    """Check if FFmpeg is installed and accessible"""
    print("=" * 60)
    print("1. Checking FFmpeg Installation")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=True
        )
        version_output = result.stdout.decode().split('\n')[0]
        print(f"✅ FFmpeg found: {version_output}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print("❌ FFmpeg not found!")
        print("   Install FFmpeg for guaranteed browser compatibility:")
        print("   winget install --id=Gyan.FFmpeg -e --source winget")
        return False


def check_opencv_codecs():
    """Check which video codecs are available in OpenCV"""
    print("\n" + "=" * 60)
    print("2. Checking OpenCV Video Codec Support")
    print("=" * 60)
    
    try:
        import cv2
        import numpy as np
        
        # Test codecs
        codecs_to_test = [
            ("avc1", "H.264/AVC"),
            ("H264", "H.264"),
            ("X264", "x264"),
            ("mp4v", "MPEG-4 Part 2"),
            ("XVID", "Xvid"),
        ]
        
        # Create a dummy frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        test_path = "test_codec.mp4"
        
        available_codecs = []
        
        for fourcc_code, codec_name in codecs_to_test:
            try:
                fourcc = cv2.VideoWriter_fourcc(*fourcc_code)
                writer = cv2.VideoWriter(test_path, fourcc, 25.0, (640, 480))
                
                if writer.isOpened():
                    writer.write(test_frame)
                    writer.release()
                    
                    # Check if file was created
                    if os.path.exists(test_path) and os.path.getsize(test_path) > 0:
                        print(f"✅ {fourcc_code:6s} ({codec_name:20s}) - AVAILABLE")
                        available_codecs.append(fourcc_code)
                        os.remove(test_path)
                    else:
                        print(f"❌ {fourcc_code:6s} ({codec_name:20s}) - NOT WORKING")
                else:
                    print(f"❌ {fourcc_code:6s} ({codec_name:20s}) - NOT AVAILABLE")
                    
            except Exception as e:
                print(f"❌ {fourcc_code:6s} ({codec_name:20s}) - ERROR: {e}")
        
        # Cleanup
        if os.path.exists(test_path):
            os.remove(test_path)
        
        return available_codecs
        
    except ImportError:
        print("❌ OpenCV (cv2) not installed!")
        return []


def test_video_conversion():
    """Test the video conversion function"""
    print("\n" + "=" * 60)
    print("3. Testing Video Conversion Function")
    print("=" * 60)
    
    try:
        from backend.alerts import _convert_to_browser_compatible_mp4
        import cv2
        import numpy as np
        
        # Create a test video with OpenCV
        test_input = "test_input.mp4"
        test_output = "test_output.mp4"
        
        print("Creating test video...")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(test_input, fourcc, 25.0, (640, 480))
        
        # Write 75 frames (3 seconds at 25fps)
        for i in range(75):
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            # Add frame number
            cv2.putText(frame, f"Frame {i}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            writer.write(frame)
        
        writer.release()
        print(f"✅ Test video created: {os.path.getsize(test_input)} bytes")
        
        # Test conversion
        print("\nTesting conversion to H.264...")
        success = _convert_to_browser_compatible_mp4(test_input, test_output)
        
        if success and os.path.exists(test_output):
            print(f"✅ Conversion successful: {os.path.getsize(test_output)} bytes")
            
            # Verify codec with ffprobe
            try:
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "v:0", 
                     "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1",
                     test_output],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5,
                    check=True
                )
                codec = result.stdout.decode().strip()
                if codec == "h264":
                    print(f"✅ Codec verified: {codec}")
                else:
                    print(f"⚠️  Codec is {codec}, expected h264")
            except Exception as e:
                print(f"⚠️  Could not verify codec: {e}")
            
        else:
            print("❌ Conversion failed!")
        
        # Cleanup
        if os.path.exists(test_input):
            os.remove(test_input)
        if os.path.exists(test_output):
            os.remove(test_output)
        
        return success
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("VIDEO ENCODING TEST SUITE")
    print("=" * 60)
    
    results = {
        "ffmpeg": check_ffmpeg(),
        "opencv_codecs": len(check_opencv_codecs()) > 0,
        "conversion": False
    }
    
    if results["ffmpeg"]:
        results["conversion"] = test_video_conversion()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    print(f"FFmpeg Available:     {'✅ PASS' if results['ffmpeg'] else '❌ FAIL'}")
    print(f"OpenCV Codecs:        {'✅ PASS' if results['opencv_codecs'] else '❌ FAIL'}")
    print(f"Conversion Function:  {'✅ PASS' if results['conversion'] else '⚠️  SKIP' if not results['ffmpeg'] else '❌ FAIL'}")
    
    if results["ffmpeg"] and results["opencv_codecs"]:
        print("\n🎉 System is ready for browser-compatible video recording!")
    elif results["opencv_codecs"] and not results["ffmpeg"]:
        print("\n⚠️  System will work but FFmpeg is recommended for best compatibility")
    else:
        print("\n❌ System needs configuration. Check errors above.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
