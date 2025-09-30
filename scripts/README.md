# Generate Ninja Build Script

This script generates a ninja build script to convert LaTeX files from `src/content` to AsciiDoc files.

## Features

The script generates ninja build rules to:

1. **Convert LaTeX files**: Transform `.tex` files from `src/content` to `.adoc` files in the `out/adoc` directory
2. **Copy code snippets**: Copy the `code/` directory from each chapter (includes code in haskell, ocaml, reason, scala, etc.)
3. **Copy images**: Copy the `images/` directory from each chapter
4. **Copy source files**: Copy existing `.adoc` files from `src`
5. **Copy icons**: Copy the `src/fig` directory (includes icons and other resources)
6. **Copy other resources**: Copy fonts and CSS files

## Usage

### 1. Generate build.ninja file

```bash
uv run scripts/generate_ninja.py
```

This will generate a `build.ninja` file in the project root.

You can also customize the generation with command-line options:

```bash
# Custom output path
uv run scripts/generate_ninja.py --output custom.ninja

# Custom directories
uv run scripts/generate_ninja.py --src-dir /path/to/src --out-dir /path/to/out

# Show help
uv run scripts/generate_ninja.py --help
```

### 2. Run ninja build

```bash
# Build all files
ninja

# Use multiple parallel jobs to speed up the build
ninja -j8

# Build only specific targets (use absolute path)
ninja /workspace/milewski-ctfp-pdf/out/adoc/1.1/category-the-essence-of-composition.adoc

# Show build plan without executing
ninja -n

# Clean all build outputs
ninja -t clean

# Show build statistics
ninja -t compdb
```

### Incremental Builds

Ninja supports intelligent incremental builds:
- Only modified `.tex` source files will be re-converted
- Resource files (code, images) are automatically updated based on timestamps
- This makes rebuilding after modifying a single file very fast in large projects

## Directory Structure

The generated output directory structure matches the `src` directory structure:

```
out/adoc/
├── 0.0/
│   ├── preface.adoc
│   └── images/
├── 1.1/
│   ├── category-the-essence-of-composition.adoc
│   ├── code/
│   │   ├── haskell/
│   │   ├── ocaml/
│   │   ├── reason/
│   │   └── scala/
│   └── images/
├── ...
├── fig/
│   └── icons/
├── acknowledgments.adoc
├── colophon.adoc
├── ctfp.adoc
└── ...
```

## Dependencies

- Python >= 3.12
- uv (for running scripts and the ctfp-parse tool)
- ninja (for executing the build)
- tools/ctfp-parse (the project's LaTeX parser tool)

## Technical Details

The script uses [uv inline script metadata](https://docs.astral.sh/uv/guides/scripts/#declaring-script-dependencies) syntax to declare dependencies and is a single-file Python script.

The generated ninja file contains:
- `tex2adoc` rule: Invokes `uv run --directory tools ctfp-parse` to convert files
- `copy` rule: Copies resource files
- `all` default target: Builds all output files

## Modifying the Script

If you need to modify the script, you can edit `scripts/generate_ninja.py`:

- Modify conversion rules: Edit the `add_tex_conversion()` method
- Add new resource types: Edit the `scan_content_resources()` method
- Change output directory: Modify the `NinjaGenerator` constructor parameters
