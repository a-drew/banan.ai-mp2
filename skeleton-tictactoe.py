#!/usr/bin/env pypy3

# based on code from https://stackabuse.com/minimax-and-alpha-beta-pruning-in-python

import time
import sys
import logging


class Game:
    LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    MINIMAX = 0
    ALPHABETA = 1
    HUMAN = 2
    AI = 3

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

    def __init__(self, n=3, b=0, s=3, blocs=None, a=None, d1=100, d2=100, t=5, recommend=True, gametrace_logfile=None):
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
       
        if not gametrace_logfile is None:
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
        self.player_turn = 'X'  # Player X always plays first
        self.max_diag = 2 * self.n - 1 - 2 * (self.s - 1)
        self.split_diag = int((self.max_diag - 1) / 2)

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
                    return True
        return False

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
                y = (self.n - self.s) - d

            line = []
            while x < self.n and y < self.n:
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
            while x < self.n and y >= 0:
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
        if self.is_full():
            return None
        # It's a tie!
        return '.'

    def check_end(self):
        self.result = self.is_end()
        # Printing the appropriate message if the game has ended
        if self.result != None:
            if self.result == '.':
                print("It's a tie!")
            else:
                print(F'The winner is {self.result}!')
            self.initialize_game()
        return self.result

    def input_move(self):
        while True:
            word = [c for c in input(F'Player {self.player_turn}, enter your move:')]
            px = ord(word[0].upper()) - 65  # ascii
            py = int(word[1])

            if self.is_valid(px, py):
                return (px, py)
            else:
                print('The move is not valid! Try again.')

    def switch_player(self):
        if self.player_turn == 'X':
            self.player_turn = 'O'
        elif self.player_turn == 'O':
            self.player_turn = 'X'
        return self.player_turn

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
        elif depth and depth <= 0:
            return (self.eval(), x, y)

        next_depth = depth-1 if depth else None
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
        elif depth and depth <= 0:
            return (self.eval(), x, y)

        next_depth = depth-1 if depth else None
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

    def eval(self):
        # @TODO: choosing strategy for whether use h1 or h2
        return 0

    def play(self, algo=None, player_x=None, player_o=None):
        # self.a allows for override of algo
        if algo == None or self.a == True:
            algo = self.ALPHABETA
        if self.a == False:
            algo = self.MINIMAX
        if player_x == None:
            player_x = self.HUMAN
        if player_o == None:
            player_o = self.HUMAN

        #@TODO: make it an option to have the two AI players with different algos
        logging.info('AI algorithm: ' + 'AlphaBeta' if (algo == self.ALPHABETA) else 'Minimax')
        logging.info('')
        logging.info('player X: ' + 'human' if (player_x == self.HUMAN) else 'AI')
        logging.info('vs.')
        logging.info('player O: ' + 'human\n' if (player_o == self.HUMAN) else 'AI\n')

        while True:
            self.draw_board()
            if self.check_end():
                return

            self.search_start = start = time.time()
            if algo == self.MINIMAX:
                (_, x, y) = self.minimax(max=self.player_turn == 'O')
            else:  # algo == self.ALPHABETA
                (m, x, y) = self.alphabeta(max=self.player_turn == 'O')
            t = time.time() - start
            if t > self.t - 0.01:
                print('*** Search ran out of time ***')
                print(F'Selected random move for {self.player_turn}: {self.LETTERS[x]}{y}')
            elif t > self.t:
                print(F'{self.player_turn} lost, they ran out of time!')
                break

            if (self.player_turn == 'X' and player_x == self.HUMAN) or (self.player_turn == 'O' and player_o == self.HUMAN):
                if self.recommend:
                    print(F'Evaluation time: {t}s')
                    print(F'Recommended move: {self.LETTERS[x]}{y}')
                (x, y) = self.input_move()
            if (self.player_turn == 'X' and player_x == self.AI) or (
                    self.player_turn == 'O' and player_o == self.AI):
                print(F'Evaluation time: {t}s')
                if player_x == self.HUMAN or player_o == self.HUMAN:
                    print(F'Player {self.player_turn} under AI control plays: {self.LETTERS[x]}{y}')
                else:
                    print(F'Player {self.player_turn} under AI control plays: x = {x}, y = {y}')
            self.current_state[x][y] = self.player_turn
            self.switch_player()


def main():
    USAGE = 'Either run directly for default parameters: ./lineEmUp.py'
    USAGE += '\nOr with custom parameters: ./lineEmUp.py [-r] -x:[h|a] -o:[h|a] [-a:[a|m]] '
    USAGE += '\n\nIf not specified: \n-a: AI mode will default to ALPHABETA algorithm\n-r: Recommendations will not be shown'
    USAGE += '\n-b: blocks set to 0\n-s:  to 3\n-n: board size set to 3x3'

    # @TODO: add prompt to choose game type
    if len(sys.argv) == 1:
        g = Game(recommend=True)
        g.play(algo=Game.ALPHABETA, player_x=Game.AI, player_o=Game.AI)
        g.play(algo=Game.MINIMAX, player_x=Game.AI, player_o=Game.HUMAN)
    elif len(sys.argv) >= 1:
        if sys.argv[1] == '-h' or sys.argv[1] == '--help':
            print(USAGE)

        # default values
        recommend = False
        args_present = [False, False, False]
        player_x = player_y = algo = None
        s = n = 3
        b = 0
        t = d1 = d2 = 1000000000

        for arg in sys.argv:
            # show recommended moves?
            if '-r' in arg:
                recommend = True
            # set player X
            if '-x:' in arg:
                args_present[0] = True
                player_type_x = arg.split(':')

                if player_type_x[1] == 'h':
                    player_x = Game.HUMAN
                elif player_type_x[1] == 'a':
                    player_x = Game.AI
                else:
                    print('Illegal option for player X type')
                    sys.exit(0)
            # set player O
            if '-o:' in arg:
                args_present[1] = True
                player_type_o = arg.split(':')

                if player_type_o[1] == 'h':
                    player_o = Game.HUMAN
                elif player_type_o[1] == 'a':
                    player_o = Game.AI
                else:
                    print('Illegal option for player O type')
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

        if player_x == Game.HUMAN and player_o == Game.HUMAN:
            args_present[2] = True

        for present in args_present:
            if not present:
                print('Missing required parameters')
                sys.exit(0)


        gametrace_logfile = None

        if player_x == Game.AI and player_o == Game.AI:
            gametrace_logfile = 'gameTrace-' + str(n) + 'n' + str(b) + 'b' + str(s) + 's' + str(t) + 't.txt'
            

        g = Game(recommend=recommend, s=s, b=b, n=n, t=search_time, d1=d1, d2=d2, gametrace_logfile=gametrace_logfile)
        g.play(algo=algo, player_x=player_x, player_o=player_o)


if __name__ == "__main__":
    main()
