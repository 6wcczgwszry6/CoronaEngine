import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, replace_in_file, rmdir


class HorizonConan(ConanFile):
    name = "horizon"
    package_type = "library"
    license = "MIT"
    homepage = "https://github.com/CoronaEngine/Horizon.git"
    settings = "os", "arch", "compiler", "build_type"

    options = {
        "shared": [True, False],
        "with_ocarina": [True, False],
        "with_vision_hotfix": [True, False],
        "with_cuda": [True, False],
        "with_tools": [True, False],
        "with_examples": [True, False],
        "with_tests": [True, False],
    }

    default_options = {
        "shared": False,
        "with_ocarina": True,
        "with_vision_hotfix": True,
        "with_cuda": True,
        "with_tools": False,
        "with_examples": False,
        "with_tests": False,
        "spirv-cross/*:shared": False,
        "spirv-cross/*:build_executable": False,
        "spirv-tools/*:shared": False,
        "spirv-tools/*:build_executables": False,
        "glfw/*:shared": False,
    }

    def layout(self):
        cmake_layout(self, build_folder="build/conan")

    def set_version(self):
        self.version = os.environ.get("HORIZON_CONAN_VERSION", "0.5.0")

    def source(self):
        for entry in os.listdir(self.source_folder):
            path = os.path.join(self.source_folder, entry)
            if os.path.isdir(path):
                rmdir(self, path)
            else:
                os.remove(path)

        git_url = os.environ.get("HORIZON_CONAN_GIT_URL", self.homepage)
        git_ref = os.environ.get("HORIZON_CONAN_GIT_REF", "conan-migration")
        self.run(f'git clone --depth 1 --branch "{git_ref}" "{git_url}" "."')
        self._patch_sources()

    def _patch_sources(self):
        cuda_compiler = os.path.join(
            self.source_folder,
            "modules",
            "ocarina",
            "backends",
            "cuda",
            "cuda_compiler.cpp",
        )
        if os.path.isfile(cuda_compiler):
            with open(cuda_compiler, encoding="utf-8") as source_file:
                source = source_file.read()
            if "_access" in source and "#include <io.h>" not in source:
                replace_in_file(
                    self,
                    cuda_compiler,
                    '#include "dsl/dsl.h"\n',
                    '#include "dsl/dsl.h"\n\n#ifdef _WIN32\n#include <io.h>\n#endif\n',
                    strict=False,
                )

    def requirements(self):
        self.requires("ktm/0.2.14", transitive_headers=True)
        self.requires("pfr/1.91.0", transitive_headers=True)
        self.requires("spirv-cross/1.4.350.0", transitive_headers=True, transitive_libs=True)
        self.requires("spirv-tools/1.4.350.0", transitive_headers=True, transitive_libs=True)
        self.requires("volk/1.4.350.0", transitive_headers=True, transitive_libs=True)
        self.requires("vulkan-headers/1.4.350.0", transitive_headers=True)
        self.requires("vulkan-memory-allocator/3.4.0", transitive_headers=True)
        self.requires("quill/11.0.2", transitive_headers=True, transitive_libs=True)
        self.requires("slang/2026.10", transitive_headers=True, transitive_libs=True)

        if bool(self.options.with_examples):
            self.requires("stb/cci.20240531")
            self.requires("glfw/3.4")
            self.requires("tinyobjloader/1.0.7")
            self.requires("glm/1.0.1")

        if bool(self.options.with_ocarina) and bool(self.options.with_cuda):
            self.requires("fmt/12.1.0")
            self.requires("spdlog/1.17.0")
            self.requires("xxhash/0.8.3")

    @staticmethod
    def _copy_headers(conanfile, src, dst):
        for pattern in ("*.h", "*.hpp", "*.inl"):
            copy(conanfile, pattern, src=src, dst=dst, keep_path=True)

    @staticmethod
    def _env_bool(name, default=False):
        value = os.environ.get(name, "")
        if not value:
            return default
        return value.lower() in ("1", "true", "yes", "on")

    def _fetchcontent_source_root(self):
        source_root = os.environ.get("HORIZON_FETCHCONTENT_SOURCE_ROOT")
        if source_root and os.path.isdir(source_root):
            return os.path.normpath(source_root)
        return None

    def _build_deps_root(self):
        candidates = []
        fetchcontent_source_root = self._fetchcontent_source_root()
        if fetchcontent_source_root:
            candidates.append(fetchcontent_source_root)
        candidates.extend((
            os.path.join(self.build_folder, "_deps"),
            os.path.join(os.path.dirname(self.build_folder), "_deps"),
            os.path.join(os.path.dirname(os.path.dirname(self.build_folder)), "_deps"),
        ))
        for candidate in candidates:
            if os.path.isdir(os.path.join(candidate, "ktm-src")):
                return candidate
        return None

    def _editable_build_root(self):
        return os.path.normpath(
            os.environ.get(
                "HORIZON_EDITABLE_BUILD_ROOT",
                os.path.join(self.package_folder, "build"),
            )
        )

    def _is_editable(self):
        return os.path.isfile(os.path.join(self.package_folder, "conanfile.py"))

    def _editable_includedirs(self):
        source_root = self.package_folder
        candidates = [
            os.path.join(source_root, "include"),
            os.path.join(source_root, "src", "Helicon"),
            os.path.join(source_root, "modules", "corona", "include"),
            os.path.join(source_root, "modules", "ocarina"),
            os.path.join(source_root, "modules", "ocarina", "ext", "EASTL", "include"),
            os.path.join(source_root, "modules", "ocarina", "ext", "EASTL", "packages", "EABase", "include", "Common"),
            os.path.join(source_root, "modules", "ocarina", "ext", "stblib", "stb"),
        ]

        deps_root = self._fetchcontent_source_root()
        if deps_root:
            candidates.extend((
                os.path.join(deps_root, "ktm-src"),
                os.path.join(deps_root, "pfr-src", "include"),
                os.path.join(deps_root, "quill-src", "include"),
                os.path.join(deps_root, "spirv-headers-src", "include"),
                os.path.join(deps_root, "spirv-tools-src", "include"),
                os.path.join(deps_root, "vulkan-headers-src", "include"),
                os.path.join(deps_root, "vulkanmemoryallocator-src", "include"),
            ))
        return [path for path in candidates if os.path.isdir(path)]

    def _editable_libdirs(self):
        build_root = self._editable_build_root()
        config = str(self.settings.build_type)
        candidates = [
            os.path.join(build_root, "src", config),
            os.path.join(build_root, "src", "Helicon", config),
            os.path.join(build_root, "modules", "corona", "src", "kernel", config),
            os.path.join(build_root, "modules", "corona", "src", "pal", config),
            os.path.join(build_root, "bin", config),
            os.path.join(build_root, "lib", config),
            os.path.join(build_root, "bin"),
            os.path.join(build_root, "lib"),
        ]
        for deps_dir_name in ("deps", "_deps"):
            deps_root = os.path.join(build_root, deps_dir_name)
            candidates.extend((
                os.path.join(deps_root, "volk-build", config),
                os.path.join(deps_root, "spirv-cross-build", config),
                os.path.join(deps_root, "spirv-tools-build", "source", config),
                os.path.join(deps_root, "spirv-tools-build", "source", "opt", config),
                os.path.join(deps_root, "spirv-tools-build", "source", "link", config),
            ))
        return [path for path in candidates if os.path.isdir(path)]

    def _shader_tool_path(self):
        shader_tool_name = "ShaderCompileScripts.exe" if self.settings.os == "Windows" else "ShaderCompileScripts"
        if self._is_editable():
            return os.path.join(
                self._editable_build_root(),
                "tools",
                str(self.settings.build_type),
                shader_tool_name,
            )
        return os.path.join(self.package_folder, "bin", shader_tool_name)

    def _fetchcontent_source_overrides(self):
        source_root = self._fetchcontent_source_root()
        if not source_root:
            return {}

        dependency_sources = {
            "pfr": "pfr-src",
            "ktm": "ktm-src",
            "preprocessor": "preprocessor-src",
            "SPIRV-Cross": "spirv-cross-src",
            "SPIRV-Headers": "spirv-headers-src",
            "SPIRV-Tools": "spirv-tools-src",
            "volk": "volk-src",
            "Vulkan-Headers": "vulkan-headers-src",
            "VulkanMemoryAllocator": "vulkanmemoryallocator-src",
            "quill": "quill-src",
        }

        overrides = {}
        for cmake_name, source_dir_name in dependency_sources.items():
            source_dir = os.path.join(source_root, source_dir_name)
            if os.path.isdir(source_dir):
                overrides[f"FETCHCONTENT_SOURCE_DIR_{cmake_name.upper()}"] = os.path.normpath(source_dir)
        return overrides

    def validate(self):
        if bool(self.options.with_ocarina) and not bool(self.options.with_cuda):
            raise ConanInvalidConfiguration("with_ocarina=True requires with_cuda=True")
        if bool(self.options.with_vision_hotfix) and not bool(self.options.with_ocarina):
            raise ConanInvalidConfiguration("with_vision_hotfix=True requires with_ocarina=True")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        toolchain = CMakeToolchain(self)
        cache_variables = toolchain.cache_variables
        cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        cache_variables["HORIZON_BUILD_OCARINA"] = bool(self.options.with_ocarina and self.options.with_cuda)
        cache_variables["HORIZON_BUILD_VISION_HOTFIX"] = bool(self.options.with_vision_hotfix)
        cache_variables["HORIZON_BUILD_TOOLS"] = bool(self.options.with_tools)
        cache_variables["HORIZON_BUILD_EXAMPLES"] = bool(self.options.with_examples)
        cache_variables["HORIZON_BUILD_TESTS"] = bool(self.options.with_tests)
        cache_variables["HORIZON_BUILD_BENCHMARKS"] = False
        cache_variables["HORIZON_ENABLE_DEPENDENCY_INSTALL"] = False
        dependency_provider = os.environ.get("HORIZON_DEPENDENCY_PROVIDER", "conan")
        cache_variables["HORIZON_DEPENDENCY_PROVIDER"] = dependency_provider
        fetchcontent_source_root = self._fetchcontent_source_root()
        fetchcontent_require_source_cache = self._env_bool(
            "HORIZON_FETCHCONTENT_REQUIRE_SOURCE_CACHE",
            default=dependency_provider == "fetchcontent",
        )
        if fetchcontent_require_source_cache and not fetchcontent_source_root:
            raise ConanInvalidConfiguration(
                "HORIZON_FETCHCONTENT_REQUIRE_SOURCE_CACHE requires HORIZON_FETCHCONTENT_SOURCE_ROOT"
            )
        cache_variables["HORIZON_FETCHCONTENT_REQUIRE_SOURCE_CACHE"] = fetchcontent_require_source_cache
        if fetchcontent_source_root:
            cache_variables["HORIZON_FETCHCONTENT_SOURCE_ROOT"] = fetchcontent_source_root.replace("\\", "/")
            for variable_name, source_dir in self._fetchcontent_source_overrides().items():
                cache_variables[variable_name] = source_dir.replace("\\", "/")
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="Horizon")
        if bool(self.options.with_ocarina) and bool(self.options.with_cuda):
            cmake.build(target="ocarina")
        if bool(self.options.with_vision_hotfix):
            cmake.build(target="vision-hotfix-all")
        if bool(self.options.with_tools):
            cmake.build(target="ShaderCompileScripts")

    def package(self):
        package_include = os.path.join(self.package_folder, "include")
        self._copy_headers(self, os.path.join(self.source_folder, "include"), package_include)
        self._copy_headers(self, os.path.join(self.source_folder, "src", "Helicon"), package_include)
        self._copy_headers(self, os.path.join(self.source_folder, "modules", "corona", "include"), package_include)
        if bool(self.options.with_ocarina) and bool(self.options.with_cuda):
            ocarina_root = os.path.join(self.source_folder, "modules", "ocarina")
            self._copy_headers(self, ocarina_root, package_include)
            self._copy_headers(self, os.path.join(ocarina_root, "ext", "EASTL", "include"), package_include)
            self._copy_headers(
                self,
                os.path.join(ocarina_root, "ext", "EASTL", "packages", "EABase", "include", "Common"),
                package_include,
            )
            self._copy_headers(self, os.path.join(ocarina_root, "ext", "stblib", "stb"), package_include)
        if bool(self.options.with_vision_hotfix):
            self._copy_headers(self, os.path.join(self.source_folder, "src"), package_include)

        deps_root = self._build_deps_root()
        if deps_root:
            for dep_include in (
                os.path.join(deps_root, "ktm-src"),
                os.path.join(deps_root, "pfr-src", "include"),
                os.path.join(deps_root, "quill-src", "include"),
                os.path.join(deps_root, "spirv-headers-src", "include"),
                os.path.join(deps_root, "spirv-tools-src", "include"),
                os.path.join(deps_root, "vulkan-headers-src", "include"),
                os.path.join(deps_root, "vulkanmemoryallocator-src", "include"),
            ):
                if os.path.isdir(dep_include):
                    self._copy_headers(self, dep_include, package_include)

        package_cmake = os.path.join(self.package_folder, "cmake")
        copy(self, "HeliconShaderCompile.cmake", src=os.path.join(self.source_folder, "cmake"), dst=package_cmake)
        copy(self, "HorizonPackageAliases.cmake", src=os.path.join(self.source_folder, "cmake"), dst=package_cmake)
        copy(self, "*.lib", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        if bool(self.options.with_ocarina) and bool(self.options.with_cuda):
            copy(self, "*.dll", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
            copy(self, "*.so*", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*.dylib", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
            cuda_headers_dir = os.path.join(self.build_folder, "bin", str(self.settings.build_type), "cuda")
            if os.path.isdir(cuda_headers_dir):
                copy(self, "*", src=cuda_headers_dir, dst=os.path.join(self.package_folder, "bin", "cuda"), keep_path=True)
        if bool(self.options.with_tools):
            tool_output_dir = os.path.join(self.build_folder, "tools", str(self.settings.build_type))
            copy(self, "ShaderCompileScripts*", src=tool_output_dir, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
            copy(self, "*.dll", src=tool_output_dir, dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        def add_component(name, cmake_target_name, libs=None, requires=None, system_libs=None, defines=None):
            component = self.cpp_info.components[name]
            component.set_property("cmake_target_name", cmake_target_name)
            if libs:
                component.libs = libs
            if requires:
                component.requires = requires
            if system_libs:
                component.system_libs = system_libs
            if defines:
                component.defines = defines
            return component

        self.cpp_info.set_property("cmake_file_name", "Horizon")
        self.cpp_info.set_property("cmake_target_name", "Horizon::Horizon")
        self.cpp_info.set_property(
            "cmake_build_modules",
            [
                os.path.join("cmake", "HeliconShaderCompile.cmake"),
                os.path.join("cmake", "HorizonPackageAliases.cmake"),
            ],
        )
        if bool(self.options.with_tools):
            shader_tool_path = self._shader_tool_path().replace("\\", "/")
            self.cpp_info.set_property(
                "cmake_extra_variables",
                {"HORIZON_SHADER_COMPILE_SCRIPTS_EXECUTABLE": shader_tool_path},
            )

        self.cpp_info.components["horizon"].set_property("cmake_target_name", "Horizon")
        self.cpp_info.components["horizon"].libs = ["Horizon"]
        self.cpp_info.components["horizon"].requires = [
            "helicon",
            "corona_kernel",
            "ktm::ktm",
            "volk::libvolk",
            "vulkan-headers::vulkan-headers",
            "vulkan-memory-allocator::vulkan-memory-allocator",
        ]

        self.cpp_info.components["helicon"].set_property("cmake_target_name", "Helicon")
        self.cpp_info.components["helicon"].libs = ["Helicon"]
        self.cpp_info.components["helicon"].requires = [
            "ktm::ktm",
            "pfr::pfr",
            "spirv-cross::spirv-cross-c",
            "spirv-cross::spirv-cross-cpp",
            "spirv-cross::spirv-cross-core",
            "spirv-cross::spirv-cross-glsl",
            "spirv-cross::spirv-cross-hlsl",
            "spirv-cross::spirv-cross-util",
            "spirv-tools::spirv-tools-link",
            "slang::slang",
            "slang::slang-rt",
            "slang::gfx",
        ]

        self.cpp_info.components["corona_kernel"].set_property("cmake_target_name", "corona_kernel")
        self.cpp_info.components["corona_kernel"].libs = ["corona_kernel"]
        self.cpp_info.components["corona_kernel"].requires = ["quill::quill"]

        self.cpp_info.components["corona_pal"].set_property("cmake_target_name", "corona_pal")

        if bool(self.options.with_ocarina) and bool(self.options.with_cuda):
            add_component("eabase", "EABase")
            add_component(
                "eastl",
                "EASTL",
                libs=["EASTL"],
                requires=["eabase"],
                defines=[
                    "EA_HAVE_CPP11_CONTAINERS=1",
                    "EA_HAVE_CPP11_ATOMIC=1",
                    "EA_HAVE_CPP11_CONDITION_VARIABLE=1",
                    "EA_HAVE_CPP11_MUTEX=1",
                    "EA_HAVE_CPP11_THREAD=1",
                    "EA_HAVE_CPP11_FUTURE=1",
                    "EA_HAVE_CPP11_TYPE_TRAITS=1",
                    "EA_HAVE_CPP11_TUPLES=1",
                    "EA_HAVE_CPP11_REGEX=1",
                    "EA_HAVE_CPP11_RANDOM=1",
                    "EA_HAVE_CPP11_CHRONO=1",
                    "EA_HAVE_CPP11_SCOPED_ALLOCATOR=1",
                    "EA_HAVE_CPP11_INITIALIZER_LIST=1",
                    "EA_HAVE_CPP11_SYSTEM_ERROR=1",
                    "EA_HAVE_CPP11_TYPEINDEX=1",
                    "EASTL_USER_LITERALS_ENABLED=0",
                    "EASTL_STD_ITERATOR_CATEGORY_ENABLED=1",
                    "EASTL_STD_TYPE_TRAITS_AVAILABLE=1",
                    "EASTL_MOVE_SEMANTICS_ENABLED=1",
                    "EASTL_VARIADIC_TEMPLATES_ENABLED=1",
                    "EASTL_VARIABLE_TEMPLATES_ENABLED=1",
                    "EASTL_INLINE_VARIABLE_ENABLED=1",
                    "EASTL_HAVE_CPP11_TYPE_TRAITS=1",
                    "EASTL_INLINE_NAMESPACES_ENABLED=1",
                    "EASTL_ALLOCATOR_EXPLICIT_ENABLED=1",
                    "EA_DLL=1",
                    "EASTL_USER_DEFINED_ALLOCATOR=1",
                ],
            )
            add_component("ocarina_ext_stb", "ocarina-ext-stb", libs=["ocarina-ext-stb"])
            add_component("ocarina_ext_tinyexr", "ocarina-ext-tinyexr", libs=["ocarina-ext-tinyexr"])
            add_component(
                "ocarina_ext",
                "ocarina-ext",
                libs=["ocarina-ext"],
                requires=[
                    "eastl",
                    "ocarina_ext_stb",
                    "ocarina_ext_tinyexr",
                    "fmt::fmt",
                    "spdlog::spdlog",
                    "xxhash::libxxhash",
                ],
            )
            ocarina_core = add_component(
                "ocarina_core",
                "ocarina-core",
                libs=["ocarina-core"],
                requires=["ocarina_ext"],
            )
            if self.settings.os == "Windows":
                ocarina_core.system_libs = ["dbghelp"]
            add_component("ocarina_math", "ocarina-math", libs=["ocarina-math"], requires=["ocarina_core"])
            add_component(
                "ocarina_ast",
                "ocarina-ast",
                libs=["ocarina-ast"],
                requires=["ocarina_ext", "ocarina_core"],
            )
            add_component(
                "ocarina_generator",
                "ocarina-generator",
                libs=["ocarina-generator"],
                requires=["ocarina_ast", "ocarina_math"],
            )
            add_component(
                "ocarina_rhi",
                "ocarina-rhi",
                libs=["ocarina-rhi"],
                requires=["ocarina_generator"],
            )
            add_component(
                "ocarina_dsl",
                "ocarina-dsl",
                libs=["ocarina-dsl"],
                requires=["ocarina_rhi", "ocarina_ast"],
            )
            add_component("ocarina_backend", "ocarina-backend")
            add_component(
                "ocarina_native",
                "ocarina-native",
                requires=[
                    "ocarina_ext",
                    "ocarina_math",
                    "ocarina_dsl",
                    "ocarina_ast",
                    "ocarina_generator",
                    "ocarina_backend",
                    "ocarina_rhi",
                    "ocarina_core",
                ],
            )
            add_component("ocarina_include", "ocarina-include")
            add_component("ocarina", "ocarina", libs=["ocarina"], requires=["ocarina_native"])
            if bool(self.options.with_vision_hotfix):
                add_component("vision_hotfix", "vision-hotfix", libs=["vision-hotfix"], requires=["ocarina"])
                add_component(
                    "vision_hotfix_compiler",
                    "vision-hotfix-compiler",
                    requires=["vision_hotfix"],
                )
                add_component(
                    "vision_hotfix_rules_parser",
                    "vision-hotfix-rules_parser",
                    requires=["vision_hotfix"],
                )
                add_component(
                    "vision_hotfix_test",
                    "vision-hotfix-test",
                    libs=["vision-hotfix-test"],
                    requires=["ocarina", "vision_hotfix", "ocarina_include"],
                )
                add_component(
                    "vision_hotfix_all",
                    "vision-hotfix-all",
                    libs=["vision-hotfix-all"],
                    requires=[
                        "vision_hotfix",
                        "vision_hotfix_compiler",
                        "vision_hotfix_test",
                        "vision_hotfix_rules_parser",
                    ],
                )
                self.cpp_info.components["ocarina_include"].requires = ["vision_hotfix"]

        editable = self._is_editable()
        editable_includedirs = self._editable_includedirs() if editable else None
        editable_libdirs = self._editable_libdirs() if editable else None
        for component in self.cpp_info.components.values():
            component.includedirs = editable_includedirs if editable else ["include"]
            if editable:
                component.libdirs = editable_libdirs

        if self.settings.compiler == "msvc":
            for component_name in ("horizon", "helicon", "corona_kernel"):
                self.cpp_info.components[component_name].cxxflags = ["/utf-8"]
