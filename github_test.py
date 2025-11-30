#!/usr/bin/env python3
import subprocess
import os
import sys
import time

def compile_and_test():
    print("🔧 Compiling UDP tool...")
    
    # Compile the code
    result = subprocess.run([
        'gcc', '-o', 'udp_test', 'udp_flood.c', 
        '-lpthread', '-D_GNU_SOURCE', '-O3'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Compilation failed: {result.stderr}")
        return False
    
    print("✅ Compilation successful!")
    
    # Test with localhost (safe for GitHub)
    print("\n🧪 Running safe test (localhost, 5 seconds, 2 threads)...")
    
    test_process = subprocess.Popen([
        './udp_test', '127.0.0.1', '8080', '5', '2'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Read output in real-time
    while True:
        output = test_process.stdout.readline()
        if output == '' and test_process.poll() is not None:
            break
        if output:
            print(output.strip())
    
    stdout, stderr = test_process.communicate()
    
    if test_process.returncode == 0:
        print("✅ Test completed successfully!")
        return True
    else:
        print(f"❌ Test failed: {stderr}")
        return False

def create_release_binary():
    """Create optimized binaries for different platforms"""
    print("\n📦 Creating release binaries...")
    
    platforms = [
        ('linux', 'gcc'),
        ('android', 'aarch64-linux-gnu-gcc')
    ]
    
    for platform, compiler in platforms:
        binary_name = f"udp_flood_{platform}"
        print(f"Building {binary_name}...")
        
        # Check if compiler exists
        if subprocess.run(['which', compiler], capture_output=True).returncode != 0:
            print(f"  Skipping {platform} - {compiler} not available")
            continue
            
        result = subprocess.run([
            compiler, '-o', binary_name, 'udp_flood.c',
            '-lpthread', '-D_GNU_SOURCE', '-O3', '-static'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✅ {binary_name} created")
            # Make executable
            os.chmod(binary_name, 0o755)
        else:
            print(f"  ❌ {binary_name} failed: {result.stderr}")

if __name__ == "__main__":
    print("🚀 GitHub UDP Tool Tester")
    print("=" * 40)
    
    if compile_and_test():
        create_release_binary()
        print("\n🎉 All tasks completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Some tasks failed!")
        sys.exit(1)
