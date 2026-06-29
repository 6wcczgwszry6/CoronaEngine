import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

required_conan_version = ">=2.28"


class CoronaEngineConan(ConanFile):
    name = "coronaengine"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"

    options = {
        "shared": [True, False],
        "with_editor": [True, False],
        "with_examples": [True, False],
        "with_tests": [True, False],
        "with_vision": [True, False],
        "with_oidn": [True, False],
        "with_cef": [True, False],
    }

    default_options = {
        "shared": False,
        "with_editor": True,
        "with_examples": True,
        "with_tests": False,
        "with_vision": False,
        "with_oidn": False,
        "with_cef": True,
        "horizon/*:shared": False,
        "horizon/*:with_tools": True,
        "horizon/*:with_examples": False,
        "horizon/*:with_tests": False,
        "horizon/*:with_ocarina": False,
        "horizon/*:with_vision_hotfix": False,
        "sdl/*:shared": False,
        "glfw/*:shared": False,
        "volk/*:shared": False,
        "spirv-cross/*:shared": False,
        "spirv-cross/*:build_executable": False,
        "spirv-tools/*:shared": False,
        "spirv-tools/*:build_executables": False,
        "ffmpeg/*:shared": True,
        "hwloc/*:shared": True,
    }

    def layout(self):
        cmake_layout(self, build_folder="build/conan")

    def set_version(self):
        self.version = os.environ.get("CORONAENGINE_CONAN_VERSION", "0.5.0")

    def requirements(self):
        self.requires("horizon/0.5.0", transitive_headers=True, transitive_libs=True)
        self.requires("ktm/0.2.14", transitive_headers=True)
        self.requires("assimp/5.4.3", transitive_headers=True, transitive_libs=True)
        self.requires("stb/cci.20230920", transitive_headers=True)
        self.requires("nanobind/2.9.2", transitive_headers=True, transitive_libs=True)
        self.requires("sdl/3.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("enet/1.3.18", transitive_headers=True, transitive_libs=True)
        self.requires("onetbb/2022.3.0", transitive_headers=True, transitive_libs=True)
        self.requires("miniaudio/0.11.21", transitive_headers=True)
        self.requires("nlohmann_json/3.12.0", transitive_headers=True)
        self.requires("tinyexr/1.0.7", transitive_headers=True, transitive_libs=True)
        self.requires("meshoptimizer/0.25", transitive_headers=True, transitive_libs=True)
        self.requires("astc-encoder/5.3.0", transitive_headers=True, transitive_libs=True)
        self.requires("ffmpeg/8.1.1", transitive_headers=True, transitive_libs=True)

        if bool(self.options.with_cef):
            self.requires("cef-binary/143.0.14.gdd46a37.chromium143.0.7499.193",
                          transitive_headers=True, transitive_libs=True)

        if bool(self.options.with_vision):
            self.requires("cxxopts/3.2.1", transitive_headers=True)
            self.requires("glfw/3.4", transitive_headers=True, transitive_libs=True)
            if bool(self.options.with_oidn):
                self.requires("openimagedenoise/2.3.3", transitive_headers=True, transitive_libs=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        toolchain = CMakeToolchain(self)
        cache_variables = toolchain.cache_variables
        cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        cache_variables["BUILD_CORONA_EDITOR"] = bool(self.options.with_editor)
        cache_variables["BUILD_CORONA_EXAMPLES"] = bool(self.options.with_examples)
        cache_variables["BUILD_CORONA_TESTING"] = bool(self.options.with_tests)
        cache_variables["CORONA_BUILD_VISION"] = bool(self.options.with_vision)
        cache_variables["VISION_BUILD_OIDN"] = bool(self.options.with_oidn)
        cache_variables["CORONA_ENABLE_CEF"] = bool(self.options.with_cef)

        if bool(self.options.with_cef):
            cef_dep = self.dependencies["cef-binary"]
            cache_variables["CORONA_CEF_ROOT"] = cef_dep.package_folder.replace("\\", "/")

        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="corona_engine")
