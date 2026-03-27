import json

nodes = {
    "Cochin Port": [76.26, 9.96],
    "Kochi": [76.30, 9.98],
    "Thrissur": [76.21, 10.53],
    "Thiruvananthapuram": [76.97, 8.48],
    "Shoranur": [76.27, 10.77],
    "Kozhikode": [75.78, 11.26],
    "Mangalore": [74.84, 12.87],
    "Mumbai": [72.87, 19.07],
    "Palakkad": [76.65, 10.78],
    "Coimbatore": [77.03, 11.00],
    "Salem": [77.82, 11.31],
    "Bangalore": [77.59, 12.97],
    "Chennai": [80.27, 13.08],
    "Vijayawada": [80.62, 16.52],
    "Hyderabad": [78.49, 17.39],
    "Nagpur": [79.09, 21.15],
    "Delhi": [77.21, 28.61],
    "Wayanad": [76.13, 11.68]  # Proxied from Kozhikode
}

edges = [
    ("Thiruvananthapuram", "Kochi", [[76.97,8.48], [76.60,8.89], [76.34,9.49], [76.30,9.98]]),
    ("Cochin Port", "Kochi", [[76.26,9.96], [76.30,9.98]]),
    ("Kochi", "Thrissur", [[76.30,9.98], [76.21,10.21], [76.21,10.53]]),
    ("Thrissur", "Shoranur", [[76.21,10.53], [76.27,10.77]]),
    ("Shoranur", "Kozhikode", [[76.27,10.77], [75.93,10.91], [75.78,11.26]]),
    ("Kozhikode", "Wayanad", [[75.78,11.26], [75.93,10.91], [76.13,11.68]]),
    ("Kozhikode", "Mangalore", [[75.78,11.26], [75.59,11.60], [75.35,11.87], [74.99,12.50], [74.84,12.87]]),
    ("Mangalore", "Mumbai", [[74.84,12.87], [73.83,15.49], [73.30,17.00], [72.87,19.07]]),
    ("Shoranur", "Palakkad", [[76.27,10.77], [76.65,10.78]]),
    ("Palakkad", "Coimbatore", [[76.65,10.78], [77.03,11.00]]),
    ("Coimbatore", "Salem", [[77.03,11.00], [77.82,11.31]]),
    ("Salem", "Bangalore", [[77.82,11.31], [77.59,12.97]]),
    ("Salem", "Chennai", [[77.82,11.31], [79.13,12.91], [80.27,13.08]]),
    ("Chennai", "Vijayawada", [[80.27,13.08], [79.99,14.44], [80.62,16.52]]),
    ("Bangalore", "Hyderabad", [[77.59,12.97], [77.60,15.00], [78.49,17.39]]),
    ("Vijayawada", "Hyderabad", [[80.62,16.52], [79.50,17.00], [78.49,17.39]]),
    ("Mumbai", "Delhi", [[72.87,19.07], [73.30,17.00], [75.86,22.72], [76.91,28.63], [77.21,28.61]]),
    ("Hyderabad", "Nagpur", [[78.49,17.39], [79.09,21.15]]),
    ("Nagpur", "Delhi", [[79.09,21.15], [78.50,25.00], [77.21,28.61]])
]

# Simple BFS
def get_path(start, end):
    queue = [[start]]
    visited = set()
    while queue:
        path = queue.pop(0)
        node = path[-1]
        
        if node == end:
            return path
            
        if node not in visited:
            visited.add(node)
            for u, v, p in edges:
                if u == node:
                    queue.append(path + [v])
                elif v == node:
                    queue.append(path + [u])
    return None

hubs = [
    "Kochi", "Thrissur", "Palakkad", "Wayanad", "Kozhikode", 
    "Thiruvananthapuram", "Mumbai", "Bangalore", "Chennai", 
    "Delhi", "Hyderabad", "Mangalore", "Cochin Port"
]

routes = {}

for i in range(len(hubs)):
    for j in range(i+1, len(hubs)):
        u = hubs[i]
        v = hubs[j]
        
        p = get_path(u, v)
        if p:
            full_path = []
            for k in range(len(p)-1):
                n1 = p[k]
                n2 = p[k+1]
                edge_path = None
                for eu, ev, ep in edges:
                    if eu == n1 and ev == n2:
                        edge_path = ep
                        break
                    elif eu == n2 and ev == n1:
                        edge_path = ep[::-1]
                        break
                
                if not full_path:
                    full_path.extend(edge_path)
                else:
                    full_path.extend(edge_path[1:])
            
            # Formatted list of floats to 2 precision
            formatted_path = []
            for wp in full_path:
                formatted_path.append([round(wp[0], 2), round(wp[1], 2)])
                
            routes[f"{u}|{v}"] = formatted_path

# Write output as python dict literal
with open("routes_dict.py", "w") as f:
    f.write("RAIL_ROUTES = {\n")
    for k, v in routes.items():
        f.write(f'    "{k}": {v},\n'.replace(' ', ''))
    f.write("}\n")
    f.write("print('done!')\n")

print('Script written successfully.')
