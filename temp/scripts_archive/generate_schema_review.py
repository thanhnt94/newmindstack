"""
Script to generate database schema review.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mindstack_app import create_app
from sqlalchemy import inspect, text

app = create_app()

with app.app_context():
    from mindstack_app.models import db
    inspector = inspect(db.engine)
    
    tables = inspector.get_table_names()
    
    output = []
    output.append("# Database Schema Review")
    output.append("# Generated: 2025-12-28")
    output.append(f"# Total Tables: {len(tables)}")
    output.append("")
    
    for table in sorted(tables):
        # Get row count
        result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
        count = result.scalar()
        
        output.append(f"## {table} ({count} rows)")
        output.append("| Column | Type | Constraints |")
        output.append("|--------|------|-------------|")
        
        columns = inspector.get_columns(table)
        pk_cols = inspector.get_pk_constraint(table).get("constrained_columns", [])
        
        for col in columns:
            constraints = []
            if col["name"] in pk_cols:
                constraints.append("PK")
            if not col.get("nullable", True):
                constraints.append("NOT NULL")
            default = col.get("default")
            if default:
                constraints.append(f"DEFAULT {default}")
                
            constraint_str = ", ".join(constraints) if constraints else "-"
            output.append(f"| {col['name']} | {col['type']} | {constraint_str} |")
        output.append("")
    
    # Write to file
    with open("db_schema_review.md", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    
    print(f"Generated schema for {len(tables)} tables")
