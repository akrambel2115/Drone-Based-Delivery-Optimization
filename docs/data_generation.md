Drone Delivery Data Generation Specifications

1. General Generation Strategy

The Template Approach: Build a dynamic data generator (e.g., in Python) to easily adjust parameters and test layouts.

Configuration-Driven Architecture: The generator must not use hardcoded variables. It should be driven by a centralized Configuration File (e.g., config.json) using Feature Flags (booleans to toggle features on/off).

The Output Requirement: Use the generator to export exactly 10 static dataset instances (e.g., 3 small, 4 medium, 3 large) based on different configurations. All future algorithms must be tested against these exact same 10 files for a fair comparative analysis.

File Format: Use JSON. It perfectly handles nested 3D coordinates, bounding boxes, configuration metadata, and terrain arrays.

2. The 3D Space & Terrain Rules

Coordinate System: The space is a 3D matrix (X, Y, Z).

The Ground Floor & Voxel Terrain: * There are no negative Z values.

Advanced Topology: Using a noise algorithm (like Perlin or Simplex noise), the ground can be generated as a "Voxel Map".

Any coordinate $(x, y, z)$ where $z < \text{NoiseHeight}(x, y)$ is automatically classified as solid ground/No-Fly Zone.

Static Environment: All orders and demands are known at $T=0$. This is an offline, static optimization problem.

3. Data Entities to Generate

A. The Depot

Location: Fixed at a central point. If Perlin terrain is enabled, it must be placed on the surface of the topology (or a flattened plateau) to ensure accessibility.

Capacity: Assume the depot has an infinite supply of packages (no depot inventory constraints) to keep the mathematical model focused purely on routing.

B. The Customers

Attributes: Unique ID, 3D coordinate (X, Y, Z), and Payload Demand (weight/units).

Placement: If terrain is enabled, customers must be placed on top of the generated noise, creating Altitude Demand (delivering to a mountain costs more energy than a valley).

Delivery Rule: Split deliveries are strictly forbidden. A customer's total demand must fit on a single drone.

C. No-Fly Zones (Obstacles)

Terrain as NFZ: As mentioned, the generated topological ground inherently acts as a No-Fly Zone.

Voxel Obstacles: Additional obstacles like tall urban buildings or trees can be generated as 3D bounding boxes or clusters of solid voxels sitting on top of the terrain.

4. Drone Fleet & Constraint Parameters

Your configuration file and the resulting generated JSON must define the global limits and costs for the drones operating in that specific instance.

Fleet Size Limit: Controlled by a feature flag. If disabled, assume an infinite fleet where the algorithm must minimize the number of drones used. If enabled, set a strict integer limit.

Payload Capacity: A hard limit on the total weight a single drone can carry per trip.

Battery/Energy Capacity: A hard limit on the total energy a drone can expend per trip.

Energy Consumption Rates: * Horizontal Cost Rate: Energy used per unit distance moving along X and Y axes.

Vertical Penalty Multiplier: Energy used ascending/hovering along the Z axis (e.g., $1.5\times$ the horizontal rate).

5. Ideal JSON Schema Structure (Per Instance)

Every exported instance file should follow this general structure, dictated by the master config:

Metadata: instance_name, grid_bounds (x, y, z scale), and active feature flags.

Drone Profile: battery_capacity, payload_capacity, fleet_size (if enabled).

Energy Costs: horizontal_rate, vertical_penalty_multiplier.

Terrain Map (Optional): A 2D array representing the height_map at each X,Y coordinate.

Depot: id, x, y, z.

Customers (Array): List of objects containing id, x, y, z, demand.

No-Fly Zones (Array): List of explicit obstacle bounding boxes (trees/buildings).