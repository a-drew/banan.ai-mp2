#!/usr/bin/env pypy3

# based on code from https://stackabuse.com/minimax-and-alpha-beta-pruning-in-python

import time
import sys
import logging
from itertools import groupby
import random

class TurnStats:
    def __init__(self):
        self.elapsed = 0
        self.end_count = 0
        self.end_cache_hit = 0
        self.eval_count = 0
        self.eval_cache_hit = 0
        self.eval_by_depth = {}
        self.avg_recursion_depth = 0

    @property
    def avg_eval_depth(self):
        sum = 0
        leafs = 0
        for _, (depth, count) in enumerate(self.eval_by_depth.items()):
            sum += depth * count
            leafs += count
        if leafs == 0:
            return 0
        return sum / leafs

    def __str__(self):
        return F'\n' \
            + F'i   Evaluation time: {self.elapsed}s' \
            + F'\nii  Heuristic evaluations: {self.eval_count} (cached:{self.eval_cache_hit})' \
            + F' + Endgames found: {self.end_count} (cached:{self.end_cache_hit})' \
            + F'\niii Evaluations by depth: {self.eval_by_depth}' \
            + F'\niv  Average evaluation depth: {self.avg_eval_depth}' \
            + F'\nv   Average recursion depth: {self.avg_recursion_depth}' \
            + F'\n'

    def summary(self):
        logging.info(self)


class Player:
    MINIMAX = 0
    ALPHABETA = 1
    AI = 0
    HUMAN = 1
    E1 = 0
    E2 = 1

    def __init__(self, symbol='X', t=AI, d=None, h=E1, a=ALPHABETA):
        self.symbol = symbol
        self.human = t
        self.depth = d
        self.heuristic = h
        self.algo = a

    def __str__(self):
        return self.symbol

    def is_ai(self):
        return self.human == Player.AI

    def is_human(self):
        return self.human == Player.HUMAN

    def use_minimax(self):
        return self.algo == Game.MINIMAX

    def use_alphabeta(self):
        return self.algo == Game.ALPHABETA

    def use_e1(self):
        return self.heuristic == Player.E1

    def use_e2(self):
        return self.algo == Player.E2

    def summary(self):
        if self.human:
            t = 'HUMAN'
        else:
            t = 'AI'
        if self.heuristic:
            h = 'e2(defensive)'
        else:
            h = 'e1(aggressive)'
        if self.algo:
            a = 'alphabeta'
        else:
            a = 'minimax'

        logging.info(F'Player {self.symbol}: {t} d={self.depth} a={a} {h}')


class Game:
    LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    MINIMAX = 0
    ALPHABETA = 1

    # (a) the n of the board – n – an integer in [3..10]
    # (b) the number of blocs – b – an integer in [0..2n]
    # (c) the positions of the blocs – b board coordinates
    # (d) the winning line-up n – s – an integer in [3..n]
    # (e) the maximum depth of the adversarial search for player 1 and for player 2 – 2 integers d1 and d2
    # (f) the maximum allowed time (in seconds) for your program to return a move – t
    # Your AI should not take more than t seconds to return its move. If it does, your AI will automatically
    # lose the game. This entails that even if your adversarial search is allowed to go to a depth of d in the
    # game tree, it may not have time to do so every time. Your program must monitor the time, and if not
    # enough time is left to explore all the states at depth d, it must interrupt its search at depth d and
    # return values for the remaining states quickly before time is up.
    # (g) a Boolean to force the use of either minimax (FALSE) or alphabeta (TRUE) – a
    # (h) the play modes, didn't add since w=they are controlled directly in Game.play()
    # Your program should be able to make either player be a human or the AI. This means that you should
    # be able to run your program in all 4 combinations of players: H-H, H-AI, AI-H and AI-AI

    def __init__(self, n=3, b=0, s=3, blocs=None, a=None, d1=5, d2=5, t=10, recommend=True,
                 gametrace_logfile=None):
        self.n = n  # size of board
        self.s = s  # size of winning line
        self.b = b  # size of blocs
        self.blocs = [] if blocs is None else blocs
        self.a = a  # force algorithm, None / True: AlphaBeta, False: MiniMax
        self.d1 = d1  # p1 search depth
        self.d2 = d2  # p2 search depth
        self.t = t  # search timeout
        self.leeway = 0.01
        self.recommend = recommend  # recommend human moves
        # helpers for determining diagonals to read
        self.max_diag = 2 * self.n - 1 - 2 * (self.s - 1)
        self.split_diag = int((self.max_diag - 1) / 2)

        if gametrace_logfile is not None:
            logging.basicConfig(level=logging.INFO, format='%(message)s', filename=gametrace_logfile, filemode='w')
            console = logging.StreamHandler()
            console.setLevel(logging.INFO)

            logging.getLogger().addHandler(console)
            logging.debug('DEBUG: gametrace will be written to ' + gametrace_logfile)
        else:
            # print info level logging to console
            logging.basicConfig(level=logging.DEBUG, format='%(message)s')
            logging.debug('DEBUG: gametrace output is disabled!')

        self.initialize_game()

    def tweak(self, d1=2, d2=6, a=True, blocs=None):
        self.d1 = d1
        self.d2 = d2
        self.a = a
        self.blocs = [] if blocs is None else blocs

    def __str__(self):
        return F'n: {self.n} b: {self.b} s: {self.s} t: {self.t} \nblocs: {self.blocs} \nrecommend: {self.recommend}'

    def validate(self):
        if self.n > 10 or self.n < 3:
            raise Exception("Invalid board size")
        if self.b != len(self.blocs):
            self.b = len(self.blocs)
        if self.b > 2 * self.n:
            raise Exception("Too many blocs")
        if self.s > self.n:
            raise Exception("Invalid size of winning line")

    def initialize_game(self):
        self.validate()
        board = []
        for y in range(self.n):
            row = []
            for x in range(self.n):
                for bloc in self.blocs:
                    if type(bloc) is str or (type(bloc) is tuple and type(bloc[0]) is str):
                        bloc = (ord(bloc[0].upper()) - 65, int(bloc[1]))
                    if type(bloc) is tuple and type(bloc[1]) is str:
                        # I don't like the weird (2, 'D') syntax so let's invert it back
                        bloc = (ord(bloc[1].upper()) - 65, int(bloc[0]))
                    # inverted for check, but api supports (x,y) or 'XY' or ('X', y) or (y, 'X')
                    if bloc == (y, x):
                        row.append('*')
                        break
                else:
                    row.append('.')
            board.append(row)
        self.current_state = board
        # cache board evaluations
        self.state_end = {}
        self.state_lines = {}
        self.state_eval1 = {}
        self.state_eval2 = {}
        # winning lines
        self.xs = 'X' * self.s
        self.os = 'O' * self.s
        logging.info(self)

    def draw_board(self, board=None):
        if board is None:
            board = self.current_state
        size = self.n

        buffer = ''
        buffer += "  " + "".join(self.LETTERS[:size]) + '\n'
        buffer += " +" + "".join(['-' for x in range(size)]) + '\n'

        for y in range(size):
            buffer += F'{y}|'
            for x in range(size):
                buffer += F'{board[x][y]}'
            buffer += '\n'
        buffer += '\n'

        logging.info(buffer)

    def is_valid(self, px, py):
        if px < 0 or px >= self.n or py < 0 or py >= self.n:
            return False
        elif self.current_state[px][py] != '.':
            return False
        else:
            return True

    def read_all_lines(self, callback=None):
        state_str = str(self.current_state)
        if callback is None and state_str in self.state_lines:
            return self.state_lines[state_str]
        lines = []
        # Horizontal & Vertical
        for x in range(self.n):
            row = []
            col = []
            for y in range(self.n):
                row.append(self.current_state[y][x])
                col.append(self.current_state[x][y])
            lines.append(row)
            lines.append(col)
            if callback:
                result = callback(col)
                if result:
                    return result
                result = callback(row)
                if result:
                    return result
        # Main Diagonal
        for d in range(self.max_diag):
            if d < self.split_diag:
                x = (self.n - self.s) - d
                y = 0
            else:
                x = 0
                y = d - self.split_diag

            line = []
            while 0 <= x < self.n and 0 <= y < self.n:
                line.append(self.current_state[x][y])
                x += 1
                y += 1
            lines.append(line)
            if callback:
                result = callback(line)
                if result:
                    return result
        # Second Diagonal
        for d in range(self.max_diag):
            if d <= self.split_diag:
                x = 0
                y = (self.s - 1) + d
            else:
                x = d - self.split_diag
                y = self.n - 1
            line = []
            while 0 <= x < self.n and 0 <= y < self.n:
                line.append(self.current_state[x][y])
                x += 1
                y -= 1
            lines.append(line)
            if callback:
                result = callback(line)
                if result:
                    return result
        self.state_lines[state_str] = lines
        if callback:
            return False
        return lines

    def is_full(self):
        for line in self.read_all_lines():
            if '.' in line:
                return False
        return True

    def is_end(self, depth=None):
        state_str = str(self.current_state)
        if state_str in self.state_end:
            # count is_end evaluations if they reach an endgame state
            result = self.state_end[state_str]
            if result is not None:
                self.turn_stats.end_count += 1
                self.turn_stats.end_cache_hit += 1
                if depth in self.turn_stats.eval_by_depth:
                    self.turn_stats.eval_by_depth[depth] += 1
                elif depth:
                    self.turn_stats.eval_by_depth[depth] = 1
            return result

        def check_win(line):
            line = ''.join(line)
            if self.xs in line:
                return 'X'
            elif self.os in line:
                return 'O'

        result = self.read_all_lines(check_win)
        if result:
            # count is_end evaluations if they reach an endgame state
            self.turn_stats.end_count += 1
            if depth in self.turn_stats.eval_by_depth:
                self.turn_stats.eval_by_depth[depth] += 1
            elif depth:
                self.turn_stats.eval_by_depth[depth] = 1
            self.state_end[state_str] = result
            return result
        # Is whole board full?
        if self.is_full():
            result = '.'  # It's a tie!
        else:
            result = None  # continue game

        self.state_end[state_str] = result
        return result

    def check_end(self):
        self.result = self.is_end()
        # Printing the appropriate message if the game has ended
        if self.result != None:
            if self.result == '.':
                logging.info("It's a tie!")
            else:
                logging.info(F'The winner is {self.result}!')
            self.initialize_game()
        return self.result

    def input_move(self):
        while True:
            word = [c for c in input(F'Player {self.active_player}, enter your move:')]
            px = ord(word[0].upper()) - 65  # ascii
            py = int(word[1])

            if self.is_valid(px, py):
                return (px, py)
            else:
                logging.info('The move is not valid! Try again.')

    def switch_player(self):
        if self.active_player == self.player_x:
            self.active_player = self.player_o
        elif self.active_player == self.player_o:
            self.active_player = self.player_x
        return self.active_player

    # f)
    # the maximum allowed time (in seconds) for your program to return a move – t
    # Your AI should not take more than t seconds to return its move. If it does, your AI will automatically
    # lose the game. This entails that even if your adversarial search is allowed to go to a depth of d in the
    # game tree, it may not have time to do so every time. Your program must monitor the time, and if not
    # enough time is left to explore all the states at depth d, it must interrupt its search at depth d and
    # return values for the remaining states quickly before time is up.

    def minimax(self, max=False, depth=None):
        # Minimizing for 'X' and maximizing for 'O'
        # Possible values are:
        # -1 - win for 'X'
        # 0  - a tie
        # 1  - loss for 'X'
        # We're initially setting it to 2 or -2 as worse than the worst case:

        value = 2
        if max:
            value = -2
        x = None
        y = None
        result = self.is_end(self.max_depth - depth)

        if result == 'X':
            return -1, x, y, self.max_depth - depth
        elif result == 'O':
            return 1, x, y, self.max_depth - depth
        elif result == '.':
            return 0, x, y, self.max_depth - depth
        elif time.time() - self.search_start > self.t - self.leeway or (depth is not None and depth <= 0):
            return self.eval(max, depth), x, y, self.max_depth - depth

        children = []
        next_depth = depth - 1 if depth else self.active_player.depth
        for i in range(self.n):
            for j in range(self.n):
                if self.current_state[i][j] == '.':
                    if max:
                        self.current_state[i][j] = 'O'
                        (v, _, _, adr) = self.minimax(max=False, depth=next_depth)
                        if v > value:
                            value = v
                            x = i
                            y = j
                    else:
                        self.current_state[i][j] = 'X'
                        (v, _, _, adr) = self.minimax(max=True, depth=next_depth)
                        if v < value:
                            value = v
                            x = i
                            y = j
                    self.current_state[i][j] = '.'
                    children.append(adr)
        return value, x, y, sum(children) / len(children)

    def alphabeta(self, alpha=-2, beta=2, max=False, depth=None):
        # Minimizing for 'X' and maximizing for 'O'
        # Possible values are:
        # -1 - win for 'X'
        # 0  - a tie
        # 1  - loss for 'X'
        # We're initially setting it to 2 or -2 as worse than the worst case:

        value = 2
        if max:
            value = -2
        x = None
        y = None
        result = self.is_end(self.max_depth - depth)

        if result == 'X':
            return -1, x, y, self.max_depth - depth
        elif result == 'O':
            return 1, x, y, self.max_depth - depth
        elif result == '.':
            return 0, x, y, self.max_depth - depth
        elif time.time() - self.search_start > self.t - self.leeway or (depth is not None and depth <= 0):
            return self.eval(max, depth), x, y, self.max_depth - depth

        children = []
        next_depth = depth - 1 if depth else self.active_player.depth
        for i in range(self.n):
            for j in range(self.n):
                if self.current_state[i][j] == '.':
                    if max:
                        self.current_state[i][j] = 'O'
                        (v, _, _, adr) = self.alphabeta(alpha, beta, max=False, depth=next_depth)
                        if v > value:
                            value = v
                            x = i
                            y = j
                    else:
                        self.current_state[i][j] = 'X'
                        (v, _, _, adr) = self.alphabeta(alpha, beta, max=True, depth=next_depth)
                        if v < value:
                            value = v
                            x = i
                            y = j
                    self.current_state[i][j] = '.'
                    children.append(adr)
                    if max:
                        if value >= beta:
                            return value, x, y, sum(children) / len(children)
                        if value > alpha:
                            alpha = value
                    else:
                        if value <= alpha:
                            return value, x, y, sum(children) / len(children)
                        if value < beta:
                            beta = value
        return value, x, y, sum(children) / len(children)

    # prioritize chaining and building bigger lines
    def e1(self, maximize=None, depth=0):
        # resize the score to the -1 to +1 range
        def clamp(number):
            return number / 10 ** self.s

        # use depth to prioritize less moves
        if maximize is None:
            depth = 0
        elif not maximize:
            depth = -depth

        state_str = str(self.current_state)
        if state_str in self.state_eval1:
            self.turn_stats.eval_cache_hit += 1
            return clamp(self.state_eval1[state_str] + depth)
        score = 0
        for line in self.read_all_lines():
            # favor lines without blocks
            if 'X*' in line or '*X' in line:
                score += 5
            if 'O*' in line or '*O' in line:
                score -= 5
            groups = groupby(line)
            for label, group in groups:
                count = sum(1 for _ in group)
                if label == 'O':
                    score += 10 ** count
                elif label == 'X':
                    score -= 10 ** count
        self.state_eval1[state_str] = score
        return clamp(score + depth)

    # prioritize blocking the other (X) player
    def e2(self):
        score = 0
        total_lines = self.n * 2 - 1
        # assuming downwards pointing arrows
        UNIT = 100 ** (-1 * self.s)  # @TODO: scale down based on s -> *10^(-s)
        BLOCK_WEIGHT = 5

        lines = self.read_all_lines()

        for line in lines:
            prev = '?'
            for curr in line:
                if curr == prev and curr == 'X':
                    score -= UNIT
                if curr == prev and curr == 'O':
                    score += UNIT
                elif not (curr == prev):
                    score += UNIT * BLOCK_WEIGHT
            prev = '?'
            for curr in reversed(line):
                if curr == prev and curr == 'X':
                    score -= UNIT
                if curr == prev and curr == 'O':
                    score += UNIT
                elif not (curr == prev):
                    score += UNIT * BLOCK_WEIGHT

        return score

    def eval(self, maximize, depth):
        real_depth = self.max_depth - depth
        self.turn_stats.eval_count += 1
        if real_depth in self.turn_stats.eval_by_depth:
            self.turn_stats.eval_by_depth[real_depth] += 1
        else:
            self.turn_stats.eval_by_depth[real_depth] = 1
        if self.active_player.heuristic == Player.E1:
            return self.e1(maximize, depth)
        elif self.active_player.heuristic == Player.E2:
            return self.e2()

    def play(self, algo=None, player_x=Player('X'), player_o=Player('O')):
        # self.a allows for override of algo
        if self.a == True:
            algo = self.ALPHABETA
        if self.a == False:
            algo = self.MINIMAX

        # algo will override the player's algo
        if algo is not None:
            player_x.algo = algo
            player_o.algo = algo
        # player set depth will prevail over game settings
        if player_x.depth is None:
            player_x.depth = self.d1
        if player_o.depth is None:
            player_o.depth = self.d2

        # player X always goes first
        self.active_player = self.player_x = player_x
        self.player_o = player_o

        player_x.summary()
        player_o.summary()
        logging.info(F'\n')

        while True:
            self.draw_board()

            if self.check_end():
                return

            x = y = -1
            if self.recommend or self.active_player.is_ai():
                self.turn_stats = TurnStats()
                self.search_start = start = time.time()
                max = self.active_player == player_o
                self.max_depth = depth = self.active_player.depth
                if self.active_player.use_minimax():
                    (m, x, y, adr) = self.minimax(max=max, depth=depth)
                else:  # algo == self.ALPHABETA
                    (m, x, y, adr) = self.alphabeta(max=max, depth=depth)
                self.turn_stats.elapsed = t = time.time() - start
                self.turn_stats.avg_recursion_depth = adr
                if self.active_player.is_ai() and t >= self.t:
                    logging.info(F'{self.active_player} lost, they ran out of time!')
                    break
                elif self.t > t > self.t - 0.1:
                    logging.info('*** Search ran out of time ***')
                    logging.info(F'Selected random move for {self.active_player}: {self.LETTERS[x]}{y}')

                if self.active_player.is_ai():
                    logging.info(
                        F'Player {self.active_player} under AI control plays: {self.LETTERS[x]}{y} (score: {m})')
                elif self.recommend:
                    logging.info(F'Recommended move: {self.LETTERS[x]}{y} (score: {m})')
                self.turn_stats.summary()

            if self.active_player.is_human():
                (x, y) = self.input_move()

            self.current_state[x][y] = self.active_player.symbol
            self.switch_player()


def main():
    USAGE = 'Either run directly for default parameters: ./lineEmUp.py'
    USAGE += '\nOr with custom parameters: ./lineEmUp.py [-r] -x:[h|a] -o:[h|a] [-a:[a|m]] '
    USAGE += '\n\nIf not specified: \n-a: AI mode will default to ALPHABETA algorithm\n-r: Recommendations will not be shown'
    USAGE += '\n-b: blocks set to 0\n-s:  to 3\n-n: board size set to 3x3'

    print('sys.argv', sys.argv)

    # @TODO: add prompt to choose game type
    if len(sys.argv) == 1:
        # g = Game(n=5, s=3, blocs=['B1', 'a2', 'C1', 'A5', 'E1', 'D2', 'B4', 'A0', 'A3', 'C4'], recommend=True)
        g = Game(n=5, s=4, blocs=[(2, 3)], t=8, d1=4, d2=8)
        g.play(algo=Game.ALPHABETA, player_x=Player('X', t=Player.HUMAN), player_o=Player('O', t=Player.HUMAN))
        g.play(algo=Game.MINIMAX, player_x=Player('X', t=Player.AI), player_o=Player('O', t=Player.HUMAN))
    elif len(sys.argv) >= 1:
        if sys.argv[1] == '-h' or sys.argv[1] == '--help':
            print(USAGE)
        #: n=4, b=4, s=3, t=5
        #[(0,0),(0,4),(4,0),(4,4)]
        for arg in sys.argv:
            if '--tournament' in arg and len(arg.split(':')) >= 2:
                r = int(arg.split(':')[1])
                dr = r * 2

                blocs=['A0', 'A3', 'D0', 'D3']
                g = Game(n=4, s=3, t=5, b=4, d1=2, d2=6, gametrace_logfile='scoreboard.txt', blocs=blocs)
                player_x = Player('X', t=Player.AI, a=Game.MINIMAX, h=Player.E1)
                player_o = Player('O', t=Player.AI, a=Game.MINIMAX, h=Player.E2)

                logging.info('\n\nFIRST HALF')

                x_wins = 0 # represents heuristic 1
                o_wins = 0 # represents heuristic 2
                ties = 0

                for i in range(r):
                    if i % 2 == 0:
                        g.play(algo=Game.ALPHABETA, player_x=player_x, player_o=player_o)
                    else:
                        g.play(algo=Game.ALPHABETA, player_x=player_o, player_o=player_x)

                    result = g.result

                    if result == 'X':
                        x_wins += 1
                    elif result == 'O':
                        o_wins += 1
                    else:
                        ties += 1


                logging.info('\n\nSECOND HALF')

                for i in range(r):
                    # generate random blocs
                    blocs = []

                    while len(blocs) < 4:
                        x = chr(random.randint(65, 69))
                        y = random.randint(0,3)
                        coord = str(x) + str(y)
                        print('coord', coord)

                        if not coord in blocs:
                            blocs.append(coord)

                    g.tweak(blocs=blocs)

                    if i % 2 == 0:
                        g.play(algo=Game.ALPHABETA, player_x=player_x, player_o=player_o)
                    else:
                        g.play(algo=Game.ALPHABETA, player_x=player_o, player_o=player_x)


                    result = g.result

                    if result == 'X':
                        x_wins += 1
                    elif result == 'O':
                        o_wins += 1
                    else:
                        ties += 1

                h1_winrate = x_wins / (2 * r) * 100
                h2_winrate = o_wins / (2 * r) * 100

                logging.info('\n\n--- SCOREBOARD SUMMARY ---\ntotal games played: ' + str(r * 2))
                logging.info('h1 winrate: ' + str(h1_winrate) + '%')
                logging.info('h2 winrate: ' + str(h2_winrate) + '%')
                logging.info('number of ties: ' + str(ties))

                sys.exit(0)

        # default values
        recommend = False
        args_present = [False, False, False]
        player_x = player_y = None
        algo_x = algo_y = Game.ALPHABETA
        s = n = 3
        b = 0
        d1 = d2 = 10
        t = 5

        for arg in sys.argv:
            # show recommended moves?
            if '-r' in arg:
                recommend = True
            # set player X
            if '-x:' in arg:
                args_present[0] = True
                player_type_x = arg.split(':')

                if player_type_x[1] == 'h':
                    player_x = Player.HUMAN
                elif player_type_x[1] == 'a':
                    player_x = Player.AI

                    if len(player_type_x) >= 3:
                        algo_x = player_type_x[2]
                    else:
                        algo_x = Game.ALPHABETA
                else:
                    logging.info('Illegal option for player X type')
                    sys.exit(0)

            # set player O
            if '-o:' in arg:
                args_present[1] = True
                player_type_o = arg.split(':')

                if player_type_o[1] == 'h':
                    player_o = Player.HUMAN
                elif player_type_o[1] == 'a':
                    player_o = Player.AI

                    if len(player_type_o) >= 3:
                        algo_o = player_type_x[2]
                    else:
                        algo_o = Game.ALPHABETA

                else:
                    logging.info('Illegal option for player O type')
                    sys.exit(0)

            if '-n:' in arg:
                n = int(arg.split(':')[1])
            if '-b:' in arg:
                b = int(arg.split(':')[1])
            if '-s:' in arg:
                s = int(arg.split(':')[1])
            if '-a:' in arg:
                args_present[2] = True
                algo_type = arg.split(':')[1]

                if algo_type == 'a':
                    algo = Game.ALPHABETA
                elif algo_type == 'm':
                    algo = Game.MINIMAX
            if '-t:' in arg:
                search_time = int(arg.split(':')[1])
            if '-d1:' in arg:
                d1 = int(arg.split(':')[1])
            if '-d2:' in arg:
                d2 = int(arg.split(':')[1])

        if player_x == Player.HUMAN and player_o == Player.HUMAN:
            args_present[2] = True

        for present in args_present:
            if not present:
                logging.info('Missing required parameters')
                sys.exit(0)

        gametrace_logfile = None

        if player_x == Player.AI and player_o == Player.AI:
            gametrace_logfile = 'gameTrace-' + str(n) + 'n' + str(b) + 'b' + str(s) + 's' + str(t) + 't.txt'

        g = Game(recommend=recommend, s=s, b=b, n=n, t=search_time, d1=d1, d2=d2, gametrace_logfile=gametrace_logfile)
        g.play(player_x=Player('X', t=player_x, a=algo_x), player_o=Player('O', t=player_o, a=algo_y))


if __name__ == "__main__":
    main()
