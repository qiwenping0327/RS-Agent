#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_VERSION="22.14.0"

TARGET_PLATFORM="${TARGET_PLATFORM:-}"
TARGET_ARCH="${TARGET_ARCH:-}"

if [[ -z "${TARGET_PLATFORM}" ]]; then
  case "$(uname -s)" in
    Darwin) TARGET_PLATFORM="darwin" ;;
    Linux)  TARGET_PLATFORM="linux" ;;
    MINGW*|MSYS*|CYGWIN*) TARGET_PLATFORM="win32" ;;
    *) echo "Unsupported OS: $(uname -s)" >&2; exit 1 ;;
  esac
fi

if [[ -z "${TARGET_ARCH}" ]]; then
  case "$(uname -m)" in
    arm64|aarch64) TARGET_ARCH="arm64" ;;
    x86_64|amd64) TARGET_ARCH="x64" ;;
    *) echo "Unsupported arch: $(uname -m)" >&2; exit 1 ;;
  esac
fi

OUT_DIR="${ROOT}/resources/node-bin"

if [[ "${TARGET_PLATFORM}" == "win32" ]]; then
  ARCHIVE="node-v${NODE_VERSION}-win-${TARGET_ARCH}.zip"
  OUT_BIN="${OUT_DIR}/node.exe"
  TAR_PREFIX="node-v${NODE_VERSION}-win-${TARGET_ARCH}"
else
  ARCHIVE="node-v${NODE_VERSION}-${TARGET_PLATFORM}-${TARGET_ARCH}.tar.gz"
  OUT_BIN="${OUT_DIR}/node"
  TAR_PREFIX="node-v${NODE_VERSION}-${TARGET_PLATFORM}-${TARGET_ARCH}"
fi

BASE_URL="https://nodejs.org/dist/v${NODE_VERSION}"
EXPECTED_VER="v${NODE_VERSION}"

if [[ -x "${OUT_BIN}" ]]; then
  ver="$("${OUT_BIN}" --version 2>/dev/null || true)"
  if [[ "${ver}" == "${EXPECTED_VER}" ]]; then
    echo "Node ${EXPECTED_VER} already present at ${OUT_BIN}; skipping download."
    exit 0
  fi
  echo "Existing binary reports '${ver}', expected '${EXPECTED_VER}'; re-downloading."
fi

mkdir -p "${OUT_DIR}"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

echo "Downloading ${BASE_URL}/${ARCHIVE} ..."
curl -fsSL "${BASE_URL}/${ARCHIVE}" -o "${TMP}/${ARCHIVE}"

echo "Downloading SHASUMS256.txt for checksum verification ..."
curl -fsSL "${BASE_URL}/SHASUMS256.txt" -o "${TMP}/SHASUMS256.txt"

LINE="$(grep -F "${ARCHIVE}" "${TMP}/SHASUMS256.txt" | head -n1)"
if [[ -z "${LINE}" ]]; then
  echo "error: could not find SHA256 line for ${ARCHIVE} in SHASUMS256.txt" >&2
  exit 1
fi
EXPECTED_SHA256="$(awk '{print $1}' <<< "${LINE}")"

ACTUAL_SHA256="$(shasum -a 256 "${TMP}/${ARCHIVE}" | awk '{print $1}')"
if [[ "${ACTUAL_SHA256}" != "${EXPECTED_SHA256}" ]]; then
  echo "error: SHA256 mismatch for ${ARCHIVE}" >&2
  echo "  expected: ${EXPECTED_SHA256}" >&2
  echo "    actual: ${ACTUAL_SHA256}" >&2
  exit 1
fi

echo "SHA256 OK (${ACTUAL_SHA256})"

if [[ "${TARGET_PLATFORM}" == "win32" ]]; then
  unzip -q "${TMP}/${ARCHIVE}" -d "${TMP}"
  install -m 0755 "${TMP}/${TAR_PREFIX}/node.exe" "${OUT_BIN}"
else
  tar -xzf "${TMP}/${ARCHIVE}" -C "${TMP}" "${TAR_PREFIX}/bin/node"
  install -m 0755 "${TMP}/${TAR_PREFIX}/bin/node" "${OUT_BIN}"
fi

if [[ "${TARGET_PLATFORM}" == "win32" ]] && [[ "$(uname -s)" != "MINGW"* ]] && [[ "$(uname -s)" != "MSYS"* ]] && [[ "$(uname -s)" != "CYGWIN"* ]]; then
  echo "Cross-compile mode: skipping version verification (Windows binary on non-Windows host)"
  echo "Installed node.exe (v${NODE_VERSION}) -> ${OUT_BIN}"
  exit 0
fi

VERIFY="$("${OUT_BIN}" --version)"
if [[ "${VERIFY}" != "${EXPECTED_VER}" ]]; then
  echo "error: ${OUT_BIN} --version returned '${VERIFY}', expected '${EXPECTED_VER}'" >&2
  exit 1
fi

echo "Installed ${VERIFY} -> ${OUT_BIN}"
