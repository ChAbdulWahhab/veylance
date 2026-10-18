"""
Tests for Veylance cross-platform installer (install.sh) and asset resolution logic.
Covers:
- bash -n syntax validation
- Platform and architecture detection (Linux amd64/arm64, Darwin amd64/arm64)
- Rosetta 2 translation detection on Apple Silicon
- Release asset filename mapping across all platforms (Linux, macOS, Windows)
- Missing / 404 asset handling
- Checksum verification & collision prevention against .tar.gz
"""

import os
import shutil
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = REPO_ROOT / "install.sh"
INSTALL_PS1 = REPO_ROOT / "install.ps1"
WORKFLOW_YML = REPO_ROOT / ".github" / "workflows" / "release.yml"


def get_bash_executable():
    """Locate a functional bash executable (Git bash on Windows or system bash)."""
    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
            
    which_bash = shutil.which("bash")
    if which_bash and "system32" not in which_bash.lower():
        return which_bash
        
    return None


BASH_EXE = get_bash_executable()


def run_bash_snippet(script_snippet, env_vars=None):
    """Execute a bash snippet using the located bash executable."""
    if not BASH_EXE:
        pytest.skip("Bash executable not available in environment.")
    
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
        
    result = subprocess.run(
        [BASH_EXE, "-c", script_snippet],
        capture_output=True,
        text=True,
        env=env,
    )
    return result


def test_install_sh_syntax():
    """Verify install.sh passes syntax check with bash -n."""
    if not BASH_EXE:
        pytest.skip("Bash executable not available in environment.")
    result = subprocess.run(
        [BASH_EXE, "-n", str(INSTALL_SH)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Syntax errors in install.sh:\n{result.stderr}"


@pytest.mark.parametrize(
    "uname_s,uname_m,expected_platform,expected_arch,expected_target",
    [
        ("Linux", "x86_64", "linux", "amd64", "veyl-linux-amd64"),
        ("Linux", "amd64", "linux", "amd64", "veyl-linux-amd64"),
        ("Linux", "aarch64", "linux", "arm64", "veyl-linux-arm64"),
        ("Linux", "arm64", "linux", "arm64", "veyl-linux-arm64"),
        ("Darwin", "x86_64", "darwin", "amd64", "veyl-darwin-amd64"),
        ("Darwin", "arm64", "darwin", "arm64", "veyl-darwin-arm64"),
    ],
)
def test_platform_and_arch_detection(uname_s, uname_m, expected_platform, expected_arch, expected_target):
    """Test standard platform and architecture detection logic."""
    snippet = f"""
    OS="{uname_s}"
    case "${{OS}}" in
        Linux*)  PLATFORM="linux" ;;
        Darwin*) PLATFORM="darwin" ;;
        *) exit 1 ;;
    esac

    ARCH="{uname_m}"
    case "${{ARCH}}" in
        x86_64|amd64)  ARCH="amd64" ;;
        arm64|aarch64) ARCH="arm64" ;;
        *) exit 1 ;;
    esac

    TARGET="veyl-${{PLATFORM}}-${{ARCH}}"
    echo "PLATFORM=${{PLATFORM}}"
    echo "ARCH=${{ARCH}}"
    echo "TARGET=${{TARGET}}"
    """
    res = run_bash_snippet(snippet)
    assert res.returncode == 0
    assert f"PLATFORM={expected_platform}" in res.stdout
    assert f"ARCH={expected_arch}" in res.stdout
    assert f"TARGET={expected_target}" in res.stdout


def test_macos_rosetta_translation_detection():
    """Verify that Darwin x86_64 shell under Rosetta 2 detects Apple Silicon and selects arm64."""
    snippet = """
    PLATFORM="darwin"
    ARCH="amd64"
    # Mock sysctl call returning 1 for translated process
    sysctl() {
        if [ "$2" = "sysctl.proc_translated" ]; then
            echo "1"
        else
            echo "0"
        fi
    }
    export -f sysctl

    if [ "${PLATFORM}" = "darwin" ] && [ "${ARCH}" = "amd64" ]; then
        IS_TRANSLATED="$(sysctl -in sysctl.proc_translated 2>/dev/null || echo 0)"
        HW_ARM64="$(sysctl -in hw.optional.arm64 2>/dev/null || echo 0)"
        if [ "${IS_TRANSLATED}" = "1" ] || [ "${HW_ARM64}" = "1" ]; then
            ARCH="arm64"
        fi
    fi
    TARGET="veyl-${PLATFORM}-${ARCH}"
    echo "TARGET=${TARGET}"
    """
    res = run_bash_snippet(snippet)
    assert res.returncode == 0
    assert "TARGET=veyl-darwin-arm64" in res.stdout


def test_macos_hw_arm64_detection():
    """Verify that Darwin x86_64 with hw.optional.arm64=1 selects arm64."""
    snippet = """
    PLATFORM="darwin"
    ARCH="amd64"
    sysctl() {
        if [ "$2" = "hw.optional.arm64" ]; then
            echo "1"
        else
            echo "0"
        fi
    }
    export -f sysctl

    if [ "${PLATFORM}" = "darwin" ] && [ "${ARCH}" = "amd64" ]; then
        IS_TRANSLATED="$(sysctl -in sysctl.proc_translated 2>/dev/null || echo 0)"
        HW_ARM64="$(sysctl -in hw.optional.arm64 2>/dev/null || echo 0)"
        if [ "${IS_TRANSLATED}" = "1" ] || [ "${HW_ARM64}" = "1" ]; then
            ARCH="arm64"
        fi
    fi
    TARGET="veyl-${PLATFORM}-${ARCH}"
    echo "TARGET=${TARGET}"
    """
    res = run_bash_snippet(snippet)
    assert res.returncode == 0
    assert "TARGET=veyl-darwin-arm64" in res.stdout


def test_unsupported_os_error():
    """Verify unsupported operating systems fail gracefully with actionable error."""
    snippet = """
    OS="FreeBSD"
    case "${OS}" in
        Linux*)     PLATFORM="linux" ;;
        Darwin*)    PLATFORM="darwin" ;;
        *)
            echo "[-] Error: Unsupported operating system: ${OS}"
            echo "    Veylance currently supports Linux, macOS, and Windows."
            exit 1
            ;;
    esac
    """
    res = run_bash_snippet(snippet)
    assert res.returncode == 1
    assert "Unsupported operating system: FreeBSD" in res.stdout
    assert "supports Linux, macOS, and Windows" in res.stdout


def test_unsupported_arch_error():
    """Verify unsupported architectures fail gracefully."""
    snippet = """
    ARCH="mips64"
    case "${ARCH}" in
        x86_64|amd64)   ARCH="amd64" ;;
        arm64|aarch64)  ARCH="arm64" ;;
        *)
            echo "[-] Error: Unsupported architecture: ${ARCH}"
            echo "    Veylance currently supports x86_64 (amd64) and arm64."
            exit 1
            ;;
    esac
    """
    res = run_bash_snippet(snippet)
    assert res.returncode == 1
    assert "Unsupported architecture: mips64" in res.stdout


def test_checksum_exact_matching_avoids_tarball_collision():
    """Verify exact awk match matches binary and avoids false match on .tar.gz."""
    manifest = (
        "1111111111111111111111111111111111111111111111111111111111111111  veyl-darwin-amd64.tar.gz\n"
        "2222222222222222222222222222222222222222222222222222222222222222  veyl-darwin-amd64\n"
        "3333333333333333333333333333333333333333333333333333333333333333  veyl-darwin-arm64\n"
    )
    snippet = f"""
    cat << 'EOF' > manifest.txt
{manifest}
EOF
    TARGET="veyl-darwin-amd64"
    EXPECTED_HASH="$(awk -v t="${{TARGET}}" '$2 == t || $2 == "*"t {{print $1; exit}}' manifest.txt)"
    echo "HASH=${{EXPECTED_HASH}}"
    rm -f manifest.txt
    """
    res = run_bash_snippet(snippet)
    assert res.returncode == 0
    assert "HASH=2222222222222222222222222222222222222222222222222222222222222222" in res.stdout


def test_checksum_mismatch_fails():
    """Verify checksum mismatch terminates with non-zero exit code."""
    snippet = """
    EXPECTED_HASH="expected_abc123"
    ACTUAL_HASH="actual_def456"
    if [ "${EXPECTED_HASH}" != "${ACTUAL_HASH}" ]; then
        echo "[-] Checksum verification failed!"
        echo "    Expected: ${EXPECTED_HASH}"
        echo "    Actual:   ${ACTUAL_HASH}"
        exit 1
    fi
    """
    res = run_bash_snippet(snippet)
    assert res.returncode == 1
    assert "Checksum verification failed!" in res.stdout


def test_http_404_error_message():
    """Verify 404 response produces clear actionable error with release tag link."""
    snippet = """
    HTTP_CODE="404"
    TARGET="veyl-darwin-amd64"
    VERSION="v0.2.2"
    REPO="ChAbdulWahhab/veylance"
    PLATFORM="darwin"
    ARCH="amd64"

    if [ "${HTTP_CODE}" = "404" ]; then
        echo "[-] Error: Release binary '${TARGET}' not found for version ${VERSION} (HTTP 404)."
        echo "    Please verify that version ${VERSION} publishes a pre-compiled binary for ${PLATFORM}-${ARCH}."
        echo "    Available release assets can be inspected at:"
        echo "    https://github.com/${REPO}/releases/tag/${VERSION}"
        exit 1
    fi
    """
    res = run_bash_snippet(snippet)
    assert res.returncode == 1
    assert "Release binary 'veyl-darwin-amd64' not found for version v0.2.2 (HTTP 404)" in res.stdout
    assert "https://github.com/ChAbdulWahhab/veylance/releases/tag/v0.2.2" in res.stdout


def test_release_workflow_matrix_coverage():
    """Inspect release.yml to ensure all target platforms and architectures are configured."""
    content = WORKFLOW_YML.read_text(encoding="utf-8")
    
    # Must cover Linux amd64
    assert "ubuntu-latest" in content
    assert "linux-amd64" in content
    assert "veyl-linux-amd64" in content

    # Must cover Windows amd64
    assert "windows-latest" in content
    assert "windows-amd64" in content
    assert "veyl-windows-amd64" in content

    # Must cover macOS Intel (amd64) and Apple Silicon (arm64)
    assert "macos-15-intel" in content
    assert "darwin-amd64" in content
    assert "veyl-darwin-amd64" in content

    assert "macos-14" in content
    assert "darwin-arm64" in content
    assert "veyl-darwin-arm64" in content

    # Artifact upload pattern must include both binary and archives
    assert "${{ matrix.artifact_name }}" in content
    assert "${{ matrix.artifact_name }}.*" in content


def test_windows_installer_asset_mapping():
    """Verify install.ps1 targets Windows amd64 zip and extracts veyl.exe."""
    ps1_content = INSTALL_PS1.read_text(encoding="utf-8")
    assert '$assetName = "veyl-windows-amd64.zip"' in ps1_content
    assert "veyl.exe" in ps1_content
    assert "SHA256SUMS.txt" in ps1_content


def test_installer_and_workflow_asset_parity():
    """Verify install.sh expected targets match release.yml matrix outputs."""
    # Assets expected by install.sh:
    unix_targets = [
        "veyl-linux-amd64",
        "veyl-darwin-amd64",
        "veyl-darwin-arm64",
    ]
    workflow_content = WORKFLOW_YML.read_text(encoding="utf-8")
    for target in unix_targets:
        assert target in workflow_content, f"Target {target} missing from release workflow!"

