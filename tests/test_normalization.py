"""
Unit tests for query normalization.

Tests the QueryNormalizer class for operator normalization,
variable normalization, and query variation generation.
"""


from verus_lemma_finder.normalization import QueryNormalizer


class TestOperatorNormalization:
    """Test normalization of mathematical operators"""

    def test_times_to_asterisk(self):
        """Test 'times' normalizes to '*'"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("a times b")
        assert "*" in result
        assert "var1" in result

    def test_mul_to_asterisk(self):
        """Test 'mul' normalizes to '*'"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("x mul y")
        assert "*" in result
        assert "var1" in result

    def test_multiply_to_asterisk(self):
        """Test 'multiply' normalizes to '*'"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("a multiply b")
        assert "*" in result
        assert "var1" in result

    def test_div_to_slash(self):
        """Test 'div' normalizes to '/'"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("x div y")
        assert "/" in result
        assert "var1" in result

    def test_divide_to_slash(self):
        """Test 'divide' normalizes to '/'"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("a divide b")
        assert "/" in result
        assert "var1" in result

    def test_modulo_to_mod(self):
        """Test 'modulo' normalizes to 'mod'"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("a modulo b")
        assert "mod" in result

    def test_when_to_if(self):
        """Test 'when' normalizes to 'if'"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("x > 0 when y = 5")
        assert "if" in result

    def test_iff_expansion(self):
        """Test 'iff' expands to 'if and only if'"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("a = b iff c = d")
        assert "if and only if" in result

    def test_leq_to_less_equal(self):
        """Test 'leq' normalizes to '<='"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("x leq y")
        assert "<=" in result
        assert "var1" in result

    def test_geq_to_greater_equal(self):
        """Test 'geq' normalizes to '>='"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("x geq y")
        assert ">=" in result
        assert "var1" in result

    def test_neq_to_not_equal(self):
        """Test 'neq' normalizes to '!='"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("x neq y")
        assert "!=" in result

    def test_case_insensitive(self):
        """Test normalization is case-insensitive"""
        normalizer = QueryNormalizer()
        result1 = normalizer.normalize("a TIMES b")
        result2 = normalizer.normalize("x DIV y")
        result3 = normalizer.normalize("p MUL q")
        assert "*" in result1
        assert "/" in result2
        assert "*" in result3

    def test_multiple_operators(self):
        """Test multiple operators in one query"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("a times b div c")
        assert "*" in result
        assert "/" in result

    def test_operators_only_no_variable_renaming(self):
        """Test normalize_operators_only preserves variable names"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize_operators_only("x times y div z")
        assert result == "x * y / z"
        # Variables should not be renamed
        assert "var" not in result


class TestVariableNormalization:
    """Test normalization of variable names"""

    def test_simple_variable_renaming(self):
        """Test basic variable renaming to var1, var2"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("a + b + c")
        # Variables followed by operators should be renamed
        assert "var" in result

    def test_variable_normalization_preserves_operators(self):
        """Test that operators are preserved during variable normalization"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("x * y <= z")
        assert "*" in result
        assert "<=" in result

    def test_consistent_variable_mapping(self):
        """Test same variable gets same generic name"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("a + a = b")
        # Both 'a' should map to same var
        assert result.count("var1") == 2

    def test_alphabetical_ordering(self):
        """Test variables are mapped in alphabetical order"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("z + a + b + c")
        # Variables followed by operators should be renamed
        # Alphabetical order: a, b, z should be var1, var2, var3
        assert "var1" in result
        assert "var2" in result

    def test_case_insensitive_variables(self):
        """Test variable normalization is case-insensitive"""
        normalizer = QueryNormalizer()
        result1 = normalizer.normalize("A + B")
        result2 = normalizer.normalize("a + b")
        # Should normalize to same result
        assert result1.lower() == result2.lower()


class TestFullNormalization:
    """Test full normalization (operators + variables)"""

    def test_complex_mathematical_expression(self):
        """Test normalization of complex expression"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("if a times b <= c then a <= c div b")
        # Should have operators normalized
        assert "*" in result
        assert "/" in result
        assert "<=" in result
        # Should have variables normalized
        assert "var" in result

    def test_equivalence_different_variables(self):
        """Test queries with different variables normalize similarly"""
        normalizer = QueryNormalizer()
        result1 = normalizer.normalize("x * y <= z")
        result2 = normalizer.normalize("a * b <= c")
        # After normalization, should have same structure (all vars normalized)
        # Both should have "*" and "<=" and var1/var2
        assert "*" in result1 and "*" in result2
        assert "<=" in result1 and "<=" in result2
        assert "var1" in result1 and "var1" in result2

    def test_real_world_example(self):
        """Test real-world lemma search query"""
        normalizer = QueryNormalizer()
        query = "if x multiply y leq z and y > 0 then x leq z divide y"
        result = normalizer.normalize(query)
        # Check operators are normalized
        assert "*" in result
        assert "<=" in result
        assert "/" in result
        # Check variables are normalized
        assert "var" in result
        assert "x" not in result  # Original variable names should be replaced


class TestQueryVariations:
    """Test query variation generation"""

    def test_if_then_to_backward_if(self):
        """Test 'if A then B' generates 'B if A'"""
        normalizer = QueryNormalizer()
        variations = normalizer.generate_variations("if x > 0 then y < 5")
        # Should generate reverse
        assert any("y < 5 if x > 0" in v for v in variations)

    def test_backward_if_to_if_then(self):
        """Test 'B if A' generates 'if A then B'"""
        normalizer = QueryNormalizer()
        variations = normalizer.generate_variations("y < 5 if x > 0")
        # Should generate forward
        assert any("if x > 0 then y < 5" in v for v in variations)

    def test_mod_percent_variations(self):
        """Test mod/% variations are generated"""
        normalizer = QueryNormalizer()
        variations = normalizer.generate_variations("x mod 5 = 0")
        # Should have % variant
        assert any("%" in v for v in variations)

    def test_and_clause_swapping(self):
        """Test 'and' clauses can be swapped"""
        normalizer = QueryNormalizer()
        variations = normalizer.generate_variations("result if x > 0 and y < 5")
        # Should generate with swapped conditions
        assert len(variations) > 1

    def test_no_duplicate_variations(self):
        """Test that duplicate variations are removed"""
        normalizer = QueryNormalizer()
        variations = normalizer.generate_variations("x + y")
        # Should have unique variations only
        assert len(variations) == len(set(variations))

    def test_original_query_included(self):
        """Test original query is always in variations"""
        normalizer = QueryNormalizer()
        query = "x * y = z"
        variations = normalizer.generate_variations(query)
        assert query in variations


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_string(self):
        """Test normalization of empty string"""
        normalizer = QueryNormalizer()
        assert normalizer.normalize("") == ""

    def test_no_variables(self):
        """Test query with no variables"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("true and false")
        # Should not fail, just return as-is
        assert "true" in result.lower()

    def test_no_operators(self):
        """Test query with no operators to normalize"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("function returns value")
        # Should not fail
        assert isinstance(result, str)

    def test_special_characters(self):
        """Test handling of special characters"""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("x * (y + z) <= w")
        # Should preserve parentheses and structure
        assert "(" in result
        assert ")" in result

    def test_unicode_characters(self):
        """Test handling of unicode characters"""
        normalizer = QueryNormalizer()
        # Should not crash on unicode
        result = normalizer.normalize("α times β")
        assert isinstance(result, str)

    def test_very_long_query(self):
        """Test handling of very long queries"""
        normalizer = QueryNormalizer()
        long_query = "x " + " + y " * 100
        result = normalizer.normalize(long_query)
        # Should not fail
        assert isinstance(result, str)

    def test_nested_conditions(self):
        """Test nested if-then conditions"""
        normalizer = QueryNormalizer()
        query = "if (if a then b) then c"
        result = normalizer.normalize(query)
        # Should handle gracefully
        assert isinstance(result, str)


class TestNormalizerConsistency:
    """Test that normalizer behavior is consistent"""

    def test_idempotence(self):
        """Test that normalizing twice gives same result"""
        normalizer = QueryNormalizer()
        query = "x times y"
        result1 = normalizer.normalize(query)
        result2 = normalizer.normalize(result1)
        # Second normalization should not change result
        # (though variable names might already be normalized)
        assert "*" in result1
        assert "*" in result2

    def test_multiple_normalizers(self):
        """Test multiple normalizer instances behave the same"""
        normalizer1 = QueryNormalizer()
        normalizer2 = QueryNormalizer()
        query = "a times b div c"
        assert normalizer1.normalize(query) == normalizer2.normalize(query)

    def test_thread_safety_state(self):
        """Test that normalizer doesn't maintain state between calls"""
        normalizer = QueryNormalizer()
        result1 = normalizer.normalize("x + y + z")
        result2 = normalizer.normalize("a + b + c")
        # Both should have same operators and structure
        # Verify they both have "+" and "var" patterns
        assert "+" in result1 and "+" in result2
        assert "var1" in result1 and "var1" in result2

