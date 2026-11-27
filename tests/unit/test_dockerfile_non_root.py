from pathlib import Path


def test_dockerfile_runs_as_non_root():
    dockerfile_path = Path(__file__).parents[2] / "Dockerfile"
    assert dockerfile_path.exists(), "Dockerfile must exist at repository root"

    content = dockerfile_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]

    # Verify user/group creation
    assert any("useradd" in line or "adduser" in line for line in lines), (
        "Dockerfile must create a dedicated non-root user"
    )

    # Verify USER directive switches to non-root user
    user_directives = [line for line in lines if line.startswith("USER")]
    assert len(user_directives) >= 1, "Dockerfile must declare a USER directive"
    target_user = user_directives[-1].split()[1]
    assert target_user not in ["root", "0"], f"Target user must not be root, got: {target_user}"

    # Verify application files are copied with non-root ownership
    assert any("--chown=" in line for line in lines), (
        "Dockerfile COPY command must assign ownership to non-root user via --chown"
    )
