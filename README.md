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

## Usage

Run the application using the `python flyway_schema_visualizer.py` command followed by the path to the directory containing your SQL files:

```bash
python flyway_schema_visualizer.py ./sample_data/users
```

This will process all `.sql` files in the specified directory and output the final database schema in SQL format.

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