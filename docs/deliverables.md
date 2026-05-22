1\. \[cite\_start]Two Distinct Mathematical Formulations \[cite: 55]



\* \[cite\_start]Requirement: You must propose two different mathematical models that represent the problem at different abstraction levels, not just equivalent reformulations. \[cite: 57]

\* \[cite\_start]Formulation 1 (Classical Approach): Needs to be a classical optimization approach. \[cite: 59]

\* \[cite\_start]Example: A Mixed-Integer Linear Programming (MILP) model focused on assignment or scheduling. \[cite: 61] \[cite\_start]You could use binary decision variables to indicate if a drone travels from node $i$ to node $j$, with constraints ensuring no-fly zones are avoided and payload limits are respected. \[cite: 62, 63]

\* \[cite\_start]Formulation 2 (Alternative Perspective): Needs to provide an alternative modeling perspective. \[cite: 65]

\* \[cite\_start]Example: A graph-based, flow-based, or constraint programming formulation. \[cite: 67] \[cite\_start]You could map the delivery network as a flow problem where "energy" and "payload weight" flow through the graph, draining at each customer node. \[cite: 67]



2\. \[cite\_start]Computational Complexity Study \[cite: 68]



\* \[cite\_start]Requirement: You must analyze and prove the computational complexity of the problem. \[cite: 70]

\* \[cite\_start]Example: Formally proving that the problem is NP-hard by demonstrating a reduction from a well-known NP-hard problem, such as the standard Traveling Salesperson Problem (TSP) or the Capacitated Vehicle Routing Problem (CVRP). \[cite: 71]



3\. \[cite\_start]Exact Solving Method \[cite: 72]



\* \[cite\_start]Requirement: Implement an exact algorithm to find the optimal solution. \[cite: 74] \[cite\_start]A Branch and Bound approach is recommended. \[cite: 74]

\* \[cite\_start]Example: Building a Branch and Bound algorithm that uses a relaxed version of your MILP model to calculate lower bounds, pruning branches of the search tree that exceed the current best known total energy consumption. \[cite: 75]



4\. \[cite\_start]Two Metaheuristics Implementations \[cite: 76]



\* \[cite\_start]Requirement: Because exact methods struggle with scale, you must develop two specific types of metaheuristics. \[cite: 78]

\* \[cite\_start]Deliverable 4a (Population-based): Example: A Genetic Algorithm (GA) that evolves a population of drone routes over multiple generations to iteratively find lower-energy paths. \[cite: 80]

\* \[cite\_start]Deliverable 4b (Local Search): Example: Simulated Annealing (SA) or Tabu Search that starts with a single greedy route and explores neighboring solutions by making small, incremental swaps while avoiding local optima. \[cite: 82, 83]



5\. \[cite\_start]Problem-Specific Operators \[cite: 84]



\* \[cite\_start]Requirement: Design custom operators for your metaheuristics, specifically for data encoding, neighborhood exploration, and route repair. \[cite: 86]

\* \[cite\_start]Examples: \[cite: 87]

&#x20;   \* \[cite\_start]Encoding: Representing a solution as an array of customer IDs separated by zeros (where zero represents returning to the depot). \[cite: 88]

&#x20;   \* \[cite\_start]Neighborhood: Implementing a "2-opt" or "swap" operator that uncrosses overlapping flight paths to save distance. \[cite: 89]

&#x20;   \* \[cite\_start]Repair: If a mutation causes a drone to exceed its battery limit, the repair operator forcibly splits the route and inserts a return trip to the depot to swap the battery. \[cite: 90]



6\. \[cite\_start]Experimental Study \& Datasets \[cite: 91]



\* \[cite\_start]Requirement: Perform tests on at least 10 different instances. \[cite: 93] \[cite\_start]You can generate your own datasets (randomizing locations, demands, and energy parameters) as long as you state and justify your assumptions. \[cite: 93]

\* \[cite\_start]Example: Generating 10 JSON or CSV files categorized by difficulty (e.g., 3 small instances with 10 customers, 4 medium instances with 30 customers, and 3 large instances with 100+ customers). \[cite: 94] \[cite\_start]You would explicitly state assumptions like "Drones consume 1 unit of energy per kilometer" in your report. \[cite: 95]



7\. \[cite\_start]Comparative Analysis \[cite: 96]



\* \[cite\_start]Requirement: Provide a thorough comparison of all your implemented methods (the exact method, population-based method, and local search). \[cite: 98]

\* \[cite\_start]Example: A detailed section in your presentation featuring charts or tables that plot "Execution Time vs. Total Energy Consumed." \[cite: 99] \[cite\_start]This would likely demonstrate that your Branch and Bound finds the perfect route but times out on large datasets, while your Genetic Algorithm finds a "good enough" solution in seconds. \[cite: 100]

