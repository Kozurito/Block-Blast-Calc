# Block Blast Calc by Kozurito
import pygame
import sys
import copy
import itertools

# Initialize pygame
pygame.init()

# Constants
GRID_SIZE = 8
CELL_SIZE = 50
MAX_BLOCK_SIZE = 5
SCREEN_WIDTH = CELL_SIZE * GRID_SIZE + 200
SCREEN_HEIGHT = CELL_SIZE * GRID_SIZE + 500
BLOCK_COLORS = (255, 100, 100)
GRID_COLOR = (50, 50, 50)
FILLED_COLOR = (100, 100, 255)
HIGHLIGHT_COLOR = (255, 255, 100)
CURRENT_BLOCK_COLOR = (255, 100, 100)

# Initialize screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Block Blast Calc")

# Initialize grid and blocks
grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
blocks = []
phase = "map"
current_grid = []
num_blocks = 0
current_block_width = 0
current_block_height = 0
block_index = 0
user_input = ''
best_moves_sequence = []
current_move_index = -1

# Functions
def draw_grid(surface, grid, grid_width, grid_height, offset_x=0, offset_y=0, highlight_rows=None, highlight_cols=None):
    "Draw the grid"
    if highlight_rows is None:
        highlight_rows = []
    if highlight_cols is None:
        highlight_cols = []

    for x in range(grid_width):
        for y in range(grid_height):
            rect = pygame.Rect((x + offset_x) * CELL_SIZE, (y + offset_y) * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            color = GRID_COLOR
            if y in highlight_rows or x in highlight_cols: # Highlight the row or column
                color = HIGHLIGHT_COLOR
            pygame.draw.rect(surface, color, rect, 1)
            if grid[y][x] == 1: # Draw a filled cell if the grid value is 1
                pygame.draw.rect(surface, FILLED_COLOR, rect)

def draw_blocks(surface, blocks):
    "Draw the blocks at the bottom of the screen, wrapping if necessary"
    x_offset = 20
    y_offset = GRID_SIZE * CELL_SIZE + 20
    max_width = SCREEN_WIDTH - 40 # Maximum width available for blocks

    for block in blocks:
        block_width = len(block[0]) * CELL_SIZE
        if x_offset + block_width > max_width: # Check if block goes off-screen
            x_offset = 20 # Reset x offset to the beginning of the line
            y_offset += (len(block) + 1) * CELL_SIZE + 10 # Move to the next line

        for row_index, row in enumerate(block):
            for col_index, cell in enumerate(row):
                if cell == 1:
                    rect = pygame.Rect(
                        x_offset + col_index * CELL_SIZE,
                        y_offset + row_index * CELL_SIZE,
                        CELL_SIZE,
                        CELL_SIZE,
                    )
                    pygame.draw.rect(surface, BLOCK_COLORS, rect)
        x_offset += (len(block[0]) + 1) * CELL_SIZE + 25 # Move to the right for the next block

def can_place_block(grid, block, x, y):
    "Check if a block can be placed at the given position"
    for row_index, row in enumerate(block):
        for col_index, cell in enumerate(row):
            if cell == 1:
                grid_x = x + col_index
                grid_y = y + row_index

                if (grid_x < 0 or grid_x >= GRID_SIZE or
                    grid_y < 0 or grid_y >= GRID_SIZE or
                    (grid and grid_y < GRID_SIZE and grid_x < GRID_SIZE and grid[grid_y][grid_x] == 1)): # Handle empty grid case and out of bounds after clearing
                    return False
    return True

def place_block(grid, block, x, y):
    "Place a block on the grid"
    for row_index, row in enumerate(block):
        for col_index, cell in enumerate(row):
            if cell == 1:
                grid[y + row_index][x + col_index] = 1

def clear_lines(grid):
    "Clear filled lines (rows and columns) in-place"
    rows_to_clear = []
    cols_to_clear = []

    # Identify rows to clear
    for y in range(GRID_SIZE):
        if all(grid[y][x] == 1 for x in range(GRID_SIZE)):
            rows_to_clear.append(y)

    # Identify columns to clear
    for x in range(GRID_SIZE):
        if all(grid[y][x] == 1 for y in range(GRID_SIZE)):
            cols_to_clear.append(x)

    # Clear rows (set to 0)
    for y in rows_to_clear:
        for x in range(GRID_SIZE):
            grid[y][x] = 0

    # Clear columns (set to 0)
    for x in cols_to_clear:
        for y in range(GRID_SIZE):
            grid[y][x] = 0

    return len(rows_to_clear) + len(cols_to_clear), rows_to_clear, cols_to_clear

def remove_blank_lines(grid):
    "Removes blank rows and columns to find the minimum bounding box of the blocks"

    # Handle if the user doesn't enter a block
    empty_grid = []
    if all(all(cell == 0 for cell in row) for row in grid): 
        return empty_grid

    rows_to_remove = []
    cols_to_remove = []

    # Identify rows to remove from the top
    for y in range(MAX_BLOCK_SIZE):
        if all(grid[y][x] == 0 for x in range(MAX_BLOCK_SIZE)):
            rows_to_remove.append(y)
        else:
            break

    # Identify rows to remove from the bottom
    for y in range(MAX_BLOCK_SIZE - 1, -1, -1): # Iterate in reverse
        if all(grid[y][x] == 0 for x in range(MAX_BLOCK_SIZE)):
            rows_to_remove.append(y)
        else:
            break

    # Identify columns to remove from the left
    for x in range(MAX_BLOCK_SIZE):
        if all(grid[y][x] == 0 for y in range(MAX_BLOCK_SIZE)):
            cols_to_remove.append(x)
        else:
            break
    
    # Identify columns to remove from the right
    for x in range(MAX_BLOCK_SIZE - 1, -1, -1): # Iterate in reverse
        if all(grid[y][x] == 0 for y in range(MAX_BLOCK_SIZE)):
            cols_to_remove.append(x)
        else:
            break

    # Remove rows (iterate in reverse)
    for y in sorted(rows_to_remove, reverse=True):
        del grid[y]

    # Remove columns (iterate in reverse)
    for row in grid:
        for x in sorted(cols_to_remove, reverse=True):
            del row[x]
    
    return grid
    

def find_best_placement(grid, blocks):
    "Find the best placement using recursion"

    def solve(current_grid, remaining_blocks, current_moves, current_score):
        "Recursive helper function"
        nonlocal best_score, best_move_sequence, min_remaining_units

        if not remaining_blocks: # Base case: all blocks placed
            remaining_units = sum(sum(row) for row in current_grid)
            if current_score > best_score: # Update best score and move sequence if score is higher
                best_score = current_score
                best_move_sequence = current_moves
                min_remaining_units = remaining_units
            elif current_score == best_score and remaining_units < min_remaining_units: # Update move sequence if score is the same but remaining units are less
                best_move_sequence = current_moves
                min_remaining_units = remaining_units
            return

        block = remaining_blocks[0]
        # Try placing the block in all possible positions
        for y in range(GRID_SIZE - len(block) + 1):
            for x in range(GRID_SIZE - len(block[0]) + 1):
                temp_grid = copy.deepcopy(current_grid)
                if can_place_block(temp_grid, block, x, y):
                    place_block(temp_grid, block, x, y)
                    lines_cleared, rows, cols = clear_lines(temp_grid)
                    new_moves = current_moves + [(block, x, y, lines_cleared, rows, cols)]
                    solve(temp_grid, remaining_blocks[1:], new_moves, current_score + lines_cleared) # Recursive call
    # Initialize best score and move sequence
    best_score = -1
    best_move_sequence = None
    min_remaining_units = float('inf')

    for permutation in itertools.permutations(blocks): # Generate all permutations of blocks
        solve(copy.deepcopy(grid), list(permutation), [], 0) # Start the recursive calls

    if best_move_sequence is None: # Handle no valid moves
        return 0, 0, []
    return best_score, len(best_move_sequence), best_move_sequence

def wrap_text(text, font, max_width):
    "Wrap text to fit within the max width"
    words = text.split(' ')
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + " " + word if current_line else word
        test_width, _ = font.size(test_line)
        
        if test_width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word # Start a new line with the current word

    if current_line:
        lines.append(current_line)

    return lines

def draw_next_button():
    "Draw the Next button"
    next_button_rect = pygame.Rect(GRID_SIZE * CELL_SIZE + 25, 50, 150, 50)
    pygame.draw.rect(screen, (200, 200, 200), next_button_rect)
    font = pygame.font.SysFont(None, 36)
    if phase == "done":
        text = font.render("Calculate", True, (0, 0, 0))
        screen.blit(text, (GRID_SIZE * CELL_SIZE + 45, 63))
    else:
        text = font.render("Next", True, (0, 0, 0))
        screen.blit(text, (GRID_SIZE * CELL_SIZE + 73, 63))

    return next_button_rect

def draw_again_button():
    "Draw the Show Again button"
    show_again_rect = pygame.Rect(GRID_SIZE * CELL_SIZE + 25, 125, 150, 50)

    pygame.draw.rect(screen, (200, 200, 200), show_again_rect)

    font = pygame.font.SysFont(None, 36)
    show_again_text = font.render("Show Again", True, (0, 0, 0))

    screen.blit(show_again_text, (GRID_SIZE * CELL_SIZE + 31, 138))

    return show_again_rect

def draw_back_button():
    "Draw the Back button"
    back_button_rect = pygame.Rect(GRID_SIZE * CELL_SIZE + 25, 125, 150, 50) # Positioned below Next button
    pygame.draw.rect(screen, (200, 200, 200), back_button_rect)
    font = pygame.font.SysFont(None, 36)
    text = font.render("Back", True, (0, 0, 0))
    screen.blit(text, (GRID_SIZE * CELL_SIZE + 70, 138))
    return back_button_rect

def draw_reset_button():
    "Draw the Reset button"
    reset_button_rect = pygame.Rect(GRID_SIZE * CELL_SIZE + 25, 125, 150, 50) # Positioned below Next button
    pygame.draw.rect(screen, (200, 200, 200), reset_button_rect)
    font = pygame.font.SysFont(None, 36)
    text = font.render("Reset", True, (0, 0, 0))
    screen.blit(text, (GRID_SIZE * CELL_SIZE + 66, 138))
    return reset_button_rect

# Main loop
running = True
block_grid_1 = [[0 for _ in range(MAX_BLOCK_SIZE)] for _ in range(MAX_BLOCK_SIZE)]
block_grid_2 = [[0 for _ in range(MAX_BLOCK_SIZE)] for _ in range(MAX_BLOCK_SIZE)]
block_grid_3 = [[0 for _ in range(MAX_BLOCK_SIZE)] for _ in range(MAX_BLOCK_SIZE)]
num_blocks = 0
block_index = 0
phase = "map" # Start with map input phase
user_input = '' # User input for number of blocks
font = pygame.font.SysFont(None, 32)

while running:
    screen.fill((0, 0, 0)) # Clear screen

    # Draw buttons based on the phase
    if phase == "create_block_1" or phase == "create_block_2" or phase == "create_block_3":
        back_button_rect = draw_back_button()
    if phase == "done" or phase == "cooked":
        reset_button_rect = draw_reset_button()
    
    next_button_rect = draw_next_button() # Draw Next button

    # Draw grids based on the current phase
    if phase == "map":
        draw_grid(screen, grid, GRID_SIZE, GRID_SIZE)
    # Draw the three grids for the three blocks
    elif phase == "create_block_1":
        draw_grid(screen, block_grid_1, MAX_BLOCK_SIZE, MAX_BLOCK_SIZE)
    elif phase == "create_block_2":
        draw_grid(screen, block_grid_2, MAX_BLOCK_SIZE, MAX_BLOCK_SIZE)
    elif phase == "create_block_3":
        draw_grid(screen, block_grid_3, MAX_BLOCK_SIZE, MAX_BLOCK_SIZE)

    # Phase 5: Display moves
    elif phase == "display_moves" and current_move_index == -1:
        draw_grid(screen, grid, GRID_SIZE, GRID_SIZE)
    elif phase == "display_moves" and current_move_index >= 0 and best_moves_sequence:
        grid_copy = copy.deepcopy(grid)
        highlight_rows = []
        highlight_cols = []
        total_score = 0

        # Apply moves up to the current move
        for i in range(current_move_index + 1):
            block, x, y, move_score, rows_cleared, cols_cleared = best_moves_sequence[i]
            place_block(grid_copy, block, x, y)
            lines_cleared, rows_cleared, cols_cleared = clear_lines(grid_copy)
            total_score += move_score
            if i == current_move_index: # Only highlight the current move
                highlight_rows = rows_cleared
                highlight_cols = cols_cleared

        # Draw the grid with highlights for the CURRENT move
        draw_grid(screen, grid_copy, GRID_SIZE, GRID_SIZE, highlight_rows=highlight_rows, highlight_cols=highlight_cols)

        # Draw the CURRENT block (red) on top of the grid
        block, x, y, _, _, _ = best_moves_sequence[current_move_index]
        for row_index, row in enumerate(block):
            for col_index, cell in enumerate(row):
                if cell == 1:
                    rect = pygame.Rect((x + col_index) * CELL_SIZE, (y + row_index) * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    pygame.draw.rect(screen, CURRENT_BLOCK_COLOR, rect) # Draw the block here AFTER drawing the grid

    else:
        draw_grid(screen, grid, GRID_SIZE, GRID_SIZE)
        draw_blocks(screen, blocks)

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = pygame.mouse.get_pos() # Get the mouse position
            
            # Handle Next button click
            if next_button_rect.collidepoint(mouse_x, mouse_y):
                if phase == "map":
                    phase = "create_block_1"
                elif phase == "create_block_1":
                    block_1 = remove_blank_lines(block_grid_1)
                    if block_1: # Check if the block is valid
                        blocks.append(block_1)
                        block_index += 1
                        phase = "create_block_2"
                elif phase == "create_block_2":
                    block_2 = remove_blank_lines(block_grid_2)
                    if block_2: # Check if the block is valid
                        blocks.append(block_2)
                        block_index += 1
                        phase = "create_block_3"
                elif phase == "create_block_3":
                    block_3 = remove_blank_lines(block_grid_3)
                    if block_3: # Check if the blocks are valid
                        blocks.append(block_3)
                        block_index += 1
                        phase = "done"
                elif phase == "done":
                    if current_move_index == -1:
                        best_score, best_moves, best_moves_sequence = find_best_placement(grid, blocks)
                        if best_moves_sequence: # Check if the sequence is empty
                            current_move_index = 0 # Initialize for display
                            phase = "display_moves"
                        else:
                            phase = "cooked"
                elif phase == "display_moves":
                    if current_move_index < len(best_moves_sequence) - 1:
                        current_move_index += 1
                    else:
                        show_again_rect = draw_again_button() # Draw the Show Again button
                        pygame.display.flip()
                        waiting_for_choice = True # Wait for the user to click Show Again or Next button
                        while waiting_for_choice:
                            for choice_event in pygame.event.get():
                                if choice_event.type == pygame.MOUSEBUTTONDOWN:
                                    choice_mouse_x, choice_mouse_y = pygame.mouse.get_pos()
                                    # Handle Show Again button click
                                    if show_again_rect.collidepoint(choice_mouse_x, choice_mouse_y):
                                        current_move_index = 0
                                        waiting_for_choice = False
                                        break
                                    # Handle Next button click
                                    if next_button_rect.collidepoint(choice_mouse_x, choice_mouse_y):
                                        grid = copy.deepcopy(grid_copy)
                                        blocks = []
                                        block_index = 0
                                        block_grid_1 = [[0 for _ in range(MAX_BLOCK_SIZE)] for _ in range(MAX_BLOCK_SIZE)]
                                        block_grid_2 = [[0 for _ in range(MAX_BLOCK_SIZE)] for _ in range(MAX_BLOCK_SIZE)]
                                        block_grid_3 = [[0 for _ in range(MAX_BLOCK_SIZE)] for _ in range(MAX_BLOCK_SIZE)]
                                        phase = "create_block_1"
                                        current_move_index = -1
                                        waiting_for_choice = False
                                        break
                                elif choice_event.type == pygame.QUIT:
                                    pygame.quit()
                                    sys.exit()
                        break
            
            # Handle Back button click
            if phase == "create_block_1" or phase == "create_block_2" or phase == "create_block_3":
                back_button_rect = draw_back_button()
                if back_button_rect.collidepoint(mouse_x, mouse_y):
                    if phase == "create_block_1" or phase == "create_block_2" or phase == "create_block_3":
                        if block_index < 0:
                            block_index = 0
                        if phase == "create_block_1":
                            phase = "map"
                        elif phase == "create_block_2":
                            blocks.pop() # Remove the last block
                            block_grid_1 = [[0 for _ in range(MAX_BLOCK_SIZE)] for _ in range(MAX_BLOCK_SIZE)] # Reset the previous block grid
                            block_index -= 1
                            phase = "create_block_1"
                        elif phase == "create_block_3":
                            blocks.pop() # Remove the last block
                            block_grid_2 = [[0 for _ in range(MAX_BLOCK_SIZE)] for _ in range(MAX_BLOCK_SIZE)] # Reset the previous block grid
                            block_index -= 1
                            phase = "create_block_2"

            # Handle Reset button click
            if phase == "done" or phase == "cooked":
                reset_button_rect = draw_reset_button()
                if reset_button_rect.collidepoint(mouse_x, mouse_y):
                    phase = "map"
                    blocks = []
                    block_index = 0
                    current_move_index = -1
                    grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
                    block_grid_1 = [[0 for _ in range(MAX_BLOCK_SIZE)] for _ in range(MAX_BLOCK_SIZE)]
                    block_grid_2 = [[0 for _ in range(MAX_BLOCK_SIZE)] for _ in range(MAX_BLOCK_SIZE)]
                    block_grid_3 = [[0 for _ in range(MAX_BLOCK_SIZE)] for _ in range(MAX_BLOCK_SIZE)]
                    user_input = ''

            # Phase 1: Input the map (toggle cells on the grid)
            if phase == "map":
                if mouse_x < GRID_SIZE * CELL_SIZE and mouse_y < GRID_SIZE * CELL_SIZE: # Ensure the click is within the grid bounds
                    grid_x, grid_y = mouse_x // CELL_SIZE, mouse_y // CELL_SIZE
                    grid[grid_y][grid_x] = 1 - grid[grid_y][grid_x] # Toggle state of the cell

            # Phase 2: Create block 1
            elif phase == "create_block_1":
                if mouse_x < MAX_BLOCK_SIZE * CELL_SIZE and mouse_y < MAX_BLOCK_SIZE * CELL_SIZE: # Ensure the click is within the grid bounds
                    block_grid_1_x, block_grid_1_y = mouse_x // CELL_SIZE, mouse_y // CELL_SIZE
                    block_grid_1[block_grid_1_y][block_grid_1_x] = 1 - block_grid_1[block_grid_1_y][block_grid_1_x] # Toggle state of the cell

            # Phase 3: Create block 2
            elif phase == "create_block_2":
                if mouse_x < MAX_BLOCK_SIZE * CELL_SIZE and mouse_y < MAX_BLOCK_SIZE * CELL_SIZE: # Ensure the click is within the grid bounds
                    block_grid_2_x, block_grid_2_y = mouse_x // CELL_SIZE, mouse_y // CELL_SIZE
                    block_grid_2[block_grid_2_y][block_grid_2_x] = 1 - block_grid_2[block_grid_2_y][block_grid_2_x] # Toggle state of the cell
            
            # Phase 4: Create block 3
            elif phase == "create_block_3":
                if mouse_x < MAX_BLOCK_SIZE * CELL_SIZE and mouse_y < MAX_BLOCK_SIZE * CELL_SIZE: # Ensure the click is within the grid bounds
                    block_grid_3_x, block_grid_3_y = mouse_x // CELL_SIZE, mouse_y // CELL_SIZE
                    block_grid_3[block_grid_3_y][block_grid_3_x] = 1 - block_grid_3[block_grid_3_y][block_grid_3_x] # Toggle state of the cell

    font = pygame.font.SysFont(None, 32)

    # Define the message based on the current phase
    if phase == "map":
        text = "Click to toggle map units, then click next to continue."
    elif phase == "create_block_1" or phase == "create_block_2" or phase == "create_block_3":
        text = f"Create block {block_index + 1}. Click to toggle cells."
    elif phase == "done":
        text = "Ready to calculate."
    elif phase == "display_moves":
        text = f"Displaying move {current_move_index + 1}. Click next to see the next move."
    elif phase == "cooked":
        text = "You're cooked."

    # Wrap the text so it fits within the space
    max_text_width = SCREEN_WIDTH - GRID_SIZE * CELL_SIZE - 40
    wrapped_text = wrap_text(text, font, max_text_width)

    # Display the wrapped text with padding from the bottom
    text_x = GRID_SIZE * CELL_SIZE + 20
    text_y = 200 # Adjusted space for text
    for line in wrapped_text:
        screen.blit(font.render(line, True, (255, 255, 255)), (text_x, text_y))
        text_y += 40 # Adjust spacing between lines

    # Update display
    pygame.display.flip()