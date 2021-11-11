#!/usr/bin/env pypy3

# based on code from https://stackabuse.com/minimax-and-alpha-beta-pruning-in-python

import time
import sys

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

    def __init__(self, n=3, b=0, s=3, blocs=None, a=None, d1=1, d2=1, t=1000, recommend=True):
        self.n = n  # size of board
        self.s = s  # size of winning line
        self.b = b  # size of blocs
        self.blocs = [] if blocs is None else blocs
        self.a = a  # force algorithm, None / True: AlphaBeta, False: MiniMax
        self.d1 = d1  # p1 search depth
        self.d2 = d2  # p2 search depth
        self.t = t    # search timeout
        self.recommend = recommend  # recommend human moves
        self.initialize_game()

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
        # Player X always plays first
        self.current_state = board
        self.player_turn = 'X'

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

    # TODO: FIX WIN CONDITIONS FOR NEW GAME, this only work for 3x3 no blocs
    def is_end(self):
        # Vertical win
        for i in range(0, 3):
            if (self.current_state[0][i] != '.' and
                    self.current_state[0][i] == self.current_state[1][i] and
                    self.current_state[1][i] == self.current_state[2][i]):
                return self.current_state[0][i]
        # Horizontal win
        for y in range(self.n):
            if self.current_state[y] == ['X' for x in range(self.n)]:
                return 'X'
            elif self.current_state[y] == ['O' for x in range(self.n)]:
                return 'O'
        # Main diagonal win
        if (self.current_state[0][0] != '.' and
                self.current_state[0][0] == self.current_state[1][1] and
                self.current_state[0][0] == self.current_state[2][2]):
            return self.current_state[0][0]
        # Second diagonal win
        if (self.current_state[0][2] != '.' and
                self.current_state[0][2] == self.current_state[1][1] and
                self.current_state[0][2] == self.current_state[2][0]):
            return self.current_state[0][2]
        # Is whole board full?
        for i in range(self.n):
            for j in range(self.n):
                # There's an empty field, we continue the game
                if (self.current_state[i][j] == '.'):
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

    def minimax(self, max=False):
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
        for i in range(self.n):
            for j in range(self.n):
                if self.current_state[i][j] == '.':
                    if max:
                        self.current_state[i][j] = 'O'
                        (v, _, _) = self.minimax(max=False)
                        if v > value:
                            value = v
                            x = i
                            y = j
                    else:
                        self.current_state[i][j] = 'X'
                        (v, _, _) = self.minimax(max=True)
                        if v < value:
                            value = v
                            x = i
                            y = j
                    self.current_state[i][j] = '.'
        return (value, x, y)

    def alphabeta(self, alpha=-2, beta=2, max=False):
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
        for i in range(self.n):
            for j in range(self.n):
                if self.current_state[i][j] == '.':
                    if max:
                        self.current_state[i][j] = 'O'
                        (v, _, _) = self.alphabeta(alpha, beta, max=False)
                        if v > value:
                            value = v
                            x = i
                            y = j
                    else:
                        self.current_state[i][j] = 'X'
                        (v, _, _) = self.alphabeta(alpha, beta, max=True)
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
        while True:
            self.draw_board()
            if self.check_end():
                return
            start = time.time()
            if algo == self.MINIMAX:
                if self.player_turn == 'X':
                    (_, x, y) = self.minimax(max=False)
                else:
                    (_, x, y) = self.minimax(max=True)
            else:  # algo == self.ALPHABETA
                if self.player_turn == 'X':
                    (m, x, y) = self.alphabeta(max=False)
                else:
                    (m, x, y) = self.alphabeta(max=True)
            end = time.time()
            if (self.player_turn == 'X' and player_x == self.HUMAN) or (
                    self.player_turn == 'O' and player_o == self.HUMAN):
                if self.recommend:
                    print(F'Evaluation time: {round(end - start, 7)}s')
                    print(F'Recommended move: {self.LETTERS[x]}{y}')
                (x, y) = self.input_move()
            if (self.player_turn == 'X' and player_x == self.AI) or (self.player_turn == 'O' and player_o == self.AI):
                print(F'Evaluation time: {round(end - start, 7)}s')
                if player_x == self.HUMAN or player_o == self.HUMAN:
                    print(F'Player {self.player_turn} under AI control plays: {self.LETTERS[x]}{y}')
                else:
                    print(F'Player {self.player_turn} under AI control plays: x = {x}, y = {y}')
            self.current_state[x][y] = self.player_turn
            self.switch_player()


def main():

    USAGE = 'Either run directly for default parameters: ./lineEmUp.py'
    USAGE += '\nOr with custom parameters: ./lineEmUp.py [-r] -x:[h|a] -o:[h|a] [-a:[a|m]]'

    #@TODO: add prompt to choose game type
    if len(sys.argv) == 1:
        g = Game(recommend=True)
        g.play(algo=Game.ALPHABETA, player_x=Game.AI, player_o=Game.AI)
        g.play(algo=Game.MINIMAX, player_x=Game.AI, player_o=Game.HUMAN)
    elif len(sys.argv) >= 1:
        if sys.argv[1] == '-h' or sys.argv[1] == '--help':
            print(USAGE)

        recommend = False
        args_present = [False, False, False]
        player_x = player_y = algo = None

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
            if '-a:' in arg:
                args_present[2] = True
                algo_type = arg.split(':')[1]

                if algo_type == 'a':
                    algo = Game.ALPHABETA
                elif algo_type == 'm':
                    algo = Game.MINIMAX

        if player_x == Game.HUMAN and player_o == Game.HUMAN:
            args_present[2] = True

        for present in args_present:
            if not present:
                print('Missing required parameters')
                sys.exit(0)

        g = Game(recommend=recommend)
        g.play(algo=algo, player_x=player_x, player_o=player_o)
        

if __name__ == "__main__":
    main()
