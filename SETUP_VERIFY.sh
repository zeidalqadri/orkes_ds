#!/bin/bash
set -e

echo "🔍 Harga CLI Setup Verification"
echo "================================="
echo ""

# 1. Check Python & venv
echo "1️⃣  Python Environment"
python --version
[ -d "/home/the_bomb/orkes/.venv" ] && echo "   ✓ Venv exists" || echo "   ✗ Venv missing"

# 2. Check orkes packages
echo ""
echo "2️⃣  Orkes Packages"
python -c "import orkes_core; print('   ✓ orkes-core')" 2>/dev/null || echo "   ✗ orkes-core missing"
python -c "import orkes_pricing; print('   ✓ orkes-pricing')" 2>/dev/null || echo "   ✗ orkes-pricing missing"
python -c "import orkes_tender; print('   ✓ orkes-tender')" 2>/dev/null || echo "   ✗ orkes-tender missing"

# 3. Check databases
echo ""
echo "3️⃣  Databases"
[ -f "/home/the_bomb/orkes/harga/data/harga_v8.db" ] && echo "   ✓ harga_v8.db" || echo "   ✗ harga_v8.db missing"
[ -f "/home/the_bomb/orkes/harga/data/price_memory.db" ] && echo "   ✓ price_memory.db" || echo "   ✗ price_memory.db missing"
[ -f "/home/the_bomb/orkes/harga/data/supplier_index.db" ] && echo "   ✓ supplier_index.db" || echo "   ✗ supplier_index.db missing"

# 4. Check package structure
echo ""
echo "4️⃣  Package Structure"
[ -f "tools/harga_cli/__init__.py" ] && echo "   ✓ __init__.py" || echo "   ✗ __init__.py missing"
[ -f "tools/harga_cli/__main__.py" ] && echo "   ✓ __main__.py" || echo "   ✗ __main__.py missing"
[ -f "tools/harga_cli/db.py" ] && echo "   ✓ db.py" || echo "   ✗ db.py missing"
[ -f "tools/harga_cli/formatters.py" ] && echo "   ✓ formatters.py" || echo "   ✗ formatters.py missing"
[ -d "tools/harga_cli/commands" ] && echo "   ✓ commands/" || echo "   ✗ commands/ missing"

# 5. Check documentation
echo ""
echo "5️⃣  Documentation"
[ -f "CLAUDE.md" ] && echo "   ✓ CLAUDE.md" || echo "   ✗ CLAUDE.md missing"
[ -f "PROMPT.md" ] && echo "   ✓ PROMPT.md" || echo "   ✗ PROMPT.md missing"
[ -f "context/HARGA_CLI_REFERENCE.md" ] && echo "   ✓ HARGA_CLI_REFERENCE.md" || echo "   ✗ HARGA_CLI_REFERENCE.md missing"
[ -f "context/experts.json" ] && echo "   ✓ experts.json" || echo "   ✗ experts.json missing"
[ -f "context/shared_learnings.md" ] && echo "   ✓ shared_learnings.md" || echo "   ✗ shared_learnings.md missing"

# 6. Check pytest
echo ""
echo "6️⃣  Testing Infrastructure"
python -m pytest --version 2>/dev/null | head -1 && echo "   ✓ pytest installed" || echo "   ✗ pytest missing"
[ -f "tests/conftest.py" ] && echo "   ✓ conftest.py" || echo "   ✗ conftest.py missing"

# 7. Syntax check
echo ""
echo "7️⃣  Code Quality"
python -c "import py_compile; py_compile.compile('tools/harga_cli/__init__.py', doraise=True)" 2>/dev/null && echo "   ✓ Package syntax valid" || echo "   ✗ Package syntax error"

echo ""
echo "✅ Setup verification complete!"
