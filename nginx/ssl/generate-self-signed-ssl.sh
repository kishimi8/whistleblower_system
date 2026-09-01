#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$DIR"

if [ ! -f "$DIR/live.crt" ] || [ ! -f "$DIR/live.key" ]; then
    echo "Generating self-signed SSL certificate for local/testing HA setup..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$DIR/live.key" \
        -out "$DIR/live.crt" \
        -subj "/C=NG/ST=Abuja/L=Abuja/O=Whistleblower/OU=IT/CN=whistle.finance.gov.ng"
    echo "Self-signed SSL certificate generated in $DIR"
else
    echo "SSL certificate already exists in $DIR"
fi
