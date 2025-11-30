# UDP Network Tool (GitHub Version)

**⚠️ Educational Purpose Only - Use Responsibly**

This is a modified version of the UDP tool that can be compiled and tested safely on GitHub Actions.

## Features

- Multi-threaded UDP packet sending
- Real-time statistics
- Safe for GitHub Actions environment
- Cross-platform compilation

## Usage

### Manual Compilation
```bash
gcc -o udp_flood udp_flood.c -lpthread -D_GNU_SOURCE -O3
