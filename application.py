from flask import Flask, request, jsonify
from flask_cors import CORS
import osmnx as ox
import networkx as nx
import logging
import pickle
import os

app = Flask(__name__)
CORS(app, resources={r"/calculate-route": {"origins": "*"}})  # Enable CORS for specific route

# Configure logging
logging.basicConfig(level=logging.DEBUG)

G = None  # Graph is loaded lazily

def load_graph():
    """Loads the Bengaluru street graph from cache or downloads it if not available."""
    global G
    if G is None:
        GRAPH_FILE = 'bengaluru_graph.pkl'
        if os.path.exists(GRAPH_FILE):
            app.logger.info("Loading graph from cache...")
            with open(GRAPH_FILE, 'rb') as f:
                G = pickle.load(f)
        else:
            app.logger.info("Downloading Bengaluru street network...")
            G = ox.graph_from_place('Bangalore, Karnataka, India', network_type='drive')
            G = ox.simplify_graph(G)  # Simplify graph to reduce size
            with open(GRAPH_FILE, 'wb') as f:
                pickle.dump(G, f)
            app.logger.info("Graph downloaded and cached.")
    return G

@app.route('/')
def home():
    """Simple endpoint to verify the server is running."""
    return "Flask server is running!"

@app.route('/calculate-route', methods=['POST'])
def calculate_route():
    """Endpoint to calculate shortest route(s) between origin and destination."""
    try:
        data = request.json
        origin = data['origin']
        destination = data['destination']
        num_routes = data.get('num_routes', 1)  # Default to 1 route if not specified

        # Validate input data
        if not origin or not destination or len(origin) != 2 or len(destination) != 2:
            raise ValueError("Invalid origin or destination coordinates")

        G = load_graph()  # Load the graph when needed

        # Find nearest nodes
        app.logger.debug(f"Finding nearest nodes for origin: {origin}, destination: {destination}")
        origin_node = ox.distance.nearest_nodes(G, origin[1], origin[0])
        dest_node = ox.distance.nearest_nodes(G, destination[1], destination[0])

        # Calculate multiple shortest paths
        all_routes = []
        for _ in range(num_routes):
            route = nx.shortest_path(G, origin_node, dest_node, weight='length')
            route_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in route]
            all_routes.append(route_coords)

        app.logger.debug(f"Routes calculated with coordinates: {all_routes}")

        return jsonify({'coordinates': all_routes})

    except Exception as e:
        app.logger.error(f"Error calculating route: {e}")
        return jsonify({'error': 'Failed to calculate route', 'details': str(e)}), 500

if __name__ == '__main__':
    # Dynamically bind to the port provided by Render or default to 5000 for local testing
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)

