#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUN_VERSION="${BUN_VERSION:-1.3.10}"

TARGET_PLATFORM="${TARGET_PLATFORM:-}"
TARGET_ARCH="${TARGET_ARCH:-}"

if [[ -z "${TARGET_PLATFORM}" ]]; then
  case "$(uname -s)" in
    Darwin) TARGET_PLATFORM="darwin" ;;
    Linux)  TARGET_PLATFORM="linux" ;;
    MINGW*|MSYS*|CYGWIN*) TARGET_PLATFORM="windows" ;;
    *) echo "Unsupported OS: $(uname -s)" >&2; exit 1 ;;
  esac
fi

if [[ -z "${TARGET_ARCH}" ]]; then
  case "$(uname -m)" in
    arm64|aarch64) TARGET_ARCH="aarch64" ;;
    x86_64|amd64) TARGET_ARCH="x64" ;;
    *) echo "Unsupported arch: $(uname -m)" >&2; exit 1 ;;
  esac
fi

BUN_PLATFORM="${TARGET_PLATFORM}"
if [[ "${BUN_PLATFORM}" == "win32" ]]; then
  BUN_PLATFORM="windows"
fi

ARCHIVE="bun-${BUN_PLATFORM}-${TARGET_ARCH}.zip"
BASE_URL="https://github.com/oven-sh/bun/releases/download/bun-v${BUN_VERSION}"
OUT_DIR="${ROOT}/resources/bun-bin"

if [[ "${BUN_PLATFORM}" == "windows" ]]; then
  OUT_BIN="${OUT_DIR}/bun.exe"
else
  OUT_BIN="${OUT_DIR}/bun"
fi

EXPECTED_VER="${BUN_VERSION}"

if [[ -x "${OUT_BIN}" ]]; then
  ver="$("${OUT_BIN}" --version 2>/dev/null || true)"
  if [[ "${ver}" == "${EXPECTED_VER}" ]]; then
    echo "Bun ${EXPECTED_VER} already present at ${OUT_BIN}; skipping download."
    exit 0
  fi
  echo "Existing binary reports '${ver}', expected '${EXPECTED_VER}'; re-downloading."
fi

mkdir -p "${OUT_DIR}"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

echo "Downloading ${BASE_URL}/${ARCHIVE} ..."
curl -fsSL "${BASE_URL}/${ARCHIVE}" -o "${TMP}/${ARCHIVE}"

unzip -q "${TMP}/${ARCHIVE}" -d "${TMP}"

SRC="${TMP}/bun-${BUN_PLATFORM}-${TARGET_ARCH}/bun"
if [[ "${BUN_PLATFORM}" == "windows" ]]; then
  SRC="${TMP}/bun-windows-${TARGET_ARCH}/bun.exe"
fi

[[ -x "${SRC}" ]] || { echo "error: bun binary not found in archive at ${SRC}" >&2; exit 1; }

install -m 0755 "${SRC}" "${OUT_BIN}"

if [[ "${BUN_PLATFORM}" == "windows" ]] && [[ "$(uname -s)" != "MINGW"* ]] && [[ "$(uname -s)" != "MSYS"* ]] && [[ "$(uname -s)" != "CYGWIN"* ]]; then
  echo "Cross-compile mode: skipping version verification (Windows binary on non-Windows host)"
  echo "Installed bun.exe (v${BUN_VERSION}) -> ${OUT_BIN}"
  exit 0
fi

VERIFY="$("${OUT_BIN}" --version)"
if [[ "${VERIFY}" != "${EXPECTED_VER}" ]]; then
  echo "error: ${OUT_BIN} --version returned '${VERIFY}', expected '${EXPECTED_VER}'" >&2
  exit 1
fi

echo "Installed Bun ${VERIFY} -> ${OUT_BIN}"
