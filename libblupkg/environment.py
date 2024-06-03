from dataclasses import dataclass, field
import tomllib
from typing import Dict, Optional, Tuple

from libblupkg.unpack_dataclass import unpack_dataclass

@dataclass
class BlupkgBuild:
    target_dir: str = "target"


@dataclass
class BlupkgProject:
    name: str
    version: str


@dataclass
class BlupkgDep:
    git: str
    """The path to the Git repository"""
    version: Optional[str] = None
    """
    The SemVer version constraint for the dependency.
    Right now only supports SemVer-compatible i.e. '2.3' allows [2.3.0, 3.0.0).
    `version`, `rev`, `tag`, and `branch` are mutually exclusive.
    """
    rev: Optional[str] = None
    """The specific Git revision of the dependency. `version`, `rev`, `tag`, and `branch` are mutually exclusive."""
    tag: Optional[str] = None
    """The specific Git tag of the dependency. `version`, `rev`, `tag`, and `branch` are mutually exclusive."""
    branch: Optional[str] = None
    """The specific Git branch of the dependency. `version`, `rev`, `tag`, and `branch` are mutually exclusive."""

    def __post_init__(self):
        discriminators = (self.version, self.rev, self.tag, self.branch)
        if sum((1 if d else 0) for d in discriminators) != 1:
            raise ValueError(f"Cannot create {self.__class__.__name__} '{self}', only allowed to set exactly one of (version, rev, tag, branch)")


@dataclass
class BlupkgEnv:
    project: BlupkgProject
    build: BlupkgBuild = field(default_factory=BlupkgBuild)
    dependencies: Dict[str, BlupkgDep] = field(default_factory=dict)


@dataclass
class BlupkgLock:
    pass # TODO


def load_blupkg_environment() -> Tuple[BlupkgEnv, Optional[BlupkgLock]]:
    """
    We should be at the root of a blupkg environment.
    If so, there should be a valid Blupkg.toml file, and an optional Blupkg.lock file.
    """
    with open("Blupkg.toml", mode="rb") as f:
        env = unpack_dataclass(BlupkgEnv, tomllib.load(f))
        return (env, None)
    