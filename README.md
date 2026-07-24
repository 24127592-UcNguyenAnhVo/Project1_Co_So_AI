# Bloxorz Solver

Project 1 - CSC14003: Introduction to Artificial Intelligence

## 1. Introduction

This project implements the Bloxorz game and four search algorithms:

- BFS
- DFS
- UCS
- A*

The game logic and all search algorithms are implemented in Python. The main GUI is a 3D web interface written with HTML, CSS, JavaScript, and Three.js.

The project supports:

- Manual Bloxorz gameplay
- Basic and advanced tiles
- 10 JSON test levels
- BFS, DFS, UCS, and A* solvers
- Search metrics
- Search visualization
- Solution replay
- Benchmark results and comparison charts

## 2. Project Structure

```text
Project/
├── algorithms.py
├── app.py
├── benchmark.py
├── board.py
├── constants.py
├── gui.py
├── level_loader.py
├── main.py
├── plot_results.py
├── README.md
├── requirements.txt
├── state.py
│
├── templates/
│   └── index.html
│
├── static/
│   ├── app.js
│   └── style.css
│
├── levels/
│   ├── level_01.json
│   ├── ...
│   └── level_10.json
│
└── results/
    ├── results.csv
    ├── summary.csv
    └── charts/
```

## 3. Requirements

- Python 3
- A modern web browser
- Internet connection when running the web GUI, because Three.js is loaded from the jsDelivr CDN

No external Python package is required.

## 4. How to Run

Open a terminal in the project folder.

### Run tests

```powershell
python main.py
```

### Run the 3D Web GUI

```powershell
python app.py
```

The browser opens automatically at:

```text
http://127.0.0.1:8000
```

You can also run:

```powershell
python gui.py
```

`gui.py` is kept as a compatibility launcher for the same web GUI.

### Run benchmark

```powershell
python benchmark.py
```

This creates:

```text
results/results.csv
results/summary.csv
```

### Generate result charts

```powershell
python plot_results.py
```

The charts are saved in:

```text
results/charts/
```

## 5. Controls

| Control | Action |
|---|---|
| Up Arrow | Move up |
| Down Arrow | Move down |
| Left Arrow | Move left |
| Right Arrow | Move right |
| Space | Switch active cube in split mode |
| Mouse drag | Rotate 3D camera |
| Mouse wheel | Zoom camera |

GUI buttons:

- New Game
- Restart
- Solve BFS
- Solve DFS
- Solve UCS
- Solve A*
- Replay Solution
- Reset Camera

## 6. Tile Symbols

| Symbol | Meaning |
|---|---|
| `0` | Void |
| `1` | Floor |
| `S` | Start |
| `G` | Goal |
| `F` | Fragile tile |
| `B` | Bridge |
| `O` | Soft switch |
| `X` | Heavy switch |
| `T` | Split switch |

## 7. Search Algorithms

- **BFS:** Breadth-First Search
- **DFS:** Depth-First Search
- **UCS:** Uniform-Cost Search using the project's non-uniform cost function
- **A\*:** Search using accumulated path cost and an admissible heuristic

Each solver records:

- Search time
- Peak memory
- Expanded nodes
- Solution length
- Total cost

## 8. Test Cases

The project contains 10 fixed JSON levels. The levels are intentionally designed so that the search algorithms do not always behave the same:

- Open and branching boards make DFS follow long routes while BFS finds shorter solutions.
- Fragile alternative routes can make BFS choose a low-move but higher-cost path, while UCS and A* choose a lower-cost path.
- Large branching rooms allow A* to expand fewer nodes than BFS or UCS.
- Split-switch levels demonstrate the conservative A* heuristic, where A* behaves similarly to UCS because the heuristic returns 0.
- Soft switches, heavy switches, bridges, fragile tiles, and split mechanics are included across the test set.

The same fixed test set is used for BFS, DFS, UCS, and A*.

## 9. Experiments

Run:

```powershell
python benchmark.py
python plot_results.py
```

The benchmark evaluates all 10 levels with BFS, DFS, UCS, and A* over multiple runs.

Generated charts compare:

- Search time
- Peak memory
- Expanded nodes
- Solution length
- Total cost

## 10. References

- Bloxorz gameplay reference: Coolmath Games - Bloxorz  
  https://www.coolmathgames.com/0-bloxorz

- Three.js documentation and 3D rendering library  
  https://threejs.org/

- Three.js CDN installation guidance  
  https://threejs.org/manual/en/installation.html

The project does not reuse an external Bloxorz game source-code implementation. The game logic and search algorithms in this submission are implemented in the project source code. Three.js is used only as a supporting 3D rendering library for the GUI.

## 11. Team Contribution

Update this section before submission.

```text
Member 1:
- Core gameplay
- BFS
- DFS
- Completion: ...%

Member 2:
- Advanced mechanics
- UCS
- Level design
- Completion: ...%

Member 3:
- A*
- 3D Web GUI
- Search visualization
- Solution replay
- Benchmark and charts
- Completion: ...%
```

## 12. Demo Video

YouTube link:

```text
Add the public demo video link here.
```
