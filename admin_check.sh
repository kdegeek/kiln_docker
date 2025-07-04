#!/bin/bash

# Script to verify administrator privileges in Docker container

echo "=== Administrator Privileges Check ==="
echo ""

echo "1. Current user:"
whoami
echo ""

echo "2. User groups:"
groups
echo ""

echo "3. Sudo privileges:"
sudo -l 2>/dev/null || echo "No sudo access"
echo ""

echo "4. Root filesystem access:"
ls -la /root/ 2>/dev/null && echo "Root directory accessible" || echo "Root directory not accessible"
echo ""

echo "5. System processes:"
ps aux | head -10
echo ""

echo "6. Network configuration:"
ip addr show 2>/dev/null || echo "Network tools not available"
echo ""

echo "7. Mount points:"
mount | grep -E "(proc|sys|dev)" | head -5
echo ""

echo "8. Container capabilities:"
cat /proc/self/status | grep Cap
echo ""

echo "=== End of Administrator Check ==="