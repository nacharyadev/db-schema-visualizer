import os
import sys
import argparse
import sqlparse

def process_schema(directory_path):
    schema = {}

    # List all files in the directory
    for filename in os.listdir(directory_path):
        if filename.endswith('.sql'):
            file_path = os.path.join(directory_path, filename)
            print(f'Processing file: {file_path}')

            with open(file_path, 'r') as file:
                sql_content = file.read()

                # Parse SQL content
                parsed_sql = sqlparse.parse(sql_content)

                # Evaluate schema changes
                for statement in parsed_sql:
                    statement_type = statement.get_type()
                    if statement_type == 'CREATE':
                        # Extract table name and columns
                        table_name = extract_table_name(statement)
                        columns = extract_columns(statement)
                        schema[table_name] = columns
                    elif statement_type == 'ALTER':
                        # Handle ALTER TABLE statements
                        table_name, changes = extract_alterations(statement)
                        if table_name in schema:
                            schema[table_name].update(changes)

    # Generate final schema in SQL format
    final_schema_sql = generate_final_schema_sql(schema)
    print('Final Database Schema in SQL format:')
    print(final_schema_sql)

def extract_table_name(statement):
    # Extract table name from CREATE TABLE statement
    tokens = statement.tokens
    for token in tokens:
        if token.ttype is None and token.get_real_name():
            return token.get_real_name()
    return None

def extract_columns(statement):
    # Extract columns from CREATE TABLE statement
    columns = {}
    for token in statement.tokens:
        if token.ttype is None and token.is_group:
            for subtoken in token.tokens:
                if subtoken.ttype is None and subtoken.is_group:
                    column_name = subtoken.get_real_name()
                    # Assuming the column type is the next token after the column name
                    column_type = None
                    for idx, subsubtoken in enumerate(subtoken.tokens):
                        if subsubtoken.get_real_name() == column_name:
                            # Get the next token as the column type
                            if idx + 1 < len(subtoken.tokens):
                                column_type = subtoken.tokens[idx + 1].value
                    columns[column_name] = column_type
    return columns

def extract_alterations(statement):
    # Extract table name and changes from ALTER TABLE statement
    table_name = None
    changes = {}
    tokens = statement.tokens
    for token in tokens:
        if token.ttype is None and token.get_real_name():
            table_name = token.get_real_name()
        elif token.ttype is None and token.is_group:
            for subtoken in token.tokens:
                if subtoken.ttype is None and subtoken.is_group:
                    column_name = subtoken.get_real_name()
                    column_type = subtoken.get_type()
                    changes[column_name] = column_type
    return table_name, changes

def generate_final_schema_sql(schema):
    # Generate SQL statements for the final schema
    sql_statements = []
    for table_name, columns in schema.items():
        column_definitions = ', '.join([f'{name} {type}' for name, type in columns.items()])
        sql_statements.append(f'CREATE TABLE {table_name} ({column_definitions});')
    return '\n'.join(sql_statements)

def main():
    parser = argparse.ArgumentParser(description='Process SQL files to evaluate the database schema.')
    parser.add_argument('directory', type=str, help='Path to the directory containing SQL files')
    args = parser.parse_args()

    process_schema(args.directory)

if __name__ == '__main__':
    main()