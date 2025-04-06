import argparse
import re
from pathlib import Path
from natsort import natsorted, ns # ns for natural sort options
import sqlglot
from sqlglot import exp # To easily check expression types like exp.CreateTable
import base64
import io, requests
from IPython.display import Image, display
from PIL import Image as im
import matplotlib.pyplot as plt

# --- Configuration ---
# Attempt to guess dialect, but can be overridden via command line
DEFAULT_SQL_DIALECT = 'postgres' # Common dialects: 'mysql', 'postgres', 'sqlite', 'tsql' (SQL Server)

# --- Helper function for Mermaid ---

def plot_mermaid_visual(graph):
    graphbytes = graph.encode("utf8")
    base64_bytes = base64.urlsafe_b64encode(graphbytes)
    base64_string = base64_bytes.decode("ascii")
    img = im.open(io.BytesIO(requests.get('https://mermaid.ink/img/' + base64_string).content))
    plt.imshow(img)
    plt.axis('off') # allow to hide axis
    plt.savefig('image.png', dpi=1200)

def parse_foreign_key(constraint_sql):
    """
    Parses a FOREIGN KEY constraint string to extract relevant info for Mermaid.
    Returns a tuple: (child_columns_list, referenced_table) or None if parsing fails.
    Example: FOREIGN KEY (author_id) REFERENCES users(id) -> (['author_id'], 'users')
             FOREIGN KEY (col_a, col_b) REFERENCES other_table -> (['col_a', 'col_b'], 'other_table')
    NOTE: This is a simplified parser, assumes standard syntax.
    """
    # Regex breakdown:
    # FOREIGN KEY\s*\((.*?)\)       # Capture column(s) inside parentheses after FOREIGN KEY
    # \s*REFERENCES\s*              # Match REFERENCES keyword
    # (\w+)                         # Capture the referenced table name (simple word)
    # (?:\s*\(.*?\))?                # Optionally match referenced columns (non-capturing)
    # (?:\s+ON\s+(?:DELETE|UPDATE).*)* # Optionally match ON DELETE/UPDATE clauses (non-capturing)
    match = re.search(
        r"FOREIGN KEY\s*\((.*?)\)\s*REFERENCES\s*(\w+)(?:\s*\(.*?\))?(?:\s+ON\s+(?:DELETE|UPDATE).*)*",
        constraint_sql,
        re.IGNORECASE
    )
    if match:
        child_cols_str = match.group(1)
        referenced_table = match.group(2)
        # Split columns, remove potential quotes and whitespace
        child_columns = [col.strip().strip('`"') for col in child_cols_str.split(',')]
        return child_columns, referenced_table.strip('`"')
    return None

# --- Function to generate Mermaid code ---

def format_schema_mermaid(schema_dict):
    """Generates Mermaid ER diagram code from the schema dictionary."""
    output = ["erDiagram"]
    relationships = []
    foreign_key_columns = {} # Store FK columns for marking: {'table': {'col1', 'col2'}}

    # --- Pass 1: Identify all Foreign Key columns ---
    for table_name, table_info in schema_dict.get('tables', {}).items():
        if table_name not in foreign_key_columns:
            foreign_key_columns[table_name] = set()

        for constraint in table_info.get('constraints', []):
            parsed_fk = parse_foreign_key(constraint)
            if parsed_fk:
                child_columns, _ = parsed_fk
                for col in child_columns:
                     foreign_key_columns[table_name].add(col) # Mark column as FK

    # --- Pass 2: Generate Table Definitions and Collect Relationships ---
    sorted_table_names = sorted(schema_dict.get('tables', {}).keys())

    for table_name in sorted_table_names:
        table_info = schema_dict['tables'][table_name]
        output.append(f"    {table_name} {{")

        if not table_info.get('columns'):
            output.append("        # (No columns defined)") # Mermaid comment
        else:
            sorted_col_names = sorted(table_info['columns'].keys())
            for col_name in sorted_col_names:
                col_info = table_info['columns'][col_name]
                col_type = col_info.get('type', 'UNKNOWN').replace(" ", "_") # Replace spaces in type for Mermaid ID safety
                col_constraints = col_info.get('constraints', [])

                markers = []
                is_pk = any("PRIMARY KEY" in c.upper() for c in col_constraints)
                is_nn = any("NOT NULL" in c.upper() for c in col_constraints)
                is_uk = any("UNIQUE" in c.upper() for c in col_constraints)
                # Check if this column was marked as an FK in Pass 1
                is_fk = col_name in foreign_key_columns.get(table_name, set())

                if is_pk: markers.append("PK")
                if is_fk: markers.append("FK")
                if is_uk: markers.append("UK")
                if is_nn: markers.append("NN")

                marker_str = f" \"{','.join(markers)}\"" if markers else ""
                # Escape quotes in column names/types if necessary, though unlikely needed for standard names
                output.append(f"        {col_type} {col_name}{marker_str}")

        output.append("    }")
        output.append("") # Blank line for readability

        # Process constraints for relationships
        for constraint in table_info.get('constraints', []):
             parsed_fk = parse_foreign_key(constraint)
             if parsed_fk:
                 child_columns, referenced_table = parsed_fk
                 if referenced_table in schema_dict.get('tables', {}): # Ensure referenced table exists
                     # Determine cardinality (simplified: check nullability of the first FK column)
                     first_child_col = child_columns[0]
                     child_col_info = table_info.get('columns', {}).get(first_child_col)
                     child_col_constraints = child_col_info.get('constraints', []) if child_col_info else []
                     is_child_nn = any("NOT NULL" in c.upper() for c in child_col_constraints)

                     # ||--|{ : one to one-or-more (FK is NOT NULL)
                     # ||--o{ : one to zero-or-more (FK is NULLABLE)
                     # Other cardinality like zero-or-one requires more info (e.g., UNIQUE constraint on FK)
                     # Defaulting to one-to-many type relationships
                     cardinality = "||--|{" if is_child_nn else "||--o{"

                     # Use first child column name in label for clarity (optional)
                     label = f"\"FK: {first_child_col}\"" # Use quotes for labels with spaces/special chars
                     relationships.append(f"    {referenced_table} {cardinality} {table_name} : {label}")
                 else:
                      print(f"Warning: Skipping relationship for constraint '{constraint}' because referenced table '{referenced_table}' was not found in the final schema.")


    # Append relationships at the end
    if relationships:
        output.append("    %% -- Relationships --") # Mermaid comment
        # Add unique relationships only to avoid duplicates if defined multiple ways
        output.extend(sorted(list(set(relationships))))

    return "\n".join(output)

# --- Helper Functions for Flyway --- 

def parse_flyway_version(filename):
    """
    Extracts a sortable version tuple from a Flyway filename.
    Example: V1.2.3__Desc.sql -> (1, 2, 3)
             V202301011030__Desc.sql -> (202301011030,)
             R__Desc.sql -> None (Repeatable scripts don't strictly define final schema state in order)
             U1.2__Desc.sql -> None (Undo scripts shouldn't contribute to final state)
    Returns None if it's not a versioned migration ('V' prefix).
    """
    match = re.match(r"^[Vv]([0-9]+(?:[._][0-9]+)*)_.*\.sql$", filename.name)
    if match:
        version_str = match.group(1).replace('_', '.')
        try:
            # Convert version parts to integers for proper sorting
            return tuple(map(int, version_str.split('.')))
        except ValueError:
            print(f"Warning: Could not parse version from '{filename.name}'. Skipping.")
            return None # Handle potential non-integer parts gracefully
    return None # Not a standard versioned migration file

def extract_column_def(col_def_exp):
    """Extracts name, type, and constraints from a sqlglot ColumnDef expression."""
    col_name = col_def_exp.find(exp.Identifier).name
    col_type = col_def_exp.find(exp.DataType).sql(dialect=current_dialect) # Use global dialect
    constraints = []
    for constraint in col_def_exp.find_all(exp.ColumnConstraint):
        constraints.append(constraint.sql(dialect=current_dialect).upper())
    return col_name, {'type': col_type, 'constraints': constraints}

def format_schema_output(schema_dict):
    """Generates a readable string representation of the schema."""
    output = []
    output.append("--- Generated Final Schema ---")

    if not schema_dict.get('tables'):
        output.append("\nNo tables found in the final schema.")
        return "\n".join(output)

    # Sort tables by name for consistent output
    sorted_table_names = sorted(schema_dict['tables'].keys())

    for table_name in sorted_table_names:
        table_info = schema_dict['tables'][table_name]
        output.append(f"\n-- Table: {table_name}")

        if not table_info.get('columns'):
            output.append("  (No columns defined)")
        else:
            output.append("  Columns:")
            # Sort columns for consistent output
            sorted_col_names = sorted(table_info['columns'].keys())
            for col_name in sorted_col_names:
                col_info = table_info['columns'][col_name]
                constraints_str = f" ({', '.join(col_info['constraints'])})" if col_info['constraints'] else ""
                output.append(f"    - {col_name}: {col_info['type']}{constraints_str}")

        if table_info.get('indexes'):
             output.append("  Indexes:")
             # Sort indexes for consistent output
             sorted_idx_names = sorted(table_info['indexes'].keys())
             for idx_name in sorted_idx_names:
                 idx_info = table_info['indexes'][idx_name]
                 unique_str = "UNIQUE " if idx_info['unique'] else ""
                 cols_str = ', '.join(idx_info['columns'])
                 output.append(f"    - {idx_name}: {unique_str}INDEX ({cols_str})")

        if table_info.get('constraints'):
            output.append("  Table Constraints:")
            # Sort constraints for consistent output
            sorted_constraints = sorted(table_info['constraints'])
            for constr in sorted_constraints:
                 output.append(f"    - {constr}")


    if schema_dict.get('not_processed'):
        unprocessed_sqls = sorted(schema_dict['not_processed'].keys())

    for sql in unprocessed_sqls:
        sql_info = schema_dict['not_processed'][sql]
        output.append(f"\n-- Not processed: {sql_info}")

    output.append("\n--- End of Schema ---")
    return "\n".join(output)

# --- Main Processing Logic ---

# Global variable to hold the current dialect being used for parsing/formatting
current_dialect = DEFAULT_SQL_DIALECT

def process_sql_scripts(directory: Path, dialect: str):
    """
    Finds, sorts, parses Flyway scripts, and simulates schema changes.
    """
    global current_dialect # Allow modification of the global dialect
    current_dialect = dialect

    schema = {'tables': {}, 'not_processed': {}} # Structure: {'table_name': {'columns': {}, 'indexes': {}, 'constraints': []}}
    sql_files = []

    # 1. Find all .sql files and extract versions
    print(f"Scanning directory: {directory}")
    for item in directory.rglob('*.sql'): # Use rglob for recursive search
        if item.is_file():
            version = parse_flyway_version(item)
            if version:
                sql_files.append({'path': item, 'version': version})
            else:
                print(f"Info: Skipping non-versioned file: {item.name}")

    # 2. Sort files by version using natural sort order
    # Use natsorted which handles tuples like (1, 1) vs (1, 10) correctly
    sorted_files = natsorted(sql_files, key=lambda x: x['version'], alg=ns.REAL)

    if not sorted_files:
        print("No valid Flyway versioned SQL files found.")
        return schema # Return empty schema

    print(f"\nFound {len(sorted_files)} versioned SQL files. Processing in order:")

    # 3. Process sorted files
    for file_info in sorted_files:
        filepath = file_info['path']
        print(f"  -> Processing: {filepath.name}")
        try:
            sql_content = filepath.read_text(encoding='utf-8')
            # Parse the whole file. Handle potential multiple statements per file.
            parsed_expressions = sqlglot.parse(sql_content, read=dialect)

            for expression in parsed_expressions:
                # Use 'try...except' for robustness against complex/unsupported SQL
                try:
                    # --- CREATE TABLE ---
                    if (expression.key == "create" and expression.kind == "TABLE"):
                        table_name = expression.this.find(exp.Table).name
                        if table_name in schema['tables']:
                            print(f"      Warning: Table '{table_name}' already exists. Re-creating (check scripts).")
                            # Overwrite definition based on Flyway logic (last script wins)

                        schema['tables'][table_name] = {'columns': {}, 'indexes': {}, 'constraints': []}
                        
                        # Extract columns
                        schema_exp = expression.this # The Schema object within CreateTable
                        if schema_exp and hasattr(schema_exp, 'expressions'):
                             for elem in schema_exp.expressions:
                                if isinstance(elem, exp.ColumnDef):
                                    col_name, col_info = extract_column_def(elem)
                                    schema['tables'][table_name]['columns'][col_name] = col_info
                                elif isinstance(elem, exp.ForeignKey):
                                     # Store raw constraint SQL for simplicity
                                     schema['tables'][table_name]['constraints'].append(elem.sql(dialect=dialect))
                                elif isinstance(elem, exp.Index): # Sometimes indexes are part of CREATE TABLE
                                     # Handle inline index definitions if needed (less common)
                                     pass # Add logic here if necessary


                        # Extract separate table constraints if any (outside the main schema element)
                        # This structure might vary slightly based on sqlglot's parsing of specific dialects
                        # Add more robust searching if needed.

                    # --- DROP TABLE ---
                    elif (expression.key == "drop" and expression.kind == "TABLE"):
                        table_name = expression.this.find(exp.Table).name
                        if table_name in schema['tables']:
                            print(f"      Dropping table: {table_name}")
                            del schema['tables'][table_name]
                        else:
                            print(f"      Warning: Trying to drop non-existent table: {table_name}")

                    # --- ALTER TABLE ---
                    elif (expression.key == "alter" and expression.kind == "TABLE"):
                        table_name = expression.this.find(exp.Table).name
                        if table_name not in schema['tables']:
                            print(f"      Warning: Altering non-existent table: {table_name}. Skipping action.")
                            continue

                        # Iterate through ALTER actions
                        for action in expression.args.get('actions', []):
                            # ADD COLUMN
                            if (action.key == "columndef"):
                                # col_def = action.this
                                col_def = action
                                col_name, col_info = extract_column_def(col_def)
                                if col_name in schema['tables'][table_name]['columns']:
                                    print(f"      Warning: Column '{col_name}' already exists in table '{table_name}'. Overwriting definition.")
                                print(f"      Adding column: {table_name}.{col_name}")
                                schema['tables'][table_name]['columns'][col_name] = col_info
                            # DROP COLUMN
                            elif (action.key == "drop" and action.kind == "COLUMN"):
                                col_name = action.this.find(exp.Identifier).name
                                if col_name in schema['tables'][table_name]['columns']:
                                    print(f"      Dropping column: {table_name}.{col_name}")
                                    del schema['tables'][table_name]['columns'][col_name]
                                else:
                                     print(f"      Warning: Dropping non-existent column: {table_name}.{col_name}")
                            # ALTER COLUMN / MODIFY COLUMN (Syntax varies)
                            elif isinstance(action, exp.AlterColumn):
                                # This often contains the new definition or constraint changes
                                # Need more detailed inspection based on dialect/specific ALTER TYPE
                                identifier = action.this.find(exp.Identifier)
                                col_name = identifier.name
                                new_name = identifier.output_name
                                if col_name in schema['tables'][table_name]['columns']:
                                    print(f"      Altering column: {table_name}.{col_name} (Details depend on specific ALTER action)")
                                    # Basic approach: Just log it. More complex: parse the action type (e.g., SET TYPE)
                                    # For simplicity, we won't parse the *exact* change here, but acknowledge it happened.
                                    # A more advanced version could parse action.args['kind'] etc.
                                    
                                    updated = False
                                    # Strategy 1: Check if action.this IS the new ColumnDef (MySQL MODIFY/CHANGE often parsed this way)
                                    # This assumes the name in the ColumnDef IS the target column name.
                                    # Doesn't handle RENAME (CHANGE old new) easily here without more logic.
                                    if isinstance(action.this, exp.ColumnDef):
                                        try:
                                            new_col_name, new_col_info = extract_column_def(action.this)
                                            if new_col_name == col_name:
                                                print(f"        -> Applying new definition (Type/Constraints): {action.this.sql(dialect=current_dialect)}")
                                                schema['tables'][table_name]['columns'][col_name] = new_col_info
                                                updated = True
                                            else:
                                                # This case would be RENAME, which needs separate handling
                                                # For now, log it as unhandled if names differ significantly
                                                print(f"        -> Detected potential RENAME/CHANGE action from '{col_name}' to '{new_col_name}'. Full update skipped (Rename logic not implemented).")
                                        except Exception as extract_err:
                                            print(f"        -> Error extracting new definition from AlterColumn action: {extract_err}")

                                    
                                    # Strategy 2: If not a full definition, check for specific SET clauses (e.g., SET DATA TYPE)
                                    if not updated:
                                        # Check for data type change
                                        new_type_exp = action.this.find(exp.DataType)
                                        if new_type_exp:
                                            new_type_sql = new_type_exp.sql(dialect=current_dialect)
                                            print(f"        -> Updating type to: {new_type_sql}")
                                            # TODO: check this
                                            schema['tables'][table_name]['columns'][col_name] = new_type_sql
                                            updated = True
                                        
                                        # Check for constraint changes *within* the alter action
                                        # This is less common for standard ALTER but might occur
                                        action_constraints = action.this.find_all(exp.ColumnConstraint)
                                        if action_constraints:
                                            # Simple approach: Assume these REPLACE existing type-specific constraints (NULL/NOT NULL, DEFAULT)
                                            # More robust: Parse 'kind' (SET/DROP) and merge carefully
                                            print(f"        -> Found constraints within ALTER action: {[c.sql(dialect=current_dialect) for c in action_constraints]}")
                                            # Naive update: Replace constraints entirely with these new ones + any non-overridden old ones.
                                            # This is likely INACCURATE for many cases (e.g., doesn't handle DROP). Needs refinement.
                                            # For now, just log that we found them. A better implementation is needed for precise constraint updates via SET/DROP.
                                            # table_schema['columns'][col_name]['constraints'] = [c.sql(dialect=current_dialect) for c in action_constraints]
                                            print(f"        -> (Info) Constraint update logic based on SET/DROP kind is basic. Review final schema.")
                                            updated = True # Mark as updated even if logic is simple
                                        
                                    # Fallback Log
                                    if not updated:
                                        print(f"        -> Alteration type not fully parsed/applied by this script: {action.sql(dialect=current_dialect)}")

                                else:
                                    print(f"      Warning: Altering non-existent column: {table_name}.{col_name}")
                            # ADD CONSTRAINT
                            elif isinstance(action, exp.AddConstraint):
                                 #constraint_sql = action.this.sql(dialect=dialect)
                                 constraint_sql = action.sql(dialect=dialect)
                                 print(f"      Adding constraint to {table_name}: {constraint_sql}")
                                 schema['tables'][table_name]['constraints'].append(constraint_sql)
                            # DROP CONSTRAINT (Parsing might be tricky)
                            # RENAME TABLE / COLUMN etc (Add more handlers as needed)
                            else:
                                print(f"      Info: Unsupported ALTER TABLE action type: {type(action).__name__}")

                    # --- CREATE INDEX ---
                    elif (expression.key == "create" and expression.kind == "INDEX"):
                        index_name = expression.this.find(exp.Identifier).name
                        table_name = expression.find(exp.Table).name
                        if table_name in schema['tables']:
                            cols = [col.name for col in expression.find(exp.Index).find_all(exp.Identifier)]
                            is_unique = expression.find(exp.UniqueColumnConstraint) is not None or 'unique' in expression.sql(dialect=dialect).lower() # Simple check
                            print(f"      Creating {'UNIQUE ' if is_unique else ''}index '{index_name}' on {table_name} ({', '.join(cols)})")
                            schema['tables'][table_name]['indexes'][index_name] = {'columns': cols, 'unique': is_unique}
                        else:
                            print(f"      Warning: Creating index on non-existent table: {table_name}")

                    # --- DROP INDEX ---
                    elif (expression.key == "drop" and expression.kind == "INDEX"):
                         index_name = expression.this.find(exp.Identifier).name
                         # Finding the table might require context or specific dialect parsing
                         # Assume we can find it associated with a table in our schema
                         found = False
                         for table_name, table_info in schema['tables'].items():
                            if index_name in table_info['indexes']:
                                print(f"      Dropping index: {index_name} from table {table_name}")
                                del table_info['indexes'][index_name]
                                found = True
                                break
                         if not found:
                             print(f"      Warning: Could not find index '{index_name}' to drop.")

                    # TODO: Add handlers for other DDL like CREATE VIEW, ALTER VIEW, etc. if needed
                    
                    # Fallback, just log
                    elif (expression.key == 'command'):
                        schema['not_processed'][filepath.name] = expression.sql(dialect=dialect)

                except Exception as parse_err:
                    print(f"      ERROR processing statement in {filepath.name}: {parse_err}")
                    print(f"      Statement causing error: {expression.sql(dialect=dialect)}")
                    # Decide whether to continue or stop on error

        except sqlglot.errors.ParseError as e:
            print(f"  ERROR: Failed to parse file {filepath.name} with dialect '{dialect}'.")
            print(f"  Error details: {e}")
            # Optionally skip file or stop execution
            continue # Skip this file
        except IOError as e:
            print(f"  ERROR: Could not read file {filepath.name}: {e}")
            continue # Skip this file
        except Exception as e:
            print(f"  UNEXPECTED ERROR processing file {filepath.name}: {e}")
            continue # Skip this file


    return schema

# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(
        description="Generate a final DB schema representation from Flyway SQL scripts.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    parser.add_argument(
        "directory",
        type=str,
        help="Directory containing the Flyway SQL migration files."
        )
    all_dialacts = [member.value for member in sqlglot.dialects.Dialects if member.value]
    print(all_dialacts)
    parser.add_argument(
        "-d", "--dialect",
        type=str,
        default=DEFAULT_SQL_DIALECT,
        help=f"SQL dialect for parsing (e.g., {', '.join(all_dialacts)})."
        )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Optional file path to write the final schema output."
        )
    parser.add_argument(
        "--format", # Add format argument
        choices=['text', 'mermaid'],
        default='text',
        help="Output format for the schema."
    )

    args = parser.parse_args()

    script_dir = Path(args.directory)
    if not script_dir.is_dir():
        print(f"Error: Directory not found: {args.directory}")
        return 1 # Exit with error code

    if args.dialect not in all_dialacts:
         print(f"Warning: Unknown dialect '{args.dialect}'. Using default '{DEFAULT_SQL_DIALECT}'.")
         print(f"Available dialects: {', '.join(all_dialacts)}")
         args.dialect = DEFAULT_SQL_DIALECT


    print(f"Starting schema generation for directory: {script_dir.resolve()}")
    print(f"Using SQL dialect: {args.dialect}")

    final_schema = process_sql_scripts(script_dir, args.dialect)
    schema_output = format_schema_output(final_schema)
    print("\n" + schema_output) # Print to console

    # Choose the formatting function based on the argument
    if args.format == 'mermaid':
        schema_output = format_schema_mermaid(final_schema)
        print("\n --- Mermaid schema output ---")
        print("\n" + schema_output)
        #TODO plot_mermaid_visual(schema_output)
        # Suggest using a .md or .mmd extension for Mermaid files
        if args.output and not Path(args.output).suffix.lower() in ['.md', '.mmd']:
            print(f"Suggestion: Consider using a '.md' or '.mmd' extension for Mermaid output file '{args.output}'.")
        elif not args.output:
            args.output = args.directory + "/output_schema.mmd"

    if args.output:
        output_file = Path(args.output)
        try:
            output_file.write_text(schema_output, encoding='utf-8')
            print(f"\nSchema also written to: {output_file.resolve()}")
        except IOError as e:
            print(f"\nError writing schema to file {args.output}: {e}")
            return 1

    return 0 # Exit successfully

if __name__ == "__main__":
    import sys
    sys.exit(main())