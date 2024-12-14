from dataclasses import dataclass, field
import enum

import compiler.languages

LANGUAGE = compiler.languages.Language.C

class LanguageVersion(enum.StrEnum):
    C99 = "c99"
    C11 = "c11"
    C17 = "c17"
    C23 = "c23"
    Gnu99 = "gnu99"
    Gnu11 = "gnu11"
    Gnu17 = "gnu17"
    Gnu23 = "gnu23"

@dataclass(frozen=True)
class Warnings:
    all: bool = False
    extra: bool = False
    pedantic: bool = False

    def to_args(self) -> list[str]:
        result = []

        if self.all:
            result.append("-Wall")
        if self.extra:
            result.append("-Wextra")
        if self.pedantic:
            result.append("-Wpedantic")

        return result

@dataclass(frozen=True)
class Flags:
    include_directories: set[str] = field(default_factory=set)
    system_include_directories: set[str] = field(default_factory=set)
    includes: set[str] = field(default_factory=set)
    definitions: dict[str, str | None] = field(default_factory=dict)

    opt_level: int | None = None
    lang_version: LanguageVersion | None = None
    warnings_as_errors: bool | None = None
    warnings: Warnings = Warnings()

    def to_args(self) -> list[str]:
        result = []

        if self.opt_level is not None:
            result.append(f"-O{self.opt_level}")

        if self.lang_version is not None:
            result.append(f"-std={self.lang_version}")

        if self.warnings_as_errors is True:
            result.append("-Werror")

        for d in self.include_directories:
            result.append("-I" + d)

        for d in self.system_include_directories:
            result.append("-isystem")
            result.append(d)

        for d in self.includes:
            result.append("-include")
            result.append(d)

        for (k, v) in self.definitions.items():
            if v is None:
                result.append(f"-D{k}")
            else:
                result.append(f"-D{k}={v}")

        return result + self.warnings.to_args()

class Kind(enum.StrEnum):
    gcc = "gcc"
    clang = "clang"

class CompileTarget:
    def __init__(self, private: Flags, public: Flags, sources):
        self.private = private
        self.public = public
        self.sources = sources

