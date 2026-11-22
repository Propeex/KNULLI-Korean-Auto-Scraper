"""v0.8.6 beta: GitHub prerelease discovery and unattended safe updates."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app_version
import auto_update as update
import auto_update_helper as helper
import scripts.package_release as packager


def release_row(tag, prerelease=True, draft=False, with_assets=True):
    basename = f"KNULLI-Korean-Auto-Scraper-{tag}-Windows.zip"
    url = (f"https://github.com/{app_version.GITHUB_REPOSITORY}"
           f"/releases/download/{tag}/{basename}")
    assets = [
        {"name": basename, "browser_download_url": url, "digest": "sha256:" + "a" * 64},
        {"name": basename + ".sha256", "browser_download_url": url + ".sha256"},
    ]
    return {
        "tag_name": tag,
        "prerelease": prerelease,
        "draft": draft,
        "assets": assets if with_assets else [],
    }


def archive_bytes(tag: str, additional: dict[str, bytes] | None = None,
                  unsafe: str | None = None) -> bytes:
    prefix = f"KNULLI-Korean-Auto-Scraper-{tag}/"
    items = {
        "GUI_실행.pyw": b"print('launch')\n",
        "gui.py": b"print('new GUI')\n",
        "app_version.py": f'VERSION_TAG = "{tag}"\n'.encode(),
        "auto_update.py": b"print('updater')\n",
        "auto_update_helper.py": b"print('helper')\n",
        "aliases.json": b'{"defaults":"new"}',
        "docs/KNOWN_ISSUES.md": b"new documentation",
    }
    if additional:
        items.update(additional)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, content in items.items():
            z.writestr(prefix + rel, content)
        if unsafe:
            z.writestr(prefix + unsafe, b"evil")
    return output.getvalue()


class TestBetaDiscovery(unittest.TestCase):
    def test_find_newest_beta_not_latest_stable_or_draft(self):
        records = [
            release_row("v0.8.7-beta.1"),
            release_row("v1.0.0-beta.1", draft=True),
            release_row("v0.9.0-beta.1", with_assets=False),
            release_row("v0.8.9-beta.2"),
            release_row("v1.0.0-beta.1", prerelease=False),
            release_row("v0.8.5-beta.9"),
        ]
        match = update.choose_newest_beta(records, "v0.8.6-beta.1")
        self.assertEqual(match.tag, "v0.8.9-beta.2")

    def test_no_downgrade_and_no_reinstall(self):
        records = [release_row("v0.8.6-beta.1"), release_row("v0.8.5-beta.100")]
        self.assertIsNone(update.choose_newest_beta(records, "v0.8.6-beta.1"))

    def test_invalid_release_url_not_trusted(self):
        row = release_row("v0.8.6-beta.2")
        row["assets"][0]["browser_download_url"] = "https://attacker.example/bad.zip"
        self.assertIsNone(update.choose_newest_beta([row], "v0.8.6-beta.1"))

    def test_beta_version_order_is_numeric(self):
        self.assertGreater(update.beta_key("v0.8.6-beta.10"),
                           update.beta_key("v0.8.6-beta.9"))
        self.assertGreater(update.beta_key("v0.9.0-beta.1"),
                           update.beta_key("v0.8.99-beta.100"))
        with self.assertRaises(ValueError):
            update.beta_key("v0.9.0")

    def test_release_api_timeout_is_nonfatal_at_startup(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(update, "data_dir", return_value=Path(td)), \
             mock.patch.object(update, "discover", side_effect=TimeoutError("offline")), \
             mock.patch.object(update, "log_error") as logger:
            self.assertFalse(update.try_launch_update(Path(td)))
            logger.assert_called_once()

    def test_startup_launches_detached_helper_without_prompt(self):
        r = release_row("v0.8.6-beta.2")
        staged_release = update.choose_newest_beta([r], "v0.8.6-beta.1")
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(update, "data_dir", return_value=Path(td)), \
             mock.patch.object(update, "discover", return_value=staged_release), \
             mock.patch.object(update, "stage_release", return_value=Path(td)) as stage, \
             mock.patch.object(update.subprocess, "Popen") as launch:
            self.assertTrue(update.try_launch_update(Path(td)))
        stage.assert_called_once_with(staged_release)
        args, kwargs = launch.call_args
        self.assertEqual(args[0][1], str(Path(td) / "update_worker.py"))
        self.assertTrue(kwargs["close_fds"])

    def test_concurrent_launch_does_not_install_twice(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(update, "data_dir", return_value=Path(td)), \
             mock.patch.object(update, "discover") as discover:
            lock = update._acquire_update_lock()
            self.assertTrue(lock.is_file())
            self.assertFalse(update.try_launch_update(Path(td)))
            discover.assert_not_called()
            update._release_update_lock(lock)
            self.assertFalse(lock.exists())

    def test_no_update_releases_lock(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(update, "data_dir", return_value=Path(td)), \
             mock.patch.object(update, "discover", return_value=None):
            self.assertFalse(update.try_launch_update(Path(td)))
            self.assertFalse((Path(td) / "auto_update.lock").exists())

    def test_skip_retry_after_failed_worker(self):
        with mock.patch.dict(os.environ, {"KNULLI_SKIP_UPDATE_ONCE": "1"}), \
             mock.patch.object(update, "discover") as discover:
            self.assertFalse(update.try_launch_update(Path(".")))
            discover.assert_not_called()


class TestArchiveSafety(unittest.TestCase):
    TAG = "v0.8.6-beta.2"

    def test_zip_verify_rejects_traversal_unknown_and_version_mismatch(self):
        safe = archive_bytes(self.TAG)
        result = update.verify_archive(safe, self.TAG)
        self.assertTrue(update.MANDATORY.issubset(result))
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            update.verify_archive(archive_bytes(self.TAG, unsafe="../outside.py"), self.TAG)
        with self.assertRaisesRegex(ValueError, "unexpected"):
            update.verify_archive(archive_bytes(self.TAG, unsafe="private_config.json"), self.TAG)
        with self.assertRaisesRegex(ValueError, "version"):
            incorrect_version = archive_bytes(
                self.TAG,
                additional={"app_version.py": b'VERSION_TAG = "v0.8.6-beta.9"\n'},
            )
            update.verify_archive(incorrect_version, self.TAG)

    def test_reject_duplicate_files(self):
        prefix = f"KNULLI-Korean-Auto-Scraper-{self.TAG}/"
        with io.BytesIO() as output:
            with zipfile.ZipFile(output, "w") as z:
                for rel, content in update.verify_archive(archive_bytes(self.TAG), self.TAG).items():
                    z.writestr(prefix + rel, content)
                z.writestr(prefix + "gui.py", b"duplicate")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                update.verify_archive(output.getvalue(), self.TAG)

    def test_sha256_and_manifest_before_update(self):
        data = archive_bytes(self.TAG)
        archive_name = f"KNULLI-Korean-Auto-Scraper-{self.TAG}-Windows.zip"
        checksum = hashlib.sha256(data).hexdigest()
        r = update.Release(self.TAG, "https://github.com/release.zip",
                           "https://github.com/release.zip.sha256", "sha256:" + checksum)
        def fake_download(url, limit, timeout=5):
            if url == r.zip_url:
                return data
            return f"{checksum}  {archive_name}\n".encode("ascii")
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(update, "_read_https", side_effect=fake_download):
            stage = update.stage_release(r, Path(td))
            manifest = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["tag"], self.TAG)
            self.assertEqual(len(manifest["files"]), 7)
            self.assertEqual((stage / "payload" / "gui.py").read_bytes(), b"print('new GUI')\n")
            self.assertTrue((stage / "update_worker.py").exists())

    def test_corrupted_download_does_not_get_staged(self):
        data = archive_bytes(self.TAG)
        r = update.Release(self.TAG, "https://github.com/release.zip",
                           "https://github.com/release.zip.sha256")
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(update, "_read_https",
                               side_effect=[data, b"0" * 64 + b"  archive.zip\n"]):
            with self.assertRaisesRegex(ValueError, "checksum"):
                update.stage_release(r, Path(td))
            self.assertFalse(list(Path(td).glob("knulli_autoupdate_*")))

    def test_package_release_tag_alignment(self):
        # The running app's version and next package tag must match.
        self.assertEqual(app_version.VERSION_TAG, "v0.8.6-beta.1")
        self.assertTrue(update.MANDATORY.issubset({
            "GUI_실행.pyw", "gui.py", "app_version.py",
            "auto_update.py", "auto_update_helper.py",
        }))


class TestHelper(unittest.TestCase):
    TAG = "v0.8.6-beta.2"

    def make_install(self, root: Path):
        install = root / "install"
        install.mkdir()
        (install / "GUI_실행.pyw").write_text("old launcher", encoding="utf-8")
        (install / "gui.py").write_text("old gui", encoding="utf-8")
        (install / "aliases.json").write_text("user alias", encoding="utf-8")
        (install / "config.json").write_text("USER CONFIG", encoding="utf-8")
        work = install / "work"
        work.mkdir()
        (work / "game_scrape_cache.bin").write_bytes(b"SCRAPE DATA")
        outside = root / "Documents" / "KNULLI Auto Scraper Data"
        outside.mkdir(parents=True)
        (outside / "settings.json").write_text("KEEP THIS", encoding="utf-8")
        return install, outside

    def make_stage(self, root: Path):
        source = archive_bytes(self.TAG)
        release = update.verify_archive(source, self.TAG)
        stage = root / "staged"
        stage.mkdir()
        payload = stage / "payload"
        manifest = {}
        for rel, body in release.items():
            path = payload / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            manifest[rel] = hashlib.sha256(body).hexdigest()
        (stage / "manifest.json").write_text(
            json.dumps({"tag": self.TAG, "files": manifest}), encoding="utf-8")
        return stage

    def test_update_in_place_preserves_user_and_scraped_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            install, outside = self.make_install(root)
            stage = self.make_stage(root)
            total = helper.apply_update(stage, install)
            self.assertGreaterEqual(total, 5)
            self.assertEqual((install / "gui.py").read_text(), "print('new GUI')\n")
            self.assertEqual((install / "aliases.json").read_text(), "user alias")
            self.assertEqual((install / "config.json").read_text(), "USER CONFIG")
            self.assertEqual((install / "work" / "game_scrape_cache.bin").read_bytes(), b"SCRAPE DATA")
            self.assertEqual((outside / "settings.json").read_text(), "KEEP THIS")
            self.assertTrue((install / "docs" / "KNOWN_ISSUES.md").is_file())

    def test_bad_staged_hash_cannot_modify_app(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            install, _ = self.make_install(root)
            stage = self.make_stage(root)
            (stage / "payload" / "gui.py").write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                helper.apply_update(stage, install)
            self.assertEqual((install / "gui.py").read_text(), "old gui")

    def test_failed_replace_rolls_back_application_code(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            install, _ = self.make_install(root)
            stage = self.make_stage(root)
            actual_replace = helper.os.replace
            attempts = 0
            def fail_once(src, dst):
                nonlocal attempts
                attempts += 1
                if attempts == 3:
                    raise PermissionError("simulated Windows locked file")
                return actual_replace(src, dst)
            with mock.patch.object(helper.os, "replace", side_effect=fail_once):
                with self.assertRaises(PermissionError):
                    helper.apply_update(stage, install)
            self.assertEqual((install / "GUI_실행.pyw").read_text(), "old launcher")
            self.assertEqual((install / "gui.py").read_text(), "old gui")
            self.assertEqual((install / "aliases.json").read_text(), "user alias")

    def test_symlinked_destination_refused(self):
        if os.name == "nt":
            self.skipTest("Symlink privileges vary on Windows")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            install, _ = self.make_install(root)
            stage = self.make_stage(root)
            protected = root / "personal_file.py"
            protected.write_text("PERSONAL", encoding="utf-8")
            (install / "auto_update.py").symlink_to(protected)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                helper.apply_update(stage, install)
            self.assertEqual(protected.read_text(), "PERSONAL")

    def test_restart_is_silent_and_no_retry_on_failure(self):
        with mock.patch.object(helper.subprocess, "Popen") as proc:
            helper._restart("pythonw.exe", Path("C:/DemoApp"), skip_update=True)
            kwargs = proc.call_args.kwargs
            self.assertEqual(kwargs["env"]["KNULLI_SKIP_UPDATE_ONCE"], "1")
            self.assertTrue(kwargs["close_fds"])


if __name__ == "__main__":
    unittest.main()
