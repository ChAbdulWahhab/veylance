#!/usr/bin/env bash
# Veylance (veyl) Unix Installation Script
# Supports Linux and macOS on x86_64 and arm64 architectures.

set -euo pipefail

REPO="ChAbdulWahhab/veylance"
INSTALL_DIR="${VEYLANCE_INSTALL_DIR:-/usr/local/bin}"

# 1. Detect Operating System
OS="$(uname -s)"
case "${OS}" in
    Linux*)     PLATFORM="linux" ;;
    Darwin*)    PLATFORM="darwin" ;;
    *)
        echo "[-] Error: Unsupported operating system: ${OS}"
        echo "    Veylance currently supports Linux, macOS, and Windows."
        exit 1
        ;;
esac

# 2. Detect Architecture
ARCH="$(uname -m)"
case "${ARCH}" in
    x86_64|amd64)   ARCH="amd64" ;;
    arm64|aarch64)  ARCH="arm64" ;;
    *)
        echo "[-] Error: Unsupported architecture: ${ARCH}"
        echo "    Veylance currently supports x86_64 (amd64) and arm64."
        exit 1
        ;;
esac

# Check for Apple Silicon Mac running a shell under Rosetta 2 translation
if [ "${PLATFORM}" = "darwin" ] && [ "${ARCH}" = "amd64" ]; then
    IS_TRANSLATED="$(sysctl -in sysctl.proc_translated 2>/dev/null || echo 0)"
    HW_ARM64="$(sysctl -in hw.optional.arm64 2>/dev/null || echo 0)"
    if [ "${IS_TRANSLATED}" = "1" ] || [ "${HW_ARM64}" = "1" ]; then
        echo "[*] Detected Apple Silicon Mac running under Rosetta emulation. Selecting native arm64 binary."
        ARCH="arm64"
    fi
fi

TARGET="veyl-${PLATFORM}-${ARCH}"
echo "[*] Detected platform: ${PLATFORM} (${ARCH})"

# 3. Determine Version & Download URL
if [ -z "${VERSION:-}" ]; then
    echo "[*] Resolving latest release version..."
    VERSION="$(curl -sSL "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null | grep '"tag_name":' | head -n 1 | sed -E 's/.*"([^"]+)".*/\1/' || echo "")"
    if [ -z "${VERSION}" ]; then
        VERSION="v0.2.2"
        echo "[!] Warning: Failed to query GitHub API. Falling back to default version ${VERSION}"
    fi
fi

# Ensure version has 'v' prefix
if [[ "${VERSION}" != v* ]]; then
    VERSION="v${VERSION}"
fi

DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${VERSION}/${TARGET}"
CHECKSUMS_URL="https://github.com/${REPO}/releases/download/${VERSION}/SHA256SUMS.txt"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "[*] Downloading Veylance ${VERSION} (${TARGET})..."

if command -v curl >/dev/null 2>&1; then
    HTTP_CODE="$(curl -sSL -w "%{http_code}" -o "${TMP_DIR}/veyl" "${DOWNLOAD_URL}" || echo "000")"
    if [ "${HTTP_CODE}" = "404" ]; then
        echo "[-] Error: Release binary '${TARGET}' not found for version ${VERSION} (HTTP 404)."
        echo "    Please verify that version ${VERSION} publishes a pre-compiled binary for ${PLATFORM}-${ARCH}."
        echo "    Available release assets can be inspected at:"
        echo "    https://github.com/${REPO}/releases/tag/${VERSION}"
        exit 1
    elif [ "${HTTP_CODE}" != "200" ]; then
        echo "[-] Error: Failed to download '${TARGET}' (HTTP status ${HTTP_CODE})."
        echo "    URL: ${DOWNLOAD_URL}"
        exit 1
    fi
    curl -fsSL "${CHECKSUMS_URL}" -o "${TMP_DIR}/SHA256SUMS.txt" 2>/dev/null || true
elif command -v wget >/dev/null 2>&1; then
    if ! wget -q "${DOWNLOAD_URL}" -O "${TMP_DIR}/veyl"; then
        echo "[-] Error: Failed to download binary '${TARGET}' from ${DOWNLOAD_URL}."
        echo "    Please verify that version ${VERSION} publishes an asset for ${PLATFORM}-${ARCH} at:"
        echo "    https://github.com/${REPO}/releases/tag/${VERSION}"
        exit 1
    fi
    wget -q "${CHECKSUMS_URL}" -O "${TMP_DIR}/SHA256SUMS.txt" 2>/dev/null || true
else
    echo "[-] Error: curl or wget is required to download Veylance."
    exit 1
fi

# 4. Checksum Verification
if [ -f "${TMP_DIR}/SHA256SUMS.txt" ]; then
    EXPECTED_HASH="$(awk -v t="${TARGET}" '$2 == t || $2 == "*"t {print $1; exit}' "${TMP_DIR}/SHA256SUMS.txt")"
    if [ -n "${EXPECTED_HASH}" ]; then
        echo "[*] Verifying SHA256 checksum..."
        if command -v sha256sum >/dev/null 2>&1; then
            ACTUAL_HASH="$(sha256sum "${TMP_DIR}/veyl" | awk '{print $1}')"
        elif command -v shasum >/dev/null 2>&1; then
            ACTUAL_HASH="$(shasum -a 256 "${TMP_DIR}/veyl" | awk '{print $1}')"
        else
            ACTUAL_HASH=""
        fi

        if [ -n "${ACTUAL_HASH}" ]; then
            if [ "${EXPECTED_HASH}" != "${ACTUAL_HASH}" ]; then
                echo "[-] Checksum verification failed!"
                echo "    Expected: ${EXPECTED_HASH}"
                echo "    Actual:   ${ACTUAL_HASH}"
                exit 1
            fi
            echo "[+] Checksum verified."
        else
            echo "[!] Warning: Neither sha256sum nor shasum found; skipping checksum validation."
        fi
    else
        echo "[!] Notice: ${TARGET} not found in SHA256SUMS.txt; skipping checksum verification."
    fi
fi

chmod +x "${TMP_DIR}/veyl"

# 5. Install Binary
if [ ! -d "${INSTALL_DIR}" ]; then
    INSTALL_DIR="${HOME}/.local/bin"
    mkdir -p "${INSTALL_DIR}"
fi

if [ -w "${INSTALL_DIR}" ]; then
    mv "${TMP_DIR}/veyl" "${INSTALL_DIR}/veyl"
else
    echo "[*] Root permissions required to install to ${INSTALL_DIR}"
    if command -v sudo >/dev/null 2>&1; then
        sudo mv "${TMP_DIR}/veyl" "${INSTALL_DIR}/veyl" || {
            echo "[!] Sudo install failed. Falling back to ~/.local/bin..."
            INSTALL_DIR="${HOME}/.local/bin"
            mkdir -p "${INSTALL_DIR}"
            mv "${TMP_DIR}/veyl" "${INSTALL_DIR}/veyl"
        }
    else
        echo "[!] Sudo not available. Falling back to ~/.local/bin..."
        INSTALL_DIR="${HOME}/.local/bin"
        mkdir -p "${INSTALL_DIR}"
        mv "${TMP_DIR}/veyl" "${INSTALL_DIR}/veyl"
    fi
fi

chmod +x "${INSTALL_DIR}/veyl"
echo "[+] Successfully installed veyl to ${INSTALL_DIR}/veyl"

# 6. Verify command path
if ! command -v veyl >/dev/null 2>&1; then
    echo "[!] Notice: ${INSTALL_DIR} is not in your current PATH."
    echo "    Add it by running:"
    echo "    export PATH=\"${INSTALL_DIR}:\$PATH\""
else
    echo "[+] Verification:"
    veyl --version || true
fi

echo "[+] Done. Run 'veyl' to launch the interactive terminal audit menu."
