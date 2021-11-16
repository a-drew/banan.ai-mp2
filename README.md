# MP2

## team: banana.ai

### Setup

1. Ensure you have the `pypy` runtime installed, running on Python 3.7, as well as the `pip` package manager.
2. Install python required packages, run from root folder: `pip install -r requirements.txt`

### How to run

- run `./lineEmUp.py --help` to see command line options

### Analysis

#### Heuristics

The 2 separate heuristics functions developed were done so that h1 would outperform h2. Both functions take advantage of a helper method which returns an array of arrays, each representing the elements in a line: horizontally, vertically, and diagonally. A simple caching system implemented allows for end game calculations and heuristic evaluations to be sped up.

##### h1

The h1 function focuses on an aggressive approach to solving the problem.


##### h2

The h2 function employs a simple approach which focuses on a more defensive strategy overall. While analyzing the board and computing scores, more weight is placed on boards that showed more "blocking" moves made.

Essentially the algorithm simply looks at each line (horizontally, vertically, diagonally) and runs through each element one by one, once for each direction. The only thing that is kept track of is the current and previous value. Priority is given to state changes from `X` to `O`, and vice versa.

Since this heuristic only accounts for some basic checking, and does not use the depth or maximizing information, it is easily outperformed by the h1 heuristic.
