#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-alea-service-prod.retr.ac}"
OUT="${2:-$HOME/retrac-debug/wrapper-network-timing.txt}"

mkdir -p "$(dirname "$OUT")"

IP="$(getent ahostsv4 "$HOST" | awk 'NR==1 {print $1}')"

if [[ -z "$IP" ]]; then
  echo "Could not resolve $HOST" >&2
  exit 1
fi

echo "Capturing TCP headers/timing for $HOST ($IP):80"
echo "Output: $OUT"

exec sudo tcpdump -i any -nn -tttt "host $IP and tcp port 80" > "$OUT"
