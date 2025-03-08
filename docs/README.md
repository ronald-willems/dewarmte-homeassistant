# DeWarmte Integration Documentation

## Sequence Diagram

The `sequence_diagram.puml` file contains a PlantUML sequence diagram that shows the interaction flow between different components of the DeWarmte integration.

### Viewing the Diagram

There are several ways to view the sequence diagram:

1. **Online PlantUML Renderer**:
   - Copy the contents of `sequence_diagram.puml`
   - Visit [PlantUML Online Server](http://www.plantuml.com/plantuml/uml/)
   - Paste the contents and view the rendered diagram

2. **VS Code**:
   - Install the "PlantUML" extension
   - Open `sequence_diagram.puml`
   - Press Alt+D to preview the diagram

3. **Command Line**:
   ```bash
   # Install PlantUML (requires Java)
   brew install plantuml  # macOS
   apt-get install plantuml  # Ubuntu/Debian

   # Generate PNG
   plantuml sequence_diagram.puml
   ```

## Diagram Components

The sequence diagram shows:

1. **Home Assistant Components**:
   - Home Assistant Core
   - DeWarmte Coordinator
   - DeWarmte Sensors
   - DeWarmte API Client

2. **External Components**:
   - MyDeWarmte Website

3. **Key Flows**:
   - Integration initialization
   - Data update cycle (60-second intervals)
   - Error handling
   - Cleanup process

## Integration Architecture

The integration follows a coordinator pattern where:
1. The coordinator manages the update cycle
2. The API client handles communication with mydewarmte.com
3. Sensor entities represent the various data points
4. Home Assistant Core manages the lifecycle 