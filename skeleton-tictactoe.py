#!/usr/bin/env pypy3

# based on code from https://stackabuse.com/minimax-and-alpha-beta-pruning-in-python

import time
import sys
import logging
from itertools import groupby


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

    def __init__(self, n=3, b=0, s=3, blocs=None, a=None, d1=10, d2=10, t=15, recommend=True, gametrace_logfile=None):
        self.n = n  # size of board
        self.s = s  # size of winning line
        self.b = b  # size of blocs
        self.blocs = [] if blocs is None else blocs
        self.a = a  # force algorithm, None / True: AlphaBeta, False: MiniMax
        self.d1 = d1  # p1 search depth
        self.d2 = d2  # p2 search depth
        self.t = t  # search timeout
        self.recommend = recommend  # recommend human moves
        self.initialize_game()
        # helpers for determining diagonals to read
        self.max_diag = 2 * self.n - 1 - 2 * (self.s - 1)
        self.split_diag = int((self.max_diag - 1) / 2)

        if gametrace_logfile is not None:
            logging.basicConfig(level=logging.INFO,
                                format='%(message)s',
                                filename=gametrace_logfile,
                                filemode='w')
            console = logging.StreamHandler()
            console.setLevel(logging.INFO)
            logging.getLogger().addHandler(console)
            logging.info('using log file: ' + gametrace_logfile)
        else:
            # print info level logging to console
            logging.basicConfig(level=logging.INFO, format='%(message)s')
            logging.info('not using log file')

        # print/log initial configuration info
        ## game params
        logging.info('n: ' + str(self.n))
        logging.info('b: ' + str(self.b))
        logging.info('s: ' + str(self.s))
        logging.info('t: ' + str(self.t))
        ## position of blocs
        logging.info('blocs: ' + str(blocs))

        ## parameters of each player (others in 'play' method)
        logging.info('d1: ' + str(self.d1))
        logging.info('d2: ' + str(self.d2))
        logging.info('recommendations enabled: ' + str(recommend))

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

    def draw_board(self):
        print("  " + "".join(self.LETTERS[:self.n]))
        print(" +" + "".join(['-' for x in range(self.n)]))
        for y in range(self.n):
            print(F'{y}|', end="")
            for x in range(self.n):
                print(F'{self.current_state[x][y]}', end="")
            print()
        print()

    def is_valid(self, px, py):
        if px < 0 or px >= self.n or py < 0 or py >= self.n:
            return False
        elif self.current_state[px][py] != '.':
            return False
        else:
            return True

    def is_full(self):
        for i in range(self.n):
            for j in range(self.n):
                if self.current_state[i][j] == '.':
                    return False
        return True

    def read_all_lines(self, callback=None):
        lines = []
        # Horizontal & Vertical
        for x in range(self.n):
            row = []
            col = []
            for y in range(self.n):
                row.append(self.current_state[y][x])
                col.append(self.current_state[x][y])
            if callback:
                result = callback(col)
                if result:
                    return result
                result = callback(row)
                if result:
                    return result
            else:
                lines.append(row)
                lines.append(col)
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
            if callback:
                result = callback(line)
                if result:
                    return result
            else:
                lines.append(line)
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
            if callback:
                result = callback(line)
                if result:
                    return result
            else:
                lines.append(line)
        if callback:
            return False
        return lines

    def is_end(self):
        xs = 'X' * self.s
        os = 'O' * self.s

        def check_win(line):
            nonlocal xs, os
            line = ''.join(line)
            if xs in line:
                return 'X'
            elif os in line:
                return 'O'

        result = self.read_all_lines(check_win)
        if result:
            return result
        # Is whole board full?
        if not self.is_full():
            return None
        # It's a tie!
        return '.'

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
        result = self.is_end()
        if result == 'X':
            return (-1, x, y)
        elif result == 'O':
            return (1, x, y)
        elif result == '.':
            return (0, x, y)
        elif time.time() - self.search_start > self.t - 0.01:
            return (self.eval(), x, y)
        elif depth is not None and depth <= 0:
            return (self.eval(), x, y)

        next_depth = depth - 1 if depth else self.active_player.depth
        for i in range(self.n):
            for j in range(self.n):
                if self.current_state[i][j] == '.':
                    if max:
                        self.current_state[i][j] = 'O'
                        (v, _, _) = self.minimax(max=False, depth=next_depth)
                        if v > value:
                            value = v
                            x = i
                            y = j
                    else:
                        self.current_state[i][j] = 'X'
                        (v, _, _) = self.minimax(max=True, depth=next_depth)
                        if v < value:
                            value = v
                            x = i
                            y = j
                    self.current_state[i][j] = '.'
        return (value, x, y)

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
        result = self.is_end()

        if result == 'X':
            return (-1, x, y)
        elif result == 'O':
            return (1, x, y)
        elif result == '.':
            return (0, x, y)
        elif time.time() - self.search_start > self.t - 0.01:
            return (self.eval(), x, y)
        elif depth is not None and depth <= 0:
            return (self.eval(), x, y)

        next_depth = depth - 1 if depth else self.active_player.depth
        for i in range(self.n):
            for j in range(self.n):
                if self.current_state[i][j] == '.':
                    if max:
                        self.current_state[i][j] = 'O'
                        (v, _, _) = self.alphabeta(alpha, beta, max=False, depth=next_depth)
                        if v > value:
                            value = v
                            x = i
                            y = j
                    else:
                        self.current_state[i][j] = 'X'
                        (v, _, _) = self.alphabeta(alpha, beta, max=True, depth=next_depth)
                        if v < value:
                            value = v
                            x = i
                            y = j
                    self.current_state[i][j] = '.'
                    if max:
                        if value >= beta:
                            return (value, x, y)
                        if value > alpha:
                            alpha = value
                    else:
                        if value <= alpha:
                            return (value, x, y)
                        if value < beta:
                            beta = value
        return (value, x, y)

    def e1(self):
        score = 0
        available_moves = 0
        for line in self.read_all_lines():
            groups = groupby(line)
            for label, group in groups:
                count = sum(1 for _ in group)
                if label == '.':
                    available_moves += 1
                elif label == 'O':
                    score += 10 ** count
                elif label == 'X':
                    score -= 10 ** count
        if available_moves == 0:
            return -1  # a tie is basically a loss
        clamp_score = score / 10 ** self.s
        return clamp_score

    # prioritize blocking the other (X) player
    def e2(self):
        score = 0
        total_lines = self.n * 2 - 1
        # assuming downwards pointing arrows
        diagonals_rl = [[] for i in range(total_lines)]
        diagonals_lr = [[] for i in range(total_lines)]
        UNIT = 10 ** (-1 * self.s) # @TODO: scale down based on s -> *10^(-s)

        # vertical check
        for x in range(len(self.current_state)):
            prev = '?'
            for y in range(len(self.current_state)):
                #print(str(x) + ':' + str(y) + ' -> ' + str(self.current_state[x][y]))
                curr = self.current_state[x][y]
                diagonals_rl[x + y].append(self.current_state[x][y])
                diagonals_lr[(self.n - 1) + x - y].append(self.current_state[x][y])

                if curr == 'X' and prev == 'O' or curr == 'O' and prev == 'X':
                    score += UNIT
                elif curr == 'O' and prev == curr:
                    score += UNIT
                elif curr == 'X' and prev == curr:
                    score -= UNIT
                prev = curr

        #print('diagonals_rl', diagonals_rl)
        #print('diagonals_lr', diagonals_lr)

        # horizontal check
        for x in range(len(self.current_state)):
            prev = '?'
            for y in range(len(self.current_state)):
                print(str(y) + ':' + str(x) + ' -> ' + str(self.current_state[y][x]))
                curr = self.current_state[y][x]

                if curr == 'X' and prev == 'O' or curr == 'O' and prev == 'X':
                    score += UNIT
                elif curr == 'O' and prev == curr:
                    score += UNIT
                elif curr == 'X' and prev == curr:
                    score -= UNIT
                prev = curr

        # diagonal check (merge first, then prune)
        diagonals = []

        for d in diagonals_lr:
            if len(d) >= self.s:
                diagonals.append(d)

        for d in diagonals_rl:
            if len(d) >= self.s:
                diagonals.append(d)

        #print('diagonals', diagonals)

        for i in range(len(diagonals)):
            prev = '?'
            for j in range(len(diagonals[i])):
                curr = self.current_state[y][x]

                if curr == 'X' and prev == 'O' or curr == 'O' and prev == 'X':
                    score += UNIT
                elif curr == 'O' and prev == curr:
                    score += UNIT
                elif curr == 'X' and prev == curr:
                    score -= UNIT
                prev = curr
        return score

    def eval(self):
        # @TODO: choosing strategy for whether use e1 or e2
        return self.e1()

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
        self.active_player = player_x
        self.player_x = player_x
        self.player_o = player_o

        player_x.summary()
        player_o.summary()

        while True:
            self.draw_board()

            if self.check_end():
                return

            self.search_start = start = time.time()
            max = self.active_player == player_o
            depth = (self.d2 if max else self.d1)
            if self.active_player.use_minimax():
                (m, x, y) = self.minimax(max=max, depth=depth)
            else:  # algo == self.ALPHABETA
                (m, x, y) = self.alphabeta(max=max, depth=depth)
            t = time.time() - start
            if t > self.t - 0.01:
                logging.info('*** Search ran out of time ***')
                logging.info(F'Selected random move for {self.active_player}: {self.LETTERS[x]}{y}')
            elif t > self.t:
                logging.info(F'{self.active_player} lost, they ran out of time!')
                break

            if self.active_player.is_human():
                if self.recommend:
                    logging.info(F'Evaluation time: {t}s')
                    logging.info(F'Recommended move: {self.LETTERS[x]}{y} (score: {m})')
                (x, y) = self.input_move()
            if self.active_player.is_ai():
                logging.info(F'Evaluation time: {t}s')
                logging.info(F'Player {self.active_player} under AI control plays: {self.LETTERS[x]}{y} (score: {m})')
            self.current_state[x][y] = self.active_player.symbol
            self.switch_player()


def main():
    USAGE = 'Either run directly for default parameters: ./lineEmUp.py'
    USAGE += '\nOr with custom parameters: ./lineEmUp.py [-r] -x:[h|a] -o:[h|a] [-a:[a|m]] '
    USAGE += '\n\nIf not specified: \n-a: AI mode will default to ALPHABETA algorithm\n-r: Recommendations will not be shown'
    USAGE += '\n-b: blocks set to 0\n-s:  to 3\n-n: board size set to 3x3'

    # @TODO: add prompt to choose game type
    if len(sys.argv) == 1:
        g = Game(recommend=True)
        g.play(algo=Game.ALPHABETA, player_x=Player('X', t=Player.AI), player_o=Player('O', t=Player.AI))
        g.play(algo=Game.MINIMAX, player_x=Player('X', t=Player.AI), player_o=Player('O', t=Player.HUMAN))
    elif len(sys.argv) >= 1:
        if sys.argv[1] == '-h' or sys.argv[1] == '--help':
            print(USAGE)

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
