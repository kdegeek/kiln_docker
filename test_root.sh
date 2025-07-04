#!/bin/bash

echo "=== Root Access Test ==="
echo "Current user: $(whoami)"
echo "User ID: $(id -u)"
echo "Group ID: $(id -g)"
echo "All groups: $(groups)"

if [ $(id -u) -eq 0 ]; then
    echo "✓ Running as root user"
else
    echo "✗ Not running as root user"
fi

echo "=== System Access Test ==="
echo "Can read /etc/passwd: $([ -r /etc/passwd ] && echo 'Yes' || echo 'No')"
echo "Can write to /tmp: $([ -w /tmp ] && echo 'Yes' || echo 'No')"
echo "Can execute system commands: $(which ps > /dev/null && echo 'Yes' || echo 'No')"

echo "=== Network Access Test ==="
echo "Network interfaces:"
ip addr show 2>/dev/null || ifconfig 2>/dev/null || echo "Network tools not available"

echo "=== Root Test Complete ==="