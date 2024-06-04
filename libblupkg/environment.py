from dataclasses import dataclass, field
import tomllib
from typing import Dict, List, Optional, Tuple

from libblupkg.unpack_dataclass import unpack_dataclass

@dataclass
class BlupkgBuild:
    target_dir: str = "target"


@dataclass
class BlupkgProject:
    name: str
    """The name of the package"""
    version: str
    """A SemVer-compatible version number for this package"""
    toplevel: Optional[str] = None
    """The toplevel Bluespec module created in simulation/synthesis."""
    defines: Dict[str, str] = field(default_factory=dict)
    """-D defines to pass as command-line arguments"""
    features: Dict[str, List[str]] = field(default_factory=dict)
    """
    The features this package exposes, a la `cargo features`.
    See https://doc.rust-lang.org/cargo/reference/features.html
    """


@dataclass
class BlupkgDep:
    git: Optional[str] = None
    """The path to a Git repository, e.g. hosted on Github. Must have a Blupkg.toml at the repository root."""
    path: Optional[str] = None
    """The path to a local non-Git folder containing the dependent package. Must have a Blupkg.toml."""

    version: Optional[str] = None
    """
    The SemVer version constraint for the dependency.
    Right now only supports SemVer-compatible i.e. '2.3' allows [2.3.0, 3.0.0), '0.3' allows [0.3.0, 0.4.0).
    Only supported if using `git` path.
    `version`, `rev`, `tag`, and `branch` are mutually exclusive.
    """

    rev: Optional[str] = None
    """
    The specific Git revision of the dependency.
    Only supported if using `git` path.
    `version`, `rev`, `tag`, and `branch` are mutually exclusive.
    """

    tag: Optional[str] = None
    """
    The specific Git tag of the dependency.
    Only supported if using `git` path.
    `version`, `rev`, `tag`, and `branch` are mutually exclusive.
    """

    branch: Optional[str] = None
    """
    The specific Git branch of the dependency.
    Only supported if using `git` path.
    `version`, `rev`, `tag`, and `branch` are mutually exclusive.
    """

    optional: bool = False
    """
    Whether
    """

    def __post_init__(self):
        if self.git and self.path:
            raise ValueError(f"Cannot create {self.__class__.__name__} '{self}', BlupkgDep cannot come from both a repository and a local path")
        if not self.git and not self.path:
            raise ValueError(f"Cannot create {self.__class__.__name__} '{self}', one of (git, path) must be non-empty")

        discriminators = (self.version, self.rev, self.tag, self.branch)
        set_discriminators = sum((1 if d else 0) for d in discriminators)
        if set_discriminators and self.path:
            raise ValueError(f"Cannot create {self.__class__.__name__} '{self}', can't set (version, rev, tag, or branch) if using a local path")
        if set_discriminators != 1:
            raise ValueError(f"Cannot create {self.__class__.__name__} '{self}', can't set more than one of (version, rev, tag, branch)")

@dataclass
class BlupkgEnv:
    project: BlupkgProject
    build: BlupkgBuild = field(default_factory=BlupkgBuild)
    dependencies: Dict[str, BlupkgDep] = field(default_factory=dict)


@dataclass
class BlupkgLockedPackage:
    name: str
    """The name of the package"""
    version: str
    """The resolved exact version of the package"""

    dependencies: Dict[str, BlupkgDep]
    """The dependencies of the package, non-exact"""

    git: Optional[Tuple[str, str]] = None
    """
    (git path, commit hash) if set
    """
    path: Optional[str] = None
    """
    local path if set
    """


@dataclass
class BlupkgLock:
    packages: List[BlupkgLockedPackage]
    version: int = 1


def load_blupkg_environment() -> Tuple[BlupkgEnv, Optional[BlupkgLock]]:
    """
    We should be at the root of a blupkg environment.
    If so, there should be a valid Blupkg.toml file and an optional Blupkg.lock file.
    """
    with open("Blupkg.toml", mode="rb") as f:
        env = unpack_dataclass(BlupkgEnv, tomllib.load(f))

    lock = None
    try:
        with open("Blupkg.lock", mode="rb") as f:
            lock_dict = tomllib.load(f)
            lock_version = lock_dict.get("version", None)
            if lock_version is None:
                print("Blupkg.lock has no version, must be corrupt")
            else:
                try:
                    lock_version_int = int(lock_version)
                except ValueError:
                    print(f"Blupkg.lock has non-int version '{lock_version}', must be corrupt")
                else:
                    if lock_version_int < BlupkgLock.version:
                        print(f"Blupkg.lock has outdated version '{lock_version_int}', need to recreate")
                    elif lock_version_int > BlupkgLock.version:
                        raise RuntimeError(f"Blupkg.lock has a newer version '{lock_version_int}' than expected '{BlupkgLock.version}', please update Blupkg")
                    else:
                        lock = unpack_dataclass(BlupkgLock, lock_dict)
    except OSError as ex:
        print(f"Failed to open Blupkg.lock: {ex}\nContinuing without...")

    return env, lock
