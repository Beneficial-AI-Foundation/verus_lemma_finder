//! Verus specification parser with Python bindings
//!
//! This crate provides Python bindings to parse Verus source files using `verus_syn`,
//! extracting function specifications (requires, ensures, decreases clauses).
//!
//! Based on the proven approach from scip-atoms, this handles:
//! - Top-level functions
//! - Methods in `impl` blocks
//! - Trait methods
//! - Functions inside `verus!` macros
//! - Nested modules

// Suppress false positive from PyO3 macro expansion
#![allow(clippy::useless_conversion)]

use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};
use verus_syn::spanned::Spanned;
use verus_syn::visit::Visit;
use verus_syn::{FnMode, ImplItemFn, Item, ItemFn, ItemMacro, Signature, TraitItemFn};

/// Extracted specification from a Verus function
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct FunctionSpecs {
    /// Function name
    pub name: String,
    /// File path (if provided)
    pub file_path: String,
    /// Line number of function definition (1-indexed)
    pub line_number: Option<usize>,
    /// End line number of function
    pub end_line: Option<usize>,
    /// List of requires clauses
    pub requires: Vec<String>,
    /// List of ensures clauses
    pub ensures: Vec<String>,
    /// List of decreases clauses
    pub decreases: Vec<String>,
    /// Full function signature
    pub signature: String,
    /// Whether the function is a proof function
    pub is_proof: bool,
    /// Any parse errors encountered
    pub parse_error: Option<String>,
}

impl IntoPy<PyObject> for FunctionSpecs {
    fn into_py(self, py: Python<'_>) -> PyObject {
        let dict = PyDict::new_bound(py);
        dict.set_item("name", &self.name).unwrap();
        dict.set_item("file_path", &self.file_path).unwrap();
        dict.set_item("line_number", self.line_number).unwrap();
        dict.set_item("end_line", self.end_line).unwrap();
        dict.set_item("requires", &self.requires).unwrap();
        dict.set_item("ensures", &self.ensures).unwrap();
        dict.set_item("decreases", &self.decreases).unwrap();
        dict.set_item("signature", &self.signature).unwrap();
        dict.set_item("is_proof", self.is_proof).unwrap();
        dict.set_item("parse_error", &self.parse_error).unwrap();
        dict.into()
    }
}

/// AST visitor to find functions and extract their specifications
struct FunctionFinder {
    /// Function name we're looking for (None = collect all)
    target_name: Option<String>,
    /// Collected function specs
    functions: Vec<FunctionSpecs>,
}

impl FunctionFinder {
    fn new(target_name: Option<String>) -> Self {
        Self {
            target_name,
            functions: Vec::new(),
        }
    }

    /// Extract specs from a verus_syn Signature, with span information
    fn extract_specs_from_signature<S: Spanned>(&self, sig: &Signature, spanned: &S) -> FunctionSpecs {
        let name = sig.ident.to_string();

        // Check if this is a proof function
        let is_proof = matches!(sig.mode, FnMode::Proof(_));

        // Build the full signature string
        let signature = quote::quote!(#sig).to_string();

        // Get line numbers from span
        let span = spanned.span();
        let line_number = Some(span.start().line);
        let end_line = Some(span.end().line);

        // Extract requires clauses from sig.spec
        let requires: Vec<String> = sig
            .spec
            .requires
            .as_ref()
            .map(|req| {
                req.exprs
                    .exprs
                    .iter()
                    .map(|e| quote::quote!(#e).to_string())
                    .collect()
            })
            .unwrap_or_default();

        // Extract ensures clauses from sig.spec
        let ensures: Vec<String> = sig
            .spec
            .ensures
            .as_ref()
            .map(|ens| {
                ens.exprs
                    .exprs
                    .iter()
                    .map(|e| quote::quote!(#e).to_string())
                    .collect()
            })
            .unwrap_or_default();

        // Extract decreases clauses from sig.spec
        let decreases: Vec<String> = sig
            .spec
            .decreases
            .as_ref()
            .map(|dec| {
                dec.decreases
                    .exprs
                    .exprs
                    .iter()
                    .map(|e| quote::quote!(#e).to_string())
                    .collect()
            })
            .unwrap_or_default();

        FunctionSpecs {
            name,
            file_path: String::new(),
            line_number,
            end_line,
            requires,
            ensures,
            decreases,
            signature,
            is_proof,
            parse_error: None,
        }
    }

    /// Check if we should collect this function (based on target_name filter)
    fn should_collect(&self, name: &str) -> bool {
        match &self.target_name {
            Some(target) => name == target,
            None => true,
        }
    }
}

impl<'ast> Visit<'ast> for FunctionFinder {
    // Handle top-level functions
    fn visit_item_fn(&mut self, node: &'ast ItemFn) {
        let name = node.sig.ident.to_string();

        if self.should_collect(&name) {
            let specs = self.extract_specs_from_signature(&node.sig, node);
            self.functions.push(specs);
        }

        // Continue visiting nested items
        verus_syn::visit::visit_item_fn(self, node);
    }

    // Handle methods in impl blocks
    fn visit_impl_item_fn(&mut self, node: &'ast ImplItemFn) {
        let name = node.sig.ident.to_string();

        if self.should_collect(&name) {
            let specs = self.extract_specs_from_signature(&node.sig, node);
            self.functions.push(specs);
        }

        // Continue visiting nested items
        verus_syn::visit::visit_impl_item_fn(self, node);
    }

    // Handle trait method declarations
    fn visit_trait_item_fn(&mut self, node: &'ast TraitItemFn) {
        let name = node.sig.ident.to_string();

        if self.should_collect(&name) {
            let specs = self.extract_specs_from_signature(&node.sig, node);
            self.functions.push(specs);
        }

        // Continue visiting nested items
        verus_syn::visit::visit_trait_item_fn(self, node);
    }

    // Traverse into impl blocks - must manually check for macros
    fn visit_item_impl(&mut self, node: &'ast verus_syn::ItemImpl) {
        // Check each item in the impl block for macros
        for item in &node.items {
            if let verus_syn::ImplItem::Macro(mac) = item {
                // Check if this is a verus! macro
                if let Some(ident) = mac.mac.path.get_ident() {
                    if ident == "verus" {
                        // Try to parse the macro body as impl items
                        if let Ok(body) = verus_syn::parse2::<VerusImplMacroBody>(mac.mac.tokens.clone()) {
                            for impl_item in body.items {
                                self.visit_impl_item(&impl_item);
                            }
                        }
                    }
                }
            }
        }
        // Continue with default traversal for non-macro items
        verus_syn::visit::visit_item_impl(self, node);
    }

    // Traverse into trait definitions
    fn visit_item_trait(&mut self, node: &'ast verus_syn::ItemTrait) {
        verus_syn::visit::visit_item_trait(self, node);
    }

    // Traverse into modules
    fn visit_item_mod(&mut self, node: &'ast verus_syn::ItemMod) {
        verus_syn::visit::visit_item_mod(self, node);
    }

    // Handle verus! macro blocks by parsing their contents
    fn visit_item_macro(&mut self, node: &'ast ItemMacro) {
        // Check if this is a verus! macro
        if let Some(ident) = node.mac.path.get_ident() {
            if ident == "verus" {
                // Try to parse the macro body as items
                if let Ok(items) = verus_syn::parse2::<VerusMacroBody>(node.mac.tokens.clone()) {
                    for item in items.items {
                        self.visit_item(&item);
                    }
                }
            }
        }
        // Continue with default traversal
        verus_syn::visit::visit_item_macro(self, node);
    }
}

/// Helper struct to parse verus! macro body as a list of items (top-level)
struct VerusMacroBody {
    items: Vec<Item>,
}

impl verus_syn::parse::Parse for VerusMacroBody {
    fn parse(input: verus_syn::parse::ParseStream) -> verus_syn::Result<Self> {
        let mut items = Vec::new();
        while !input.is_empty() {
            items.push(input.parse()?);
        }
        Ok(VerusMacroBody { items })
    }
}

/// Helper struct to parse verus! macro body inside impl blocks
struct VerusImplMacroBody {
    items: Vec<verus_syn::ImplItem>,
}

impl verus_syn::parse::Parse for VerusImplMacroBody {
    fn parse(input: verus_syn::parse::ParseStream) -> verus_syn::Result<Self> {
        let mut items = Vec::new();
        while !input.is_empty() {
            items.push(input.parse()?);
        }
        Ok(VerusImplMacroBody { items })
    }
}

/// Parse a Verus source file and extract all function specifications
///
/// Handles:
/// - Top-level functions
/// - Methods in `impl` blocks  
/// - Trait methods
/// - Functions inside `verus!` macros
/// - Nested modules
///
/// # Arguments
/// * `content` - The source code content to parse
///
/// # Returns
/// A list of FunctionSpecs for all functions found in the file
#[pyfunction]
fn parse_verus_file(content: &str) -> PyResult<Vec<FunctionSpecs>> {
    match verus_syn::parse_file(content) {
        Ok(file) => {
            let mut finder = FunctionFinder::new(None);
            finder.visit_file(&file);
            Ok(finder.functions)
        }
        Err(e) => {
            // Return empty list with error info
            Ok(vec![FunctionSpecs {
                parse_error: Some(format!("Parse error: {}", e)),
                ..Default::default()
            }])
        }
    }
}

/// Extract specifications for a specific function from Verus source
///
/// # Arguments
/// * `content` - The source code content to parse
/// * `function_name` - The name of the function to find
///
/// # Returns
/// FunctionSpecs for the function, or specs with parse_error if not found
#[pyfunction]
fn extract_function_specs(content: &str, function_name: &str) -> PyResult<FunctionSpecs> {
    match verus_syn::parse_file(content) {
        Ok(file) => {
            let mut finder = FunctionFinder::new(Some(function_name.to_string()));
            finder.visit_file(&file);

            if let Some(specs) = finder.functions.into_iter().next() {
                Ok(specs)
            } else {
                Ok(FunctionSpecs {
                    name: function_name.to_string(),
                    parse_error: Some(format!("Function '{}' not found", function_name)),
                    ..Default::default()
                })
            }
        }
        Err(e) => Ok(FunctionSpecs {
            name: function_name.to_string(),
            parse_error: Some(format!("Parse error: {}", e)),
            ..Default::default()
        }),
    }
}

/// Extract all proof functions from Verus source
///
/// # Arguments
/// * `content` - The source code content to parse
///
/// # Returns
/// A list of FunctionSpecs for all proof functions found
#[pyfunction]
fn extract_proof_functions(content: &str) -> PyResult<Vec<FunctionSpecs>> {
    match verus_syn::parse_file(content) {
        Ok(file) => {
            let mut finder = FunctionFinder::new(None);
            finder.visit_file(&file);
            // Filter to only proof functions
            let proof_fns: Vec<_> = finder.functions.into_iter().filter(|f| f.is_proof).collect();
            Ok(proof_fns)
        }
        Err(e) => Ok(vec![FunctionSpecs {
            parse_error: Some(format!("Parse error: {}", e)),
            ..Default::default()
        }]),
    }
}

/// Check if a file can be parsed as valid Verus code
///
/// # Arguments
/// * `content` - The source code content to check
///
/// # Returns
/// True if the file parses successfully, False otherwise
#[pyfunction]
fn is_valid_verus(content: &str) -> bool {
    verus_syn::parse_file(content).is_ok()
}

/// Get the version of verus_parser
#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

/// Python module definition
#[pymodule]
fn verus_parser(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_verus_file, m)?)?;
    m.add_function(wrap_pyfunction!(extract_function_specs, m)?)?;
    m.add_function(wrap_pyfunction!(extract_proof_functions, m)?)?;
    m.add_function(wrap_pyfunction!(is_valid_verus, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parse_verus_file_core(content: &str) -> Result<Vec<FunctionSpecs>, String> {
        match verus_syn::parse_file(content) {
            Ok(file) => {
                let mut finder = FunctionFinder::new(None);
                finder.visit_file(&file);
                Ok(finder.functions)
            }
            Err(e) => Err(format!("Parse error: {}", e)),
        }
    }

    // Test top-level functions
    const SAMPLE_VERUS: &str = r#"
pub proof fn lemma_mul_inequality(x: int, y: int, z: int)
    requires
        x <= y,
        z > 0,
    ensures
        x * z <= y * z,
{
}

pub fn exec_add(a: u32, b: u32) -> (result: u32)
    requires
        a + b <= u32::MAX,
    ensures
        result == a + b,
{
    a + b
}
"#;

    #[test]
    fn test_parse_sample() {
        let result = parse_verus_file_core(SAMPLE_VERUS);
        assert!(result.is_ok(), "Parse failed: {:?}", result.err());
        let funcs = result.unwrap();
        assert_eq!(funcs.len(), 2, "Should find 2 functions");
        println!("Found {} functions", funcs.len());
        for f in &funcs {
            println!("  - {} (proof={}, lines {:?}-{:?})", f.name, f.is_proof, f.line_number, f.end_line);
        }
    }

    #[test]
    fn test_with_verus_macro() {
        let code = r#"
verus! {
    fn simple_fn(x: u32) -> u32
        requires x > 0,
        ensures result == x,
    {
        x
    }
    
    proof fn lemma_foo()
        ensures true,
    {
    }
}
"#;
        let result = parse_verus_file_core(code);
        assert!(result.is_ok(), "Parse failed: {:?}", result.err());
        let funcs = result.unwrap();
        assert_eq!(funcs.len(), 2, "Should find 2 functions inside verus! macro");
        
        let names: Vec<_> = funcs.iter().map(|f| f.name.as_str()).collect();
        assert!(names.contains(&"simple_fn"));
        assert!(names.contains(&"lemma_foo"));
        
        println!("With verus! macro:");
        for f in &funcs {
            println!("  - {} (proof={}, requires={:?})", f.name, f.is_proof, f.requires);
        }
    }

    #[test]
    fn test_impl_block() {
        let code = r#"
struct Foo {}

impl Foo {
    fn method_one(&self) -> u32
        requires true,
        ensures result > 0,
    {
        1
    }
    
    proof fn lemma_method(&self)
        ensures true,
    {
    }
}
"#;
        let result = parse_verus_file_core(code);
        assert!(result.is_ok(), "Parse failed: {:?}", result.err());
        let funcs = result.unwrap();
        assert_eq!(funcs.len(), 2, "Should find 2 methods in impl block");
        
        let names: Vec<_> = funcs.iter().map(|f| f.name.as_str()).collect();
        assert!(names.contains(&"method_one"));
        assert!(names.contains(&"lemma_method"));
        
        println!("Impl block methods:");
        for f in &funcs {
            println!("  - {} (proof={})", f.name, f.is_proof);
        }
    }

    #[test]
    fn test_verus_macro_with_impl() {
        let code = r#"
verus! {
    struct Bar {}
    
    impl Bar {
        proof fn bar_lemma(&self)
            requires true,
            ensures true,
        {
        }
    }
}
"#;
        let result = parse_verus_file_core(code);
        assert!(result.is_ok(), "Parse failed: {:?}", result.err());
        let funcs = result.unwrap();
        assert_eq!(funcs.len(), 1, "Should find 1 method in impl inside verus!");
        assert_eq!(funcs[0].name, "bar_lemma");
        assert!(funcs[0].is_proof);
        
        println!("verus! with impl:");
        for f in &funcs {
            println!("  - {} (proof={})", f.name, f.is_proof);
        }
    }
    
    #[test]
    fn test_verus_inside_impl() {
        // This tests the case where verus! is INSIDE an impl block (not around it)
        // This is common in real Verus code like curve25519-dalek
        let code = r#"
struct Scalar {}

impl Scalar {
    verus! {
        pub fn from_bytes_mod_order(bytes: [u8; 32]) -> (result: Scalar)
            ensures 
                result.bytes[31] & 0x80 == 0,
        {
            Scalar {}
        }
        
        proof fn internal_lemma()
            requires true,
            ensures true,
        {
        }
    }
    
    // Regular non-verus method
    fn regular_method(&self) {}
}
"#;
        let result = parse_verus_file_core(code);
        assert!(result.is_ok(), "Parse failed: {:?}", result.err());
        let funcs = result.unwrap();
        
        println!("verus! INSIDE impl block:");
        for f in &funcs {
            println!("  - {} (proof={}, ensures={:?})", f.name, f.is_proof, f.ensures);
        }
        
        // Should find: from_bytes_mod_order, internal_lemma, regular_method
        assert!(funcs.len() >= 2, "Should find at least 2 functions inside verus! in impl");
        
        let names: Vec<_> = funcs.iter().map(|f| f.name.as_str()).collect();
        assert!(names.contains(&"from_bytes_mod_order"), "Should find from_bytes_mod_order");
        assert!(names.contains(&"internal_lemma"), "Should find internal_lemma");
        
        // Check that ensures was extracted
        let from_bytes = funcs.iter().find(|f| f.name == "from_bytes_mod_order").unwrap();
        assert!(!from_bytes.ensures.is_empty(), "from_bytes_mod_order should have ensures");
    }
}
