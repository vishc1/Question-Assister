#!/usr/bin/env python3
"""
Setup Test Script
Verifies that all dependencies are installed and audio devices are working
"""

import sys


def test_imports():
    """Test that all required packages can be imported"""
    print("\n" + "="*60)
    print("Testing Package Imports")
    print("="*60 + "\n")

    packages = {
        'customtkinter': 'CustomTkinter',
        'pyaudiowpatch': 'PyAudioWPatch',
        'win32gui': 'PyWin32',
        'win32con': 'PyWin32',
        'ctypes': 'ctypes (built-in)',
        'threading': 'threading (built-in)',
        'queue': 'queue (built-in)',
    }

    all_success = True

    for module, name in packages.items():
        try:
            __import__(module)
            print(f"✓ {name}: OK")
        except ImportError as e:
            print(f"✗ {name}: FAILED - {e}")
            all_success = False

    return all_success


def test_platform():
    """Check if running on Windows"""
    print("\n" + "="*60)
    print("Testing Platform")
    print("="*60 + "\n")

    import platform

    os_name = platform.system()
    os_version = platform.version()

    print(f"Operating System: {os_name}")
    print(f"Version: {os_version}")

    if os_name != "Windows":
        print("\n⚠ WARNING: This application requires Windows 10/11")
        print("The screen capture exclusion feature will not work on other platforms.")
        return False

    print("\n✓ Platform check passed")
    return True


def test_audio_devices():
    """Test audio device detection"""
    print("\n" + "="*60)
    print("Testing Audio Devices")
    print("="*60 + "\n")

    try:
        import pyaudiowpatch as pyaudio

        p = pyaudio.PyAudio()

        # Count devices
        device_count = p.get_device_count()
        print(f"Found {device_count} audio devices\n")

        # Find microphone
        mic_found = False
        try:
            default_mic = p.get_default_input_device_info()
            print(f"✓ Default Microphone: {default_mic['name']}")
            mic_found = True
        except:
            print("✗ No default microphone found")

        # Find loopback device
        loopback_found = False
        try:
            wasapi_info = p.get_loopback_device_info_generator()
            for loopback in wasapi_info:
                if loopback['name'].find('Loopback') != -1 or loopback.get('isLoopbackDevice', False):
                    print(f"✓ Loopback Device: {loopback['name']}")
                    loopback_found = True
                    break

            if not loopback_found:
                # Try alternative method
                try:
                    default_speakers = p.get_default_wasapi_loopback()
                    print(f"✓ Loopback Device: {default_speakers['name']}")
                    loopback_found = True
                except:
                    pass

        except Exception as e:
            print(f"✗ No loopback device found: {e}")

        p.terminate()

        if not mic_found:
            print("\n⚠ WARNING: Microphone not detected")
            print("Please check your microphone is connected and enabled")

        if not loopback_found:
            print("\n⚠ WARNING: System audio loopback not available")
            print("This may indicate WASAPI loopback is not supported on your system")

        return mic_found and loopback_found

    except Exception as e:
        print(f"\n✗ Audio device test failed: {e}")
        return False


def test_windows_api():
    """Test Windows API access"""
    print("\n" + "="*60)
    print("Testing Windows API Access")
    print("="*60 + "\n")

    try:
        import ctypes
        import win32gui
        import win32con

        # Test basic API calls
        user32 = ctypes.windll.user32
        dwmapi = ctypes.windll.dwmapi

        print("✓ user32.dll loaded")
        print("✓ dwmapi.dll loaded")
        print("✓ win32gui module loaded")

        return True

    except Exception as e:
        print(f"✗ Windows API access failed: {e}")
        return False


def run_all_tests():
    """Run all setup tests"""
    print("\n" + "="*70)
    print(" "*20 + "SETUP VERIFICATION")
    print("="*70)

    results = {
        'imports': test_imports(),
        'platform': test_platform(),
        'windows_api': test_windows_api(),
        'audio': test_audio_devices(),
    }

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60 + "\n")

    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name.capitalize()}: {status}")

    all_passed = all(results.values())

    print("\n" + "="*60)
    if all_passed:
        print("✓ All tests passed! You're ready to run the application.")
        print("\nNext steps:")
        print("  1. Run monitor mode: python main.py monitor")
        print("  2. Run with GUI: python main.py")
    else:
        print("⚠ Some tests failed. Please address the issues above.")
        print("\nCommon fixes:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Check microphone is connected and enabled")
        print("  3. Ensure you're running on Windows 10/11")
        print("  4. Verify audio devices: python main.py devices")

    print("="*60 + "\n")

    return all_passed


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n✓ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
