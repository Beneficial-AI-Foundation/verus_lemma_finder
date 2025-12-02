# Rust Parser Integration

This project uses a Rust-based parser (`verus_parser`) for accurate extraction of Verus specifications. The parser uses [`verus_syn`](https://crates.io/crates/verus_syn), a Verus-extended version of the `syn` crate that natively handles Verus-specific syntax.

## Why Rust?

The original Python implementation used regex-based parsing which had limitations:
- Couldn't handle nested structures properly
- Struggled with Verus-specific syntax like `&&&`, `|||`, `==>`, quantifiers
- Fragile comma splitting in complex expressions

The Rust parser using `verus_syn` provides:
- Proper AST-based parsing
- Native support for all Verus syntax
- Accurate extraction of `requires`, `ensures`, and `decreases` clauses
- Better error handling

## Building the Rust Extension

### Prerequisites

1. **Rust toolchain**: Install via [rustup](https://rustup.rs/)
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

2. **Maturin**: Python build tool for Rust extensions
   ```bash
   pip install maturin
   ```

### Development Build

For development, use `maturin develop` to build and install the extension in your current environment:

```bash
cd /path/to/verus_lemma_finder
maturin develop --release
```

This compiles the Rust code and installs `verus_parser` as a Python module.

### Production Build

To build wheels for distribution:

```bash
maturin build --release
```

The wheel will be in `target/wheels/`.

### Testing the Rust Code

Run Rust tests:

```bash
cd rust
cargo test
```

## Usage

Once built, the parser is automatically used by `extraction.py`. You can also use it directly:

```python
import verus_parser

# Parse an entire file
specs_list = verus_parser.parse_verus_file(source_code)

# Extract specs for a specific function
specs = verus_parser.extract_function_specs(source_code, "lemma_foo")
print(specs["requires"])  # List of requires clauses
print(specs["ensures"])   # List of ensures clauses
print(specs["is_proof"])  # True if it's a proof function

# Extract only proof functions
proof_fns = verus_parser.extract_proof_functions(source_code)

# Check if code is valid Verus
is_valid = verus_parser.is_valid_verus(source_code)
```

## Fallback Behavior

If the Rust module is not available (e.g., not built), the system automatically falls back to regex-based extraction. You can check availability:

```python
from verus_lemma_finder.extraction import VERUS_PARSER_AVAILABLE
print(f"Rust parser available: {VERUS_PARSER_AVAILABLE}")
```

## Handling `verus!` Macro

The parser handles both:
1. Raw Verus syntax (without macro wrapper)
2. Code wrapped in `verus! { ... }` macro

It automatically extracts the content from inside the macro if present.

## Troubleshooting

### Build Errors

If you get linker errors about missing Python symbols:
- Make sure you're building with `maturin develop`, not `cargo build`
- The `cargo test` command works because tests don't link to Python

### Parse Errors

If parsing fails:
- Check that the code is valid Verus syntax
- The parser expects the file to be parseable by `verus_syn`
- On parse error, the system falls back to regex extraction

## Architecture

```
rust/
├── Cargo.toml          # Rust dependencies (pyo3, verus_syn)
└── src/
    └── lib.rs          # PyO3 bindings + parsing logic
        ├── FunctionSpecs       # Result struct
        ├── FunctionFinder      # AST visitor
        ├── parse_verus_file()  # Parse entire file
        ├── extract_function_specs()  # Single function
        └── extract_proof_functions() # Filter proofs
```

## Contributing

When modifying the Rust parser:

1. Run tests: `cd rust && cargo test`
2. Rebuild Python module: `maturin develop --release`
3. Test Python integration: `pytest tests/`

