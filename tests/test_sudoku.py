"""
Pytest tests for the Sudoku Solver.
"""

import pytest
from sudoku.solver import Sudoku, SudokuBoard, Cell, CellState


class TestCell:
    def test_cell_initialization(self):
        cell = Cell(0, 0, None, CellState.EMPTY)
        assert cell.row == 0
        assert cell.col == 0
        assert cell.value is None
        assert cell.state == CellState.EMPTY

    def test_cell_filled(self):
        cell = Cell(1, 1, 5, CellState.FILLED)
        assert cell.value == 5
        assert cell.state == CellState.FILLED


class TestSudokuBoard:
    def test_empty_board(self):
        board = SudokuBoard()
        assert len(board.board) == 9
        assert all(len(row) == 9 for row in board.board)
        assert all(cell is None for row in board.board for cell in row)

    def test_board_with_values(self):
        initial = [
            [1, 2, 3, 4, 5, 6, 7, 8, 9],
            [9, 8, 7, 6, 5, 4, 3, 2, 1],
            [7, 6, 5, 3, 2, 1, 9, 8, 4],
            [5, 4, 3, 9, 8, 7, 1, 2, 6],
            [3, 2, 1, 7, 6, 9, 5, 4, 8],
            [1, 9, 8, 5, 4, 3, 6, 7, 2],
            [4, 8, 9, 2, 1, 6, 7, 3, 5],
            [6, 7, 2, 8, 3, 5, 4, 9, 1],
            [2, 3, 6, 1, 9, 8, 5, 1, 3], # Note: This row has duplicates, will fail validation
        ]
        with pytest.raises(ValueError, match="Values must be between 1 and 9"):
            SudokuBoard(initial)

    def test_board_with_valid_values(self):
        initial = [
            [1, 2, 3, 4, 5, 6, 7, 8, 9],
            [9, 8, 7, 6, 5, 4, 3, 2, 1],
            [7, 6, 5, 3, 2, 1, 9, 8, 4],
            [5, 4, 3, 9, 8, 7, 1, 2, 6],
            [3, 2, 1, 7, 6, 9, 5, 4, 8],
            [1, 9, 8, 5, 4, 3, 6, 7, 2],
            [4, 8, 9, 2, 1, 6, 7, 3, 5],
            [6, 7, 2, 8, 3, 5, 4, 9, 1],
            [2, 3, 6, 1, 9, 8, 5, 1, 3], # Note: This row has duplicates, will fail validation
        ]
        # Correcting the last row for valid test
        initial[8] = [2, 3, 6, 1, 9, 8, 5, 1, 3] # Still invalid, let's fix manually for test
        initial[8] = [2, 3, 6, 1, 9, 8, 5, 1, 3] # Wait, 1 and 3 are duplicated. Let's just make a simple valid one.
        initial = [
            [5, 3, 4, 6, 7, 8, 9, 1, 2],
            [6, 7, 2, 1, 9, 5, 3, 4, 8],
            [1, 9, 8, 3, 4, 2, 5, 6, 7],
            [8, 5, 9, 7, 6, 1, 4, 2, 3],
            [4, 2, 6, 8, 5, 3, 7, 9, 1],
            [7, 1, 3, 9, 2, 4, 8, 5, 6],
            [9, 6, 1, 5, 3, 7, 2, 8, 4],
            [2, 8, 7, 4, 1, 9, 6, 3, 5],
            [3, 4, 5, 2, 8, 6, 1, 7, 9],
        ]
        board = SudokuBoard(initial)
        assert board.is_valid()

    def test_is_valid_with_conflict(self):
        initial = [
            [1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 2, 3, 4, 5, 6, 7, 8, 9], # Duplicate row
            [7, 6, 5, 3, 2, 1, 9, 8, 4],
            [5, 4, 3, 9, 8, 7, 1, 2, 6],
            [3, 2, 1, 7, 6, 9, 5, 4, 8],
            [1, 9, 8, 5, 4, 3, 6, 7, 2],
            [4, 8, 9, 2, 1, 6, 7, 3, 5],
            [6, 7, 2, 8, 3, 5, 4, 9, 1],
            [2, 3, 6, 1, 9, 8, 5, 1, 3],
        ]
        board = SudokuBoard(initial)
        assert not board.is_valid()


class TestSudoku:
    def test_solve_empty(self):
        sudoku = Sudoku()
        assert not sudoku.solve()
        assert not sudoku.is_solved()

    def test_solve_valid(self):
        initial = [
            [5, 3, 4, 6, 7, 8, 9, 1, 2],
            [6, 7, 2, 1, 9, 5, 3, 4, 8],
            [1, 9, 8, 3, 4, 2, 5, 6, 7],
            [8, 5, 9, 7, 6, 1, 4, 2, 3],
            [4, 2, 6, 8, 5, 3, 7, 9, 1],
            [7, 1, 3, 9, 2, 4, 8, 5, 6],
            [9, 6, 1, 5, 3, 7, 2, 8, 4],
            [2, 8, 7, 4, 1, 9, 6, 3, 5],
            [3, 4, 5, 2, 8, 6, 1, 7, 9],
        ]
        sudoku = Sudoku(initial)
        assert sudoku.solve()
        assert sudoku.is_solved()
        solution = sudoku.get_solution()
        assert solution is not None
        assert len(solution) == 9
        assert all(len(row) == 9 for row in solution)

    def test_solve_partial(self):
        # A simple partial board
        initial = [
            [5, 3, 0, 0, 7, 0, 0, 0, 0],
            [6, 0, 0, 1, 9, 5, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],
            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],
            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9],
        ]
        sudoku = Sudoku(initial)
        assert sudoku.solve()
        assert sudoku.is_solved()

    def test_get_solution_without_solve(self):
        initial = [
            [5, 3, 4, 6, 7, 8, 9, 1, 2],
            [6, 7, 2, 1, 9, 5, 3, 4, 8],
            [1, 9, 8, 3, 4, 2, 5, 6, 7],
            [8, 5, 9, 7, 6, 1, 4, 2, 3],
            [4, 2, 6, 8, 5, 3, 7, 9, 1],
            [7, 1, 3, 9, 2, 4, 8, 5, 6],
            [9, 6, 1, 5, 3, 7, 2, 8, 4],
            [2, 8, 7, 4, 1, 9, 6, 3, 5],
            [3, 4, 5, 2, 8, 6, 1, 7, 9],
        ]
        sudoku = Sudoku(initial)
        # get_solution calls solve internally if needed
        solution = sudoku.get_solution()
        assert solution is not None
        assert solution == initial

    def test_invalid_board_creation(self):
        with pytest.raises(ValueError):
            Sudoku([1, 2, 3])  # Wrong dimensions
        with pytest.raises(ValueError):
            Sudoku([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]])  # Wrong row length
        with pytest.raises(ValueError):
            Sudoku([[1, 2, 3, 4, 5, 6, 7, 8, 0]])  # Invalid value (0)
        with pytest.raises(ValueError):
            Sudoku([[1, 2, 3, 4, 5, 6, 7, 8, 10]])  # Invalid value (>9)
