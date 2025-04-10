import pygame
import sys
import math
import random

# Initialize pygame
pygame.init()

# Constants
VIRTUAL_WIDTH, VIRTUAL_HEIGHT = 160, 144  # GameBoy resolution
SCALE = 4  # Scale factor for modern displays
SCREEN_WIDTH, SCREEN_HEIGHT = VIRTUAL_WIDTH * SCALE, VIRTUAL_HEIGHT * SCALE
FPS = 60

# GameBoy-inspired color palette with better contrast
GB_COLORS = [
    (205, 222, 135),  # Lighter green (background)
    (139, 172, 15),   # Medium green (branches)
    (48, 98, 48),     # Dark green (locations)
    (15, 56, 15)      # Darkest green (player, text)
]

# Additional colors for better visibility
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Debug mode
DEBUG = True

# Game states
STATE_OVERWORLD = 0
STATE_COMBAT = 1
STATE_COMBAT_RESULT = 2  # For showing results after combat

# Direction constants
DIR_NONE = 0
DIR_UP = 1
DIR_RIGHT = 2
DIR_DOWN = 3
DIR_LEFT = 4

# Tool constants for combat
TOOL_NET = 0
TOOL_JAR = 1
TOOL_MAGNIFIER = 2

# Bug types and vulnerabilities
BUG_TYPES = ["Spider", "Beetle", "Butterfly", "Ant", "Ladybug", "Grasshopper"]

class CombatBug:
    def __init__(self, bug_type):
        self.bug_type = bug_type
        # Randomly determine which tool this bug is vulnerable to
        self.vulnerable_to = random.randint(0, 2)  # 0: Net, 1: Jar, 2: Magnifier
        self.flash_timer = 0
        
    def update(self):
        if self.flash_timer > 0:
            self.flash_timer -= 1
            
    def draw(self, surface, x, y):
        # Draw a spider-like bug (16x16 virtual pixels)
        # Only draw if not in flash-off state
        if self.flash_timer % 10 < 5:  # Flash every 5 frames
            # Bug body
            pygame.draw.circle(surface, (60, 60, 60), (x, y), 8)
            
            # Bug legs (8 legs for spider)
            for i in range(8):
                angle = i * math.pi / 4
                leg_x = x + math.cos(angle) * 10
                leg_y = y + math.sin(angle) * 10
                pygame.draw.line(surface, (60, 60, 60), (x, y), (leg_x, leg_y), 2)
            
            # Bug eyes
            pygame.draw.circle(surface, WHITE, (x - 3, y - 3), 2)
            pygame.draw.circle(surface, WHITE, (x + 3, y - 3), 2)

class Location:
    def __init__(self, x, y, name):
        self.x = x
        self.y = y
        self.name = name
        self.visited = False
        self.completed = False
        self.bugs_caught = 0
        
    def draw(self, surface, is_selected):
        # Draw location marker (a square in virtual pixels)
        color = GB_COLORS[2] if is_selected else GB_COLORS[1]
        
        # If completed, use a different color
        if self.completed:
            color = (100, 200, 100)  # Light green for completed
        
        # Location is 8x8 virtual pixels
        rect = pygame.Rect(self.x - 4, self.y - 4, 8, 8)
        pygame.draw.rect(surface, color, rect)
        
        # Draw highlight if selected
        if is_selected:
            pygame.draw.rect(surface, WHITE, rect, 1)
            
        # Draw a small icon to indicate it's a location
        inner_rect = pygame.Rect(self.x - 2, self.y - 2, 4, 4)
        pygame.draw.rect(surface, BLACK, inner_rect)

class Branch:
    def __init__(self, start_x, start_y, end_x, end_y, parent=None):
        # All coordinates are in virtual pixels
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y
        self.parent = parent
        self.children = []  # Child branches
        self.location = None  # Location at the end of this branch
        self.nodes = self.generate_nodes()
        
    def generate_nodes(self):
        # For discrete movement, we only need start and end nodes
        return [(self.start_x, self.start_y), (self.end_x, self.end_y)]
        
    def add_child(self, end_x, end_y):
        child = Branch(self.end_x, self.end_y, end_x, end_y, self)
        self.children.append(child)
        return child
        
    def add_location(self, name):
        self.location = Location(self.end_x, self.end_y, name)
        return self.location
        
    def draw(self, surface):
        # Draw the branch as a line (in virtual pixels)
        pygame.draw.line(surface, GB_COLORS[1], 
                        (self.start_x, self.start_y),
                        (self.end_x, self.end_y), 2)
        
        # Draw node points at start and end for clarity - make them more visible
        pygame.draw.circle(surface, GB_COLORS[2], 
                          (self.start_x, self.start_y), 4)
        pygame.draw.circle(surface, GB_COLORS[2], 
                          (self.end_x, self.end_y), 4)
        
        # Add white outline to nodes for better visibility
        pygame.draw.circle(surface, WHITE, 
                          (self.start_x, self.start_y), 4, 1)
        pygame.draw.circle(surface, WHITE, 
                          (self.end_x, self.end_y), 4, 1)
        
        # Draw location if it exists
        if self.location:
            self.location.draw(surface, False)
            
        # Draw child branches
        for child in self.children:
            child.draw(surface)

class Player:
    def __init__(self, x, y):
        # Coordinates in virtual pixels
        self.x = x
        self.y = y
        self.current_branch = None
        self.node_index = 0
        self.selected_location = None
        self.move_cooldown = 0
        self.flash_timer = 0  # For movement feedback
        
        # Load character sprites directly
        self.overworld_sprite = pygame.image.load('character-sprite-16px.png')
        self.combat_sprite = pygame.image.load('character-sprite-32px.png')
        
    def set_branch(self, branch, node_index=0):
        self.current_branch = branch
        self.node_index = node_index
        if node_index < len(branch.nodes):
            self.x, self.y = branch.nodes[node_index]
        
    def move(self, direction):
        if self.move_cooldown > 0:
            return False
            
        if not self.current_branch:
            return False
            
        # Get direction name for debugging
        direction_names = {DIR_UP: "UP", DIR_RIGHT: "RIGHT", DIR_DOWN: "DOWN", DIR_LEFT: "LEFT"}
        direction_name = direction_names.get(direction, "UNKNOWN")
        
        # For discrete movement, we only have 2 nodes per branch (start and end)
        # Moving along current branch - jump directly to end
        if direction == DIR_RIGHT and self.node_index == 0:
            self.node_index = 1  # Jump to end node
            self.x, self.y = self.current_branch.nodes[self.node_index]
            self.move_cooldown = 15  # Slightly longer cooldown for visual feedback
            self.flash_timer = 5  # Visual feedback when moving
            print(f"Moving {direction_name} to end of current branch")
            return True
            
        # Moving back - jump directly to start
        if direction == DIR_LEFT and self.node_index == 1:
            self.node_index = 0  # Jump to start node
            self.x, self.y = self.current_branch.nodes[self.node_index]
            self.move_cooldown = 15
            self.flash_timer = 5
            print(f"Moving {direction_name} to start of current branch")
            return True
            
        # At the end node, check for up/down branches
        if self.node_index == 1:
            # Check for child branches
            for child in self.current_branch.children:
                if direction == DIR_UP and child.end_y < child.start_y:
                    print(f"Moving {direction_name} to upward branch")
                    self.set_branch(child, 0)  # Start at beginning of child branch
                    self.move_cooldown = 15
                    self.flash_timer = 5
                    return True
                elif direction == DIR_DOWN and child.end_y > child.start_y:
                    print(f"Moving {direction_name} to downward branch")
                    self.set_branch(child, 0)  # Start at beginning of child branch
                    self.move_cooldown = 15
                    self.flash_timer = 5
                    return True
                    
            # Check for horizontal continuation
            if direction == DIR_RIGHT:
                # Check if current location has been visited before continuing
                if self.current_branch.location and not self.current_branch.location.visited:
                    print(f"Must complete location '{self.current_branch.location.name}' before continuing!")
                    return False
                    
                for child in self.current_branch.children:
                    # If there's a child branch that continues horizontally
                    if abs(child.end_y - self.current_branch.end_y) < 5:  # Roughly horizontal
                        print(f"Moving {direction_name} to next horizontal branch")
                        self.set_branch(child, 0)  # Start at beginning of next branch
                        self.move_cooldown = 15
                        self.flash_timer = 5
                        return True
                    
        # Check if we can go back to parent branch
        if direction == DIR_LEFT and self.node_index == 0 and self.current_branch.parent:
            parent = self.current_branch.parent
            print(f"Moving {direction_name} back to parent branch")
            # Go to the end of the parent branch
            self.set_branch(parent, 1)
            self.move_cooldown = 15
            self.flash_timer = 5
            return True
                    
        print(f"Cannot move {direction_name} from current position")
        return False
        
    def update(self):
        if self.move_cooldown > 0:
            self.move_cooldown -= 1
            
        if self.flash_timer > 0:
            self.flash_timer -= 1
            
        # Check if at a location
        if (self.current_branch and 
            self.node_index == 1 and  # End node (index 1)
            self.current_branch.location):
            self.selected_location = self.current_branch.location
        else:
            self.selected_location = None
            
    def draw(self, surface):
        # Draw player as a 16x16 virtual pixel character sprite
        player_rect = pygame.Rect(self.x - 8, self.y - 8, 16, 16)
        
        # Use flash effect when moving
        if self.flash_timer > 0:
            # Flash effect - draw a white rectangle
            pygame.draw.rect(surface, WHITE, player_rect)
        else:
            # Draw the sprite
            surface.blit(self.overworld_sprite, (self.x - 8, self.y - 8))
        
        # If at a location that's not completed, draw exclamation mark above character
        if self.selected_location and not self.selected_location.completed:
            # Draw exclamation mark (!) - positioned above the larger sprite
            pygame.draw.rect(surface, WHITE, (self.x - 1, self.y - 14, 2, 4))  # Vertical line
            pygame.draw.rect(surface, WHITE, (self.x - 1, self.y - 9, 2, 2))   # Dot
            
            # Highlight selected location
            self.selected_location.draw(surface, True)
        elif self.selected_location:
            # Just highlight the location without exclamation mark
            self.selected_location.draw(surface, True)
            
    def draw_combat(self, surface, x, y):
        # Draw player as a 32x32 virtual pixel character sprite for combat mode
        player_rect = pygame.Rect(x - 16, y - 16, 32, 32)
        
        # Draw the sprite
        surface.blit(self.combat_sprite, (x - 16, y - 16))

class Game:
    def __init__(self):
        # Set up the display
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.virtual_screen = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        pygame.display.set_caption("BugBout")
        
        self.clock = pygame.time.Clock()
        self.state = STATE_OVERWORLD
        
        # Create the tree structure
        self.create_world()
        
        # Create player
        self.player = Player(20, VIRTUAL_HEIGHT // 2)
        self.player.set_branch(self.root_branch)
        
        # Combat variables
        self.combat_bugs = []
        self.current_bug_index = 0
        self.selected_tool = TOOL_NET  # Default to net
        self.combat_message = ""
        self.combat_attempts = 0
        self.bugs_caught_session = 0
        self.total_bugs_caught = 0
        self.combat_animation_timer = 0
        self.player_x_pos = -20  # Start off-screen for slide-in animation
        
    def create_world(self):
        # Create a simpler tree structure for better visibility and testing
        center_y = VIRTUAL_HEIGHT // 2
        
        # Create the main branch (horizontal line) with tutorial location
        self.root_branch = Branch(20, center_y, 60, center_y)
        # Add tutorial location at the end of the first branch
        self.root_branch.add_location("Tutorial")
        print("Created Tutorial location at the start")
        
        # Add a fork with up and down branches
        fork1 = self.root_branch.add_child(80, center_y)
        
        # Up branch from fork1 - make it more visible
        up_branch1 = fork1.add_child(100, center_y - 25)
        up_branch1.add_location("Forest")
        
        # Down branch from fork1 - make it more visible
        down_branch1 = fork1.add_child(100, center_y + 25)
        down_branch1.add_location("Pond")
        
        # Continue main branch
        fork2 = fork1.add_child(120, center_y)
        
        # Up branch from fork2
        up_branch2 = fork2.add_child(140, center_y - 25)
        up_branch2.add_location("Mountain")
        
        # Down branch from fork2
        down_branch2 = fork2.add_child(140, center_y + 25)
        down_branch2.add_location("Cave")
        
    def initialize_combat(self):
        # Reset combat variables
        self.combat_bugs = []
        self.current_bug_index = 0
        self.selected_tool = TOOL_NET
        self.combat_message = "Select a tool and press X to attack"
        self.combat_attempts = 0
        self.bugs_caught_session = 0
        self.combat_animation_timer = 60  # 1 second for initial animation
        self.player_x_pos = -20  # Start off-screen
        
        # Generate 6 random bugs
        for i in range(6):
            bug_type = random.choice(BUG_TYPES)
            self.combat_bugs.append(CombatBug(bug_type))
            
        # Set the first bug to flash
        self.combat_bugs[0].flash_timer = 30
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.KEYDOWN:
                if self.state == STATE_OVERWORLD:
                    if event.key == pygame.K_UP:
                        self.player.move(DIR_UP)
                    elif event.key == pygame.K_DOWN:
                        self.player.move(DIR_DOWN)
                    elif event.key == pygame.K_LEFT:
                        self.player.move(DIR_LEFT)
                    elif event.key == pygame.K_RIGHT:
                        self.player.move(DIR_RIGHT)
                    elif event.key == pygame.K_x:
                        # Enter location if at one
                        if self.player.selected_location:
                            location_name = self.player.selected_location.name
                            print(f"Entering location: {location_name}")
                            print("Transitioning to combat mode")
                            self.state = STATE_COMBAT
                            # Mark location as visited
                            self.player.selected_location.visited = True
                            # Initialize combat
                            self.initialize_combat()
                        else:
                            print("No location selected to enter")
                    
                elif self.state == STATE_COMBAT:
                    # Only allow input after animation is complete
                    if self.combat_animation_timer <= 0:
                        if event.key == pygame.K_LEFT:
                            # Cycle tools left
                            self.selected_tool = (self.selected_tool - 1) % 3
                            print(f"Selected tool: {['Net', 'Jar', 'Magnifier'][self.selected_tool]}")
                        elif event.key == pygame.K_RIGHT:
                            # Cycle tools right
                            self.selected_tool = (self.selected_tool + 1) % 3
                            print(f"Selected tool: {['Net', 'Jar', 'Magnifier'][self.selected_tool]}")
                        elif event.key == pygame.K_x:
                            # Attack with selected tool
                            self.attack_bug()
                
                elif self.state == STATE_COMBAT_RESULT:
                    if event.key == pygame.K_x:
                        # Return to overworld and mark location as completed
                        print("Returning to overworld")
                        self.state = STATE_OVERWORLD
                        if self.player.selected_location:
                            self.player.selected_location.completed = True
                            self.player.selected_location.bugs_caught = self.bugs_caught_session
                            self.total_bugs_caught += self.bugs_caught_session
                
    def attack_bug(self):
        current_bug = self.combat_bugs[self.current_bug_index]
        
        # Check if the selected tool is effective against this bug
        if self.selected_tool == current_bug.vulnerable_to:
            # Success!
            self.combat_message = "Success!"
            self.bugs_caught_session += 1
            self.combat_attempts = 0
            
            # Move to next bug or end combat
            self.current_bug_index += 1
            if self.current_bug_index >= len(self.combat_bugs):
                # End of combat
                self.state = STATE_COMBAT_RESULT
            else:
                # Set the next bug to flash
                self.combat_bugs[self.current_bug_index].flash_timer = 30
        else:
            # Failure
            self.combat_message = "Failure! Try again."
            self.combat_attempts += 1
            
            # If second failure, move to next bug
            if self.combat_attempts >= 2:
                self.combat_attempts = 0
                self.current_bug_index += 1
                if self.current_bug_index >= len(self.combat_bugs):
                    # End of combat
                    self.state = STATE_COMBAT_RESULT
                else:
                    # Set the next bug to flash
                    self.combat_bugs[self.current_bug_index].flash_timer = 30
    
    def update(self):
        if self.state == STATE_OVERWORLD:
            self.player.update()
            
        elif self.state == STATE_COMBAT:
            # Update combat animations
            if self.combat_animation_timer > 0:
                self.combat_animation_timer -= 1
                
                # Slide in player character
                if self.player_x_pos < 40:  # Target position
                    self.player_x_pos += 2
                    
            # Update current bug
            if self.current_bug_index < len(self.combat_bugs):
                self.combat_bugs[self.current_bug_index].update()
            
    def draw(self):
        # Clear the virtual screen
        self.virtual_screen.fill(GB_COLORS[0])
        
        if self.state == STATE_OVERWORLD:
            # Draw the world tree
            self.root_branch.draw(self.virtual_screen)
            
            # Draw the player
            self.player.draw(self.virtual_screen)
            
            # Draw UI elements
            self.draw_text("BugBout", 5, 5, size=12)
            
            # Draw total bugs caught
            self.draw_text(f"Total Bugs: {self.total_bugs_caught}", VIRTUAL_WIDTH - 80, 5, size=10)
            
            # Draw controls help
            self.draw_text("Controls: Arrow Keys, X to enter, Z to back", 5, VIRTUAL_HEIGHT - 30, size=8)
            
            # Draw location name if selected
            if self.player.selected_location:
                self.draw_text(f"Location: {self.player.selected_location.name}", 
                              5, VIRTUAL_HEIGHT - 20, size=8)
                self.draw_text("Press X to enter", 5, VIRTUAL_HEIGHT - 10, size=8)
            
            # Debug information
            if DEBUG:
                if self.player.current_branch:
                    self.draw_text(f"Pos: ({self.player.x}, {self.player.y})", 
                                  VIRTUAL_WIDTH - 80, 20, size=8)
                    self.draw_text(f"Node: {self.player.node_index}/{len(self.player.current_branch.nodes)-1}", 
                                  VIRTUAL_WIDTH - 80, 30, size=8)
                    
                # Debug node information
                if self.player.current_branch:
                    self.draw_text("Node-based movement: Use arrow keys", 
                                  VIRTUAL_WIDTH // 2 - 80, VIRTUAL_HEIGHT - 40, size=8)
            
        elif self.state == STATE_COMBAT:
            # Combat screen with quadrants
            self.virtual_screen.fill(GB_COLORS[0])
            
            # Draw quadrant dividers
            pygame.draw.line(self.virtual_screen, WHITE, 
                            (VIRTUAL_WIDTH // 2, 0), 
                            (VIRTUAL_WIDTH // 2, VIRTUAL_HEIGHT), 1)
            pygame.draw.line(self.virtual_screen, WHITE, 
                            (0, VIRTUAL_HEIGHT // 2), 
                            (VIRTUAL_WIDTH, VIRTUAL_HEIGHT // 2), 1)
            
            # Upper left quadrant - Tool diagram
            self.draw_tool_diagram()
            
            # Upper right quadrant - Bug
            if self.current_bug_index < len(self.combat_bugs):
                bug_x = VIRTUAL_WIDTH * 3 // 4
                bug_y = VIRTUAL_HEIGHT // 4
                self.combat_bugs[self.current_bug_index].draw(self.virtual_screen, bug_x, bug_y)
                
                # Draw bug type
                self.draw_text(f"Bug: {self.combat_bugs[self.current_bug_index].bug_type}", 
                              bug_x, bug_y - 20, size=8, align="center")
            
            # Lower left quadrant - Player character
            self.player.draw_combat(self.virtual_screen, self.player_x_pos, VIRTUAL_HEIGHT * 3 // 4)
            
            # Lower right quadrant - Message area
            message_x = VIRTUAL_WIDTH * 3 // 4
            message_y = VIRTUAL_HEIGHT * 3 // 4
            self.draw_text(self.combat_message, message_x, message_y, size=8, align="center")
            
            # Draw progress
            self.draw_text(f"Bug {self.current_bug_index + 1}/6", 
                          VIRTUAL_WIDTH - 40, 5, size=8)
            self.draw_text(f"Caught: {self.bugs_caught_session}", 
                          VIRTUAL_WIDTH - 40, 15, size=8)
                          
        elif self.state == STATE_COMBAT_RESULT:
            # Result screen
            self.virtual_screen.fill(GB_COLORS[2])
            
            # Draw a border
            pygame.draw.rect(self.virtual_screen, WHITE, 
                            pygame.Rect(10, 10, VIRTUAL_WIDTH - 20, VIRTUAL_HEIGHT - 20), 2)
            
            # Draw results
            self.draw_text("Combat Complete!", VIRTUAL_WIDTH // 2, 40, size=12, align="center")
            self.draw_text(f"You caught {self.bugs_caught_session} bugs!", 
                          VIRTUAL_WIDTH // 2, VIRTUAL_HEIGHT // 2, size=10, align="center")
            
            # Draw instructions
            self.draw_text("Press X to return to overworld", 
                          VIRTUAL_WIDTH // 2, VIRTUAL_HEIGHT - 30, size=8, align="center")
            
        # Scale the virtual screen to the actual screen
        scaled_screen = pygame.transform.scale(self.virtual_screen, (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.screen.blit(scaled_screen, (0, 0))
        
        pygame.display.flip()
        
    def draw_text(self, text, x, y, size=8, align="left"):
        # Improved text rendering with adjustable size and alignment
        font = pygame.font.SysFont('Arial', size)
        text_surface = font.render(text, True, GB_COLORS[3])
        text_rect = text_surface.get_rect()
        
        if align == "center":
            text_rect.center = (x, y)
        elif align == "right":
            text_rect.topright = (x, y)
        else:  # left
            text_rect.topleft = (x, y)
            
        self.virtual_screen.blit(text_surface, text_rect)
        
    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

    def draw_tool_diagram(self):
        # Draw tools in a triangle formation in the upper left quadrant
        center_x = VIRTUAL_WIDTH // 4
        center_y = VIRTUAL_HEIGHT // 4
        radius = 20
        
        # Calculate tool positions
        net_pos = (center_x, center_y - radius)  # Top
        jar_pos = (center_x + radius * 0.866, center_y + radius * 0.5)  # Bottom right
        mag_pos = (center_x - radius * 0.866, center_y + radius * 0.5)  # Bottom left
        
        # Draw triangle connecting tools
        pygame.draw.line(self.virtual_screen, WHITE, net_pos, jar_pos, 1)
        pygame.draw.line(self.virtual_screen, WHITE, jar_pos, mag_pos, 1)
        pygame.draw.line(self.virtual_screen, WHITE, mag_pos, net_pos, 1)
        
        # Draw arrows
        # Net to Jar
        self.draw_arrow(net_pos, jar_pos)
        # Jar to Magnifier
        self.draw_arrow(jar_pos, mag_pos)
        # Magnifier to Net
        self.draw_arrow(mag_pos, net_pos)
        
        # Draw tools
        self.draw_tool(TOOL_NET, net_pos[0], net_pos[1], self.selected_tool == TOOL_NET)
        self.draw_tool(TOOL_JAR, jar_pos[0], jar_pos[1], self.selected_tool == TOOL_JAR)
        self.draw_tool(TOOL_MAGNIFIER, mag_pos[0], mag_pos[1], self.selected_tool == TOOL_MAGNIFIER)
        
        # Draw tool names
        self.draw_text("Net", net_pos[0], net_pos[1] - 10, size=8, align="center")
        self.draw_text("Jar", jar_pos[0], jar_pos[1] + 10, size=8, align="center")
        self.draw_text("Magnifier", mag_pos[0], mag_pos[1] + 10, size=8, align="center")
        
    def draw_tool(self, tool_type, x, y, selected=False):
        # Draw a tool icon
        if tool_type == TOOL_NET:
            # Draw net
            pygame.draw.circle(self.virtual_screen, WHITE, (x, y), 6, 1)
            pygame.draw.line(self.virtual_screen, WHITE, (x, y), (x, y + 8), 1)
        elif tool_type == TOOL_JAR:
            # Draw jar
            pygame.draw.rect(self.virtual_screen, WHITE, (x - 3, y - 4, 6, 8), 1)
            pygame.draw.line(self.virtual_screen, WHITE, (x - 3, y - 4), (x + 3, y - 4), 1)
        else:  # TOOL_MAGNIFIER
            # Draw magnifying glass
            pygame.draw.circle(self.virtual_screen, WHITE, (x, y), 4, 1)
            pygame.draw.line(self.virtual_screen, WHITE, (x + 3, y + 3), (x + 6, y + 6), 1)
            
        # Draw selection outline if selected
        if selected:
            pygame.draw.circle(self.virtual_screen, (255, 255, 0), (x, y), 8, 1)
            
    def draw_arrow(self, start, end):
        # Draw an arrow from start to end
        # Calculate midpoint
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2
        
        # Draw arrowhead at midpoint
        pygame.draw.circle(self.virtual_screen, WHITE, (int(mid_x), int(mid_y)), 2)

# Start the game
if __name__ == "__main__":
    print("Starting BugBout game...")
    print("Tutorial: Use arrow keys to navigate, X to enter locations, Z to return")
    game = Game()
    game.run()
