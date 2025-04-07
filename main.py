import streamlit as st
import networkx as nx
import plotly.graph_objects as go
import random
import time

st.set_page_config(page_title="Traffic Simulation", layout="wide")
st.title("Realistic Traffic Simulation with Congestion")

# --- GRAPH SETUP ---
@st.cache_resource
def init_graph():
    G = nx.DiGraph()
    edges = [
        ("A", "B"), ("A", "C"), ("B", "C"), ("B", "D"),
        ("C", "D"), ("C", "E"), ("D", "E")
    ]
    for u, v in edges:
        G.add_edge(u, v,
                   base_weight=random.randint(5, 15),
                   weight=0,
                   open=True,
                   congestion_level=0.0)
    return G

G = init_graph()
nodes = list(G.nodes())

# --- UPDATE TRAFFIC WEIGHTS ---
def update_traffic(G, path):
    used_edges = set(zip(path, path[1:]))
    for u, v, data in G.edges(data=True):
        if data.get('open', True):
            # Update congestion
            if (u, v) in used_edges:
                data['congestion_level'] = min(data['congestion_level'] + 0.05, 1.0)
            else:
                data['congestion_level'] = max(data['congestion_level'] * 0.95, 0.0)

            fluctuation = random.uniform(0.9, 1.2)
            data['weight'] = round(
                data['base_weight'] * fluctuation * (1 + data['congestion_level']), 2)
        else:
            data['weight'] = float('inf')

# --- USER INPUT ---
col1, col2 = st.columns(2)
with col1:
    source = st.selectbox("Select Start Node", nodes)
with col2:
    target = st.selectbox("Select End Node", nodes, index=len(nodes)-1)

# --- EDGE CONTROLS ---
st.sidebar.markdown("### Traffic Controls")
st.sidebar.markdown("Toggle roads open/closed:")
for u, v in G.edges():
    key = f"toggle_{u}_{v}"
    G[u][v]['open'] = st.sidebar.checkbox(f"{u} → {v}", value=G[u][v]['open'], key=key)

# --- DIJKSTRA'S ALGORITHM ---
def get_shortest_path(G, source, target):
    try:
        path = nx.dijkstra_path(G, source, target, weight='weight')
        cost = nx.dijkstra_path_length(G, source, target, weight='weight')
        return path, cost
    except nx.NetworkXNoPath:
        return [], float('inf')

path, cost = get_shortest_path(G, source, target)

# --- SESSION STATE FOR VEHICLE ---
if 'vehicle_index' not in st.session_state:
    st.session_state.vehicle_index = 0

# --- VEHICLE CONTROL ---
st.sidebar.markdown("### Vehicle Controls")
if st.sidebar.button("Move Vehicle") and path:
    if st.session_state.vehicle_index < len(path) - 1:
        st.session_state.vehicle_index += 1
        update_traffic(G, path)

if st.sidebar.button("Reset Vehicle"):
    st.session_state.vehicle_index = 0
    update_traffic(G, [])

# --- PLOTLY VISUALIZATION ---
pos = nx.spring_layout(G, seed=42)
xn, yn = zip(*[pos[n] for n in G.nodes()])

edge_x = []
edge_y = []
edge_colors = []
for u, v in G.edges():
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    edge_x += [x0, x1, None]
    edge_y += [y0, y1, None]

    if not G[u][v]['open']:
        edge_colors.append('black')
    else:
        congestion = G[u][v]['congestion_level']
        if congestion < 0.3:
            edge_colors.append('green')
        elif congestion < 0.7:
            edge_colors.append('orange')
        else:
            edge_colors.append('red')

edge_trace = go.Scatter(
    x=edge_x, y=edge_y,
    line=dict(width=2, color='gray'),
    hoverinfo='none',
    mode='lines')

colored_edges = []
for (u, v), color in zip(G.edges(), edge_colors):
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    colored_edges.append(go.Scatter(
        x=[x0, x1], y=[y0, y1],
        line=dict(width=4, color=color),
        mode='lines'))

node_trace = go.Scatter(
    x=xn, y=yn,
    mode='markers+text',
    hoverinfo='text',
    marker=dict(size=20, color='lightblue'),
    text=list(G.nodes()),
    textposition="bottom center")

# Highlight path
highlight_edges = set(zip(path, path[1:]))
highlight_x = []
highlight_y = []
for u, v in highlight_edges:
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    highlight_x += [x0, x1, None]
    highlight_y += [y0, y1, None]

highlight_trace = go.Scatter(
    x=highlight_x, y=highlight_y,
    line=dict(width=4, color='red'),
    mode='lines',
    name='Shortest Path')

# Vehicle marker
vehicle_node = path[st.session_state.vehicle_index] if path else None
vehicle_trace = go.Scatter(
    x=[pos[vehicle_node][0]] if vehicle_node else [],
    y=[pos[vehicle_node][1]] if vehicle_node else [],
    mode='markers',
    marker=dict(size=18, color='black', symbol='star'),
    name='Vehicle')

fig = go.Figure(data=[edge_trace, *colored_edges, highlight_trace, node_trace, vehicle_trace])
fig.update_layout(
    showlegend=False,
    margin=dict(l=20, r=20, t=40, b=20),
    height=600,
    title=f"Shortest Path: {' ➝ '.join(path)} | Cost: {cost:.2f}" if path else "No Path Found"
)
st.plotly_chart(fig, use_container_width=True)

if st.button("Recalculate Traffic"):
    update_traffic(G, path)
    st.session_state.vehicle_index = 0
    st.experimental_rerun()
# --- END OF SCRIPT ---
# Note: The code is designed to run in a Streamlit environment.
