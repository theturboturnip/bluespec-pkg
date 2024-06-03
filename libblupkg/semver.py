from dataclasses import dataclass, field
import re
from typing import List, Tuple, Union


SEM_VER_RE = r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)" \
             r"(?P<prerelease_str>\-[0-9A-Z-a-z\-\.]+)?" \
             r"(?P<build_metadata_str>\+[0-9A-Z-a-z\-\.]+)?" \
             r"$"

@dataclass(init=True, repr=True, eq=True, frozen=True, order=False)
class SemVerExact:
    major: int
    minor: int
    patch: int
    prerelease: Tuple[Union[str, int], ...] = field(default_factory=tuple)
    build_metadata: Tuple[str, ...] = field(default_factory=tuple)

    def __lt__(self, other: "SemVerExact") -> bool:
        if not isinstance(other, SemVerExact):
            return False
        
        # Calculate precedence as per https://semver.org/

        """
        1. Precedence MUST be calculated by separating the version into major, minor, patch and pre-release identifiers in that order (Build metadata does not figure into precedence).

        2. Precedence is determined by the first difference when comparing each of these identifiers from left to right as follows: Major, minor, and patch versions are always compared numerically.

        Example: 1.0.0 < 2.0.0 < 2.1.0 < 2.1.1.

        3. When major, minor, and patch are equal, a pre-release version has lower precedence than a normal version:

        Example: 1.0.0-alpha < 1.0.0.

        4. Precedence for two pre-release versions with the same major, minor, and patch version MUST be determined by comparing each dot separated identifier from left to right until a difference is found as follows:

            Identifiers consisting of only digits are compared numerically.

            Identifiers with letters or hyphens are compared lexically in ASCII sort order.

            Numeric identifiers always have lower precedence than non-numeric identifiers.

            A larger set of pre-release fields has a higher precedence than a smaller set, if all of the preceding identifiers are equal.
        """

        # 1. is implicit, we're using SemVerExact

        # 2. compare with (major, minor, patch) unless equal
        mmp = (self.major, self.minor, self.patch)
        other_mmp = (other.major, other.minor, other.patch)
        if mmp < other_mmp:
            return True
        if mmp > other_mmp:
            return False
        
        # mmp = other_mmp
        # 3. a pre-release version has lower precedence than a normal version
        if self.prerelease and not other.prerelease:
            return True
        if other.prerelease and not self.prerelease:
            return False
        if (not self.prerelease) and (not other.prerelease):
            # self and other are equal in all useful terms
            return False
        
        # 4. compare the pre-release versions
        # Compare from left to right until a difference is found:
        for (self_prerel, other_prerel) in zip(self.prerelease, other.prerelease, strict=False):
            if self_prerel == other_prerel:
                continue
            # We know they're unequal
            if isinstance(self_prerel, int) and isinstance(other_prerel, int):
                # Identifiers consisting of only digits are compared numerically
                return self_prerel < other_prerel
            # Identifiers with letters or hyphens are compared lexically in ASCII
            if isinstance(self_prerel, str) and isinstance(other_prerel, str):
                return self_prerel < other_prerel
            # Numeric identifiers always have lower precedence than non-numeric
            if isinstance(self_prerel, int) and isinstance(other_prerel, str):
                return True
            else: # self_prerel is str, other_prerel is int, we're larger
                return False

        # No difference was found between the zipped subset of self.prerelease, other.prerelease
        # It's still possible for one to be longer - the longer tail wouldn't be included in the zip
        # A larger set of pre-release fields has a higher precedence than a smaller set, if all of the preceding identifiers are equal.
        return len(self.prerelease) < len(other.prerelease)

    def __str__(self) -> str:
        s = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            s += "-" + ".".join(str(x) for x in self.prerelease)
        if self.build_metadata:
            s += "+" + ".".join(self.build_metadata)
        return s

    @classmethod
    def parse(cls, s: str) -> "SemVerExact":
        match = re.match(SEM_VER_RE, s)
        if match is None:
            raise ValueError(f"'{s}' is not a valid SemVerExact string")
        
        prerelease_str = (match.group("prerelease_str") or "-").removeprefix("-")
        # dot-separated identifiers
        prerelease: List[Union[int, str]] = []
        for ident in prerelease_str.split("."):
            if not ident:
                raise ValueError(f"'{s}' had an empty identifier in the pre-release version and cannot be a SemVerExact string")
            if ident.isdigit():
                prerelease.append(int(ident))
            else:
                prerelease.append(ident)

        # dot-separated identifiers, which may be empty
        build_metadata = tuple((match.group("build_metadata_str") or "+").removeprefix("+").split("."))

        return SemVerExact(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=tuple(prerelease),
            build_metadata=build_metadata
        )


@dataclass(init=True, repr=True, eq=True)
class SemVerRange:
    """
    An [inclusive min, exclusive max) range of SemVers
    """

    min: SemVerExact
    max: SemVerExact

    @classmethod
    def parse(cls, s: str) -> "SemVerRange":
        PERMISSIVE_SEMVER = re.compile(r"^(?P<major>\d+)(\.(?P<minor>\d+)(\.(?P<patch>\d+))?)?$")
        match = PERMISSIVE_SEMVER.match(s)
        if match:
            # Create a semver-compatible range
            major = int(match.group("major"))
            minor = int(match.group("minor") or "0")
            patch = int(match.group("patch") or "0")

            if major == 0:
                return SemVerRange(
                    SemVerExact(0, minor, patch),
                    SemVerExact(0, minor+1, 0),
                )
            else:
                return SemVerRange(
                    SemVerExact(major, minor, patch),
                    SemVerExact(major+1, 0, 0),
                )
        else:
            raise ValueError(f"'{s}' wasn't a permissive SemVer string e.g. 'major.minor?.patch?'")
        # TODO try exact semver
