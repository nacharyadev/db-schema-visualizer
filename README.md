# DB Schema Visualizer

This Python console application processes Flyway SQL files to evaluate and output the final database schema in SQL format. It is designed to work with PostgreSQL dialect.

## Installation

1. **Clone the Repository**: Clone this repository to your local machine.

2. **Set Up Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## How to Run the App

To run the Flyway Schema Visualizer app, use the following command:

```
python flyway_schema_visualizer.py <directory_path> [options]
```

### Arguments

- `<directory_path>`: The path to the directory containing the Flyway SQL migration files.

### Options

- `-d`, `--dialect`: Specify the SQL dialect for parsing (e.g., `postgres`, `mysql`, `sqlite`). Default is `postgres`.
- `-o`, `--output`: Optional file path to write the final schema output.
- `--format`: Specify the output format for the schema. Options are `text` or `mermaid`. Default is `text`.
- `--help`: Show a help message and exit.

### Example Usage

To generate a schema in text format:

```
python flyway_schema_visualizer.py /path/to/sql/files --format text
```

To generate a schema in Mermaid format and save it to a file:

```
python flyway_schema_visualizer.py /path/to/sql/files --format mermaid -o schema.mmd
```

This will process the SQL files in the specified directory and output the final database schema in the chosen format.

## Development

To set up the application for development:

1. **Install the Package**:
   ```bash
   pip install .
   ```

2. **Run the Application**:
   Use the `dbviz` command as described in the usage section.

## Dependencies

- `sqlglot`: Used for parsing SQL files.
- `natsort`: Used for natural sorting of files.

## License

This project is licensed under the MIT License. 