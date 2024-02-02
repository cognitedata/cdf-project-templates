from __future__ import annotations

import shutil
import tempfile
import urllib
import zipfile
from abc import abstractmethod
from importlib import resources
from pathlib import Path

from rich import print
from rich.panel import Panel

from cognite_toolkit.cdf_tk.templates import COGNITE_MODULES, CUSTOM_MODULES, iterate_modules
from cognite_toolkit.cdf_tk.templates.data_classes import ConfigYAMLs
from cognite_toolkit.cdf_tk.utils import read_yaml_file


class ProjectDirectory:
    """This represents the project directory, and is used in the init command.

    It is responsible for copying the files from the templates to the project directory.

    Args:
        project_dir: The project directory.
        dry_run: Whether to do a dry run or not.
    """

    def __init__(self, project_dir: Path, dry_run: bool):
        self.project_dir = project_dir
        self._dry_run = dry_run
        self._files_to_copy: list[str] = [
            "README.md",
            ".gitignore",
            ".env.tmpl",
        ]
        self._root_modules: list[str] = [
            COGNITE_MODULES,
            CUSTOM_MODULES,
        ]
        self._source = Path(resources.files("cognite_toolkit"))  # type: ignore[arg-type]
        self.modules_by_root: dict[str, list[str]] = {}
        for root_module in self._root_modules:
            self.modules_by_root[root_module] = [
                f"{module.relative_to(self._source)!s}" for module, _ in iterate_modules(self._source / root_module)
            ]

    def set_source(self, git_branch: str | None) -> None:
        ...

    @property
    def target_dir_display(self) -> str:
        return f"'{self.project_dir.relative_to(Path.cwd())!s}'"

    @abstractmethod
    def create_project_directory(self, clean: bool) -> None:
        ...

    def print_what_to_copy(self) -> None:
        copy_prefix = "Would" if self._dry_run else "Will"
        print(f"{copy_prefix} copy these files to {self.target_dir_display}:")
        print(self._files_to_copy)

        for root_module, modules in self.modules_by_root.items():
            print(f"{copy_prefix} copy these modules to {self.target_dir_display} from {root_module}:")
            print(modules)

    def copy(self, verbose: bool) -> None:
        dry_run = self._dry_run
        copy_prefix = "Would copy" if dry_run else "Copying"
        for filename in self._files_to_copy:
            if verbose:
                print(f"{copy_prefix} file {filename} to {self.target_dir_display}")
            if not dry_run:
                if filename == "README.md":
                    content = (self._source / filename).read_text().replace("<MY_PROJECT>", self._source.name)
                    (self.project_dir / filename).write_text(content)
                else:
                    shutil.copyfile(self._source / filename, self.project_dir / filename)

        for root_module in self._root_modules:
            if verbose:
                print(f"{copy_prefix} the following modules from  {root_module} to {self.target_dir_display}")
                print(self.modules_by_root[root_module])
            if not dry_run:
                (Path(self.project_dir) / root_module).mkdir(exist_ok=True)
                # Default files are not copied, as they are only used to setup the config.yaml.
                shutil.copytree(
                    self._source / root_module,
                    self.project_dir / root_module,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("default.*"),
                )

    @abstractmethod
    def upsert_config_yamls(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def done_message(self) -> str:
        raise NotImplementedError()


class ProjectDirectoryInit(ProjectDirectory):
    """This represents the project directory, and is used in the init command.
    It is used when creating a new project (or overwriting an existing one).
    """

    def create_project_directory(self, clean: bool) -> None:
        if self.project_dir.exists() and not clean:
            print(f"Directory {self.target_dir_display} already exists.")
            exit(1)
        elif self.project_dir.exists() and clean and self._dry_run:
            print(f"Would clean out directory {self.target_dir_display}...")
        elif self.project_dir.exists() and clean:
            print(f"Cleaning out directory {self.target_dir_display}...")
            shutil.rmtree(self.project_dir)
        else:
            print(f"Found no directory {self.target_dir_display} to upgrade.")
            exit(1)

        if not self._dry_run:
            self.project_dir.mkdir(exist_ok=True)

    def upsert_config_yamls(self) -> None:
        # Creating the config.[environment].yaml files
        environment_default = self._source / COGNITE_MODULES / "default.environments.yaml"
        if not environment_default.is_file():
            print(
                f"  [bold red]ERROR:[/] Could not find default.environments.yaml in {environment_default.parent.relative_to(Path.cwd())!s}. "
                f"There is something wrong with your installation, try to reinstall `cognite-tk`, and if the problem persists, please contact support."
            )
            exit(1)

        config_yamls = ConfigYAMLs.load_default_environments(read_yaml_file(environment_default))

        config_yamls.load_default_variables(self._source)
        config_yamls.load_variables(self._source)

        for environment, config_yaml in config_yamls.items():
            config_filepath = self.project_dir / f"config.{environment}.yaml"

            print(f"Created config for {environment!r} environment.")
            if self._dry_run:
                print(f"Would write {config_filepath.name!r} to {self.target_dir_display}")
            else:
                config_filepath.write_text(config_yaml.dump_yaml_with_comments(indent_size=2))
                print(f"Wrote {config_filepath.name!r} file to {self.target_dir_display}")

    def done_message(self) -> str:
        return f"A new project was created in {self.target_dir_display}."


class ProjectDirectoryUpgrade(ProjectDirectory):
    """This represents the project directory, and is used in the init command.

    It is used when upgrading an existing project.

    """

    def __init__(self, project_dir: Path, dry_run: bool):
        super().__init__(project_dir, dry_run)
        self._has_copied = False

    def create_project_directory(self, clean: bool) -> None:
        if self.project_dir.exists():
            print(f"[bold]Upgrading directory {self.target_dir_display}...[/b]")
        else:
            print(f"Found no directory {self.target_dir_display} to upgrade.")
            exit(1)

    def do_backup(self, no_backup: bool, verbose: bool) -> None:
        if not no_backup:
            prefix = "Would have backed up" if self._dry_run else "Backing up"
            if verbose:
                print(f"{prefix} {self.target_dir_display}")
            if not self._dry_run:
                backup_dir = tempfile.mkdtemp(prefix=f"{self.project_dir.name}.", suffix=".bck", dir=Path.cwd())
                shutil.copytree(self.project_dir, Path(backup_dir), dirs_exist_ok=True)
        else:
            print(
                f"[bold yellow]WARNING:[/] --no-backup is specified, no backup {'would have been' if self._dry_run else 'will be'} be."
            )

    def print_what_to_copy(self) -> None:
        print("  Will upgrade modules and files in place.")
        super().print_what_to_copy()

    def copy(self, verbose: bool) -> None:
        super().copy(verbose)

    def set_source(self, git_branch: str | None) -> None:
        if git_branch is None:
            return

        self._source = self._download_templates(git_branch, self._dry_run)

    def upsert_config_yamls(self) -> None:
        ...

    def done_message(self) -> str:
        return f"Automatic upgraded of {self.target_dir_display} is done.\nManual Steps:"

    def print_manual_steps(self) -> None:
        print(Panel("[bold]Manual Upgrade Steps[/]"))
        raise NotImplementedError()

    @staticmethod
    def _download_templates(git_branch: str, dry_run: bool) -> Path:
        toolkit_github_url = f"https://github.com/cognitedata/cdf-project-templates/archive/refs/heads/{git_branch}.zip"
        extract_dir = tempfile.mkdtemp(prefix="git.", suffix=".tmp", dir=Path.cwd())
        prefix = "Would download" if dry_run else "Downloading"
        print(f"{prefix} templates from https://github.com/cognitedata/cdf-project-templates, branch {git_branch}...")
        print(
            "  [bold yellow]WARNING:[/] You are only upgrading templates, not the cdf-tk tool. "
            "Your current version may not support the new templates."
        )
        if not dry_run:
            try:
                zip_path, _ = urllib.request.urlretrieve(toolkit_github_url)
                with zipfile.ZipFile(zip_path, "r") as f:
                    f.extractall(extract_dir)
            except Exception:
                print(
                    f"Failed to download templates. Are you sure that the branch {git_branch} exists in"
                    + "the https://github.com/cognitedata/cdf-project-templatesrepository?\n{e}"
                )
                exit(1)
        return Path(extract_dir) / f"cdf-project-templates-{git_branch}" / "cognite_toolkit"
