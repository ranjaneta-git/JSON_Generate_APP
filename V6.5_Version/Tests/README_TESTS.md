# 🧪 Test Suite Documentation

This folder contains automated tests for the Modbus Register Configuration Tool.

---

## Test Files

### test_phase1_autoconfig.py

**Purpose:** Validates Phase 1 smart auto-configuration logic

**Tests Covered:**
1. Cloud Output = "Yes" triggers Lua Buffer configuration
2. Access = "Write" triggers User Variable configuration
3. P2.MPI array generation (Equipment parameters)
4. P2.RPCI array generation (User Variables)
5. P3.MPI array generation (Cloud parameters)
6. B6.RP array generation (Verification reads)

**How to Run:**
```bash
python Tests/test_phase1_autoconfig.py
```

**Expected Output:**
```
Phase 1 Auto-Configuration Test
===============================
✓ Test 1: Cloud output triggers Lua Buffer - PASS
✓ Test 2: Write access triggers User Variable - PASS
✓ Test 3: P2.MPI generation - PASS
✓ Test 4: P2.RPCI generation - PASS
✓ Test 5: P3.MPI generation - PASS
✓ Test 6: B6.RP generation - PASS

All tests passed!
```

---

## Running Tests

### Individual Test

```bash
# Run specific test file
python Tests/test_phase1_autoconfig.py
```

### All Tests (with pytest)

```bash
# Install pytest (optional)
pip install pytest

# Run all tests
pytest Tests/ -v

# Run with coverage
pytest Tests/ --cov=. --cov-report=html
```

### From IDE

Most Python IDEs (VS Code, PyCharm) can run tests directly:
- Open test file
- Click "Run Test" or "Debug Test" button

---

## Writing New Tests

### Test Structure Template

```python
"""
Test: <Description>
"""
import json
import os
import sys

def test_<feature_name>():
    """
    Test <specific functionality>
    """
    print("\n" + "="*80)
    print("TEST: <Test Name>")
    print("="*80)
    
    # Setup test data
    test_input = {...}
    
    # Execute functionality
    result = function_under_test(test_input)
    
    # Validate results
    assert result  == expected_value, "Error message"
    
    print("✓ Test passed!")
    return True

if __name__ == "__main__":
    try:
        test_<feature_name>()
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
```

### Test Naming Conventions

- Test file: `test_<feature>.py`
- Test function: `test_<specific_case>()`
- Clear, descriptive names

### Best Practices

1. **Isolate Tests:** Each test should be independent
2. **Use Assertions:** Assert expected outcomes
3. **Clear Messages:** Provide helpful error messages
4. **Test Edge Cases:** Include boundary values
5. **Document Tests:** Explain what is being tested

---

## Test Coverage Goals

### Core Functionality
- [ ] Register addition
- [ ] Register editing
- [ ] Register deletion
- [ ] Import from JSON
- [ ] Export to JSON
- [ ] Forward generation (Register → JSONs)
- [ ] Reverse transformation (JSONs → Register)

### Phase 1 Auto-Configuration
- [x] Cloud Output triggers Lua Buffer
- [x] Write Access triggers User Variable
- [x] P2.MPI generation
- [x] P2.RPCI generation
- [x] P3.MPI generation
- [x] B6.RP generation

### Validation
- [ ] Field validation (slave ID range, etc.)
- [ ] JSON syntax validation
- [ ] Duplicate address detection
- [ ] Missing required fields

### UI Components
- [ ] Dialog opening/closing
- [ ] Table insertion/update
- [ ] Import dialog
- [ ] Export dialog
- [ ] Generation panel

---

## Common Test Scenarios

### Scenario 1: Single Cloud Parameter

```python
register = {
    "slave_id": 1,
    "address": 1000,
    "cloud_output": "Yes",
    # ... other fields
}

# Expected:
# - in_lua_buffer = "Yes"
# - lua_category = "Equipment"
# - Appears in P2.MPI
# - Appears in P3.MPI
```

### Scenario 2: Write Parameter

```python
register = {
    "slave_id": 1,
    "address": 2000,
    "access_type": "Write",
    # ... other fields
}

# Expected:
# - in_lua_buffer = "Yes"
# - lua_category = "User Variable"
# - Appears in P2.RPCI
# - NOT in P3.MPI
```

### Scenario 3: Multi-Slave Configuration

```python
registers = [
    {"slave_id": 1, "address": 1000},
    {"slave_id": 2, "address": 1000},
    {"slave_id": 3, "address": 1000},
]

# Expected:
# - B4.SA = [1, 2, 3]
# - Separate packet definitions for each slave
```

### Scenario 4: Write/Feedback Pairing

```python
write_param = {
    "b5_id": 1,
    "param_type": "write",
    "paired_with": "2"
}

feedback_param = {
    "b5_id": 2,
    "param_type": "feedback",
    "paired_with": "1"
}

# Expected:
# - Write param in P2.RPCI
# - Feedback param in B6.RP
# - Bidirectional pairing maintained
```

---

## Debugging Failed Tests

### Issue: Test fails with import error

```python
ModuleNotFoundError: No module named 'xxx'
```

**Solution:**
- Run from project root: `python Tests/test_xxx.py`
- Or add parent to path:
```python
import sys
sys.path.insert(0, '..')
```

### Issue: Assertion fails

```python
AssertionError: Expected [1,2,3] but got [1,2]
```

**Solution:**
- Print intermediate values:
```python
print(f"DEBUG: P2_MPI = {P2_MPI}")
print(f"DEBUG: Expected = {expected}")
```
- Set breakpoints in IDE
- Use `pdb` debugger:
```python
import pdb; pdb.set_trace()
```

### Issue: File not found

```python
FileNotFoundError: 'Example.json' not found
```

**Solution:**
- Use absolute paths:
```python
import os
script_dir = os.path.dirname(__file__)
file_path = os.path.join(script_dir, '../Examples/Example.json')
```

---

## Continuous Integration (Future)

### GitHub Actions Template

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Run tests
        run: python Tests/test_phase1_autoconfig.py
```

---

## Test Metrics

### Current Status

| Category | Tests | Passing | Coverage |
|----------|-------|---------|----------|
| Phase 1 Auto-Config | 6 | 6 | 100% |
| Generation | 0 | 0 | 0% |
| Validation | 0 | 0 | 0% |
| UI | 0 | 0 | 0% |
| **Total** | **6** | **6** | **25%** |

### Goals

Target: 80% code coverage across all modules

---

## Contributing Tests

When contributing new features:

1. Write tests **before** implementing feature (TDD)
2. Ensure all existing tests pass
3. Add new tests for new functionality
4. Update this README with new test descriptions
5. Run full test suite before committing

---

## Additional Resources

- **pytest Documentation:** https://docs.pytest.org/
- **Python unittest:** https://docs.python.org/3/library/unittest.html
- **Test-Driven Development:** https://en.wikipedia.org/wiki/Test-driven_development

---

**Last Updated:** February 8, 2026  
**Test Framework:** Python unittest / pytest
