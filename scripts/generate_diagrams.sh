#!/bin/bash

# Directory containing PlantUML files
PUML_DIR="docs"
# Directory for output PNG files
OUTPUT_DIR="docs/images"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Generate PNGs for each PlantUML file
for puml_file in "$PUML_DIR"/*.puml; do
    if [ -f "$puml_file" ]; then
        filename=$(basename "$puml_file" .puml)
        echo "Generating PNG for $filename..."
        plantuml -tpng -o "$(pwd)/$OUTPUT_DIR" "$puml_file"
    fi
done

echo "Done! PNG files have been generated in $OUTPUT_DIR" 