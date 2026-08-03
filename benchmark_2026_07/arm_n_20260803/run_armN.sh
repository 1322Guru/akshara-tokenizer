#!/usr/bin/env bash
# Build and train the three arm N variants sequentially. Never in parallel: each train
# peaks near 15 GB against a 24 GB cap.
set -u
S="${AKSHARA_SWEEP:-/mnt/c/GuruAI-Data/akshara_v1_3_sweep}"

run () {           # $1 = label, $2 = f
  L="$1"; F="$2"
  if [ ! -f "${S}/corpus_${L}/kn.txt" ]; then
    python3 -u "${S}/build_armN.py" "$F" "${S}/corpus_${L}" > "${S}/logs/build_${L}.log" 2>&1 || {
      echo "BUILD ${L} FAILED" >> "${S}/logs/armN_driver.log"; exit 1; }
  fi
  echo "built ${L} $(date -Is)" >> "${S}/logs/armN_driver.log"
  if [ ! -f "${S}/models/${L}.model" ]; then
    python3 -u "${S}/train_arm_fixed.py" 1 "${S}/models/${L}" "${S}/corpus_${L}" \
      > "${S}/logs/${L}.log" 2>&1 || {
      echo "TRAIN ${L} FAILED" >> "${S}/logs/armN_driver.log"; exit 1; }
  fi
  echo "trained ${L} $(date -Is) sha256=$(sha256sum "${S}/models/${L}.model" | cut -d' ' -f1)" \
    >> "${S}/logs/armN_driver.log"
}

run armNa 0.10
run armNb 0.25
run armNc 0.50
echo "ALL ARM N COMPLETE $(date -Is)" >> "${S}/logs/armN_driver.log"
