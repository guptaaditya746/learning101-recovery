"""
Modular Sudoku Solver using Backtracking.
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class CellState(Enum):
    EMPTY = 0
    FILLED = 1


@dataclass
class Cell:
    row: int
    col: int
    value: Optional[int]
    state: CellState

    def __post_init__(self):
        if self.state == CellState.EMPTY:
            self.value = None

    def is_valid(self, board: 'SudokuBoard') -> bool:
        """Check if placing this value in this cell is valid."""
        if self.value is None:
            return True

        # Check row
        if self.value in [board.board[self.row][c] for c in range(9) if board.board[self.row][c] is not None]:
            return False

        # Check column
        if self.value in [board.board[r][self.col] for r in range(9) if board.board[r][self.col] is not None]:
            return False

        # Check 3x3 box
        box_row = self.row // 3
        box_col = self.col // 3
        start_row = box_row * 3
        start_col = box_col * 3

        for r in range(start_row, start_row + 3):
            for c in range(start_col, start_col + 3):
                if board.board[r][c] is not None and board.board[r][c] == self.value:
                    return False

        return True


class SudokuBoard:
    def __init__(self, initial_state: Optional[List[List[Optional[int]]]] = None):
        self.board: List[List[Optional[int]]] = []
        self.solutions: List[List[List[Optional[int]]]] = []
        self._parse(initial_state)

    def _parse(self, initial_state: Optional[List[List[Optional[int]]]] = None):
        if initial_state is None:
            # Create empty board
            self.board = [[None for _ in range(9)] for _ in range(9)]
        else:
            # Validate and set board
            if len(initial_state) != 9:
                raise ValueError("Board must be 9x9")
            for row in initial_state:
                if len(row) != 9:
                    raise ValueError("Each row must have 9 elements")
                for val in row:
                    if val is not None and not (1 <= val <= 9):
                        raise ValueError("Values must be between 1 and 9")
            self.board = [list(row) for row in initial_state]

    def is_valid(self) -> bool:
        """Check if the current board state is valid (no conflicts)."""
        for r in range(9):
            for c in range(9):
                if self.board[r][c] is not None:
                    if not self.board[r][c].is_valid(self):
                        return False
        return True

    def solve(self) -> bool:
        """
        Solve the Sudoku using backtracking.
        Returns True if a solution is found, False otherwise.
        """
        for solution in self._backtrack():
            self.solutions.append(solution)
        return len(self.solutions) > 0

    def _backtrack(self) -> List[List[int]]:
        """Internal recursive backtracking solver."""
        # Find the next empty cell
        empty_cells = []
        for r in range(9):
            for c in range(9):
                if self.board[r][c] is None:
                    empty_cells.append((r, c))
                    break
            else:
                continue
            break

        if not empty_cells:
            # No empty cells left, solution found
            return [row[:] for row in self.board]

        for r, c in empty_cells:
            for val in range(1, 10):
                cell = Cell(r, c, val, CellState.FILLED)
                if cell.is_valid(self):
                    self.board[r][c] = val
                    result = self._backtrack()
                    if result:
                        return result
                    self.board[r][c] = None
        return []

    def get_solution(self) -> Optional[List[List[int]]]:
        """Get the first found solution."""
        if not self.solutions:
            self.solve()
        return self.solutions[0] if self.solutions else None

    def __str__(self):
        lines = []
        for row in self.board:
            line = ""
            for val in row:
                if val is None:
                    line += ". "
                else:
                    line += f"{val} "
            lines.append(line)
        return "\n".join(lines)


class Sudoku:
    """High-level Sudoku interface."""

    def __init__(self, initial_state: Optional[List[List[Optional[int]]]] = None):
        self.board = SudokuBoard(initial_state)

    def solve(self) -> bool:
        return self.board.solve()

    def get_solution(self) -> Optional[List[List[int]]]:
        return self.board.get_solution()

    def is_solved(self) -> bool:
        return len(self.board.solutions) > 0

    def __str__(self):
        return str(self.board)
