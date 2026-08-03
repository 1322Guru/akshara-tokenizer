#!/usr/bin/env bash
# Train the three arm-0 replicates sequentially, never in parallel: each run peaks near
# 14.7 GB against a 24 GB cap, so two at once would swap or be killed.
set -u
SWEEP="${AKSHARA_SWEEP:-/mnt/c/GuruAI-Data/akshara_v1_3_sweep}"

for S in 1 2 3; do
  PREFIX="${SWEEP}/models/arm0_seed${S}"
  LOG="${SWEEP}/logs/arm0_seed${S}.log"
  if [ -f "${PREFIX}.model" ]; then
    echo "seed ${S}: model already present, skipping" >> "${SWEEP}/logs/driver.log"
    continue
  fi
  {
    echo "=== arm0 seed=${S} start $(date -Is) ==="
    echo "mem_avail_MB=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)"
  } >> "$LOG"
  python3 -u "${SWEEP}/train_arm.py" "$S" "$PREFIX" >> "$LOG" 2>&1
  RC=$?
  echo "=== arm0 seed=${S} end $(date -Is) exit=${RC} ===" >> "$LOG"
  if [ "$RC" -ne 0 ]; then
    echo "seed ${S} FAILED rc=${RC}, aborting" >> "${SWEEP}/logs/driver.log"
    exit "$RC"
  fi
  echo "seed ${S} done $(date -Is) sha256=$(sha256sum "${PREFIX}.model" | cut -d' ' -f1)" >> "${SWEEP}/logs/driver.log"
done
echo "ALL SEEDS COMPLETE $(date -Is)" >> "${SWEEP}/logs/driver.log"
