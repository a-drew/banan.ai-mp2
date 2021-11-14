#!/usr/bin/env pypy3

# based on code from https://stackabuse.com/minimax-and-alpha-beta-pruning-in-python

import time
import sys
import logging

class OutOfTimeException(Exception):
    pass

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

    def __init__(self, n=3, b=0, s=3, blocs=None, a=None, d1=1000000000, d2=1000000000, t=1000, recommend=True, gametrace_logfile=None):
        self.n = n  # size of board
        self.s = s  # size of winning line
        self.b = b  # size of blocs
        self.blocs = [] if blocs is None else blocs
        self.a = a  # force algorithm, None / True: AlphaBeta, False: MiniMax
        self.d1 = d1  # p1 search depth
        self.d2 = d2  # p2 search depth
        self.t = t  # search timeout
        self.recommend = recommend  # recommend human moves
        self.d1_ctr = 0
        self.d2_ctr = 0
        self.initialize_game()
        self.previous = '?'
        self.repeat_count = 1
        
        if not gametrace_logfile is None:
            logging.basicConfig(filename=gametrace_logfile, level=logging.INFO)
            logging.info('using log file')
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

    def is_vert(self, check_win):
        for x in range(self.n):
            self.previous = 'N'
            for y in range(self.n):
                result = check_win(x, y)
                if result:
                    return result
        return False

    def is_horz(self, check_win):
        for y in range(self.n):
            self.previous = 'N'
            for x in range(self.n):
                result = check_win(x, y)
                if result:
                    return result
        return False

    def is_diag(self, check_win):
        # Main diagonal win (top left to bottom right)
        result = self.is_main_diag(check_win)
        if result:
            return result
        # Second diagonal win (bottom left to top right)
        return self.is_sec_diag(check_win)

    def is_main_diag(self, check_win):
        for d in range(self.max_diag):
            if d < self.split_diag:
                x = (self.n - self.s) - d
                y = 0
            else:
                x = 0
                y = (self.n - self.s) - d

            self.previous = 'N'
            while x < self.n and y < self.n:
                result = check_win(x, y)
                if result:
                    return result
                # continue
                x += 1
                y += 1
        return False

    def is_sec_diag(self, check_win):
        for d in range(self.max_diag):
            if d <= self.split_diag:
                x = 0
                y = (self.s - 1) + d
            else:
                x = d - self.split_diag
                y = self.n - 1
            self.previous = 'N'
            while x < self.n and y >= 0:
                result = check_win(x, y)
                if result:
                    return result
                # continue
                x += 1
                y -= 1
        return False

    def is_full(self):
        for i in range(self.n):
            for j in range(self.n):
                if self.current_state[i][j] == '.':
                    return True
        return False

    def is_end(self):
        def check_win(x, y):
            current = self.current_state[x][y]
            if current == self.previous:
                self.repeat_count += 1
            else:
                self.repeat_count = 1
            if current in ['X', 'O'] and self.repeat_count == self.s:  # we won
                return current
            self.previous = current
            return False

        # Vertical win
        result = self.is_vert(check_win)
        if result:
            return result
        # Horizontal win
        result = self.is_horz(check_win)
        if result:
            return result
        # Diagonal win
        result = self.is_diag(check_win)
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
            if self.result == 'X':
                print('The winner is X!')
            elif self.result == 'O':
                print('The winner is O!')
            elif self.result == '.':
                print("It's a tie!")
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
    '''
    the maximum allowed time (in seconds) for your program to return a move – t
    Your AI should not take more than t seconds to return its move. If it does, your AI will automatically
    lose the game. This entails that even if your adversarial search is allowed to go to a depth of d in the
    game tree, it may not have time to do so every time. Your program must monitor the time, and if not
    enough time is left to explore all the states at depth d, it must interrupt its search at depth d and
    return values for the remaining states quickly before time is up.

    '''

    def minimax(self, max=False, player_type=None, curr_player=None):
        self.d1_ctr = self.d2_ctr = 0  # reset ctrs
        self.start_time = time.time()
        self.player_type = player_type
        return self._minimax(max=max, curr_player=curr_player)

    def _minimax(self, max=False, curr_player=None):
        # Minimizing for 'X' and maximizing for 'O'
        # Possible values are:
        # -1 - win for 'X'
        # 0  - a tie
        # 1  - loss for 'X'
        # We're initially setting it to 2 or -2 as worse than the worst case:

        if curr_player == 'X':
            self.d1_ctr += 1
        elif curr_player == 'O':
            self.d2_ctr += 1

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
        # check if it's been too long
        elif time.time() - self.start_time > self.t and self.player_type == Game.AI:
            # start bubbling up error to eventually be caught above
            raise OutOfTimeException()
        # checks for depths
        elif curr_player == 'X' and self.d1_ctr >= self.d1:
            return (self.eval(), x, y)
        elif curr_player == 'O' and self.d2_ctr >= self.d2:
            return (self.eval(), x, y)

        for i in range(self.n):
            for j in range(self.n):
                if self.current_state[i][j] == '.':
                    if max:
                        self.current_state[i][j] = 'O'
                        (v, _, _) = self._minimax(max=False, curr_player=curr_player)
                        if v > value:
                            value = v
                            x = i
                            y = j
                    else:
                        self.current_state[i][j] = 'X'
                        (v, _, _) = self._minimax(max=True, curr_player=curr_player)
                        if v < value:
                            value = v
                            x = i
                            y = j
                    self.current_state[i][j] = '.'
        return (value, x, y)

    def alphabeta(self, alpha=-2, beta=2, max=False, player_type=None, curr_player=None):
        self.d2_ctr = self.d1_ctr = 0
        self.start_time = time.time()
        self.player_type = player_type

        try:
            return self._alphabeta(alpha=alpha, beta=beta, max=max, curr_player=curr_player)
        except OutOfTimeException as e:
            raise OutOfTimeException(curr_player)


    def _alphabeta(self, alpha=-2, beta=2, max=False, curr_player=None):
        # Minimizing for 'X' and maximizing for 'O'
        # Possible values are:
        # -1 - win for 'X'
        # 0  - a tie
        # 1  - loss for 'X'
        # We're initially setting it to 2 or -2 as worse than the worst case:

        # TODO: there aren't counting depth, these count total iterations rn
        if curr_player == 'X':
            self.d1_ctr += 1
        elif curr_player == 'O':
            self.d2_ctr += 1

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
        # check if it's been too long
        elif time.time() - self.start_time > self.t and self.player_type == Game.AI:
            # start bubbling up error to eventually be caught above
            raise OutOfTimeException()

        # checks for depths
        elif curr_player == 'X' and self.d1_ctr >= self.d1:
            return (self.eval(), x, y)
        elif curr_player == 'O' and self.d2_ctr >= self.d2:
            return (self.eval(), x, y)

        for i in range(self.n):
            for j in range(self.n):
                if self.current_state[i][j] == '.':
                    if max:
                        self.current_state[i][j] = 'O'
                        (v, _, _) = self._alphabeta(alpha, beta, max=False, curr_player=curr_player)
                        if v > value:
                            value = v
                            x = i
                            y = j
                    else:
                        self.current_state[i][j] = 'X'
                        (v, _, _) = self._alphabeta(alpha, beta, max=True, curr_player=curr_player)
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
            try:
                start = time.time()
                if algo == self.MINIMAX:
                    if self.player_turn == 'X':
                        (_, x, y) = self.minimax(max=False, player_type=player_x, curr_player='X')
                    else:
                        (_, x, y) = self.minimax(max=True, player_type=player_o, curr_player='O')
                else:  # algo == self.ALPHABETA
                    if self.player_turn == 'X':
                        (m, x, y) = self.alphabeta(max=False, player_type=player_x, curr_player='X')
                    else:
                        (m, x, y) = self.alphabeta(max=True, player_type=player_o, curr_player='O')
                end = time.time()
                if (self.player_turn == 'X' and player_x == self.HUMAN) or (
                        self.player_turn == 'O' and player_o == self.HUMAN):
                    if self.recommend:
                        print(F'Evaluation time: {round(end - start, 7)}s')
                        print(F'Recommended move: {self.LETTERS[x]}{y}')
                    (x, y) = self.input_move()
                if (self.player_turn == 'X' and player_x == self.AI) or (
                        self.player_turn == 'O' and player_o == self.AI):
                    print(F'Evaluation time: {round(end - start, 7)}s')
                    if player_x == self.HUMAN or player_o == self.HUMAN:
                        print(F'Player {self.player_turn} under AI control plays: {self.LETTERS[x]}{y}')
                    else:
                        print(F'Player {self.player_turn} under AI control plays: x = {x}, y = {y}')
            except OutOfTimeException as e:
                print(F'{e} ran out of time!')
                # TODO: replace with random move
                break
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
